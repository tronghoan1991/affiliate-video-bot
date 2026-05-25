"""
app.py — Affiliate Studio v8
Architecture: Telegram Webhook → Render Flask → Colab GPU

FIX: Dùng webhook thay polling.
- Polling cần signal handler → chỉ chạy được ở main thread
- Gunicorn fork nhiều worker process → signal handler bị block
- Webhook: Telegram POST thẳng vào /webhook → không cần thread, không cần signal
"""
import asyncio, logging, os, threading, time, tempfile, json, base64
from pathlib import Path
from typing import Optional
import requests
from flask import Flask, jsonify, request, Response
from telegram import (Bot, InlineKeyboardButton, InlineKeyboardMarkup,
                       Update, BotCommand)
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                           ContextTypes, MessageHandler, filters)
from telegram.request import HTTPXRequest
from config import Config

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s — %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("AffiliateStudio_v8")

flask_app = Flask(__name__)

# ── Global state ──────────────────────────────────────────────────────────────
_sessions: dict = {}
_colab:    dict = {"url": "", "auto_ping": False}
_app:      Optional[Application] = None   # PTB Application (webhook mode)

STATE_IDLE         = "idle"
STATE_WAIT_PRODUCT = "wait_product"
STATE_WAIT_INFO    = "wait_info"
STATE_WAIT_MODEL   = "wait_model"
STATE_PROCESSING   = "processing"


# ── Helpers ───────────────────────────────────────────────────────────────────
def _colab_url(): return _colab.get("url", "").rstrip("/")

def _ping_colab():
    u = _colab_url()
    if not u: return False
    try: return requests.get(f"{u}/ping", timeout=12).status_code == 200
    except: return False

def _call_colab(endpoint, payload, timeout=60):
    u = _colab_url()
    if not u: return {"error": "Colab chưa kết nối. Vào Colab → chạy Cell 4"}
    try:
        r = requests.post(f"{u}/{endpoint}", json=payload, timeout=timeout)
        return r.json()
    except requests.Timeout:
        return {"error": f"Colab timeout ({timeout}s). Thử /wake"}
    except Exception as e:
        return {"error": str(e)}

def _get_session(uid: int) -> dict:
    if uid not in _sessions:
        _sessions[uid] = {
            "state": STATE_IDLE,
            "product_photo_b64": None,
            "product_bg_b64": None,
            "model_photo_b64": None,
            "product_info": {},
        }
    return _sessions[uid]

def _reset_session(uid: int):
    _sessions.pop(uid, None)

async def _send(uid: int, text: str, **kwargs):
    if _app:
        await _app.bot.send_message(uid, text, **kwargs)

async def _send_photo_b64(uid: int, b64: str, caption: str = "", **kwargs):
    if _app:
        await _app.bot.send_photo(
            uid, photo=base64.b64decode(b64),
            caption=caption, parse_mode="Markdown", **kwargs)


# ── Flask: Health routes ──────────────────────────────────────────────────────
@flask_app.route("/ping")
def ping():
    return jsonify({"status": "alive", "version": "8.0",
                    "webhook": bool(_app)}), 200

@flask_app.route("/health")
def health():
    return jsonify({
        "status": "healthy", "version": "8.0",
        "colab": bool(_colab_url()),
        "active_sessions": len(_sessions),
    }), 200


# ── Flask: Telegram Webhook endpoint ─────────────────────────────────────────
@flask_app.route("/webhook", methods=["POST"])
def webhook():
    """Telegram POST update vào đây."""
    if not _app:
        return Response("Bot not ready", status=503)
    try:
        data   = request.get_json(force=True)
        update = Update.de_json(data, _app.bot)
        asyncio.run(_app.process_update(update))
    except Exception as e:
        logger.error(f"Webhook process error: {e}")
    return Response("ok", status=200)


