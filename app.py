"""
=============================================================================
  AFFILIATE VIDEO BOT v4.0
  Video Engine : Wan2.1-I2V-14B (480P→960P) — 100% miễn phí
  Storage      : Google Drive Workspace (Service Account)
  Interface    : Telegram Bot — toàn bộ điều khiển qua InlineKeyboard
=============================================================================

LUỒNG PIPELINE:
  Telegram → [Phân loại CLIP] → [IDM-VTON Try-On]
           → [Wan2.1 I2V video] → [Real-ESRGAN ×2 upscale]
           → [Text Overlay] → [Music Engine]
           → [Google Drive upload] → Telegram trả kết quả
"""

import gc, logging, os, shutil, sys, tempfile, traceback, uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import torch
from telegram import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
    InputFile, Update,
)
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler,
    ConversationHandler, ContextTypes, MessageHandler, filters,
)

from config import Config
from pipeline.background import get_background_prompt
from pipeline.caption_gen import generate_caption
from pipeline.classifier import classify_garment
from pipeline.gdrive import GDriveUploader
from pipeline.music_engine import attach_trending_music
from pipeline.text_overlay import add_text_overlay
from pipeline.tryon import run_virtual_tryon
from pipeline.upscale import run_realesrgan_video
from pipeline.video_engine import run_video_pipeline

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("AffiliateBot_v4")

# ─── Conversation states ───────────────────────────────────────────────────────
(
    S_PRODUCT_IMG, S_MODEL_IMG, S_PRODUCT_INFO,
    S_PLATFORM, S_TEXT_STYLE, S_ORIENTATION,
    S_CONFIRM,
    S_SET_ENGINE, S_SET_UPSCALE,
) = range(9)


# ══════════════════════════════════════════════════════════════════════════════
#  KEYBOARD BUILDERS  — tất cả nút bấm Telegram
# ══════════════════════════════════════════════════════════════════════════════

def kb_main() -> InlineKeyboardMarkup:
    """Menu chính hiện ra khi /start hoặc /menu."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬  Tạo Video Mới",        callback_data="m:create")],
        [
            InlineKeyboardButton("📂  Video Đã Tạo",      callback_data="m:history"),
            InlineKeyboardButton("⚙️  Cài Đặt",           callback_data="m:settings"),
        ],
        [
            InlineKeyboardButton("📊  Trạng Thái Bot",    callback_data="m:status"),
            InlineKeyboardButton("💡  Hướng Dẫn",         callback_data="m:help"),
        ],
    ])


def kb_platform() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎵  TikTok",             callback_data="plt:tiktok"),
            InlineKeyboardButton("🛒  Shopee",             callback_data="plt:shopee"),
        ],
        [InlineKeyboardButton("📱  Cả Hai Nền Tảng",      callback_data="plt:both")],
        [InlineKeyboardButton("◀  Quay lại",              callback_data="back:main")],
    ])


def kb_text_style() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚡  Viral (chữ vàng)",  callback_data="sty:viral"),
            InlineKeyboardButton("🤍  TikTok (trắng)",   callback_data="sty:tiktok"),
        ],
        [
            InlineKeyboardButton("🛒  Shopee (cam)",      callback_data="sty:shopee"),
            InlineKeyboardButton("🚫  Không cần chữ",    callback_data="sty:none"),
        ],
        [InlineKeyboardButton("◀  Quay lại",             callback_data="back:platform")],
    ])


def kb_orientation() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📱  Dọc 9:16 (TikTok/Reels)", callback_data="ori:portrait"),
        ],
        [
            InlineKeyboardButton("🖥  Ngang 16:9 (YouTube)",    callback_data="ori:landscape"),
        ],
        [InlineKeyboardButton("◀  Quay lại",                    callback_data="back:style")],
    ])


def kb_confirm(ud: dict) -> InlineKeyboardMarkup:
    """Nút xác nhận cuối với tóm tắt."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅  Bắt đầu tạo video!",  callback_data="run:start")],
        [InlineKeyboardButton("🔄  Làm lại từ đầu",     callback_data="m:create")],
        [InlineKeyboardButton("❌  Huỷ",                callback_data="back:main")],
    ])


