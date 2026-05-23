"""
app.py — Affiliate Video Bot v6 — Render Web Server + Telegram Bot
=============================================================================
Kiến trúc:
  Telegram ──► Render (app.py) ──► Colab (AI GPU) ──► Render callback ──► Telegram

Render: Luôn online 24/7 (ping bởi Cron-job mỗi 14 phút)
Colab:  Xử lý AI nặng (video generation, ~3-5 phút/video)
=============================================================================
"""
import asyncio
import logging
import os
import threading
import time
from typing import Optional

import requests
from flask import Flask, jsonify, request
from telegram import (
    Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
)
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler,
    ContextTypes, MessageHandler, filters,
)

from config import Config

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("AffiliateBot")

# ══════════════════════════════════════════════════════════════════════════════
#  FLASK APP (web server trên Render)
# ══════════════════════════════════════════════════════════════════════════════

flask_app = Flask(__name__)

# ── State ─────────────────────────────────────────────────────────────────────
_pending: dict = {}
_colab_state: dict = {"webhook_url": Config.COLAB_WEBHOOK_URL}
_bot_app: Optional[Application] = None
_event_loop = None

# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_colab_url() -> str:
    return _colab_state.get("webhook_url", "").rstrip("/")


def _call_colab(endpoint: str, payload: dict, timeout: int = 30) -> dict:
    base = _get_colab_url()
    if not base:
        return {"error": "Colab chưa kết nối. Dùng /setcolab <url> trước."}
    try:
        resp = requests.post(f"{base}/{endpoint}", json=payload, timeout=timeout)
        return resp.json()
    except requests.Timeout:
        return {"error": f"Colab không phản hồi sau {timeout}s. Dùng /wake để kiểm tra."}
    except Exception as e:
        return {"error": str(e)}


def _ping_colab() -> bool:
    base = _get_colab_url()
    if not base:
        return False
    try:
        resp = requests.get(f"{base}/ping", timeout=12)
        return resp.status_code == 200
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════════
#  FLASK ROUTES
# ══════════════════════════════════════════════════════════════════════════════

@flask_app.route("/ping", methods=["GET"])
def ping():
    """Keep-alive cho Cron-job + health check cho Render."""
    return jsonify({"status": "alive", "service": "affiliate-video-bot-v6"}), 200


@flask_app.route("/health", methods=["GET"])
def health():
    colab_url = _get_colab_url()
    return jsonify({
        "status": "healthy",
        "colab_connected": bool(colab_url),
        "colab_url_set": bool(colab_url),
        "version": "6.0",
        "engine": Config.VIDEO_ENGINE,
    }), 200


@flask_app.route("/colab/callback", methods=["POST"])
def colab_callback():
    """
    Colab gọi về sau khi xử lý xong video.
    Payload: { user_id, status, video_url, caption, error }
    """
    if request.headers.get("X-Bot-Secret") != Config.COLAB_SECRET:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json(silent=True) or {}
    user_id  = data.get("user_id")
    status   = data.get("status", "unknown")
    video_url= data.get("video_url", "")
    caption  = data.get("caption", "")
    error    = data.get("error", "")

    if _bot_app and user_id:
        asyncio.run_coroutine_threadsafe(
            _send_result_to_user(int(user_id), status, video_url, caption, error),
            _event_loop,
        )

    return jsonify({"received": True}), 200


@flask_app.route("/colab/seturl", methods=["POST"])
def colab_seturl():
    """Colab tự đăng ký URL ngrok về (dùng trong Cell auto-register)."""
    secret = request.headers.get("X-Bot-Secret", "")
    if secret != Config.COLAB_SECRET:
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json(silent=True) or {}
    url  = data.get("url", "").strip().rstrip("/")
    if not url.startswith("http"):
        return jsonify({"error": "URL không hợp lệ"}), 400

    _colab_state["webhook_url"] = url
    logger.info(f"✅ Colab tự đăng ký URL: {url}")

    # Notify user nếu cần
    notify_uid = data.get("notify_user_id")
    if notify_uid and _bot_app:
        asyncio.run_coroutine_threadsafe(
            _bot_app.bot.send_message(
                chat_id=int(notify_uid),
                text=(
                    f"🤖 *Colab đã tự kết nối!*\n\n"
                    f"🔗 URL: `{url}`\n"
                    f"✅ Sẵn sàng nhận task. Dùng `/tao` để tạo video ngay."
                ),
                parse_mode="Markdown",
            ),
            _event_loop,
        )

    return jsonify({"success": True, "url": url}), 200


