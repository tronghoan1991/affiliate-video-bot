"""
app.py — Affiliate Video Bot v5 | Telegram Bot Entry Point
=============================================================================
Chạy lệnh: python app.py

Luồng hoạt động:
  1. User gửi ảnh sản phẩm hoặc text mô tả qua Telegram
  2. Bot nhận diện AI (CLIP) → GarmentAnalysis
  3. Script Writer tạo VideoScript (kịch bản video)
  4. Video Engine sinh clip AI (Wan2.1 / CogVideoX)
  5. Overlay text + nhạc nền
  6. Lưu output về Google Drive
  7. Gửi video + caption về Telegram
=============================================================================
"""
import asyncio
import logging
import os
import tempfile
from pathlib import Path

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
    logger.warning("python-telegram-bot not installed. Install with: pip install python-telegram-bot")
    TELEGRAM_AVAILABLE = False

# ── Config ────────────────────────────────────────────────────────────────────
try:
    from config import Config
except ImportError:
    class Config:
        TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
        VIDEO_ENGINE = "auto"
        DEFAULT_PLATFORM = "tiktok"


# ══════════════════════════════════════════════════════════════════════════════
#  STATE — Lưu thông tin task đang xử lý theo user
# ══════════════════════════════════════════════════════════════════════════════

_pending: dict = {}  # user_id → {name, price, garment, platform, image_path}


# ══════════════════════════════════════════════════════════════════════════════
#  COMMANDS
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Affiliate Video Bot v5 — 2026*\n\n"
        "🤖 Bot AI tạo video affiliate viral cho:\n"
        "  👗 Thời trang nữ\n"
        "  👔 Thời trang nam\n"
        "  👶 Thời trang trẻ em / baby\n"
        "  💕 Set đôi / gia đình / unisex\n\n"
        "📝 *Cách dùng:*\n"
        "Gửi thông tin sản phẩm theo format:\n"
        "`/tao [Tên SP] | [Giá] | [Mô tả] | [tiktok/shopee]`\n\n"
        "Hoặc gửi *ảnh sản phẩm* kèm caption mô tả.\n\n"
        "Ví dụ:\n"
        "`/tao Váy maxi hoa nhí | 299k | Váy nữ vải lụa mềm | tiktok`\n"
        "`/tao Suit nam xanh navy | 850k | Vest nam công sở | both`\n"
        "`/tao Set bé gái 3-8 tuổi | 185k | Bộ đồ trẻ em cotton | shopee`",
        parse_mode="Markdown",
    )


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *Hướng dẫn chi tiết*\n\n"
        "*Lệnh tạo video:*\n"
        "`/tao Tên SP | Giá | Mô tả | platform`\n\n"
        "*Platform options:*\n"
        "  `tiktok` — Video 9:16, text overlay TikTok style\n"
        "  `shopee` — Video 9:16, text overlay Shopee style\n"
        "  `both` — Tạo 2 version\n\n"
        "*Phân loại tự động (AI):*\n"
        "Bot tự nhận diện giới tính/loại sản phẩm từ tên và mô tả.\n"
        "Hoặc ghi rõ: `nam`, `nữ`, `bé`, `đôi` trong mô tả.\n\n"
        "*Lệnh khác:*\n"
        "`/drive` — Xem thống kê Google Drive\n"
        "`/status` — Kiểm tra trạng thái bot\n"
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
    import torch
    gpu_info = "✅ CUDA available" if torch.cuda.is_available() else "⚠️ CPU only (no GPU)"
    try:
        gpu_name = torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A"
    except Exception:
        gpu_name = "N/A"

    await update.message.reply_text(
        f"🤖 *Bot Status*\n\n"
        f"🖥️ GPU: {gpu_info}\n"
        f"💾 Device: {gpu_name}\n"
        f"🎬 Engine: {Config.VIDEO_ENGINE}\n"
        f"📱 Default platform: {Config.DEFAULT_PLATFORM}\n"
        f"📂 Drive: /content/drive/MyDrive/AffiliateBot/",
        parse_mode="Markdown",
    )


