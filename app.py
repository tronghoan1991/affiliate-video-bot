"""
app.py — Affiliate Video Bot v5 | Telegram Bot + Web Server
=============================================================================
Luồng hoạt động đầy đủ:
  1. Flask web server chạy trên PORT (cho Render health check + Cron-job ping)
  2. Telegram bot chạy song song trong asyncio event loop
  3. User gửi lệnh /wake hoặc /setcolab để kết nối với Colab
  4. Render nhận lệnh /tao → gửi task sang Colab qua webhook
  5. Colab xử lý AI (GPU) → trả video về → Render gửi lại user

Deploy: Render Web Services (Docker) → GitHub → Cron-job ping /ping
=============================================================================
"""
import asyncio
import logging
import os
import tempfile
import threading
from pathlib import Path

import requests
from flask import Flask, jsonify, request

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("AffiliateBot")

# ── Telegram imports ──────────────────────────────────────────────────────────
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application, CommandHandler, MessageHandler,
        CallbackQueryHandler, ContextTypes, filters,
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    logger.warning("python-telegram-bot not installed.")
    TELEGRAM_AVAILABLE = False

# ── Config ────────────────────────────────────────────────────────────────────
try:
    from config import Config
except ImportError:
    class Config:
        TELEGRAM_TOKEN    = os.environ.get("TELEGRAM_TOKEN", "")
        VIDEO_ENGINE      = "auto"
        DEFAULT_PLATFORM  = "tiktok"
        RENDER_URL        = os.environ.get("RENDER_URL", "")
        COLAB_WEBHOOK_URL = os.environ.get("COLAB_WEBHOOK_URL", "")


# ══════════════════════════════════════════════════════════════════════════════
#  FLASK WEB SERVER — Keep-alive + Health check
# ══════════════════════════════════════════════════════════════════════════════

flask_app = Flask(__name__)


@flask_app.route("/ping")
def ping():
    """
    Endpoint để Cron-job ping mỗi 14 phút → ngăn Render sleep.
    Cron-job.org: GET https://your-app.onrender.com/ping mỗi 14 phút
    """
    return jsonify({"status": "alive", "bot": "AffiliateVideoBot v5"}), 200


@flask_app.route("/health")
def health():
    """Health check cho Render — trả 200 OK là service đang sống."""
    colab_url = _colab_state.get("webhook_url", "")
    return jsonify({
        "status": "ok",
        "colab_connected": bool(colab_url),
        "colab_url": colab_url[:30] + "..." if len(colab_url) > 30 else colab_url,
    }), 200


@flask_app.route("/colab/callback", methods=["POST"])
def colab_callback():
    """
    Colab gọi endpoint này sau khi hoàn thành tạo video.
    Body JSON: { "user_id": 123, "video_path": "/path/to/video.mp4", "caption": "..." }
    Render nhận → gửi video về cho user qua Telegram.
    """
    data = request.get_json(silent=True) or {}
    user_id  = data.get("user_id")
    status   = data.get("status", "done")
    message  = data.get("message", "")
    video_url = data.get("video_url", "")
    caption  = data.get("caption", "")

    logger.info(f"Colab callback: user={user_id} status={status}")

    if user_id and _bot_app:
        asyncio.run_coroutine_threadsafe(
            _send_colab_result(user_id, status, message, video_url, caption),
            _event_loop,
        )

    return jsonify({"received": True}), 200


async def _send_colab_result(user_id, status, message, video_url, caption):
    """Gửi kết quả từ Colab về cho user qua Telegram."""
    try:
        bot = _bot_app.bot
        if status == "done" and video_url:
            await bot.send_message(
                chat_id=user_id,
                text=f"✅ *Video đã hoàn thành!*\n\n{caption}",
                parse_mode="Markdown",
            )
            await bot.send_video(chat_id=user_id, video=video_url)
        elif status == "error":
            await bot.send_message(
                chat_id=user_id,
                text=f"❌ Colab báo lỗi:\n`{message}`",
                parse_mode="Markdown",
            )
        else:
            await bot.send_message(chat_id=user_id, text=message or "✅ Colab đã xử lý xong.")
    except Exception as e:
        logger.error(f"Failed to send colab result to user {user_id}: {e}")


def run_flask():
    """Chạy Flask trong thread riêng — không block asyncio event loop."""
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Flask server starting on port {port}")
    flask_app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)


# ══════════════════════════════════════════════════════════════════════════════
#  STATE
# ══════════════════════════════════════════════════════════════════════════════