# ── Flask: Colab registration ─────────────────────────────────────────────────
@flask_app.route("/colab/seturl", methods=["GET", "POST"])
def colab_seturl():
    # Hỗ trợ cả GET (dễ dùng từ Colab) và POST
    if request.method == "GET":
        secret = request.args.get("secret", "")
        url    = request.args.get("url", "").strip().rstrip("/")
        uid    = request.args.get("uid", "")
    else:
        data   = request.get_json(silent=True) or {}
        secret = data.get("secret", request.headers.get("X-Bot-Secret", ""))
        url    = data.get("url", "").strip().rstrip("/")
        uid    = str(data.get("notify_user_id", ""))

    if secret != Config.COLAB_SECRET:
        return jsonify({"error": "Unauthorized"}), 403
    if not url.startswith("http"):
        return jsonify({"error": "Invalid URL"}), 400

    _colab["url"] = url
    logger.info(f"✅ Colab URL: {url}")

    if uid and uid.isdigit() and _app:
        asyncio.run(_app.bot.send_message(
            int(uid),
            f"🤖 *Colab v8 kết nối!*\n\n🔗 `{url}`\n\n"
            f"✅ Sẵn sàng! Gõ `/new` để tạo video.",
            parse_mode="Markdown"))

    return jsonify({"success": True, "url": url}), 200


# ── Flask: Colab callbacks ────────────────────────────────────────────────────
@flask_app.route("/colab/callback", methods=["POST"])
def colab_callback():
    if request.headers.get("X-Bot-Secret") != Config.COLAB_SECRET:
        return jsonify({"error": "Unauthorized"}), 403
    data = request.get_json(silent=True) or {}
    uid  = data.get("user_id")
    if _app and uid:
        asyncio.run(_handle_colab_result(int(uid), data))
    return jsonify({"received": True}), 200

@flask_app.route("/colab/progress", methods=["POST"])
def colab_progress():
    if request.headers.get("X-Bot-Secret") != Config.COLAB_SECRET:
        return jsonify({"error": "Unauthorized"}), 403
    data = request.get_json(silent=True) or {}
    uid  = data.get("user_id")
    msg  = data.get("message", "")
    if uid and _app and msg:
        asyncio.run(_app.bot.send_message(int(uid), msg, parse_mode="Markdown"))
    return jsonify({"ok": True}), 200


async def _handle_colab_result(uid: int, data: dict):
    sess  = _get_session(uid)
    step  = data.get("step")
    error = data.get("error", "")

    if step == "bg_removed":
        b64 = data.get("image_b64", "")
        sess["product_bg_b64"] = b64
        sess["state"]          = STATE_WAIT_MODEL
        kb = [[
            InlineKeyboardButton("✅ Dùng ảnh này", callback_data=f"bg_ok"),
            InlineKeyboardButton("🔄 Chụp lại",     callback_data=f"bg_retry"),
        ]]
        try:
            await _send_photo_b64(uid, b64,
                caption="✅ *Tách nền hoàn tất!*\n\n"
                        "📸 *Bước 3/4 — Gửi ảnh người mẫu*\n"
                        "• Body shot rõ, đứng thẳng\n"
                        "• Nam / nữ / trẻ em — tuỳ sản phẩm\n\n"
                        "Hoặc `/skip` để bot tự chọn từ thư viện Drive",
                reply_markup=InlineKeyboardMarkup(kb))
        except Exception:
            await _send(uid,
                "✅ Tách nền xong!\n\nGửi ảnh người mẫu hoặc /skip",
                parse_mode="Markdown")

    elif step == "tryon_preview":
        b64 = data.get("image_b64", "")
        kb  = [[
            InlineKeyboardButton("🎬 Tạo video!",    callback_data="makevid"),
            InlineKeyboardButton("🔄 Đổi model",     callback_data="retry_model"),
        ]]
        try:
            await _send_photo_b64(uid, b64,
                caption="👗 *AI Try-On Preview*\n\n"
                        "Model đã mặc sản phẩm của bạn!\n"
                        "Tạo video 30 giây viral ngay?",
                reply_markup=InlineKeyboardMarkup(kb))
        except Exception as e:
            logger.error(f"Try-on preview: {e}")
            await _send(uid, "✅ Try-on xong! Nhấn Tạo video để tiếp tục.",
                        parse_mode="Markdown")

    elif step == "video":
        sess["state"]  = STATE_IDLE
        drive_path     = data.get("drive_path", "")
        caption_txt    = data.get("caption", "")
        video_url      = data.get("video_url", "")

        if video_url and video_url.startswith("http"):
            await _app.bot.send_video(uid, video=video_url,
                caption=caption_txt[:1024], parse_mode="Markdown",
                supports_streaming=True)
        else:
            await _send(uid,
                f"✅ *Video hoàn tất!*\n\n"
                f"📂 Drive: `{drive_path}`\n\n"
                f"📋 *Caption TikTok:*\n{caption_txt[:800]}",
                parse_mode="Markdown")
        _reset_session(uid)

    elif step == "error":
        sess["state"] = STATE_IDLE
        await _send(uid,
            f"❌ *Pipeline lỗi:*\n`{error}`\n\nDùng `/new` để thử lại.",
            parse_mode="Markdown")
        _reset_session(uid)


