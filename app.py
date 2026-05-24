"""
app.py — Affiliate Studio v8
Render: Flask webhook + Telegram Bot (polling)

FIX:
- Bot tự start khi gunicorn import module (không dựa vào __main__)
- /colab/seturl nhận GET để Colab auto-register dễ hơn
- Webhook fallback khi polling bị block
"""
import asyncio, logging, os, threading, time, tempfile, json
from pathlib import Path
from typing import Optional
import requests
from flask import Flask, jsonify, request
from telegram import (InlineKeyboardButton, InlineKeyboardMarkup, Update)
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                           ContextTypes, MessageHandler, filters)
from config import Config

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s — %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("AffiliateStudio_v8")

flask_app = Flask(__name__)

# ── Global state ─────────────────────────────────────────────────────────────
_sessions: dict = {}
_colab:    dict = {"url": Config.COLAB_WEBHOOK_URL, "auto_ping": False}
_bot_app:  Optional[Application] = None
_loop:     Optional[asyncio.AbstractEventLoop] = None

STATE_IDLE         = "idle"
STATE_WAIT_PRODUCT = "wait_product"
STATE_WAIT_INFO    = "wait_info"
STATE_WAIT_MODEL   = "wait_model"
STATE_PROCESSING   = "processing"


# ── Helpers ──────────────────────────────────────────────────────────────────
def _colab_url(): return _colab.get("url", "").rstrip("/")

def _ping():
    u = _colab_url()
    if not u: return False
    try: return requests.get(f"{u}/ping", timeout=12).status_code == 200
    except: return False

def _call(endpoint, payload, timeout=60):
    u = _colab_url()
    if not u: return {"error": "Colab chưa kết nối. Dùng /wake"}
    try:
        return requests.post(f"{u}/{endpoint}", json=payload, timeout=timeout).json()
    except requests.Timeout:
        return {"error": f"Colab timeout {timeout}s"}
    except Exception as e:
        return {"error": str(e)}

def _get_session(uid: int) -> dict:
    if uid not in _sessions:
        _sessions[uid] = {
            "state": STATE_IDLE,
            "product_photo": None,
            "product_bg_removed": None,
            "model_photo": None,
            "product_info": {},
        }
    return _sessions[uid]

def _reset_session(uid: int):
    _sessions.pop(uid, None)

def _send(uid: int, text: str, **kwargs):
    """Thread-safe send message."""
    if _bot_app and _loop:
        asyncio.run_coroutine_threadsafe(
            _bot_app.bot.send_message(uid, text, **kwargs), _loop)

def _send_photo(uid: int, photo_bytes: bytes, caption: str = ""):
    if _bot_app and _loop:
        asyncio.run_coroutine_threadsafe(
            _bot_app.bot.send_photo(uid, photo=photo_bytes, caption=caption,
                                     parse_mode="Markdown"), _loop)


# ── Flask routes ─────────────────────────────────────────────────────────────
@flask_app.route("/ping")
def ping():
    return jsonify({"status": "alive", "version": "8.0",
                    "bot": _bot_app is not None}), 200

@flask_app.route("/health")
def health():
    return jsonify({
        "status": "healthy", "version": "8.0",
        "colab": bool(_colab_url()),
        "bot_running": _bot_app is not None,
        "active_sessions": len(_sessions),
    }), 200

# ── Colab tự đăng ký URL — hỗ trợ cả GET và POST ───────────────────────────
@flask_app.route("/colab/seturl", methods=["GET", "POST"])
def colab_seturl():
    # GET: /colab/seturl?url=https://xxx.ngrok.app&secret=xxx&uid=123
    if request.method == "GET":
        secret = request.args.get("secret", "")
        url    = request.args.get("url", "").strip().rstrip("/")
        uid    = request.args.get("uid", "")
    else:
        if request.headers.get("X-Bot-Secret") != Config.COLAB_SECRET:
            return jsonify({"error": "Unauthorized"}), 403
        data   = request.get_json(silent=True) or {}
        secret = data.get("secret", "")
        url    = data.get("url", "").strip().rstrip("/")
        uid    = str(data.get("notify_user_id", ""))

    if secret != Config.COLAB_SECRET:
        return jsonify({"error": "Unauthorized"}), 403
    if not url.startswith("http"):
        return jsonify({"error": "Invalid URL"}), 400

    _colab["url"] = url
    logger.info(f"✅ Colab URL registered: {url}")

    if uid and uid.isdigit() and _bot_app and _loop:
        asyncio.run_coroutine_threadsafe(
            _bot_app.bot.send_message(
                int(uid),
                f"🤖 *Colab v8 đã kết nối!*\n\n"
                f"🔗 `{url}`\n\n"
                f"✅ Sẵn sàng! Dùng `/new` để bắt đầu tạo video.",
                parse_mode="Markdown"), _loop)

    return jsonify({"success": True, "url": url}), 200