_pending: dict = {}     # user_id → task dict
_colab_state: dict = {  # Colab webhook URL đăng ký bằng /setcolab
    "webhook_url": Config.COLAB_WEBHOOK_URL,
}
_bot_app = None         # telegram.ext.Application instance
_event_loop = None      # asyncio event loop


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _get_colab_url() -> str:
    return _colab_state.get("webhook_url", "")


def _call_colab(endpoint: str, payload: dict) -> dict:
    """Gọi Colab qua ngrok URL."""
    base = _get_colab_url().rstrip("/")
    if not base:
        return {"error": "Colab chưa kết nối. Dùng /setcolab <url> trước."}
    try:
        resp = requests.post(f"{base}/{endpoint}", json=payload, timeout=30)
        return resp.json()
    except requests.exceptions.Timeout:
        return {"error": "Colab không phản hồi (timeout 30s). Colab có đang chạy không?"}
    except Exception as e:
        return {"error": str(e)}


def _ping_colab() -> bool:
    """Kiểm tra Colab có alive không."""
    base = _get_colab_url().rstrip("/")
    if not base:
        return False
    try:
        resp = requests.get(f"{base}/ping", timeout=10)
        return resp.status_code == 200
    except Exception:
        return False


# ══════════════════════════════════════════════════════════════════════════════
#  COMMANDS — Standard
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Affiliate Video Bot v5 — 2026*\n\n"
        "🤖 Bot AI tạo video affiliate viral cho:\n"
        "  👗 Thời trang nữ · 👔 Nam · 👶 Trẻ em · 💕 Đôi / Gia đình\n\n"
        "📝 *Cách dùng:*\n"
        "`/tao [Tên SP] | [Giá] | [Mô tả] | [tiktok/shopee]`\n\n"
        "Ví dụ:\n"
        "`/tao Váy maxi hoa nhí | 299k | Váy nữ vải lụa | tiktok`\n"
        "`/tao Suit nam xanh navy | 850k | Vest công sở | both`\n\n"
        "⚡ *Kết nối Colab:*\n"
        "`/wake` — Kiểm tra / đánh thức Colab\n"
        "`/setcolab <url>` — Đăng ký URL ngrok của Colab\n"
        "`/colabstatus` — Trạng thái Colab hiện tại",
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Hướng dẫn chi tiết*\n\n"
        "*Lệnh tạo video:*\n"
        "`/tao Tên SP | Giá | Mô tả | platform`\n\n"
        "*Platform:* `tiktok` | `shopee` | `both`\n\n"
        "*Lệnh Colab:*\n"
        "`/setcolab https://xxxx.ngrok-free.app` — Đăng ký Colab URL\n"
        "`/wake` — Ping Colab, xem có alive không\n"
        "`/colabstatus` — Chi tiết trạng thái\n\n"
        "*Lệnh khác:*\n"
        "`/drive` — Thống kê Google Drive\n"
        "`/status` — Trạng thái bot\n"
        "`/clear` — Xóa task đang chờ",
        parse_mode="Markdown",
    )