# ── Telegram Command Handlers ─────────────────────────────────────────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if Config.ALLOWED_USER_IDS and uid not in Config.ALLOWED_USER_IDS:
        await update.message.reply_text("⛔ Không có quyền truy cập."); return
    await update.message.reply_text(
        "🎬 *Affiliate Studio v8*\n\n"
        "Tạo video affiliate TikTok 30 giây:\n"
        "AI try-on → người mẫu review → viral hook\n\n"
        "*Quy trình:*\n"
        "① `/new` — bắt đầu\n"
        "② Gửi ảnh sản phẩm → bot tách nền\n"
        "③ Nhập `Tên | Giá | Mô tả | tiktok`\n"
        "④ Gửi ảnh người mẫu hoặc `/skip`\n"
        "⑤ Nhận video 30 giây 🔥\n\n"
        "Gõ `/help` để xem tất cả lệnh",
        parse_mode="Markdown")

async def cmd_new(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if Config.ALLOWED_USER_IDS and uid not in Config.ALLOWED_USER_IDS: return
    _reset_session(uid)
    sess = _get_session(uid)
    sess["state"] = STATE_WAIT_PRODUCT
    await update.message.reply_text(
        "📸 *Bước 1/4 — Gửi ảnh sản phẩm*\n\n"
        "• Ảnh rõ nét, nền đơn giản\n"
        "• Bot tự tách nền trắng (~15s)\n"
        "• Áo, váy, quần, giày, phụ kiện...",
        parse_mode="Markdown")

async def cmd_skip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    sess = _get_session(uid)
    if sess["state"] != STATE_WAIT_MODEL:
        await update.message.reply_text("❓ Không có bước nào cần skip."); return
    sess["model_photo_b64"] = None
    await update.message.reply_text("🤖 Bot tự chọn model phù hợp sản phẩm...")
    await _dispatch_pipeline(update.message, uid, sess)

async def cmd_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    _reset_session(update.effective_user.id)
    await update.message.reply_text("🗑️ Đã hủy. Dùng /new để bắt đầu lại.")

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid   = update.effective_user.id
    sess  = _get_session(uid)
    alive = _ping_colab()
    label = {STATE_IDLE: "💤 Idle", STATE_WAIT_PRODUCT: "📸 Chờ ảnh SP",
             STATE_WAIT_INFO: "📝 Chờ thông tin", STATE_WAIT_MODEL: "👤 Chờ model",
             STATE_PROCESSING: "⚙️ Đang render..."}.get(sess["state"], "?")
    await update.message.reply_text(
        f"📡 *Status*\n\n"
        f"🌐 Render : `{Config.RENDER_URL or 'N/A'}`\n"
        f"🔗 Colab  : {'✅ ' + _colab_url()[:40] if alive else '❌ offline'}\n"
        f"📋 Bước   : `{label}`",
        parse_mode="Markdown")

async def cmd_wake(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not _colab_url():
        await update.message.reply_text(
            "❌ Colab chưa kết nối.\n\n"
            "→ Mở notebook → T4 GPU → Cell 4"); return
    await update.message.reply_text("🔄 Ping Colab...")
    alive = _ping_colab()
    if alive:
        info   = _call_colab("info", {})
        gpu    = info.get("gpu", "?")
        models = info.get("models_loaded", [])
        await update.message.reply_text(
            f"✅ *Colab sống!*\n\n🖥️ `{gpu}`\n"
            f"🤖 Models: `{', '.join(models) or 'none'}`",
            parse_mode="Markdown")
    else:
        await update.message.reply_text("😴 Colab offline → chạy lại Cell 4")

async def cmd_setcolab(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text(
            "Dùng: `/setcolab https://xxx.ngrok-free.app`", parse_mode="Markdown"); return
    url = ctx.args[0].strip().rstrip("/")
    if not url.startswith("http"):
        await update.message.reply_text("❌ URL phải bắt đầu https://"); return
    _colab["url"] = url
    alive = _ping_colab()
    await update.message.reply_text(
        f"{'✅ Colab alive!' if alive else '⚠️ URL đã lưu, Colab chưa phản hồi'}\n`{url}`",
        parse_mode="Markdown")

async def cmd_autocolab(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Dùng: `/autocolab on` hoặc `off`"); return
    _colab["auto_ping"] = ctx.args[0].lower() == "on"
    await update.message.reply_text(
        f"{'✅ Auto-ping ON' if _colab['auto_ping'] else '⏸️ Auto-ping OFF'}")

async def cmd_drive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    result = _call_colab("drive/stats", {"secret": Config.COLAB_SECRET}, timeout=20)
    if "error" in result:
        await update.message.reply_text(f"❌ `{result['error']}`", parse_mode="Markdown"); return
    stats = result.get("stats", {})
    total = sum(v.get("size_mb", 0) for v in stats.values())
    lines = [f"📁 `{k}/`: {v['size_mb']} MB | {v['files']} files" for k, v in stats.items()]
    await update.message.reply_text(
        "📊 *Google Drive 5TB:*\n\n" + "\n".join(lines) +
        f"\n\n💾 Total: `{total:.1f} MB`", parse_mode="Markdown")

async def cmd_github(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if Config.ALLOWED_USER_IDS and uid not in Config.ALLOWED_USER_IDS: return
    msg = " ".join(ctx.args) if ctx.args else "Auto-update"
    await update.message.reply_text(f"📤 Push GitHub: `{msg}`...", parse_mode="Markdown")
    result = _call_colab("devops/github_push",
                         {"secret": Config.COLAB_SECRET, "commit_msg": msg}, timeout=60)
    if "error" in result:
        await update.message.reply_text(f"❌ `{result['error']}`", parse_mode="Markdown")
    else:
        status = result.get("status", "")
        if status == "up-to-date":
            await update.message.reply_text("✅ Code đã up-to-date, không có gì mới.")
        else:
            await update.message.reply_text(
                f"✅ *Pushed!*\n\n📝 `{result.get('commit','')}`", parse_mode="Markdown")

async def cmd_deploy(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not Config.RENDER_DEPLOY_HOOK:
        await update.message.reply_text("❌ RENDER_DEPLOY_HOOK chưa set trong Render env."); return
    await update.message.reply_text("🚀 Triggering Render redeploy...")
    try:
        r = requests.post(Config.RENDER_DEPLOY_HOOK, timeout=15)
        await update.message.reply_text(
            "✅ *Deploy triggered!*\n⏱️ ~3-5 phút\n"
            f"🌐 `{Config.RENDER_URL}/health`"
            if r.status_code in (200, 201) else f"⚠️ Status {r.status_code}",
            parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ `{e}`", parse_mode="Markdown")

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Affiliate Studio v8 — Commands*\n\n"
        "*🎬 Tạo video:*\n"
        "`/new` — bắt đầu session\n"
        "`/skip` — bỏ qua ảnh model\n"
        "`/cancel` — hủy session\n\n"
        "*📡 Colab:*\n"
        "`/wake` — ping Colab\n"
        "`/setcolab <url>` — đặt ngrok URL\n"
        "`/autocolab on/off` — auto ping\n\n"
        "*🛠️ DevOps:*\n"
        "`/github <msg>` — push code\n"
        "`/deploy` — redeploy Render\n"
        "`/drive` — Drive stats\n"
        "`/status` — xem trạng thái",
        parse_mode="Markdown")


# ── Photo & Text handlers ─────────────────────────────────────────────────────
async def handle_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    if Config.ALLOWED_USER_IDS and uid not in Config.ALLOWED_USER_IDS: return
    sess = _get_session(uid)

    photo = update.message.photo[-1]
    pfile = await photo.get_file()
    data  = await pfile.download_as_bytearray()
    b64   = base64.b64encode(bytes(data)).decode()

    if sess["state"] == STATE_WAIT_PRODUCT:
        sess["product_photo_b64"] = b64
        sess["state"]             = STATE_WAIT_INFO
        await update.message.reply_text(
            "✅ Nhận ảnh sản phẩm!\n\n"
            "📝 *Bước 2/4 — Nhập thông tin:*\n"
            "`Tên | Giá | Mô tả | platform`\n\n"
            "Ví dụ:\n"
            "`Váy maxi lụa | 299k | Váy nữ tay dài | tiktok`\n"
            "`Áo hoodie | 350k | Form rộng unisex | both`",
            parse_mode="Markdown")

    elif sess["state"] == STATE_WAIT_MODEL:
        sess["model_photo_b64"] = b64
        await update.message.reply_text("✅ Nhận ảnh model! 🔄 Đang gửi sang Colab...")
        await _dispatch_pipeline(update.message, uid, sess)

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
        platform = (parts[3].lower() if len(parts) > 3 else "tiktok")
        if platform not in ("tiktok", "shopee", "both"): platform = "tiktok"
        if not name:
            await update.message.reply_text(
                "❌ Format: `Tên | Giá | Mô tả | tiktok`", parse_mode="Markdown"); return
        sess["product_info"] = {"name": name, "price": price,
                                 "description": desc, "platform": platform}
        await update.message.reply_text(
            f"✅ *{name}* — {price}\n\n"
            "🔄 *Bước 3/4 — Đang tách nền...*\n⏱️ ~20 giây",
            parse_mode="Markdown")
        await _dispatch_bg_remove(update.message, uid, sess)

    elif sess["state"] == STATE_IDLE:
        await update.message.reply_text(
            "💡 Dùng `/new` để bắt đầu.", parse_mode="Markdown")

async def _dispatch_bg_remove(message, uid: int, sess: dict):
    result = _call_colab("pipeline/bg_remove", {
        "step": "bg_remove", "user_id": uid,
        "image_b64": sess["product_photo_b64"],
        "product_info": sess["product_info"],
        "callback_url": f"{Config.RENDER_URL}/colab/callback",
        "progress_url": f"{Config.RENDER_URL}/colab/progress",
        "secret": Config.COLAB_SECRET,
    }, timeout=45)
    if "error" in result:
        await message.reply_text(
            f"❌ Colab chưa kết nối:\n`{result['error']}`\n\n"
            "→ Chạy Cell 4 trong notebook\n→ Dùng /wake để check",
            parse_mode="Markdown")

async def _dispatch_pipeline(message, uid: int, sess: dict):
    await message.reply_text(
        "🚀 *Gửi job sang Colab GPU...*\n\n"
        "Pipeline 30 giây video:\n"
        "① Tách nền & phân tích SP\n"
        "② AI Try-On — model mặc sản phẩm\n"
        "③ AI Background phù hợp ngành hàng\n"
        "④ Wan2.1/CogVideoX animate scene\n"
        "⑤ Script cảm xúc + text + CTA + nhạc\n\n"
        "⏱️ ~8-15 phút | Sẽ tự gửi video về đây",
        parse_mode="Markdown")
    result = _call_colab("pipeline/full", {
        "step": "full_pipeline", "user_id": uid,
        "product_bg_b64": sess.get("product_bg_b64", ""),
        "model_b64": sess.get("model_photo_b64"),
        "product_info": sess["product_info"],
        "callback_url": f"{Config.RENDER_URL}/colab/callback",
        "progress_url": f"{Config.RENDER_URL}/colab/progress",
        "secret": Config.COLAB_SECRET,
    }, timeout=30)
    if "error" in result:
        sess["state"] = STATE_WAIT_MODEL
        await message.reply_text(
            f"❌ Colab lỗi:\n`{result['error']}`", parse_mode="Markdown")
    else:
        sess["state"] = STATE_PROCESSING
        await message.reply_text(
            "✅ Job nhận! Video xong bot tự gửi về.\n"
            "Dùng /status để check.", parse_mode="Markdown")

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    await q.answer()
    uid  = update.effective_user.id
    sess = _get_session(uid)
    data = q.data

    if data == "bg_ok":
        sess["state"] = STATE_WAIT_MODEL
        await q.message.reply_text(
            "📸 *Bước 3/4 — Gửi ảnh người mẫu*\n\n"
            "• Đứng thẳng, thấy toàn thân\n"
            "• Nam / nữ / trẻ em — tuỳ sản phẩm\n\n"
            "Hoặc `/skip` để bot tự chọn",
            parse_mode="Markdown")

    elif data == "bg_retry":
        _reset_session(uid)
        sess2 = _get_session(uid)
        sess2["state"] = STATE_WAIT_PRODUCT
        await q.message.reply_text("🔄 Gửi lại ảnh sản phẩm để tách nền lại.")

    elif data == "makevid":
        if sess["state"] == STATE_PROCESSING:
            await q.message.reply_text("⏳ Đang render, chờ xíu!"); return
        await _dispatch_pipeline(q.message, uid, sess)

    elif data == "retry_model":
        sess["state"]          = STATE_WAIT_MODEL
        sess["model_photo_b64"] = None
        await q.message.reply_text(
            "📸 Gửi ảnh người mẫu khác, hoặc /skip.")


# ── Auto keep-alive thread ────────────────────────────────────────────────────
def _auto_ping_loop():
    while True:
        time.sleep(Config.COLAB_PING_INTERVAL_MIN * 60)
        if _colab.get("auto_ping") and _colab_url():
            _ping_colab()

threading.Thread(target=_auto_ping_loop, daemon=True).start()


# ── Bot init — Webhook mode (gunicorn safe, no signal handler) ────────────────
def _init_bot():
    """
    Khởi tạo PTB Application ở chế độ webhook.
    Không dùng run_polling() — không cần signal handler — gunicorn safe.
    """
    global _app
    token = Config.TELEGRAM_TOKEN
    if not token:
        logger.error("❌ TELEGRAM_TOKEN chưa set")
        return

    # Build application (không start updater)
    _app = (Application.builder()
            .token(token)
            .updater(None)          # ← tắt polling updater
            .build())

    # Đăng ký handlers
    cmds = [
        ("start",     cmd_start),   ("help",      cmd_help),
        ("new",       cmd_new),     ("skip",      cmd_skip),
        ("cancel",    cmd_cancel),  ("wake",      cmd_wake),
        ("setcolab",  cmd_setcolab),("autocolab", cmd_autocolab),
        ("status",    cmd_status),  ("drive",     cmd_drive),
        ("github",    cmd_github),  ("deploy",    cmd_deploy),
    ]
    for cmd, fn in cmds:
        _app.add_handler(CommandHandler(cmd, fn))
    _app.add_handler(CallbackQueryHandler(handle_callback))
    _app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    _app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Initialize (phải gọi trước khi xử lý update)
    asyncio.run(_app.initialize())

    # Đăng ký webhook với Telegram
    webhook_url = f"{Config.RENDER_URL}/webhook"
    try:
        asyncio.run(_app.bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"],
        ))
        logger.info(f"✅ Webhook set: {webhook_url}")
    except Exception as e:
        logger.error(f"❌ Webhook set failed: {e}")

    # Set bot commands menu
    try:
        asyncio.run(_app.bot.set_my_commands([
            BotCommand("new",       "Bắt đầu tạo video"),
            BotCommand("skip",      "Bỏ qua ảnh model"),
            BotCommand("cancel",    "Hủy session"),
            BotCommand("wake",      "Ping Colab"),
            BotCommand("status",    "Xem trạng thái"),
            BotCommand("drive",     "Drive stats"),
            BotCommand("github",    "Push code GitHub"),
            BotCommand("deploy",    "Redeploy Render"),
            BotCommand("help",      "Hướng dẫn"),
        ]))
        logger.info("✅ Bot commands menu set")
    except Exception as e:
        logger.warning(f"Commands menu: {e}")

    logger.info("✅ Bot ready (webhook mode)")


# ── Khởi tạo ngay khi module import ──────────────────────────────────────────
_init_bot()
logger.info("🚀 Affiliate Studio v8 loaded")

if __name__ == "__main__":
    flask_app.run(host=Config.HOST, port=Config.PORT,
                  debug=False, use_reloader=False)