@flask_app.route("/colab/callback", methods=["POST"])
def colab_callback():
    if request.headers.get("X-Bot-Secret") != Config.COLAB_SECRET:
        return jsonify({"error": "Unauthorized"}), 403
    data = request.get_json(silent=True) or {}
    uid  = data.get("user_id")
    if _bot_app and uid and _loop:
        asyncio.run_coroutine_threadsafe(
            _handle_colab_result(int(uid), data), _loop)
    return jsonify({"received": True}), 200

@flask_app.route("/colab/progress", methods=["POST"])
def colab_progress():
    if request.headers.get("X-Bot-Secret") != Config.COLAB_SECRET:
        return jsonify({"error": "Unauthorized"}), 403
    data = request.get_json(silent=True) or {}
    uid  = data.get("user_id")
    msg  = data.get("message", "")
    if uid and _bot_app and _loop and msg:
        asyncio.run_coroutine_threadsafe(
            _bot_app.bot.send_message(int(uid), msg, parse_mode="Markdown"), _loop)
    return jsonify({"ok": True}), 200


async def _handle_colab_result(uid: int, data: dict):
    sess  = _get_session(uid)
    step  = data.get("step")
    error = data.get("error", "")

    if step == "bg_removed":
        img_b64 = data.get("image_b64", "")
        sess["product_bg_removed"] = img_b64
        try:
            import base64
            img_bytes = base64.b64decode(img_b64)
            kb = [[InlineKeyboardButton("✅ Dùng ảnh này", callback_data=f"bg_ok_{uid}"),
                   InlineKeyboardButton("🔄 Thử lại", callback_data=f"bg_retry_{uid}")]]
            await _bot_app.bot.send_photo(uid, photo=img_bytes,
                caption="✅ *Tách nền hoàn tất!*\n\n"
                        "📸 *Bước 3/4 — Gửi ảnh người mẫu*\n"
                        "• Body shot rõ ràng, đứng thẳng\n"
                        "• Nam/nữ/trẻ em — tùy sản phẩm\n\n"
                        "Hoặc /skip để bot tự chọn từ thư viện",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Preview fail: {e}")
            await _bot_app.bot.send_message(uid,
                "✅ Tách nền xong!\n\nGửi ảnh người mẫu hoặc /skip",
                parse_mode="Markdown")
        sess["state"] = STATE_WAIT_MODEL

    elif step == "tryon_preview":
        img_b64 = data.get("image_b64", "")
        try:
            import base64
            img_bytes = base64.b64decode(img_b64)
            kb = [[InlineKeyboardButton("🎬 Tạo video!", callback_data=f"makevid_{uid}"),
                   InlineKeyboardButton("🔄 Model khác", callback_data=f"retry_model_{uid}")]]
            await _bot_app.bot.send_photo(uid, photo=img_bytes,
                caption="👗 *AI Try-On Preview*\n\nModel mặc sản phẩm của bạn!\n\nTạo video viral ngay?",
                reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except Exception as e:
            logger.error(f"Try-on preview fail: {e}")

    elif step == "video":
        video_url   = data.get("video_url", "")
        drive_path  = data.get("drive_path", "")
        caption_txt = data.get("caption", "")
        sess["state"] = STATE_IDLE

        if video_url and video_url.startswith("http"):
            await _bot_app.bot.send_video(uid, video=video_url,
                caption=caption_txt[:1024], parse_mode="Markdown",
                supports_streaming=True)
        else:
            await _bot_app.bot.send_message(uid,
                f"✅ *Video hoàn tất!*\n\n"
                f"📂 Drive: `{drive_path}`\n\n"
                f"📋 *Caption:*\n{caption_txt[:800]}",
                parse_mode="Markdown")
        _reset_session(uid)

    elif step == "error":
        sess["state"] = STATE_IDLE
        await _bot_app.bot.send_message(uid,
            f"❌ Lỗi pipeline:\n`{error}`\n\nDùng `/new` để thử lại.",
            parse_mode="Markdown")
        _reset_session(uid)


# ── Telegram Handlers ─────────────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if Config.ALLOWED_USER_IDS and uid not in Config.ALLOWED_USER_IDS:
        await update.message.reply_text("⛔ Không có quyền truy cập."); return
    await update.message.reply_text(
        "🎬 *Affiliate Studio v8 — Sẵn sàng!*\n\n"
        "AI tạo video affiliate TikTok:\n"
        "người mẫu mặc sản phẩm → talking review → viral\n\n"
        "📌 *Quy trình:*\n"
        "1️⃣ `/new` — Bắt đầu\n"
        "2️⃣ Gửi ảnh sản phẩm → Bot tách nền tự động\n"
        "3️⃣ Nhập: `Tên | Giá | Mô tả | tiktok`\n"
        "4️⃣ Gửi ảnh người mẫu hoặc `/skip`\n"
        "5️⃣ AI try-on + video viral 🔥\n\n"
        "💡 Gõ `/help` để xem tất cả lệnh",
        parse_mode="Markdown")

async def cmd_new(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if Config.ALLOWED_USER_IDS and uid not in Config.ALLOWED_USER_IDS:
        await update.message.reply_text("⛔ Không có quyền."); return
    _reset_session(uid)
    sess = _get_session(uid)
    sess["state"] = STATE_WAIT_PRODUCT
    await update.message.reply_text(
        "📸 *Bước 1/4 — Gửi ảnh sản phẩm*\n\n"
        "• Ảnh rõ nét, nền đơn giản càng tốt\n"
        "• Bot tự động tách nền trắng\n"
        "• Hỗ trợ: áo, váy, quần, phụ kiện, giày...",
        parse_mode="Markdown")

async def cmd_skip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    sess = _get_session(uid)
    if sess["state"] != STATE_WAIT_MODEL:
        await update.message.reply_text("❓ Không có bước nào cần skip."); return
    sess["model_photo"] = None
    await update.message.reply_text("🤖 Bot tự chọn người mẫu phù hợp...")
    await _dispatch_tryon_from_update(update, uid, sess)

async def cmd_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    _reset_session(update.effective_user.id)
    await update.message.reply_text("🗑️ Đã hủy. Dùng /new để bắt đầu lại.")

async def handle_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    if Config.ALLOWED_USER_IDS and uid not in Config.ALLOWED_USER_IDS: return
    sess = _get_session(uid)

    photo = update.message.photo[-1]
    pfile = await photo.get_file()
    tmp   = tempfile.mktemp(suffix=".jpg")
    await pfile.download_to_drive(tmp)

    if sess["state"] == STATE_WAIT_PRODUCT:
        sess["product_photo"] = tmp
        sess["state"]         = STATE_WAIT_INFO
        await update.message.reply_text(
            "✅ Nhận ảnh sản phẩm!\n\n"
            "📝 *Bước 2/4 — Nhập thông tin:*\n"
            "`Tên SP | Giá | Mô tả | platform`\n\n"
            "Ví dụ:\n"
            "`Váy maxi lụa | 299k | Váy nữ tay dài | tiktok`\n"
            "`Áo hoodie unisex | 350k | Áo nỉ form rộng | both`",
            parse_mode="Markdown")

    elif sess["state"] == STATE_WAIT_MODEL:
        sess["model_photo"] = tmp
        await update.message.reply_text("✅ Nhận ảnh người mẫu! 🔄 Đang xử lý AI try-on...")
        await _dispatch_tryon_from_update(update, uid, sess)

    else:
        await update.message.reply_text(
            "💡 Dùng `/new` để bắt đầu session mới.", parse_mode="Markdown")

async def handle_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    sess = _get_session(uid)
    text = update.message.text.strip()

    if sess["state"] == STATE_WAIT_INFO:
        parts    = [p.strip() for p in text.split("|")]
        name     = parts[0] if parts else ""
        price    = parts[1] if len(parts) > 1 else "Liên hệ"
        desc     = parts[2] if len(parts) > 2 else name
        platform = parts[3].lower() if len(parts) > 3 else "tiktok"
        if platform not in ("tiktok", "shopee", "both"): platform = "tiktok"
        if not name:
            await update.message.reply_text(
                "❌ Format: `Tên SP | Giá | Mô tả | platform`", parse_mode="Markdown")
            return
        sess["product_info"] = {"name": name, "price": price,
                                 "description": desc, "platform": platform}
        await update.message.reply_text(
            f"✅ *{name}* — {price}\n\n"
            "🔄 *Bước 3/4 — Đang tách nền...*\n⏱️ ~15-30 giây",
            parse_mode="Markdown")
        await _dispatch_bg_remove(update, uid, sess)

    elif sess["state"] == STATE_IDLE:
        await update.message.reply_text(
            "💡 Dùng `/new` để bắt đầu tạo video.", parse_mode="Markdown")

async def _dispatch_bg_remove(update, uid: int, sess: dict):
    import base64
    product_path = sess.get("product_photo")
    if not product_path or not os.path.exists(product_path):
        await update.message.reply_text("❌ Không tìm thấy ảnh sản phẩm."); return
    with open(product_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()
    payload = {
        "step": "bg_remove", "user_id": uid,
        "image_b64": img_b64, "product_info": sess["product_info"],
        "callback_url": f"{Config.RENDER_URL}/colab/callback",
        "progress_url": f"{Config.RENDER_URL}/colab/progress",
        "secret": Config.COLAB_SECRET,
    }
    result = _call("pipeline/bg_remove", payload, timeout=45)
    if "error" in result:
        await update.message.reply_text(
            f"❌ Colab chưa kết nối:\n`{result['error']}`\n\n"
            "→ Vào Colab → chạy lại Cell 4\n"
            "→ Dùng /wake để check",
            parse_mode="Markdown")

async def _dispatch_tryon_from_update(update, uid: int, sess: dict):
    import base64
    model_b64 = None
    if sess.get("model_photo") and os.path.exists(sess["model_photo"]):
        with open(sess["model_photo"], "rb") as f:
            model_b64 = base64.b64encode(f.read()).decode()
    await update.message.reply_text(
        "🚀 *Đang gửi sang Colab...*\n\n"
        "① AI Try-On → model mặc sản phẩm\n"
        "② Chọn background phù hợp\n"
        "③ Tạo video talking + review\n"
        "④ Caption viral + nhạc\n\n"
        "⏱️ ~5-15 phút", parse_mode="Markdown")
    payload = {
        "step": "full_pipeline", "user_id": uid,
        "product_bg_b64": sess.get("product_bg_removed", ""),
        "model_b64": model_b64,
        "product_info": sess["product_info"],
        "callback_url": f"{Config.RENDER_URL}/colab/callback",
        "progress_url": f"{Config.RENDER_URL}/colab/progress",
        "secret": Config.COLAB_SECRET,
    }
    sess["state"] = STATE_PROCESSING
    result = _call("pipeline/full", payload, timeout=30)
    if "error" in result:
        sess["state"] = STATE_WAIT_MODEL
        await update.message.reply_text(
            f"❌ Lỗi Colab:\n`{result['error']}`", parse_mode="Markdown")
    else:
        await update.message.reply_text(
            "✅ Đã nhận! Video xong sẽ tự gửi về đây.\n"
            "Dùng /status để check.", parse_mode="Markdown")

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    await q.answer()
    data = q.data
    uid  = update.effective_user.id
    sess = _get_session(uid)

    if data.startswith("bg_ok_"):
        sess["state"] = STATE_WAIT_MODEL
        await q.message.reply_text(
            "📸 *Bước 3/4 — Gửi ảnh người mẫu*\n\n"
            "• Body shot rõ, đứng thẳng\n"
            "• Nam/nữ/trẻ em tuỳ sản phẩm\n\n"
            "Hoặc /skip để bot tự chọn từ thư viện",
            parse_mode="Markdown")

    elif data.startswith("bg_retry_"):
        sess["state"] = STATE_WAIT_PRODUCT
        _reset_session(uid)
        await q.message.reply_text("🔄 Gửi lại ảnh sản phẩm để tách nền lại.")

    elif data.startswith("makevid_"):
        if sess["state"] == STATE_PROCESSING:
            await q.message.reply_text("⏳ Đang xử lý, chờ xíu!"); return
        await q.message.reply_text("🎬 Bắt đầu tạo video...")
        await _dispatch_tryon_from_update(q.message, uid, sess)

    elif data.startswith("retry_model_"):
        sess["state"]       = STATE_WAIT_MODEL
        sess["model_photo"] = None
        await q.message.reply_text(
            "📸 Gửi ảnh người mẫu khác, hoặc /skip để bot tự chọn.")


# ── DevOps Commands ───────────────────────────────────────────────────────────
async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid   = update.effective_user.id
    sess  = _get_session(uid)
    alive = _ping()
    label = {STATE_IDLE: "💤 Idle", STATE_WAIT_PRODUCT: "📸 Chờ ảnh SP",
             STATE_WAIT_INFO: "📝 Chờ thông tin", STATE_WAIT_MODEL: "👤 Chờ model",
             STATE_PROCESSING: "⚙️ Đang xử lý..."}.get(sess["state"], sess["state"])
    await update.message.reply_text(
        f"📡 *Affiliate Studio v8*\n\n"
        f"🌐 Render : `{Config.RENDER_URL or 'chưa set'}`\n"
        f"🔗 Colab  : {'✅ ' + _colab_url()[:45] if alive else '❌ offline'}\n"
        f"📋 Session: `{label}`\n"
        f"👥 Active : `{len(_sessions)}`",
        parse_mode="Markdown")

async def cmd_wake(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = _colab_url()
    if not u:
        await update.message.reply_text(
            "❌ Chưa có Colab URL.\n\n"
            "1️⃣ Mở notebook trên Colab\n"
            "2️⃣ Runtime → T4 GPU\n"
            "3️⃣ Chạy Cell 4 → tự đăng ký về đây"); return
    await update.message.reply_text("🔄 Ping Colab...")
    alive = _ping()
    if alive:
        info   = _call("info", {})
        gpu    = info.get("gpu", "N/A") if "error" not in info else "N/A"
        models = info.get("models_loaded", [])
        await update.message.reply_text(
            f"✅ *Colab đang sống!*\n\n"
            f"🖥️ GPU: `{gpu}`\n"
            f"🤖 Models: `{', '.join(models) or 'none'}`\n\n"
            "Dùng `/new` để tạo video!", parse_mode="Markdown")
    else:
        await update.message.reply_text(
            "😴 Colab không phản hồi.\n\n→ Vào Colab → chạy lại Cell 4")

async def cmd_setcolab(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if not args:
        await update.message.reply_text(
            "Dùng: `/setcolab https://xxxx.ngrok-free.app`", parse_mode="Markdown"); return
    url = args[0].strip().rstrip("/")
    if not url.startswith("http"):
        await update.message.reply_text("❌ URL phải bắt đầu https://"); return
    _colab["url"] = url
    alive = _ping()
    await update.message.reply_text(
        f"{'✅ Colab alive!' if alive else '⚠️ Đã lưu URL nhưng Colab chưa phản hồi'}\n"
        f"🔗 `{url}`", parse_mode="Markdown")

async def cmd_autocolab(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if not args: await update.message.reply_text("Dùng: `/autocolab on` hoặc `off`"); return
    _colab["auto_ping"] = args[0].lower() == "on"
    await update.message.reply_text(
        f"{'✅ Auto-ping bật' if _colab['auto_ping'] else '⏸️ Auto-ping tắt'}")

async def cmd_drive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    result = _call("drive/stats", {"secret": Config.COLAB_SECRET}, timeout=20)
    if "error" in result:
        await update.message.reply_text(f"❌ `{result['error']}`", parse_mode="Markdown"); return
    stats = result.get("stats", {})
    total = sum(v.get("size_mb", 0) for v in stats.values())
    lines = [f"📁 `{k}/`: {v['size_mb']} MB | {v['files']} files" for k, v in stats.items()]
    await update.message.reply_text(
        "📊 *Google Drive 5TB:*\n\n" + "\n".join(lines) +
        f"\n\n💾 Đã dùng: `{total:.1f} MB`", parse_mode="Markdown")

async def cmd_github(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if Config.ALLOWED_USER_IDS and uid not in Config.ALLOWED_USER_IDS: return
    await update.message.reply_text("📤 Đang push lên GitHub...")
    result = _call("devops/github_push", {
        "secret": Config.COLAB_SECRET,
        "commit_msg": " ".join(ctx.args) if ctx.args else "Auto-update from bot",
    }, timeout=60)
    if "error" in result:
        await update.message.reply_text(f"❌ `{result['error']}`", parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"✅ *GitHub Push OK!*\n\n📝 `{result.get('commit','done')}`",
            parse_mode="Markdown")

async def cmd_deploy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not Config.RENDER_DEPLOY_HOOK:
        await update.message.reply_text("❌ RENDER_DEPLOY_HOOK chưa set."); return
    await update.message.reply_text("🚀 Trigger Render redeploy...")
    try:
        r = requests.post(Config.RENDER_DEPLOY_HOOK, timeout=15)
        if r.status_code in (200, 201):
            await update.message.reply_text(
                "✅ *Render đang deploy!*\n⏱️ ~3-5 phút", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"⚠️ Render {r.status_code}")
    except Exception as e:
        await update.message.reply_text(f"❌ `{e}`", parse_mode="Markdown")

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Affiliate Studio v8*\n\n"
        "*🎬 Tạo video:*\n"
        "`/new` · `/skip` · `/cancel`\n\n"
        "*📡 Colab:*\n"
        "`/wake` · `/setcolab <url>` · `/autocolab on/off`\n\n"
        "*🛠️ DevOps:*\n"
        "`/github <msg>` · `/deploy` · `/drive` · `/status`",
        parse_mode="Markdown")


# ── Auto ping thread ──────────────────────────────────────────────────────────
def _auto_ping_thread():
    while True:
        time.sleep(Config.COLAB_PING_INTERVAL_MIN * 60)
        if _colab.get("auto_ping") and _colab_url():
            alive = _ping()
            logger.debug(f"Auto-ping Colab: {'alive' if alive else 'dead'}")

# ── Bot startup — gọi khi module được import (gunicorn safe) ─────────────────
def _start_bot_thread():
    """Chạy bot polling trong thread riêng. Gọi 1 lần khi app start."""
    global _bot_app, _loop
    if not Config.TELEGRAM_TOKEN:
        logger.error("❌ TELEGRAM_TOKEN không có — bot không start được")
        return

    _loop    = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    _bot_app = Application.builder().token(Config.TELEGRAM_TOKEN).build()

    handlers = [
        ("start",     cmd_start),   ("help",      cmd_help),
        ("new",       cmd_new),     ("skip",      cmd_skip),
        ("cancel",    cmd_cancel),  ("wake",      cmd_wake),
        ("setcolab",  cmd_setcolab),("autocolab", cmd_autocolab),
        ("status",    cmd_status),  ("drive",     cmd_drive),
        ("github",    cmd_github),  ("deploy",    cmd_deploy),
    ]
    for cmd, fn in handlers:
        _bot_app.add_handler(CommandHandler(cmd, fn))
    _bot_app.add_handler(CallbackQueryHandler(handle_callback))
    _bot_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    _bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("✅ Bot polling started")
    _loop.run_until_complete(_bot_app.run_polling(drop_pending_updates=True))


# ─────────────────────────────────────────────────────────────────────────────
# START BOT NGAY KHI MODULE ĐƯỢC IMPORT — hoạt động với cả gunicorn và python
# ─────────────────────────────────────────────────────────────────────────────
threading.Thread(target=_auto_ping_thread, daemon=True).start()
threading.Thread(target=_start_bot_thread, daemon=True).start()
logger.info("🚀 Affiliate Studio v8 — Module loaded, bot starting...")

if __name__ == "__main__":
    flask_app.run(host=Config.HOST, port=Config.PORT,
                  debug=False, use_reloader=False)