def kb_settings(engine: str, scale: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"🔧  Engine: {engine}",       callback_data="set:engine")],
        [InlineKeyboardButton(f"✨  Upscale: {scale}×",      callback_data="set:upscale")],
        [InlineKeyboardButton(f"🎞  Định dạng: Vertical",    callback_data="set:orientation")],
        [InlineKeyboardButton("◀  Về Menu Chính",            callback_data="back:main")],
    ])


def kb_engine() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🌟  Wan2.1 I2V (tốt nhất, ~13GB)", callback_data="eng:wan21")],
        [InlineKeyboardButton("⚡  AnimateDiff (nhanh, ~8GB)",     callback_data="eng:animatediff")],
        [InlineKeyboardButton("☁️  HF Spaces Cloud (0 GPU)",       callback_data="eng:cloud")],
        [InlineKeyboardButton("🤖  Auto (tự chọn tốt nhất)",       callback_data="eng:auto")],
        [InlineKeyboardButton("◀  Quay lại",                       callback_data="back:settings")],
    ])


def kb_back_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("◀  Về Menu Chính", callback_data="back:main")
    ]])


def kb_after_video() -> InlineKeyboardMarkup:
    """Hiện sau khi gửi xong video."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬  Tạo Video Mới",       callback_data="m:create")],
        [
            InlineKeyboardButton("📂  Xem Drive",         callback_data="m:history"),
            InlineKeyboardButton("📊  Trạng Thái",        callback_data="m:status"),
        ],
    ])


# ══════════════════════════════════════════════════════════════════════════════
#  AUTH & HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _allowed(uid: int) -> bool:
    return not Config.ALLOWED_USER_IDS or uid in Config.ALLOWED_USER_IDS


def _free():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


async def _dl(bot, fid: str, dest: Path) -> Path:
    f = await bot.get_file(fid)
    await f.download_to_drive(str(dest))
    return dest


def _photo_id(msg) -> Optional[str]:
    if msg.photo:
        return msg.photo[-1].file_id
    if msg.document and (msg.document.mime_type or "").startswith("image"):
        return msg.document.file_id
    return None


def _summary(ud: dict) -> str:
    eng = {"wan21":"Wan2.1 I2V","animatediff":"AnimateDiff","cloud":"HF Cloud","auto":"Auto"}
    return (
        f"📋 *Tóm tắt yêu cầu:*\n\n"
        f"🏷  Sản phẩm : `{ud.get('name') or '(chưa nhập)'}`\n"
        f"💰  Giá       : `{ud.get('price') or '(chưa nhập)'}`\n"
        f"📱  Nền tảng  : `{ud.get('platform','tiktok')}`\n"
        f"✍️  Style chữ : `{ud.get('style','tiktok') or 'Không có'}`\n"
        f"📐  Định dạng : `{ud.get('orientation','portrait')}`\n"
        f"🔧  Engine    : `{eng.get(Config.VIDEO_ENGINE,'Auto')}`\n"
    )


# ══════════════════════════════════════════════════════════════════════════════
#  COMMAND HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _allowed(update.effective_user.id):
        await update.message.reply_text("⛔ Bạn không có quyền dùng bot này.")
        return
    await update.message.reply_text(
        "👗 *Affiliate Video Bot v4.0*\n\n"
        "📌 Biến ảnh sản phẩm → Video người mẫu mặc đồ\n"
        "🎬 Engine: *Wan2.1 I2V* (tốt hơn HunyuanVideo, 100% miễn phí)\n"
        "📐 Upscale: *Real-ESRGAN 2×* → ~960P Full-HD\n"
        "☁️ Lưu tự động: *Google Drive Workspace*\n\n"
        "👇 Chọn chức năng:",
        parse_mode="Markdown",
        reply_markup=kb_main(),
    )


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📋 *Menu chính:*", parse_mode="Markdown", reply_markup=kb_main()
    )


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Đã huỷ.", reply_markup=kb_main())
    return ConversationHandler.END


# ══════════════════════════════════════════════════════════════════════════════
#  CALLBACK ROUTER — tất cả nút bấm đi qua đây
# ══════════════════════════════════════════════════════════════════════════════

async def cb_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Router cho các callback không nằm trong ConversationHandler."""
    q   = update.callback_query
    await q.answer()
    d   = q.data

    if d == "back:main":
        await q.edit_message_text(
            "📋 *Menu chính:*", parse_mode="Markdown", reply_markup=kb_main()
        )
        return ConversationHandler.END

    if d == "m:help":
        await q.edit_message_text(
            "💡 *Hướng dẫn sử dụng*\n\n"
            "1️⃣  Nhấn *Tạo Video Mới* từ menu\n"
            "2️⃣  Gửi ảnh sản phẩm (trang phục, nền trắng)\n"
            "3️⃣  Gửi ảnh mặt mẫu (chân dung rõ ràng)\n"
            "4️⃣  Nhập `Tên | Giá` hoặc /skip\n"
            "5️⃣  Chọn nền tảng → style chữ → định dạng\n"
            "6️⃣  Xác nhận → chờ 5-15 phút → nhận video!\n\n"
            "📂 Video tự lưu Google Drive theo tháng\n\n"
            "⚙️  */settings* — đổi engine, upscale scale\n"
            "📊  */status*   — xem tình trạng GPU/server\n"
            "❌  */cancel*   — huỷ bất kỳ lúc nào",
            parse_mode="Markdown",
            reply_markup=kb_back_main(),
        )
        return

    if d == "m:status":
        await _cb_status(q)
        return

    if d == "m:history":
        await _cb_history(q, context)
        return

    if d == "m:settings":
        await q.edit_message_text(
            "⚙️ *Cài đặt Bot*\n\nChọn thông số muốn thay đổi:",
            parse_mode="Markdown",
            reply_markup=kb_settings(Config.VIDEO_ENGINE, Config.REALESRGAN_SCALE),
        )
        return

    if d == "set:engine":
        await q.edit_message_text(
            "🔧 *Chọn Video Engine:*\n\n"
            "• *Wan2.1* — best free, 480P→960P, ~13GB VRAM\n"
            "• *AnimateDiff* — nhẹ hơn, ~8GB VRAM\n"
            "• *HF Spaces* — cloud, không cần GPU\n"
            "• *Auto* — tự chọn tốt nhất theo VRAM",
            parse_mode="Markdown",
            reply_markup=kb_engine(),
        )
        return

    if d.startswith("eng:"):
        Config.VIDEO_ENGINE = d.split(":")[1]
        await q.edit_message_text(
            f"✅ Engine đã đổi sang: *{Config.VIDEO_ENGINE}*",
            parse_mode="Markdown",
            reply_markup=kb_settings(Config.VIDEO_ENGINE, Config.REALESRGAN_SCALE),
        )
        return

    if d == "set:upscale":
        Config.REALESRGAN_SCALE = 4 if Config.REALESRGAN_SCALE == 2 else 2
        await q.edit_message_text(
            f"✅ Upscale đổi sang: *{Config.REALESRGAN_SCALE}×*\n"
            f"({'960P Full-HD' if Config.REALESRGAN_SCALE == 2 else '1920P 4K-ish'})",
            parse_mode="Markdown",
            reply_markup=kb_settings(Config.VIDEO_ENGINE, Config.REALESRGAN_SCALE),
        )
        return

    if d == "back:settings":
        await q.edit_message_text(
            "⚙️ *Cài đặt Bot*", parse_mode="Markdown",
            reply_markup=kb_settings(Config.VIDEO_ENGINE, Config.REALESRGAN_SCALE),
        )
        return

    if d == "run:start":
        await q.edit_message_text("⏳ Đang khởi động pipeline...")
        await _run_pipeline(q.message.chat_id, context)
        return