async def cmd_drive(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        from pipeline.drive_manager import drive_mgr
        stats = drive_mgr.drive_stats()
        text = "📊 *Google Drive Stats:*\n\n"
        for folder, info in stats.items():
            text += f"  `{folder}/`: {info['size_mb']} MB | {info['files']} files\n"
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Drive error: {e}")


async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    colab_url = _get_colab_url()
    colab_info = f"`{colab_url[:40]}...`" if len(colab_url) > 40 else f"`{colab_url}`" if colab_url else "❌ Chưa kết nối"
    render_url = Config.RENDER_URL or "Chưa set RENDER_URL"

    await update.message.reply_text(
        f"🤖 *Bot Status*\n\n"
        f"🌐 Render URL: `{render_url}`\n"
        f"🔗 Colab URL: {colab_info}\n"
        f"🎬 Engine: `{Config.VIDEO_ENGINE}`\n"
        f"📱 Platform mặc định: `{Config.DEFAULT_PLATFORM}`\n"
        f"📂 Drive: `/content/drive/MyDrive/AffiliateBot/`\n\n"
        f"Dùng `/wake` để kiểm tra Colab.",
        parse_mode="Markdown",
    )


async def cmd_clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in _pending:
        del _pending[uid]
    await update.message.reply_text("🗑️ Task đã được xóa.")


# ══════════════════════════════════════════════════════════════════════════════
#  COMMANDS — Colab Control
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_setcolab(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    /setcolab https://xxxx.ngrok-free.app
    Đăng ký URL ngrok của Colab để Render biết nơi gửi task AI.
    """
    args = ctx.args
    if not args:
        await update.message.reply_text(
            "❌ Thiếu URL!\n\n"
            "Dùng: `/setcolab https://xxxx.ngrok-free.app`\n\n"
            "URL này lấy từ ô ngrok trong Colab notebook (Cell 2).",
            parse_mode="Markdown",
        )
        return

    url = args[0].strip().rstrip("/")
    if not url.startswith("http"):
        await update.message.reply_text("❌ URL không hợp lệ. Phải bắt đầu bằng `https://`.", parse_mode="Markdown")
        return

    _colab_state["webhook_url"] = url
    logger.info(f"Colab URL set to: {url}")

    # Ping thử ngay
    await update.message.reply_text("🔄 Đang ping Colab...")
    alive = _ping_colab()
    if alive:
        await update.message.reply_text(
            f"✅ *Colab đã kết nối thành công!*\n\n"
            f"🔗 URL: `{url}`\n\n"
            f"Bây giờ dùng `/tao` để tạo video — Render sẽ gửi task sang Colab xử lý.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            f"⚠️ URL đã lưu nhưng Colab chưa phản hồi.\n\n"
            f"🔗 URL: `{url}`\n\n"
            f"Kiểm tra:\n"
            f"• Colab có đang chạy không?\n"
            f"• Cell ngrok đã chạy chưa?\n"
            f"• URL đúng không?\n\n"
            f"Sau khi Colab sẵn sàng, dùng `/wake` để kiểm tra lại.",
            parse_mode="Markdown",
        )


async def cmd_wake(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    /wake — Ping Colab để kiểm tra / đánh thức.
    Nếu Colab đang sleep, gửi HTTP request sẽ đánh thức nó.
    """
    colab_url = _get_colab_url()
    if not colab_url:
        await update.message.reply_text(
            "❌ Colab chưa được kết nối!\n\n"
            "Quy trình:\n"
            "1️⃣ Mở Colab → chạy Cell 1 (cài deps)\n"
            "2️⃣ Chạy Cell 2 (ngrok server)\n"
            "3️⃣ Copy URL ngrok từ Cell 2\n"
            "4️⃣ Gửi: `/setcolab https://xxxx.ngrok-free.app`",
            parse_mode="Markdown",
        )
        return

    await update.message.reply_text(f"🔄 Đang ping Colab tại `{colab_url[:50]}...`", parse_mode="Markdown")
    alive = _ping_colab()

    if alive:
        await update.message.reply_text(
            "✅ *Colab đang hoạt động!*\n\n"
            "GPU sẵn sàng nhận task. Dùng `/tao` để tạo video ngay.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "😴 *Colab không phản hồi.*\n\n"
            "Colab có thể bị disconnect hoặc ngrok đã hết session.\n\n"
            "Cần làm:\n"
            "1️⃣ Vào Colab → kiểm tra runtime còn kết nối không\n"
            "2️⃣ Nếu mất → chạy lại Cell 2 (ngrok) để lấy URL mới\n"
            "3️⃣ Gửi `/setcolab <url_moi>` để cập nhật\n\n"
            "💡 Colab Free bị disconnect sau ~12h hoặc khi tab đóng lâu.",
            parse_mode="Markdown",
        )


async def cmd_colabstatus(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Chi tiết trạng thái kết nối Colab."""
    colab_url = _get_colab_url()
    render_url = Config.RENDER_URL

    if not colab_url:
        status_text = "❌ Chưa đăng ký URL"
        ping_text = "N/A"
    else:
        alive = _ping_colab()
        status_text = "✅ Online" if alive else "❌ Offline / Timeout"
        ping_text = "OK" if alive else "FAIL"

    await update.message.reply_text(
        f"📡 *Colab Connection Status*\n\n"
        f"🔗 Colab URL: `{colab_url or 'Chưa set'}`\n"
        f"📶 Ping: `{ping_text}`\n"
        f"📊 Trạng thái: {status_text}\n\n"
        f"🌐 Render URL: `{render_url or 'Chưa set RENDER_URL env'}`\n\n"
        f"*Cập nhật URL Colab:*\n"
        f"`/setcolab https://xxxx.ngrok-free.app`",
        parse_mode="Markdown",
    )


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN TASK COMMAND: /tao
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_tao(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Parse lệnh /tao → gửi task sang Colab."""
    text = update.message.text.replace("/tao", "").strip()
    parts = [p.strip() for p in text.split("|")]

    if len(parts) < 2:
        await update.message.reply_text(
            "❌ Sai format!\nDùng: `/tao Tên SP | Giá | Mô tả | platform`",
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
        "image_path": None,
        "user_id": uid,
    }

    keyboard = [
        [
            InlineKeyboardButton("✅ Tạo ngay!", callback_data=f"gen_{uid}"),
            InlineKeyboardButton("✏️ Đổi platform", callback_data=f"plat_{uid}"),
        ]
    ]
    await update.message.reply_text(
        f"📋 *Xác nhận thông tin:*\n\n"
        f"🏷️ Tên: `{name}`\n"
        f"💰 Giá: `{price}`\n"
        f"📝 Mô tả: `{desc}`\n"
        f"📱 Platform: `{platform}`\n\n"
        "Nhấn *Tạo ngay!* để bắt đầu sinh video.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )


async def handle_photo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Nhận ảnh sản phẩm → phân tích AI → hỏi thêm thông tin."""
    photo = update.message.photo[-1]
    caption = update.message.caption or ""
    parts = [p.strip() for p in caption.split("|")]
    name  = parts[0] if parts else "Sản phẩm"
    price = parts[1] if len(parts) > 1 else "Liên hệ"
    desc  = parts[2] if len(parts) > 2 else caption

    photo_file = await photo.get_file()
    tmp_img = tempfile.mktemp(suffix=".jpg")
    await photo_file.download_to_drive(tmp_img)

    await update.message.reply_text("🤖 Đang phân tích ảnh bằng AI...")
    try:
        from pipeline.ai_analyzer import analyze_product
        analysis = analyze_product(
            product_name=name,
            product_description=desc,
            image_path=tmp_img,
        )
        gender_vi = {
            "women": "Nữ", "men": "Nam",
            "children": "Trẻ em", "baby": "Em bé", "unisex": "Unisex",
        }.get(analysis.gender, analysis.gender)
        await update.message.reply_text(
            f"🧠 *AI đã nhận diện:*\n\n"
            f"👤 Đối tượng: `{gender_vi}`\n"
            f"🏷️ Loại: `{analysis.garment_type}`\n"
            f"🎨 Phong cách: `{analysis.style_category}`\n"
            f"✨ USP: `{analysis.usp}`\n"
            f"⚡ Độ chính xác: `{analysis.confidence:.0%}`\n",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.warning(f"AI analysis failed: {e}")
        analysis = None

    uid = update.effective_user.id
    _pending[uid] = {
        "name": name, "price": price,
        "description": desc, "platform": "tiktok",
        "image_path": tmp_img,
        "analysis": analysis,
        "user_id": uid,
    }

    keyboard = [[InlineKeyboardButton("🎬 Tạo video ngay!", callback_data=f"gen_{uid}")]]
    await update.message.reply_text(
        "✅ Sẵn sàng tạo video!\nNhấn nút bên dưới để bắt đầu.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ══════════════════════════════════════════════════════════════════════════════
#  CALLBACK
# ══════════════════════════════════════════════════════════════════════════════

async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("gen_"):
        uid = int(data.split("_")[1])
        if uid not in _pending:
            await query.message.reply_text("❌ Không tìm thấy task. Dùng /tao để bắt đầu lại.")
            return
        task = _pending[uid]
        await query.message.reply_text("⏳ Đang gửi task sang Colab...")
        await _dispatch_to_colab(query.message, task)
        del _pending[uid]

    elif data.startswith("plat_"):
        uid = int(data.split("_")[1])
        keyboard = [[
            InlineKeyboardButton("TikTok", callback_data=f"setplat_{uid}_tiktok"),
            InlineKeyboardButton("Shopee", callback_data=f"setplat_{uid}_shopee"),
            InlineKeyboardButton("Cả hai", callback_data=f"setplat_{uid}_both"),
        ]]
        await query.message.reply_text("Chọn platform:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("setplat_"):
        _, uid_str, platform = data.split("_", 2)
        uid = int(uid_str)
        if uid in _pending:
            _pending[uid]["platform"] = platform
            await query.message.reply_text(f"✅ Platform đã đổi thành: `{platform}`", parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
#  DISPATCHER — Gửi task sang Colab
# ══════════════════════════════════════════════════════════════════════════════

async def _dispatch_to_colab(message, task: dict):
    """
    Gửi task sang Colab qua HTTP.
    Colab xử lý AI xong sẽ gọi lại /colab/callback trên Render.
    """
    colab_url = _get_colab_url()

    if not colab_url:
        # Colab chưa kết nối → chạy local pipeline (nếu có GPU)
        await message.reply_text(
            "⚠️ Colab chưa kết nối — đang thử chạy local...\n"
            "Nếu không có GPU, kết quả sẽ chậm hơn nhiều.\n\n"
            "💡 Để tăng tốc: mở Colab → chạy Cell 2 → `/setcolab <url>`"
        )
        await _run_pipeline_local(message, task)
        return

    # Chuẩn bị payload
    render_callback_url = f"{Config.RENDER_URL.rstrip('/')}/colab/callback" if Config.RENDER_URL else ""
    payload = {
        "user_id":      task.get("user_id"),
        "name":         task.get("name"),
        "price":        task.get("price"),
        "description":  task.get("description", task.get("name")),
        "platform":     task.get("platform", "tiktok"),
        "callback_url": render_callback_url,
    }

    result = _call_colab("generate", payload)

    if "error" in result:
        await message.reply_text(
            f"❌ Không gửi được sang Colab:\n`{result['error']}`\n\n"
            "Kiểm tra:\n"
            "• Colab có đang chạy không? Dùng `/wake`\n"
            "• URL còn đúng không? Dùng `/setcolab <url_moi>`",
            parse_mode="Markdown",
        )
    else:
        await message.reply_text(
            "🚀 *Task đã gửi sang Colab thành công!*\n\n"
            "⏱️ Thời gian xử lý: ~3-5 phút (tùy GPU)\n"
            "📲 Video hoàn thành sẽ tự động gửi về đây.\n\n"
            "💡 Dùng `/wake` để kiểm tra Colab bất kỳ lúc nào.",
            parse_mode="Markdown",
        )


async def _run_pipeline_local(message, task: dict):
    """Fallback: chạy pipeline local khi không có Colab (chậm, không GPU)."""
    name       = task["name"]
    price      = task["price"]
    desc       = task.get("description", name)
    platform   = task.get("platform", "tiktok")
    image_path = task.get("image_path")
    analysis   = task.get("analysis")

    try:
        if analysis is None:
            from pipeline.ai_analyzer import analyze_product
            analysis = analyze_product(
                product_name=name,
                product_description=desc,
                image_path=image_path,
            )

        from pipeline.script_writer import write_video_script
        script = write_video_script(analysis, name, price, platform)

        from pipeline.viral_strategy import build_viral_content
        content = build_viral_content(analysis, script, platform)

        await message.reply_text(
            f"✅ *Script đã tạo (chế độ local — không có video AI)*\n\n"
            f"📝 Hook: `{script.hook_scene.hook_text}`\n"
            f"💰 Info: `{script.reveal_scene.hook_text}`\n"
            f"🏷️ Caption:\n{content.caption[:300]}...\n\n"
            f"#️⃣ Hashtags: {' '.join(content.hashtags[:8])}\n\n"
            f"⚠️ Video AI cần Colab GPU. Dùng `/setcolab` để kết nối.",
            parse_mode="Markdown",
        )
    except Exception as e:
        logger.error(f"Local pipeline error: {e}")
        await message.reply_text(f"❌ Lỗi pipeline: `{e}`", parse_mode="Markdown")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN ENTRY
# ══════════════════════════════════════════════════════════════════════════════

def main():
    global _bot_app, _event_loop

    if not TELEGRAM_AVAILABLE:
        logger.error("python-telegram-bot not installed.")
        return

    token = Config.TELEGRAM_TOKEN
    if not token:
        logger.error("TELEGRAM_TOKEN is not set. Set env var TELEGRAM_TOKEN.")
        return

    # ── Start Flask in background thread ──────────────────────────────────────
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("Flask web server started in background thread.")

    # ── Build Telegram bot ────────────────────────────────────────────────────
    app = Application.builder().token(token).build()
    _bot_app = app

    # Standard commands
    app.add_handler(CommandHandler("start",       cmd_start))
    app.add_handler(CommandHandler("help",        cmd_help))
    app.add_handler(CommandHandler("drive",       cmd_drive))
    app.add_handler(CommandHandler("status",      cmd_status))
    app.add_handler(CommandHandler("clear",       cmd_clear))
    app.add_handler(CommandHandler("tao",         cmd_tao))

    # Colab control commands
    app.add_handler(CommandHandler("setcolab",    cmd_setcolab))
    app.add_handler(CommandHandler("wake",        cmd_wake))
    app.add_handler(CommandHandler("colabstatus", cmd_colabstatus))

    # Media & callbacks
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("Telegram bot starting (polling mode)...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