async def _send_result_to_user(
    user_id: int, status: str,
    video_url: str, caption: str, error: str
):
    """Gửi kết quả video về Telegram sau khi Colab xử lý xong."""
    if not _bot_app:
        return
    try:
        if status == "success" and video_url:
            await _bot_app.bot.send_video(
                chat_id=user_id,
                video=video_url,
                caption=caption[:1024] if caption else "🎬 Video của bạn đây!",
                parse_mode="Markdown",
            )
        elif status == "success_drive":
            await _bot_app.bot.send_message(
                chat_id=user_id,
                text=(
                    f"✅ *Video đã tạo xong!*\n\n"
                    f"📂 Đã lưu vào Google Drive:\n`AffiliateBot/outputs/`\n\n"
                    f"{caption}"
                ),
                parse_mode="Markdown",
            )
        else:
            await _bot_app.bot.send_message(
                chat_id=user_id,
                text=f"❌ Tạo video thất bại:\n`{error or 'Lỗi không xác định'}`\n\nThử lại bằng `/tao`",
                parse_mode="Markdown",
            )
    except Exception as e:
        logger.error(f"Không gửi được kết quả cho user {user_id}: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  TELEGRAM COMMANDS
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Affiliate Video Bot v6 — 2026*\n\n"
        "🤖 Bot AI tạo video affiliate viral cho TikTok & Shopee\n"
        "  👗 Thời trang nữ · 👔 Nam · 👶 Trẻ em · 💕 Đôi/Gia đình\n\n"
        "📝 *Cách tạo video:*\n"
        "`/tao Tên SP | Giá | Mô tả | tiktok`\n\n"
        "📌 *Ví dụ:*\n"
        "`/tao Váy maxi hoa nhí | 299k | Váy nữ vải lụa | tiktok`\n"
        "`/tao Suit nam xanh navy | 850k | Vest công sở | both`\n\n"
        "⚡ *Quản lý Colab:*\n"
        "`/wake` — Kiểm tra / đánh thức Colab\n"
        "`/setcolab <url>` — Đăng ký URL ngrok\n"
        "`/colabstatus` — Trạng thái kết nối\n\n"
        "📊 *Thông tin:*\n"
        "`/status` — Trạng thái bot\n"
        "`/drive` — Dung lượng Google Drive\n"
        "`/help` — Hướng dẫn chi tiết",
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Hướng dẫn chi tiết v6*\n\n"
        "*Tạo video:*\n"
        "`/tao Tên | Giá | Mô tả | platform`\n"
        "Platform: `tiktok` | `shopee` | `both`\n\n"
        "*Gửi ảnh sản phẩm:*\n"
        "Gửi ảnh + caption: `Tên | Giá | Mô tả`\n"
        "→ AI tự phân tích và tạo video\n\n"
        "*Quản lý Colab:*\n"
        "`/setcolab <url>` — Đăng ký ngrok URL\n"
        "`/wake` — Ping Colab\n"
        "`/colabstatus` — Chi tiết kết nối\n"
        "`/autocolab on|off` — Tự giữ Colab sống\n\n"
        "*Khác:*\n"
        "`/drive` — Thống kê Drive\n"
        "`/status` — Trạng thái bot\n"
        "`/clear` — Xóa task đang chờ\n\n"
        "*Video engines (theo thứ tự ưu tiên):*\n"
        "1. Wan2.1-I2V-14B (tốt nhất, 12GB VRAM)\n"
        "2. CogVideoX-5B (nhanh, 8GB VRAM)\n"
        "3. AnimateDiff XL (nhẹ, 6GB VRAM)\n"
        "4. FLUX.1 + Slideshow (ảnh AI)\n"
        "5. MoviePy (không cần GPU)",
        parse_mode="Markdown",
    )