async def _cb_status(q: CallbackQuery):
    dev   = "cuda" if torch.cuda.is_available() else "cpu"
    if torch.cuda.is_available():
        name  = torch.cuda.get_device_name(0)
        total = torch.cuda.get_device_properties(0).total_memory / 1e9
        used  = torch.cuda.memory_allocated(0) / 1e9
        gpu   = f"`{name}`\n💾 VRAM: `{used:.1f}/{total:.1f} GB`"
    else:
        gpu   = "`Không có GPU (CPU mode)`"

    eng_label = {
        "wan21": "Wan2.1 I2V 14B (best)",
        "animatediff": "AnimateDiff (fallback)",
        "cloud": "HF Spaces Cloud",
        "auto": "Auto (local→cloud)",
    }.get(Config.VIDEO_ENGINE, "Auto")

    await q.edit_message_text(
        f"📊 *Trạng thái hệ thống*\n\n"
        f"🖥  GPU: {gpu}\n"
        f"🔧  Engine: `{eng_label}`\n"
        f"✨  Upscale: `{Config.REALESRGAN_SCALE}× Real-ESRGAN`\n"
        f"☁️  Google Drive: `{'✅ Đã cấu hình' if Config.GDRIVE_FOLDER_ID else '❌ Chưa cấu hình'}`\n"
        f"🎵  Music: `{'✅ Pixabay API' if Config.PIXABAY_KEY else '📁 Local files only'}`",
        parse_mode="Markdown",
        reply_markup=kb_back_main(),
    )


