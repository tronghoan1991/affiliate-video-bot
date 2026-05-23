"""
app.py — Affiliate Video Bot v7 — Render Server + Telegram Bot
=============================================================================
Hỗ trợ 10 ngành hàng: fashion | beauty | health | home | food | tech | pet | sports | baby | fashion_kids
Tính năng mới v7: A/B hook test, /trending, /caption nhanh (không cần Colab), /abtest
=============================================================================
"""
import asyncio, logging, os, threading, time
from typing import Optional
import requests
from flask import Flask, jsonify, request
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler,
                           ContextTypes, MessageHandler, filters)
from config import Config

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(name)s — %(message)s", level=logging.INFO)
logger = logging.getLogger("AffiliateBot_v7")

flask_app = Flask(__name__)

_pending: dict   = {}
_colab:   dict   = {"url": Config.COLAB_WEBHOOK_URL, "auto_ping": False}
_bot_app: Optional[Application] = None
_loop:    Optional[asyncio.AbstractEventLoop] = None


def _colab_url():  return _colab.get("url","").rstrip("/")
def _ping():
    u = _colab_url()
    if not u: return False
    try: return requests.get(f"{u}/ping", timeout=12).status_code == 200
    except: return False
def _call(endpoint, payload, timeout=30):
    u = _colab_url()
    if not u: return {"error":"Colab chưa kết nối. Dùng /setcolab <url>"}
    try: return requests.post(f"{u}/{endpoint}", json=payload, timeout=timeout).json()
    except requests.Timeout: return {"error":f"Colab timeout {timeout}s. Dùng /wake kiểm tra."}
    except Exception as e: return {"error":str(e)}


# ══════════════════════════════════════════════════════════════════════════════
#  FLASK ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@flask_app.route("/ping")
def ping(): return jsonify({"status":"alive","version":"7.0"}), 200

@flask_app.route("/health")
def health():
    return jsonify({"status":"healthy","colab":bool(_colab_url()),"version":"7.0",
                    "engine":Config.VIDEO_ENGINE,"categories":10}), 200

@flask_app.route("/colab/seturl", methods=["POST"])
def colab_seturl():
    if request.headers.get("X-Bot-Secret") != Config.COLAB_SECRET:
        return jsonify({"error":"Unauthorized"}), 403
    data = request.get_json(silent=True) or {}
    url  = data.get("url","").strip().rstrip("/")
    if not url.startswith("http"): return jsonify({"error":"Invalid URL"}), 400
    _colab["url"] = url
    logger.info(f"✅ Colab URL registered: {url}")
    uid = data.get("notify_user_id")
    if uid and _bot_app and _loop:
        asyncio.run_coroutine_threadsafe(
            _bot_app.bot.send_message(int(uid),
                f"🤖 *Colab v7 đã tự kết nối!*\n\n🔗 `{url}`\n\n✅ Sẵn sàng! Dùng `/tao` để tạo video.",
                parse_mode="Markdown"), _loop)
    return jsonify({"success":True,"url":url}), 200

@flask_app.route("/colab/callback", methods=["POST"])
def colab_callback():
    if request.headers.get("X-Bot-Secret") != Config.COLAB_SECRET:
        return jsonify({"error":"Unauthorized"}), 403
    data = request.get_json(silent=True) or {}
    uid  = data.get("user_id")
    if _bot_app and uid and _loop:
        asyncio.run_coroutine_threadsafe(
            _send_result(int(uid), data.get("status"), data.get("video_url",""),
                         data.get("caption",""), data.get("error","")), _loop)
    return jsonify({"received":True}), 200