async def cmd_clear(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if uid in _pending:
        del _pending[uid]
    await update.message.reply_text("🗑️ Task đã được xóa.")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN TASK COMMAND: /tao
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_tao(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Parse lệnh /tao và bắt đầu pipeline."""
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
    }

    # Platform selection keyboard
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
    photo = update.message.photo[-1]  # Largest size
    caption = update.message.caption or ""

    # Parse caption nếu có format
    parts = [p.strip() for p in caption.split("|")]
    name  = parts[0] if parts else "Sản phẩm"
    price = parts[1] if len(parts) > 1 else "Liên hệ"
    desc  = parts[2] if len(parts) > 2 else caption

    # Download ảnh
    photo_file = await photo.get_file()
    tmp_img = tempfile.mktemp(suffix=".jpg")
    await photo_file.download_to_drive(tmp_img)

    # AI Analysis
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
        method_vi = "CLIP Vision AI" if "clip" in analysis.analysis_method else "Keyword AI"

        await update.message.reply_text(
            f"🧠 *AI đã nhận diện:*\n\n"
            f"👤 Đối tượng: `{gender_vi}`\n"
            f"🏷️ Loại: `{analysis.garment_type}`\n"
            f"🎨 Phong cách: `{analysis.style_category}`\n"
            f"🎯 Màu sắc: `{', '.join(analysis.color_palette)}`\n"
            f"✨ USP: `{analysis.usp}`\n"
            f"🎯 Target: `{analysis.target_customer}`\n"
            f"⚡ Method: `{method_vi}` ({analysis.confidence:.0%})\n",
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
    }

    keyboard = [[InlineKeyboardButton("🎬 Tạo video ngay!", callback_data=f"gen_{uid}")]]
    await update.message.reply_text(
        "✅ Sẵn sàng tạo video!\nNhấn nút bên dưới để bắt đầu.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ══════════════════════════════════════════════════════════════════════════════
#  CALLBACK — Xử lý button bấm
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
        await query.message.reply_text("⏳ Đang tạo video... (~3-5 phút)\n\n🎬 Đang chạy AI pipeline...")
        await _run_pipeline(query.message, task)
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
#  PIPELINE RUNNER
# ══════════════════════════════════════════════════════════════════════════════

async def _run_pipeline(message, task: dict):
    """Chạy toàn bộ pipeline tạo video."""
    name       = task["name"]
    price      = task["price"]
    desc       = task.get("description", name)
    platform   = task.get("platform", "tiktok")
    image_path = task.get("image_path")
    analysis   = task.get("analysis")

    try:
        # ── Step 1: AI Analysis (nếu chưa có) ────────────────────
        if analysis is None:
            from pipeline.ai_analyzer import analyze_product
            analysis = analyze_product(
                product_name=name,
                product_description=desc,
                image_path=image_path,
            )

        # ── Step 2: Script Writer ─────────────────────────────────
        from pipeline.script_writer import write_video_script
        script = write_video_script(
            analysis=analysis,
            product_name=name,
            product_price=price,
            platform=platform,
        )
        await message.reply_text(
            f"📝 *Kịch bản AI đã viết:*\n\n"
            f"🎯 Hook: `{script.hook_scene.hook_text[:60]}...`\n"
            f"🎵 Music: `{script.music_mood}`\n"
            f"📱 Platform: `{platform}`",
            parse_mode="Markdown",
        )

        # ── Step 3: Generate Video ────────────────────────────────
        from pipeline.video_engine import generate_affiliate_video
        platforms = ["tiktok", "shopee"] if platform == "both" else [platform]

        for plat in platforms:
            await message.reply_text(f"🎬 Đang tạo video {plat.upper()}...")
            safe_name = "".join(c for c in name[:20] if c.isalnum() or c in (" ", "_")).strip()
            out_filename = f"{safe_name}_{plat}.mp4"

            result = generate_affiliate_video(
                prompt=script.ai_prompt_main,
                negative_prompt=_get_negative(),
                product_name=name,
                product_price=price,
                garment_class=analysis.garment_key,
                gender=analysis.gender,
                platform=plat,
                image_path=image_path,
                output_filename=out_filename,
                engine=Config.VIDEO_ENGINE,
                hook_text=script.hook_scene.hook_text,
                hook_subtext=script.hook_scene.subtext,
                value_stack=script.value_scene.hook_text,
                comment_cta=script.cta_scene.subtext,
                cta=script.cta_scene.hook_text,
                music_mood=script.music_mood,
            )

            if "error" in result:
                await message.reply_text(f"❌ Lỗi tạo video: {result['error']}")
                continue

            # ── Step 4: Send result ───────────────────────────────
            video_path = result["video_path"]
            caption    = result["caption"]
            drive_path = result.get("drive_path", "")

            with open(video_path, "rb") as vf:
                await message.reply_video(
                    video=vf,
                    caption=f"✅ *Video {plat.upper()} sẵn sàng!*\n\n{caption[:900]}",
                    parse_mode="Markdown",
                )

            await message.reply_text(
                f"📊 *Thông tin video:*\n"
                f"🎯 Hook: `{script.hook_scene.hook_text[:50]}...`\n"
                f"💎 Value stack: Đã thêm\n"
                f"💬 Comment CTA: `{script.cta_scene.subtext[:40]}`\n"
                f"🎬 Engine: `{result['engine']}`\n"
                f"📂 Drive: `{drive_path}`",
                parse_mode="Markdown",
            )

    except Exception as e:
        logger.error(f"Pipeline error: {e}", exc_info=True)
        await message.reply_text(
            f"❌ Lỗi pipeline: `{str(e)[:200]}`\n\nDùng /help để xem hướng dẫn.",
            parse_mode="Markdown",
        )


def _get_negative() -> str:
    return (
        "ugly, deformed, blurry product, low quality, watermark, text in scene, "
        "extra limbs, bad anatomy, distorted face, cartoon, anime, nsfw, "
        "unrealistic motion, product hidden, oversaturated, grainy"
    )


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    if not TELEGRAM_AVAILABLE:
        logger.error("python-telegram-bot not installed. Run: pip install python-telegram-bot")
        return

    token = Config.TELEGRAM_TOKEN or os.environ.get("TELEGRAM_TOKEN", "")
    if not token:
        logger.error("TELEGRAM_TOKEN not set! Add to config.py or env vars.")
        return

    # Initialize Drive
    try:
        from pipeline.drive_manager import setup_drive
        setup_drive()
    except Exception as e:
        logger.warning(f"Drive setup: {e}")

    app = Application.builder().token(token).build()

    # Commands
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("help", cmd_help))
    app.add_handler(CommandHandler("drive", cmd_drive))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("clear", cmd_clear))
    app.add_handler(CommandHandler("tao", cmd_tao))

    # Photo handler
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    # Callback buttons
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("🚀 Affiliate Video Bot v5 starting...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