async def _cb_history(q: CallbackQuery, context: ContextTypes.DEFAULT_TYPE):
    history = context.bot_data.get("history", [])[-8:]
    if not history:
        text = "📂 *Lịch sử video*\n\nChưa có video nào được tạo trong phiên này."
    else:
        lines = ["📂 *Video gần nhất:*\n"]
        for i, item in enumerate(reversed(history), 1):
            name = item.get("name", "?")[:30]
            ts   = item.get("ts", "?")
            url  = item.get("url", "")
            eng  = item.get("engine", "?")
            lines.append(f"{i}. `{name}`\n   📅 {ts} | 🔧 {eng}")
            if url:
                lines.append(f"   [📂 Xem Drive]({url})")
        text = "\n".join(lines)

    await q.edit_message_text(
        text, parse_mode="Markdown",
        disable_web_page_preview=True,
        reply_markup=kb_back_main(),
    )


# ══════════════════════════════════════════════════════════════════════════════
#  CONVERSATION FLOW  (Tạo video)
# ══════════════════════════════════════════════════════════════════════════════

async def cb_start_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data.clear()
    await q.edit_message_text(
        "📦 *Bước 1/5 — Ảnh sản phẩm*\n\n"
        "Gửi ảnh trang phục trên nền *trắng hoặc sáng*.\n\n"
        "💡 *Mẹo:* Ảnh nền trắng → Try-On đẹp hơn nhiều!",
        parse_mode="Markdown",
    )
    return S_PRODUCT_IMG


async def recv_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fid = _photo_id(update.message)
    if not fid:
        await update.message.reply_text("⚠️ Vui lòng gửi ảnh (JPG/PNG). Thử lại!")
        return S_PRODUCT_IMG

    tmp = Path(tempfile.mkdtemp(prefix="afv4_"))
    p   = tmp / "product.jpg"
    await _dl(context.bot, fid, p)
    context.user_data.update({"product": str(p), "tmp": str(tmp)})

    await update.message.reply_text(
        "✅ Nhận ảnh sản phẩm!\n\n"
        "👤 *Bước 2/5 — Ảnh mặt mẫu*\n\n"
        "Gửi ảnh *chân dung rõ mặt* của người mẫu.\n"
        "💡 Mặt chiếm >50% khung hình, nền đơn giản.",
        parse_mode="Markdown",
    )
    return S_MODEL_IMG