async def cmd_drive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        from pipeline.drive_manager import drive_mgr
        stats = drive_mgr.drive_stats()
        text = "📊 *Google Drive — AffiliateBot:*\n\n"
        total_mb = 0
        for folder, info in stats.items():
            text += f"  📁 `{folder}/`: {info['size_mb']} MB | {info['files']} files\n"
            total_mb += info["size_mb"]
        text += f"\n💾 Tổng: `{total_mb:.1f} MB` / 5.000.000 MB (5TB)"
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Drive error: `{e}`", parse_mode="Markdown")


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    colab_url = _get_colab_url()
    colab_display = (f"`{colab_url[:45]}...`" if len(colab_url) > 45
                     else f"`{colab_url}`" if colab_url else "❌ Chưa kết nối")
    render_url = Config.RENDER_URL or "Chưa set RENDER_URL"

    await update.message.reply_text(
        f"🤖 *Bot Status v6*\n\n"
        f"🌐 Render: `{render_url}`\n"
        f"🔗 Colab: {colab_display}\n"
        f"🎬 Engine: `{Config.VIDEO_ENGINE}`\n"
        f"📱 Platform mặc định: `{Config.DEFAULT_PLATFORM}`\n"
        f"📂 Drive root: `AffiliateBot/`\n\n"
        f"Dùng `/wake` để kiểm tra Colab.",
        parse_mode="Markdown",
    )


async def cmd_clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in _pending:
        del _pending[uid]
    await update.message.reply_text("🗑️ Task đã xóa.")


# ── Colab Control ─────────────────────────────────────────────────────────────