async def _send_result(uid, status, video_url, caption, error):
    if not _bot_app: return
    try:
        if status == "success" and video_url:
            await _bot_app.bot.send_video(uid, video=video_url,
                caption=caption[:1024], parse_mode="Markdown")
        elif status == "success_drive":
            await _bot_app.bot.send_message(uid,
                f"✅ *Video xong!*\n\n📂 Lưu vào Drive: `AffiliateBot/outputs/`\n\n{caption[:800]}",
                parse_mode="Markdown")
        else:
            await _bot_app.bot.send_message(uid,
                f"❌ Tạo video thất bại:\n`{error or 'Lỗi không xác định'}`\n\nThử `/tao` lại.",
                parse_mode="Markdown")
    except Exception as e: logger.error(f"Send result fail {uid}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  TELEGRAM COMMANDS
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Affiliate Video Bot v7 — 2026*\n\n"
        "AI tạo video viral cho TikTok & Shopee\n"
        "Hỗ trợ *10 ngành hàng*: Thời trang · Làm đẹp · Sức khoẻ · Gia dụng\n"
        "Đồ ăn · Công nghệ · Thú cưng · Thể thao · Mẹ&Bé · Trẻ em\n\n"
        "📝 *Tạo video:*\n"
        "`/tao Tên | Giá | Mô tả | platform`\n\n"
        "⚡ *Lấy caption ngay (không cần Colab):*\n"
        "`/caption Tên | Giá | Mô tả`\n\n"
        "🔬 *A/B test 3 hooks:*\n"
        "`/abtest Tên | Giá | Mô tả`\n\n"
        "📊 *Trending 2026:*\n"
        "`/trending` — Ngành hàng hot nhất\n\n"
        "🖥️ *Quản lý Colab:*\n"
        "`/wake` · `/setcolab <url>` · `/autocolab on/off`",
        parse_mode="Markdown")

async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Hướng dẫn v7*\n\n"
        "*Ngành hàng được hỗ trợ:*\n"
        "fashion · beauty · health · home\n"
        "food · tech · pet · sports · baby · kids\n\n"
        "*Tạo video:*\n"
        "`/tao Tên | Giá | Mô tả | tiktok`\n\n"
        "*Caption ngay (không cần Colab):*\n"
        "`/caption Váy maxi | 299k | Váy nữ lụa mềm`\n\n"
        "*A/B test hooks:*\n"
        "`/abtest Serum VC | 350k | Serum trắng da`\n"
        "→ Bot sinh 3 hook khác nhau để bạn chọn\n\n"
        "*Gửi ảnh:* Gửi ảnh + caption `Tên | Giá | Mô tả`\n\n"
        "*Trending:* `/trending` xem ngành hot nhất 2026\n\n"
        "*Quản lý Colab:*\n"
        "`/setcolab <url>` · `/wake` · `/colabstatus`\n"
        "`/autocolab on/off` · `/drive` · `/status`",
        parse_mode="Markdown")

async def cmd_trending(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📊 *Ngành Hàng Affiliate Hot Nhất 2026 — Vietnam*\n\n"
        "🥇 *Beauty/Skincare* — Commission 10-15%\n"
        "   Serum Vit C, retinol, SPF, làm trắng da\n"
        "   👥 Target: Nữ 18-40\n\n"
        "🥈 *Health/Supplement* — Commission 12-20%\n"
        "   Collagen uống, vitamin tổng hợp, protein\n"
        "   👥 Target: Nữ 25-45, Nam 22-40 tập gym\n\n"
        "🥉 *Fashion* — Commission 7-12%\n"
        "   Streetwear 2026, áo dài, đồ đi biển\n"
        "   👥 Target: Gen Z 16-28\n\n"
        "4️⃣ *Home/Decor* — Commission 8-12%\n"
        "   Đèn decor, nến thơm, tổ chức tủ\n"
        "   👥 Target: Nữ 22-40 yêu nhà đẹp\n\n"
        "5️⃣ *Pet Products* — Commission 8-15%\n"
        "   Thức ăn cao cấp, đồ chơi, grooming\n"
        "   👥 Target: Pet owner 20-40\n\n"
        "6️⃣ *Baby/Kids* — Commission 8-15%\n"
        "   An toàn, hữu cơ, phát triển trí tuệ\n"
        "   👥 Target: Mẹ trẻ 22-38\n\n"
        "7️⃣ *Tech Accessories* — Commission 5-8%\n"
        "   AirPods dupe, ring light, setup desk\n"
        "   👥 Target: Nam 18-35 dân tech\n\n"
        "💡 *Tip:* Beauty + Health có commission cao nhất\n"
        "và CTR video cao nhất vì yếu tố transformation rõ rệt.",
        parse_mode="Markdown")