async def recv_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fid = _photo_id(update.message)
    if not fid:
        await update.message.reply_text("⚠️ Vui lòng gửi ảnh mặt mẫu. Thử lại!")
        return S_MODEL_IMG

    tmp = Path(context.user_data["tmp"])
    p   = tmp / "model.jpg"
    await _dl(context.bot, fid, p)
    context.user_data["model"] = str(p)

    await update.message.reply_text(
        "✅ Nhận ảnh mặt mẫu!\n\n"
        "🏷️ *Bước 3/5 — Thông tin sản phẩm*\n\n"
        "Nhập theo mẫu:\n`Tên sản phẩm | Giá`\n\n"
        "Ví dụ: `Váy hoa nhí dáng xòe | 299.000đ`\n\n"
        "Hoặc gõ /skip để bỏ qua.",
        parse_mode="Markdown",
    )
    return S_PRODUCT_INFO


async def recv_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    parts = txt.split("|", 1)
    context.user_data["name"]  = parts[0].strip()
    context.user_data["price"] = parts[1].strip() if len(parts) > 1 else ""

    await update.message.reply_text(
        "📱 *Bước 4/5 — Nền tảng đăng bài*\n\nBạn sẽ đăng video lên đâu?",
        parse_mode="Markdown",
        reply_markup=kb_platform(),
    )
    return S_PLATFORM


async def recv_skip_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.update({"name": "", "price": ""})
    await update.message.reply_text(
        "📱 *Bước 4/5 — Nền tảng đăng bài*\n\nBạn sẽ đăng video lên đâu?",
        parse_mode="Markdown",
        reply_markup=kb_platform(),
    )
    return S_PLATFORM


async def recv_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["platform"] = q.data.split(":")[1]

    await q.edit_message_text(
        "✍️ *Bước 5/5 — Style chữ overlay*\n\nChọn kiểu chữ trên video:",
        parse_mode="Markdown",
        reply_markup=kb_text_style(),
    )
    return S_TEXT_STYLE