async def cmd_setcolab(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if not args:
        await update.message.reply_text(
            "❌ Thiếu URL!\n\n"
            "Dùng: `/setcolab https://xxxx.ngrok-free.app`\n\n"
            "Lấy URL từ Colab Cell 2 sau khi chạy ngrok.",
            parse_mode="Markdown",
        )
        return

    url = args[0].strip().rstrip("/")
    if not url.startswith("http"):
        await update.message.reply_text("❌ URL phải bắt đầu bằng `https://`", parse_mode="Markdown")
        return

    _colab_state["webhook_url"] = url
    await update.message.reply_text("🔄 Đang ping Colab...")
    alive = _ping_colab()
    if alive:
        await update.message.reply_text(
            f"✅ *Colab đã kết nối!*\n\n🔗 `{url}`\n\nDùng `/tao` để tạo video ngay.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            f"⚠️ URL đã lưu nhưng Colab chưa phản hồi.\n\n🔗 `{url}`\n\n"
            "Kiểm tra:\n• Colab đang chạy?\n• Cell ngrok đã chạy chưa?\n"
            "Dùng `/wake` sau khi Colab ready.",
            parse_mode="Markdown",
        )


async def cmd_wake(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    colab_url = _get_colab_url()
    if not colab_url:
        await update.message.reply_text(
            "❌ Colab chưa kết nối!\n\n"
            "Quy trình:\n"
            "1️⃣ Mở Colab → chọn T4 GPU\n"
            "2️⃣ Chạy Cell 1 (cài deps — lần đầu)\n"
            "3️⃣ Chạy Cell 2 (ngrok server)\n"
            "4️⃣ Copy URL ngrok\n"
            "5️⃣ Gửi: `/setcolab https://xxxx.ngrok-free.app`",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(f"🔄 Đang ping `{colab_url[:50]}...`", parse_mode="Markdown")
    alive = _ping_colab()

    if alive:
        # Lấy thêm thông tin GPU
        info = _call_colab("info", {})
        gpu_info = info.get("gpu", "T4") if "error" not in info else "T4"
        await update.message.reply_text(
            f"✅ *Colab đang hoạt động!*\n\n"
            f"🖥️ GPU: `{gpu_info}`\n"
            f"🔗 URL: `{colab_url[:50]}`\n\n"
            "Dùng `/tao` để tạo video ngay!",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "😴 *Colab không phản hồi.*\n\n"
            "Colab có thể đã disconnect hoặc ngrok hết session.\n\n"
            "Cần làm:\n"
            "1️⃣ Vào Colab → kiểm tra runtime\n"
            "2️⃣ Nếu mất kết nối → chạy lại Cell 2\n"
            "3️⃣ Gửi `/setcolab <url_moi>`\n\n"
            "💡 Colab Free disconnect sau ~12h hoặc khi tab đóng lâu.",
            parse_mode="Markdown",
        )


async def cmd_colabstatus(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    colab_url = _get_colab_url()
    if not colab_url:
        status_text = "❌ Chưa đăng ký URL"
        ping_text = "N/A"
    else:
        alive = _ping_colab()
        status_text = "✅ Online" if alive else "❌ Offline / Timeout"
        ping_text = "✅ OK" if alive else "❌ FAIL"

    await update.message.reply_text(
        f"📡 *Colab Connection Status*\n\n"
        f"🔗 URL: `{colab_url or 'Chưa set'}`\n"
        f"📶 Ping: {ping_text}\n"
        f"📊 Trạng thái: {status_text}\n\n"
        f"🌐 Render: `{Config.RENDER_URL or 'Chưa set'}`\n\n"
        f"Cập nhật URL: `/setcolab <url>`",
        parse_mode="Markdown",
    )


async def cmd_autocolab(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Bật/tắt tự động ping giữ Colab sống mỗi 10 phút."""
    args = ctx.args
    if not args:
        await update.message.reply_text(
            "Dùng: `/autocolab on` hoặc `/autocolab off`", parse_mode="Markdown"
        )
        return
    mode = args[0].lower()
    if mode == "on":
        _colab_state["auto_ping"] = True
        await update.message.reply_text(
            "✅ *Auto-ping Colab đã bật!*\n\n"
            f"Bot sẽ tự ping Colab mỗi {Config.COLAB_PING_INTERVAL_MIN} phút.\n"
            "Giảm nguy cơ Colab disconnect khi tab đóng.",
            parse_mode="Markdown",
        )
    else:
        _colab_state["auto_ping"] = False
        await update.message.reply_text("⏸️ Auto-ping Colab đã tắt.", parse_mode="Markdown")


# ── Task Creation ─────────────────────────────────────────────────────────────

async def cmd_tao(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """/tao Tên SP | Giá | Mô tả | platform"""
    text = update.message.text.replace("/tao", "").strip()
    parts = [p.strip() for p in text.split("|")]

    if len(parts) < 2:
        await update.message.reply_text(
            "❌ Sai format!\n\nDùng:\n`/tao Tên SP | Giá | Mô tả | tiktok`\n\n"
            "Ví dụ:\n`/tao Váy maxi | 299k | Váy nữ lụa | tiktok`",
            parse_mode="Markdown",
        )
        return

    name     = parts[0] if len(parts) > 0 else "Sản phẩm"
    price    = parts[1] if len(parts) > 1 else "Liên hệ"
    desc     = parts[2] if len(parts) > 2 else name
    platform = parts[3].lower() if len(parts) > 3 else Config.DEFAULT_PLATFORM
    if platform not in ("tiktok", "shopee", "both"):
        platform = Config.DEFAULT_PLATFORM

    uid = update.effective_user.id
    _pending[uid] = {
        "name": name, "price": price,
        "description": desc, "platform": platform,
        "image_path": None, "user_id": uid,
    }

    keyboard = [[
        InlineKeyboardButton("✅ Tạo ngay!", callback_data=f"gen_{uid}"),
        InlineKeyboardButton("🔄 Đổi platform", callback_data=f"plat_{uid}"),
    ]]
    await update.message.reply_text(
        f"📋 *Xác nhận:*\n\n"
        f"🏷️ Tên: `{name}`\n"
        f"💰 Giá: `{price}`\n"
        f"📝 Mô tả: `{desc}`\n"
        f"📱 Platform: `{platform}`\n\n"
        "Nhấn *Tạo ngay!* để bắt đầu.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def handle_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Nhận ảnh sản phẩm + caption → phân tích AI → tạo video."""
    import tempfile
    photo   = update.message.photo[-1]
    caption = update.message.caption or ""
    parts   = [p.strip() for p in caption.split("|")]
    name    = parts[0] if parts else "Sản phẩm"
    price   = parts[1] if len(parts) > 1 else "Liên hệ"
    desc    = parts[2] if len(parts) > 2 else caption

    photo_file = await photo.get_file()
    tmp_img = tempfile.mktemp(suffix=".jpg")
    await photo_file.download_to_drive(tmp_img)

    await update.message.reply_text("🤖 Đang phân tích ảnh...")
    try:
        from pipeline.ai_analyzer import analyze_product
        analysis = analyze_product(name, desc, image_path=tmp_img)
        gender_vi = {"women": "Nữ", "men": "Nam", "children": "Trẻ em", "baby": "Em bé", "unisex": "Unisex"}
        await update.message.reply_text(
            f"🧠 *AI nhận diện:*\n\n"
            f"👤 Đối tượng: `{gender_vi.get(analysis.gender, analysis.gender)}`\n"
            f"🏷️ Loại: `{analysis.garment_type}`\n"
            f"🎨 Phong cách: `{analysis.style_category}`\n"
            f"✨ USP: `{analysis.usp[:60]}`\n"
            f"⚡ Confidence: `{analysis.confidence:.0%}`",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.warning(f"AI analysis lỗi: {e}")

    uid = update.effective_user.id
    _pending[uid] = {
        "name": name, "price": price,
        "description": desc, "platform": "tiktok",
        "image_path": tmp_img, "user_id": uid,
    }

    keyboard = [[InlineKeyboardButton("🎬 Tạo video ngay!", callback_data=f"gen_{uid}")]]
    await update.message.reply_text(
        "✅ Sẵn sàng tạo video!\nNhấn nút bên dưới.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ── Callbacks ─────────────────────────────────────────────────────────────────

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data  = query.data

    if data.startswith("gen_"):
        uid = int(data.split("_")[1])
        if uid not in _pending:
            await query.message.reply_text("❌ Task đã hết hạn. Dùng /tao lại nhé.")
            return
        task = _pending.pop(uid)
        await query.message.reply_text("⏳ Đang gửi task sang Colab xử lý...")
        await _dispatch_to_colab(query.message, task)

    elif data.startswith("plat_"):
        uid = int(data.split("_")[1])
        kb = [[
            InlineKeyboardButton("TikTok", callback_data=f"setplat_{uid}_tiktok"),
            InlineKeyboardButton("Shopee", callback_data=f"setplat_{uid}_shopee"),
            InlineKeyboardButton("Cả hai", callback_data=f"setplat_{uid}_both"),
        ]]
        await query.message.reply_text("Chọn platform:", reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("setplat_"):
        parts = data.split("_", 2)
        uid, platform = int(parts[1]), parts[2]
        if uid in _pending:
            _pending[uid]["platform"] = platform
        await query.message.reply_text(f"✅ Platform: `{platform}`", parse_mode="Markdown")


# ── Dispatch ──────────────────────────────────────────────────────────────────

async def _dispatch_to_colab(message, task: dict):
    """Gửi task sang Colab qua HTTP."""
    colab_url = _get_colab_url()

    if not colab_url:
        await message.reply_text(
            "⚠️ Colab chưa kết nối.\n\n"
            "1️⃣ Mở Colab → chạy Cell 1+2\n"
            "2️⃣ Gửi `/setcolab <url>`\n"
            "3️⃣ Thử lại `/tao`"
        )
        return

    render_callback = f"{Config.RENDER_URL}/colab/callback" if Config.RENDER_URL else ""
    payload = {
        "user_id":      task.get("user_id"),
        "name":         task.get("name"),
        "price":        task.get("price"),
        "description":  task.get("description", task.get("name")),
        "platform":     task.get("platform", "tiktok"),
        "callback_url": render_callback,
        "secret":       Config.COLAB_SECRET,
    }

    result = _call_colab("generate", payload, timeout=30)

    if "error" in result:
        await message.reply_text(
            f"❌ Không gửi được sang Colab:\n`{result['error']}`\n\n"
            "• Dùng `/wake` kiểm tra Colab\n"
            "• Nếu ngrok hết session → chạy lại Cell 2 và `/setcolab <url_moi>`",
            parse_mode="Markdown",
        )
    else:
        await message.reply_text(
            "🚀 *Task đã gửi sang Colab!*\n\n"
            "⏱️ Thời gian xử lý: ~3-8 phút (tùy engine + GPU)\n"
            "📲 Video xong sẽ tự gửi về đây.\n\n"
            "Dùng `/wake` để check Colab bất kỳ lúc nào.",
            parse_mode="Markdown",
        )


# ══════════════════════════════════════════════════════════════════════════════
#  AUTO-PING COLAB (background thread)
# ══════════════════════════════════════════════════════════════════════════════

def _auto_ping_thread():
    """Tự động ping Colab mỗi N phút để giữ sống."""
    while True:
        time.sleep(Config.COLAB_PING_INTERVAL_MIN * 60)
        if _colab_state.get("auto_ping") and _get_colab_url():
            alive = _ping_colab()
            logger.info(f"Auto-ping Colab: {'alive' if alive else 'offline'}")


# ══════════════════════════════════════════════════════════════════════════════
#  BOT + FLASK STARTUP
# ══════════════════════════════════════════════════════════════════════════════

def start_telegram_bot():
    """Khởi động Telegram bot trong thread riêng."""
    global _bot_app, _event_loop

    if not Config.TELEGRAM_TOKEN:
        logger.error("TELEGRAM_TOKEN chưa set — bot không chạy được")
        return

    _event_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_event_loop)

    _bot_app = (
        Application.builder()
        .token(Config.TELEGRAM_TOKEN)
        .build()
    )

    _bot_app.add_handler(CommandHandler("start",        cmd_start))
    _bot_app.add_handler(CommandHandler("help",         cmd_help))
    _bot_app.add_handler(CommandHandler("tao",          cmd_tao))
    _bot_app.add_handler(CommandHandler("setcolab",     cmd_setcolab))
    _bot_app.add_handler(CommandHandler("wake",         cmd_wake))
    _bot_app.add_handler(CommandHandler("colabstatus",  cmd_colabstatus))
    _bot_app.add_handler(CommandHandler("autocolab",    cmd_autocolab))
    _bot_app.add_handler(CommandHandler("drive",        cmd_drive))
    _bot_app.add_handler(CommandHandler("status",       cmd_status))
    _bot_app.add_handler(CommandHandler("clear",        cmd_clear))
    _bot_app.add_handler(CallbackQueryHandler(handle_callback))
    _bot_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    logger.info("✅ Telegram bot đang khởi động...")
    _event_loop.run_until_complete(_bot_app.run_polling(drop_pending_updates=True))


if __name__ == "__main__":
    # Validate config
    errors = Config.validate()
    if errors:
        for e in errors:
            logger.warning(f"Config cảnh báo: {e}")

    # Start auto-ping thread
    threading.Thread(target=_auto_ping_thread, daemon=True).start()

    # Start bot in background thread
    bot_thread = threading.Thread(target=start_telegram_bot, daemon=True)
    bot_thread.start()

    # Start Flask (main thread)
    flask_app.run(
        host=Config.HOST,
        port=Config.PORT,
        debug=False,
        use_reloader=False,
    )