async def cmd_caption(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Sinh caption ngay trên Render — không cần Colab."""
    text  = update.message.text.replace("/caption","").strip()
    parts = [p.strip() for p in text.split("|")]
    if len(parts) < 2:
        await update.message.reply_text(
            "❌ Format: `/caption Tên SP | Giá | Mô tả`\n\nVí dụ:\n`/caption Serum VC | 350k | Serum trắng da`",
            parse_mode="Markdown"); return

    name  = parts[0]; price = parts[1] if len(parts)>1 else "Liên hệ"
    desc  = parts[2] if len(parts)>2 else name

    await update.message.reply_text("⚡ Đang sinh caption...")
    try:
        from pipeline.product_analyzer import analyze_product
        from pipeline.emotional_engine import build_emotional_package
        from pipeline.viral_caption import generate_viral_caption

        analysis = analyze_product(name, desc, price)
        emotional = build_emotional_package(name, analysis.category, analysis.gender, price)
        vc = generate_viral_caption(name, price, analysis.category, analysis.gender, emotional, "tiktok")

        await update.message.reply_text(
            f"📋 *Caption TikTok:*\n\n{vc.tiktok[:900]}",
            parse_mode="Markdown")
        await update.message.reply_text(
            f"🛒 *Caption Shopee:*\n\n{vc.shopee[:900]}",
            parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: `{e}`", parse_mode="Markdown")

async def cmd_abtest(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Sinh 3 hook variants để A/B test."""
    text  = update.message.text.replace("/abtest","").strip()
    parts = [p.strip() for p in text.split("|")]
    if len(parts) < 1:
        await update.message.reply_text("❌ Format: `/abtest Tên SP | Giá | Mô tả`", parse_mode="Markdown"); return

    name  = parts[0]; price = parts[1] if len(parts)>1 else "Liên hệ"
    desc  = parts[2] if len(parts)>2 else name

    await update.message.reply_text("🔬 Đang tạo 3 hook variants...")
    try:
        from pipeline.product_analyzer import analyze_product
        from pipeline.emotional_engine import build_emotional_package

        analysis  = analyze_product(name, desc, price)
        emotional = build_emotional_package(name, analysis.category, analysis.gender, price)
        hooks = emotional.ab_hooks

        msg = f"🔬 *A/B Test — 3 Hook Variants*\n*{name}*\n\n"
        for i, hook in enumerate(hooks[:3], 1):
            msg += f"*Hook {i}:*\n{hook}\n\n"
        msg += "💡 Test mỗi hook 24h — hook nào có CTR cao nhất thì dùng cho video."
        await update.message.reply_text(msg, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Lỗi: `{e}`", parse_mode="Markdown")

async def cmd_tao(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/tao Tên | Giá | Mô tả | platform"""
    text  = update.message.text.replace("/tao","").strip()
    parts = [p.strip() for p in text.split("|")]
    if len(parts) < 2:
        await update.message.reply_text(
            "❌ Sai format!\n\n`/tao Tên SP | Giá | Mô tả | tiktok`\n\n"
            "Ví dụ:\n`/tao Serum Vit C | 350k | Serum trắng da | tiktok`\n"
            "`/tao Váy maxi | 299k | Váy nữ lụa | both`\n"
            "`/tao Gym set | 450k | Đồ tập gym nữ | shopee`",
            parse_mode="Markdown"); return

    name     = parts[0]; price = parts[1] if len(parts)>1 else "Liên hệ"
    desc     = parts[2] if len(parts)>2 else name
    platform = (parts[3].lower() if len(parts)>3 else Config.DEFAULT_PLATFORM)
    if platform not in ("tiktok","shopee","both"): platform = Config.DEFAULT_PLATFORM

    # Quick analysis để show ngành hàng
    try:
        from pipeline.product_analyzer import analyze_product
        analysis = analyze_product(name, desc, price)
        cat_vi = {"fashion":"👗 Thời trang","beauty":"💆 Làm đẹp","health":"💊 Sức khoẻ",
                  "home":"🏠 Gia dụng","food":"🍱 Đồ ăn","tech":"📱 Công nghệ",
                  "pet":"🐾 Thú cưng","sports":"💪 Thể thao","baby":"👶 Mẹ&Bé",
                  "fashion_kids":"🎀 Trẻ em"}
        cat_label = cat_vi.get(analysis.category, analysis.category)
        tier_label = {"budget":"💚 Bình dân","mid":"💛 Tầm trung","premium":"🔴 Cao cấp","luxury":"💎 Luxury"}.get(analysis.price_tier,"")
        info_text  = f"🏷️ Ngành: {cat_label}\n👥 Target: {analysis.target_demo[:60]}\n{tier_label}"
    except Exception:
        info_text = ""

    uid = update.effective_user.id
    _pending[uid] = {"name":name,"price":price,"description":desc,"platform":platform,"image_path":None,"user_id":uid}

    kb = [[InlineKeyboardButton("🎬 Tạo video!", callback_data=f"gen_{uid}"),
           InlineKeyboardButton("📋 Caption trước", callback_data=f"cap_{uid}")],
          [InlineKeyboardButton("🔬 A/B Hooks", callback_data=f"ab_{uid}"),
           InlineKeyboardButton("🔄 Đổi platform", callback_data=f"plat_{uid}")]]

    await update.message.reply_text(
        f"📋 *Xác nhận task:*\n\n🏷️ `{name}`\n💰 `{price}`\n📝 `{desc}`\n"
        f"📱 `{platform}`\n\n{info_text}",
        reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

async def handle_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    import tempfile
    photo   = update.message.photo[-1]
    caption = update.message.caption or ""
    parts   = [p.strip() for p in caption.split("|")]
    name    = parts[0] if parts else "Sản phẩm"
    price   = parts[1] if len(parts)>1 else "Liên hệ"
    desc    = parts[2] if len(parts)>2 else caption

    pf = await photo.get_file()
    tmp_img = tempfile.mktemp(suffix=".jpg")
    await pf.download_to_drive(tmp_img)

    await update.message.reply_text("🔍 AI đang phân tích ảnh...")
    try:
        from pipeline.product_analyzer import analyze_product
        from pipeline.emotional_engine import build_emotional_package
        a  = analyze_product(name, desc, price, image_path=tmp_img)
        ep = build_emotional_package(name, a.category, a.gender, price)
        cat_vi = {"fashion":"Thời trang","beauty":"Làm đẹp","health":"Sức khoẻ",
                  "home":"Gia dụng","food":"Đồ ăn","tech":"Công nghệ",
                  "pet":"Thú cưng","sports":"Thể thao","baby":"Mẹ&Bé","fashion_kids":"Trẻ em"}
        await update.message.reply_text(
            f"🧠 *AI nhận diện:*\n\n"
            f"📦 Ngành: `{cat_vi.get(a.category, a.category)}`\n"
            f"👤 Đối tượng: `{a.gender}`\n"
            f"💡 Lợi ích: `{a.key_benefit}`\n"
            f"🎯 Pain point: `{a.pain_point[:60]}`\n"
            f"🎵 Nhạc: `{ep.emotional_music}`\n"
            f"⚡ Độ tin cậy: `{a.confidence:.0%}`",
            parse_mode="Markdown")
    except Exception as e:
        logger.warning(f"Photo analysis fail: {e}")

    uid = update.effective_user.id
    _pending[uid] = {"name":name,"price":price,"description":desc,"platform":"tiktok","image_path":tmp_img,"user_id":uid}
    kb = [[InlineKeyboardButton("🎬 Tạo video ngay!", callback_data=f"gen_{uid}")]]
    await update.message.reply_text("✅ Sẵn sàng! Nhấn để tạo video.", reply_markup=InlineKeyboardMarkup(kb))

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer(); data = q.data

    if data.startswith("gen_"):
        uid = int(data.split("_")[1])
        if uid not in _pending: await q.message.reply_text("❌ Task hết hạn. Dùng /tao lại."); return
        task = _pending.pop(uid)
        await q.message.reply_text("🚀 Đang gửi sang Colab...")
        await _dispatch(q.message, task)

    elif data.startswith("cap_"):
        uid = int(data.split("_")[1])
        if uid not in _pending: await q.message.reply_text("❌ Task hết hạn."); return
        task = _pending[uid]
        await q.message.reply_text("⚡ Đang sinh caption nhanh...")
        try:
            from pipeline.product_analyzer import analyze_product
            from pipeline.emotional_engine import build_emotional_package
            from pipeline.viral_caption import generate_viral_caption
            a  = analyze_product(task["name"], task["description"], task["price"])
            ep = build_emotional_package(task["name"], a.category, a.gender, task["price"])
            vc = generate_viral_caption(task["name"], task["price"], a.category, a.gender, ep, task["platform"])
            await q.message.reply_text(f"📋 *Caption TikTok:*\n\n{vc.tiktok[:900]}", parse_mode="Markdown")
            await q.message.reply_text(f"🛒 *Caption Shopee:*\n\n{vc.shopee[:700]}", parse_mode="Markdown")
        except Exception as e:
            await q.message.reply_text(f"❌ `{e}`", parse_mode="Markdown")

    elif data.startswith("ab_"):
        uid = int(data.split("_")[1])
        if uid not in _pending: await q.message.reply_text("❌ Task hết hạn."); return
        task = _pending[uid]
        try:
            from pipeline.product_analyzer import analyze_product
            from pipeline.emotional_engine import build_emotional_package
            a  = analyze_product(task["name"], task["description"], task["price"])
            ep = build_emotional_package(task["name"], a.category, a.gender, task["price"])
            msg = f"🔬 *A/B Hooks — {task['name']}*\n\n"
            for i, h in enumerate(ep.ab_hooks[:3], 1): msg += f"*Hook {i}:* {h}\n\n"
            msg += "Test mỗi cái 24h rồi chọn hook CTR cao nhất 💡"
            await q.message.reply_text(msg, parse_mode="Markdown")
        except Exception as e:
            await q.message.reply_text(f"❌ `{e}`", parse_mode="Markdown")

    elif data.startswith("plat_"):
        uid = int(data.split("_")[1])
        kb  = [[InlineKeyboardButton("TikTok",  callback_data=f"setp_{uid}_tiktok"),
                InlineKeyboardButton("Shopee",  callback_data=f"setp_{uid}_shopee"),
                InlineKeyboardButton("Cả hai",  callback_data=f"setp_{uid}_both")]]
        await q.message.reply_text("Chọn platform:", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("setp_"):
        parts = data.split("_",2); uid, platform = int(parts[1]), parts[2]
        if uid in _pending: _pending[uid]["platform"] = platform
        await q.message.reply_text(f"✅ Platform: `{platform}`", parse_mode="Markdown")

async def _dispatch(message, task: dict):
    url = _colab_url()
    if not url:
        await message.reply_text(
            "⚠️ *Colab chưa kết nối!*\n\n"
            "1️⃣ Mở file `affiliate_video_bot_v7.ipynb` trong Colab\n"
            "2️⃣ Đổi runtime → T4 GPU\n"
            "3️⃣ Chạy Cell 0 → 1 → 2 → 4 theo thứ tự\n"
            "4️⃣ Telegram sẽ tự nhận thông báo khi Colab ready",
            parse_mode="Markdown"); return

    payload = {
        "user_id": task.get("user_id"), "name": task.get("name"),
        "price": task.get("price"), "description": task.get("description", task.get("name")),
        "platform": task.get("platform","tiktok"),
        "callback_url": f"{Config.RENDER_URL}/colab/callback" if Config.RENDER_URL else "",
        "secret": Config.COLAB_SECRET,
    }
    result = _call("generate", payload, timeout=30)
    if "error" in result:
        await message.reply_text(
            f"❌ Không gửi được sang Colab:\n`{result['error']}`\n\n"
            "• `/wake` để check Colab\n• Nếu ngrok hết session: chạy lại Cell 4 trong Colab",
            parse_mode="Markdown")
    else:
        await message.reply_text(
            "🚀 *Task đã gửi sang Colab!*\n\n"
            "⏱️ ~3-8 phút tuỳ engine + GPU\n"
            "📲 Video xong tự gửi về đây.\n\n"
            "Dùng `/wake` để check trạng thái Colab.",
            parse_mode="Markdown")

# ── Status / Colab commands ─────────────────────────────────────────────────
async def cmd_status(update, ctx):
    u = _colab_url()
    await update.message.reply_text(
        f"🤖 *Bot Status v7*\n\n🌐 Render: `{Config.RENDER_URL or 'chưa set'}`\n"
        f"🔗 Colab: {f'`{u[:50]}`' if u else '❌ chưa kết nối'}\n"
        f"🎬 Engine: `{Config.VIDEO_ENGINE}`\n📊 Ngành hàng: 10",
        parse_mode="Markdown")
async def cmd_wake(update, ctx):
    u = _colab_url()
    if not u: await update.message.reply_text("❌ Chưa set URL Colab. Chạy notebook và dùng /setcolab <url>"); return
    await update.message.reply_text("🔄 Đang ping Colab...")
    alive = _ping()
    if alive:
        info = _call("info", {})
        gpu  = info.get("gpu","T4") if "error" not in info else "T4"
        await update.message.reply_text(f"✅ *Colab đang sống!*\n\n🖥️ GPU: `{gpu}`\n\nDùng `/tao` ngay!", parse_mode="Markdown")
    else:
        await update.message.reply_text("😴 Colab không phản hồi.\n\n→ Vào Colab → chạy lại Cell 4\n→ `/setcolab <url_mới>`")
async def cmd_setcolab(update, ctx):
    args = ctx.args
    if not args: await update.message.reply_text("Dùng: `/setcolab https://xxxx.ngrok-free.app`", parse_mode="Markdown"); return
    url = args[0].strip().rstrip("/")
    if not url.startswith("http"): await update.message.reply_text("❌ URL phải bắt đầu https://"); return
    _colab["url"] = url
    alive = _ping()
    status = "✅ Colab đang sống!" if alive else "⚠️ URL đã lưu nhưng Colab chưa phản hồi"
    await update.message.reply_text(f"{status}\n\n🔗 `{url}`", parse_mode="Markdown")
async def cmd_colabstatus(update, ctx):
    u = _colab_url(); alive = _ping() if u else False
    await update.message.reply_text(
        f"📡 *Colab Status*\n\n🔗 URL: `{u or 'chưa set'}`\n"
        f"📶 Ping: {'✅ OK' if alive else '❌ FAIL'}\n🌐 Render: `{Config.RENDER_URL or 'chưa set'}`",
        parse_mode="Markdown")
async def cmd_autocolab(update, ctx):
    args = ctx.args
    if not args: await update.message.reply_text("Dùng: `/autocolab on` hoặc `/autocolab off`", parse_mode="Markdown"); return
    _colab["auto_ping"] = args[0].lower() == "on"
    await update.message.reply_text(f"{'✅ Auto-ping bật' if _colab['auto_ping'] else '⏸️ Auto-ping tắt'}")
async def cmd_drive(update, ctx):
    try:
        from pipeline.drive_manager import drive_mgr
        s = drive_mgr.drive_stats(); total = sum(v["size_mb"] for v in s.values())
        t = "📊 *Google Drive:*\n\n" + "".join(f"  📁 `{k}/`: {v['size_mb']} MB\n" for k,v in s.items())
        t += f"\n💾 Tổng: `{total:.1f} MB`"
        await update.message.reply_text(t, parse_mode="Markdown")
    except Exception as e: await update.message.reply_text(f"❌ `{e}`", parse_mode="Markdown")
async def cmd_clear(update, ctx):
    _pending.pop(update.effective_user.id, None); await update.message.reply_text("🗑️ Cleared.")

def _auto_ping_thread():
    while True:
        time.sleep(Config.COLAB_PING_INTERVAL_MIN * 60)
        if _colab.get("auto_ping") and _colab_url(): _ping()

def start_bot():
    global _bot_app, _loop
    if not Config.TELEGRAM_TOKEN: logger.error("TELEGRAM_TOKEN not set"); return
    _loop = asyncio.new_event_loop(); asyncio.set_event_loop(_loop)
    _bot_app = Application.builder().token(Config.TELEGRAM_TOKEN).build()
    for cmd, handler in [
        ("start", cmd_start), ("help", cmd_help), ("tao", cmd_tao),
        ("caption", cmd_caption), ("abtest", cmd_abtest), ("trending", cmd_trending),
        ("setcolab", cmd_setcolab), ("wake", cmd_wake), ("colabstatus", cmd_colabstatus),
        ("autocolab", cmd_autocolab), ("drive", cmd_drive), ("status", cmd_status), ("clear", cmd_clear),
    ]: _bot_app.add_handler(CommandHandler(cmd, handler))
    _bot_app.add_handler(CallbackQueryHandler(handle_callback))
    _bot_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    logger.info("✅ Bot v7 starting...")
    _loop.run_until_complete(_bot_app.run_polling(drop_pending_updates=True))

if __name__ == "__main__":
    threading.Thread(target=_auto_ping_thread, daemon=True).start()
    threading.Thread(target=start_bot, daemon=True).start()
    flask_app.run(host=Config.HOST, port=Config.PORT, debug=False, use_reloader=False)