async def recv_style(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    raw = q.data.split(":")[1]
    context.user_data["style"] = None if raw == "none" else raw

    await q.edit_message_text(
        "📐 *Định dạng video*\n\nChọn tỉ lệ khung hình:",
        parse_mode="Markdown",
        reply_markup=kb_orientation(),
    )
    return S_ORIENTATION


async def recv_orientation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["orientation"] = q.data.split(":")[1]

    await q.edit_message_text(
        _summary(context.user_data),
        parse_mode="Markdown",
        reply_markup=kb_confirm(context.user_data),
    )
    return S_CONFIRM


# ══════════════════════════════════════════════════════════════════════════════
#  PIPELINE CHÍNH
# ══════════════════════════════════════════════════════════════════════════════

async def _run_pipeline(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    ud          = context.user_data
    uid         = str(uuid.uuid4())[:8]
    tmp         = Path(ud["tmp"])
    product     = Path(ud["product"])
    model       = Path(ud["model"])
    name        = ud.get("name", "")
    price       = ud.get("price", "")
    platform    = ud.get("platform", "tiktok")
    style       = ud.get("style", "tiktok")
    orientation = ud.get("orientation", "portrait")
    device      = "cuda" if torch.cuda.is_available() else "cpu"

    status = await context.bot.send_message(chat_id, "🤖 Pipeline v4.0 đang khởi động...")

    async def upd(txt: str, md: bool = False):
        kw = {"parse_mode": "Markdown"} if md else {}
        await status.edit_text(txt, **kw)

    try:
        # ── 1. Phân loại trang phục ────────────────────────────────────────
        await upd("🔍 [1/6] Đang phân tích trang phục (CLIP)...")
        garment = classify_garment(product, device="cpu")
        bg      = get_background_prompt(garment)
        logger.info(f"[{uid}] garment={garment}")

        # ── 2. Virtual Try-On ──────────────────────────────────────────────
        await upd(f"👗 [2/6] Đang ghép trang phục lên mẫu...\n_({garment})_", md=True)
        tryon = tmp / f"tryon_{uid}.png"
        run_virtual_tryon(product, model, tryon, device, bg)
        _free()

        # ── 3. Video Generation (Wan2.1 / AnimateDiff / HF) ──────────────
        await upd(
            "🎬 [3/6] Đang tạo video với *Wan2.1 I2V*...\n"
            "_(5-15 phút — đây là bước lâu nhất, xin đừng gửi lệnh mới)_", md=True
        )
        raw_video = tmp / f"raw_{uid}.mp4"
        engine_used = await run_video_pipeline(
            image_path=tryon,
            output_path=raw_video,
            bg_prompt=bg,
            garment_class=garment,
            orientation=orientation,
            device=device,
        )
        _free()

        # ── 4. Real-ESRGAN Upscale ─────────────────────────────────────────
        scale = Config.REALESRGAN_SCALE
        await upd(
            f"✨ [4/6] Upscale {scale}× (Real-ESRGAN)...\n"
            f"_({'960P Full-HD' if scale == 2 else '1920P 4K'})_", md=True
        )
        upscaled = tmp / f"up_{uid}.mp4"
        try:
            run_realesrgan_video(raw_video, upscaled, scale, device)
            working = upscaled
        except Exception as e:
            logger.warning(f"[{uid}] ESRGAN skip: {e}")
            working = raw_video
        _free()

        # ── 5. Text Overlay & Music ────────────────────────────────────────
        await upd("✍️ [5/6] Thêm text và nhạc trending...")
        txt_vid = tmp / f"txt_{uid}.mp4"
        if style:
            add_text_overlay(working, txt_vid, name, price, garment, platform, style)
            working = txt_vid

        final = tmp / f"final_{uid}.mp4"
        attach_trending_music(working, final, garment, platform)
        _free()

        # ── 6. Upload Google Drive ─────────────────────────────────────────
        await upd("☁️ [6/6] Đang lưu lên Google Drive...")
        ts       = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{(name or garment).replace(' ','_')[:40]}_{ts}.mp4"
        drive_url = ""
        try:
            uploader  = GDriveUploader()
            drive_url = uploader.upload_video(final, filename, platform)
        except Exception as e:
            logger.warning(f"[{uid}] Drive upload skip: {e}")

        # Lưu vào history
        h = context.bot_data.setdefault("history", [])
        h.append({
            "name": filename, "ts": datetime.now().strftime("%d/%m %H:%M"),
            "url": drive_url, "engine": engine_used,
        })
        if len(h) > 60:
            h.pop(0)

        # ── Gửi về Telegram ────────────────────────────────────────────────
        caption    = generate_caption(name, price, garment, platform)
        drive_line = f"\n\n📂 [Xem trên Drive]({drive_url})" if drive_url else ""
        fsize_mb   = final.stat().st_size / 1e6

        await upd("📤 Đang gửi video về Telegram...")

        if fsize_mb > Config.MAX_TG_VIDEO_MB:
            await context.bot.send_message(
                chat_id,
                f"✅ *Video tạo xong!*\n"
                f"_(File {fsize_mb:.0f}MB — quá lớn gửi qua Telegram)_\n"
                f"📂 Xem trực tiếp: {drive_url}\n\n{caption}",
                parse_mode="Markdown",
                reply_markup=kb_after_video(),
            )
        else:
            with open(final, "rb") as vf:
                await context.bot.send_video(
                    chat_id=chat_id,
                    video=InputFile(vf, filename=filename),
                    caption=caption + drive_line,
                    parse_mode="Markdown",
                    supports_streaming=True,
                    width=480 if orientation == "portrait" else 854,
                    height=832 if orientation == "portrait" else 480,
                    reply_markup=kb_after_video(),
                )

        await status.delete()
        logger.info(f"[{uid}] ✅ Pipeline done | engine={engine_used}")

    except Exception as e:
        tb  = traceback.format_exc()
        logger.error(f"[{uid}] Error:\n{tb}")
        msg = _err_msg(e, tb)
        await status.edit_text(msg, parse_mode="Markdown", reply_markup=kb_main())

    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        context.user_data.clear()
        _free()


def _err_msg(e: Exception, tb: str) -> str:
    if "OutOfMemory" in tb or "CUDA out of memory" in tb:
        return (
            "❌ *Hết VRAM!*\n\n"
            "💡 Giải pháp:\n"
            "• Vào ⚙️ Cài đặt → đổi sang *AnimateDiff* hoặc *HF Spaces*\n"
            "• Nếu dùng Colab: Runtime → Disconnect → Reconnect → chọn A100\n"
            "• Gõ /menu để thử lại"
        )
    if "credentials" in tb.lower() or "Drive" in tb:
        return (
            "❌ *Lỗi Google Drive!*\n\n"
            "Kiểm tra lại `GDRIVE_CREDENTIALS_JSON` và `GDRIVE_ROOT_FOLDER_ID`\n"
            "trong Colab Secrets (xem hướng dẫn)."
        )
    if "model" in tb.lower() and ("not found" in tb.lower() or "FileNotFound" in tb):
        return "❌ *Không tìm thấy model!*\nChạy lại Cell *Download Models* trong Colab."
    return (
        f"❌ *Lỗi không xác định:*\n`{str(e)[:250]}`\n\n"
        "Gõ /menu để thử lại hoặc kiểm tra logs Colab."
    )


# ══════════════════════════════════════════════════════════════════════════════
#  BACK NAVIGATION trong conversation
# ══════════════════════════════════════════════════════════════════════════════

async def cb_back_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await q.edit_message_text(
        "📱 *Bước 4/5 — Nền tảng*\n\nBạn đăng lên đâu?",
        parse_mode="Markdown", reply_markup=kb_platform(),
    )
    return S_PLATFORM


async def cb_back_style(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await q.edit_message_text(
        "✍️ *Bước 5/5 — Style chữ*",
        parse_mode="Markdown", reply_markup=kb_text_style(),
    )
    return S_TEXT_STYLE


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

def main():
    if not Config.TELEGRAM_BOT_TOKEN:
        raise ValueError("Chưa set TELEGRAM_BOT_TOKEN trong .env hoặc Secrets!")

    app = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()

    # ── ConversationHandler: luồng tạo video ──────────────────────────────────
    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_start_create, pattern=r"^m:create$")],
        states={
            S_PRODUCT_IMG:  [MessageHandler(filters.PHOTO | filters.Document.IMAGE, recv_product)],
            S_MODEL_IMG:    [MessageHandler(filters.PHOTO | filters.Document.IMAGE, recv_model)],
            S_PRODUCT_INFO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, recv_info),
                CommandHandler("skip", recv_skip_info),
            ],
            S_PLATFORM:     [
                CallbackQueryHandler(recv_platform, pattern=r"^plt:"),
                CallbackQueryHandler(cb_router, pattern=r"^back:main$"),
            ],
            S_TEXT_STYLE:   [
                CallbackQueryHandler(recv_style, pattern=r"^sty:"),
                CallbackQueryHandler(cb_back_platform, pattern=r"^back:platform$"),
            ],
            S_ORIENTATION:  [
                CallbackQueryHandler(recv_orientation, pattern=r"^ori:"),
                CallbackQueryHandler(cb_back_style, pattern=r"^back:style$"),
            ],
            S_CONFIRM:      [CallbackQueryHandler(cb_router, pattern=r"^(run:|back:main|m:create)")],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
        conversation_timeout=900,
    )

    # ── Handlers ──────────────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("menu",   cmd_menu))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(
        cb_router,
        pattern=r"^(back:|m:|set:|eng:|run:)",
    ))

    logger.info("🚀 Affiliate Bot v4.0 đang chạy...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
