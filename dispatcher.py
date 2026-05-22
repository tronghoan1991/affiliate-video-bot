"""
dispatcher.py — Affiliate Video Bot v4.0 — Dispatcher
=============================================================================
Chạy 24/7 trên Replit (miễn phí, không cần GPU).

Vai trò:
  - Nhận lệnh Telegram từ người dùng
  - Thu thập ảnh + thông số
  - Forward task sang Google Colab GPU Worker
  - Nhận kết quả từ Colab và gửi về người dùng
  - /wakeup: kiểm tra Colab và hướng dẫn khởi động
=============================================================================
"""

import asyncio, base64, json, logging, os, tempfile
from pathlib import Path
from typing import Optional

import aiohttp
from aiohttp import web

from telegram import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
    InputFile, Update,
)
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler,
    ConversationHandler, ContextTypes, MessageHandler, filters,
)

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("Dispatcher")

# ─── Config từ env ────────────────────────────────────────────────────────────
TOKEN           = os.environ.get("TELEGRAM_BOT_TOKEN", "")
PORT            = int(os.environ.get("PORT", 5000))
COLAB_LINK      = os.environ.get("COLAB_NOTEBOOK_URL", "")   # URL notebook Colab
ALLOWED_IDS_STR = os.environ.get("ALLOWED_USER_IDS", "")
ALLOWED_IDS     = [int(x) for x in ALLOWED_IDS_STR.split(",") if x.strip()]

# ─── Trạng thái Colab ─────────────────────────────────────────────────────────
colab_state = {
    "url": None,        # ngrok URL của Colab worker (None = chưa chạy)
    "registered_at": None,
    "last_ping": None,
}

# ─── Tham chiếu đến app Telegram (để dùng trong HTTP handlers) ────────────────
ptb_app_ref: Optional[Application] = None

# ─── Conversation states ──────────────────────────────────────────────────────
(
    S_PRODUCT_IMG, S_MODEL_IMG, S_PRODUCT_INFO,
    S_PLATFORM, S_TEXT_STYLE, S_ORIENTATION, S_CONFIRM,
) = range(7)


# ══════════════════════════════════════════════════════════════════════════════
#  HTTP SERVER — nhận đăng ký từ Colab + callback kết quả
# ══════════════════════════════════════════════════════════════════════════════

async def http_register(request: web.Request) -> web.Response:
    """Colab gọi endpoint này khi khởi động để đăng ký URL ngrok."""
    try:
        data = await request.json()
        url  = data.get("colab_url", "").rstrip("/")
        if not url:
            return web.json_response({"error": "colab_url missing"}, status=400)

        from datetime import datetime
        colab_state["url"] = url
        colab_state["registered_at"] = datetime.now().isoformat()
        colab_state["last_ping"] = datetime.now().isoformat()
        logger.info(f"✅ Colab đã đăng ký: {url}")

        # Thông báo tới tất cả user đang chờ (nếu có)
        if ptb_app_ref:
            waiting = ptb_app_ref.bot_data.get("waiting_wakeup", [])
            for chat_id in waiting:
                try:
                    await ptb_app_ref.bot.send_message(
                        chat_id,
                        "🟢 *Google Colab đã sẵn sàng!*\n\n"
                        "GPU đã được kết nối. Bạn có thể tạo video ngay bây giờ.\n"
                        "Nhấn /menu để bắt đầu!",
                        parse_mode="Markdown",
                    )
                except Exception:
                    pass
            ptb_app_ref.bot_data["waiting_wakeup"] = []

        return web.json_response({"status": "ok", "message": "Registered!"})
    except Exception as e:
        logger.error(f"Register error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def http_callback(request: web.Request) -> web.Response:
    """Colab gọi endpoint này khi xử lý video xong."""
    try:
        data = await request.json()
        chat_id   = data.get("chat_id")
        status    = data.get("status", "error")
        drive_url = data.get("drive_url", "")
        caption   = data.get("caption", "")
        engine    = data.get("engine", "?")
        error_msg = data.get("error_msg", "Lỗi không xác định")

        from datetime import datetime
        colab_state["last_ping"] = datetime.now().isoformat()

        if not chat_id or not ptb_app_ref:
            return web.json_response({"status": "ok"})

        if status == "success":
            msg = (
                f"✅ *Video đã xử lý xong!*\n\n"
                f"🔧 Engine: `{engine}`\n"
            )
            if drive_url:
                msg += f"\n📂 [Xem trên Google Drive]({drive_url})"
            if caption:
                msg += f"\n\n📝 Caption đã copy:\n{caption}"
            await ptb_app_ref.bot.send_message(
                chat_id, msg,
                parse_mode="Markdown",
                disable_web_page_preview=False,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🎬 Tạo video mới", callback_data="m:create"),
                ]]),
            )
            # Lưu history
            h = ptb_app_ref.bot_data.setdefault("history", [])
            h.append({
                "name": caption[:30] if caption else "Video",
                "ts": datetime.now().strftime("%d/%m %H:%M"),
                "url": drive_url,
                "engine": engine,
            })
        else:
            await ptb_app_ref.bot.send_message(
                chat_id,
                f"❌ *Colab báo lỗi:*\n`{error_msg[:300]}`\n\nThử lại với /menu",
                parse_mode="Markdown",
            )

        return web.json_response({"status": "ok"})
    except Exception as e:
        logger.error(f"Callback error: {e}")
        return web.json_response({"error": str(e)}, status=500)


async def http_ping(request: web.Request) -> web.Response:
    """Colab ping định kỳ để giữ kết nối."""
    from datetime import datetime
    colab_state["last_ping"] = datetime.now().isoformat()
    return web.json_response({"status": "ok"})


async def http_health(request: web.Request) -> web.Response:
    return web.json_response({
        "status": "running",
        "colab_connected": colab_state["url"] is not None,
        "colab_url": colab_state["url"],
        "last_ping": colab_state["last_ping"],
    })


def _is_colab_alive() -> bool:
    """Kiểm tra Colab có đang chạy không."""
    return colab_state["url"] is not None


# ══════════════════════════════════════════════════════════════════════════════
#  KEYBOARD BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def kb_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎬  Tạo Video Mới",     callback_data="m:create")],
        [
            InlineKeyboardButton("📂  Video Đã Tạo",   callback_data="m:history"),
            InlineKeyboardButton("⚙️  Trạng Thái",     callback_data="m:status"),
        ],
        [
            InlineKeyboardButton("🔌  Đánh Thức Colab", callback_data="m:wakeup"),
            InlineKeyboardButton("💡  Hướng Dẫn",       callback_data="m:help"),
        ],
    ])


def kb_platform() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎵  TikTok",           callback_data="plt:tiktok"),
            InlineKeyboardButton("🛒  Shopee",           callback_data="plt:shopee"),
        ],
        [InlineKeyboardButton("📱  Cả Hai Nền Tảng",    callback_data="plt:both")],
        [InlineKeyboardButton("◀  Quay lại",            callback_data="back:main")],
    ])


def kb_text_style() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚡  Viral (chữ vàng)", callback_data="sty:viral"),
            InlineKeyboardButton("🤍  TikTok (trắng)",  callback_data="sty:tiktok"),
        ],
        [
            InlineKeyboardButton("🛒  Shopee (cam)",     callback_data="sty:shopee"),
            InlineKeyboardButton("🚫  Không chữ",       callback_data="sty:none"),
        ],
        [InlineKeyboardButton("◀  Quay lại",            callback_data="back:platform")],
    ])


def kb_orientation() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱  Dọc 9:16 (TikTok/Reels)", callback_data="ori:portrait")],
        [InlineKeyboardButton("🖥  Ngang 16:9 (YouTube)",    callback_data="ori:landscape")],
        [InlineKeyboardButton("◀  Quay lại",                 callback_data="back:style")],
    ])


def kb_confirm() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅  Gửi lên Colab xử lý!", callback_data="run:start")],
        [InlineKeyboardButton("🔄  Làm lại từ đầu",       callback_data="m:create")],
        [InlineKeyboardButton("❌  Huỷ",                  callback_data="back:main")],
    ])


def kb_back_main() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("◀  Về Menu Chính", callback_data="back:main")
    ]])


def kb_wakeup() -> InlineKeyboardMarkup:
    btns = [[InlineKeyboardButton("◀  Về Menu Chính", callback_data="back:main")]]
    if COLAB_LINK:
        btns.insert(0, [InlineKeyboardButton("🚀  Mở Colab Notebook", url=COLAB_LINK)])
    return InlineKeyboardMarkup(btns)


# ══════════════════════════════════════════════════════════════════════════════
#  HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _allowed(uid: int) -> bool:
    return not ALLOWED_IDS or uid in ALLOWED_IDS


async def _dl_to_b64(bot, fid: str) -> str:
    """Tải ảnh từ Telegram, encode base64 để gửi sang Colab."""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
        f = await bot.get_file(fid)
        await f.download_to_drive(tmp.name)
        data = Path(tmp.name).read_bytes()
        return base64.b64encode(data).decode()


def _photo_id(msg) -> Optional[str]:
    if msg.photo:
        return msg.photo[-1].file_id
    if msg.document and (msg.document.mime_type or "").startswith("image"):
        return msg.document.file_id
    return None


def _summary(ud: dict) -> str:
    colab_icon = "🟢" if _is_colab_alive() else "🔴"
    return (
        f"📋 *Tóm tắt yêu cầu:*\n\n"
        f"🏷  Sản phẩm : `{ud.get('name') or '(chưa nhập)'}`\n"
        f"💰  Giá       : `{ud.get('price') or '(chưa nhập)'}`\n"
        f"📱  Nền tảng  : `{ud.get('platform','tiktok')}`\n"
        f"✍️  Style chữ : `{ud.get('style','tiktok') or 'Không có'}`\n"
        f"📐  Định dạng : `{ud.get('orientation','portrait')}`\n"
        f"🔌  Colab     : {colab_icon} {'Đang chạy' if _is_colab_alive() else 'Chưa kết nối'}\n"
    )


# ══════════════════════════════════════════════════════════════════════════════
#  COMMAND HANDLERS
# ══════════════════════════════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _allowed(update.effective_user.id):
        await update.message.reply_text("⛔ Bạn không có quyền dùng bot này.")
        return
    colab_icon = "🟢 Đang chạy" if _is_colab_alive() else "🔴 Chưa kết nối"
    await update.message.reply_text(
        "👗 *Affiliate Video Bot v4.0*\n\n"
        "📌 Biến ảnh sản phẩm → Video người mẫu mặc đồ\n"
        "🎬 Engine: *Wan2.1 I2V* (miễn phí, qua Google Colab)\n"
        "📐 Upscale: *Real-ESRGAN 2×* → ~960P Full-HD\n"
        "☁️ Lưu tự động: *Google Drive*\n\n"
        f"🔌 Trạng thái Colab: *{colab_icon}*\n\n"
        "👇 Chọn chức năng:",
        parse_mode="Markdown",
        reply_markup=kb_main(),
    )


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📋 *Menu chính:*", parse_mode="Markdown", reply_markup=kb_main())


async def cmd_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("❌ Đã huỷ.", reply_markup=kb_main())
    return ConversationHandler.END


async def cmd_wakeup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _do_wakeup(update.message.chat_id, context, reply_fn=update.message.reply_text)


async def _do_wakeup(chat_id: int, context, reply_fn=None):
    if _is_colab_alive():
        text = "🟢 *Google Colab đang chạy rồi!*\n\nBạn có thể tạo video ngay. Nhấn /menu."
        markup = kb_main()
    else:
        text = (
            "🔴 *Google Colab chưa kết nối.*\n\n"
            "Để đánh thức Colab:\n"
            "1️⃣ Nhấn nút *Mở Colab Notebook* bên dưới\n"
            "2️⃣ Đăng nhập Google nếu cần\n"
            "3️⃣ Nhấn *Runtime → Run all* (hoặc Ctrl+F9)\n"
            "4️⃣ Chờ ~3-5 phút để cài xong\n"
            "5️⃣ Bot sẽ tự báo khi Colab sẵn sàng ✅\n\n"
            "_(Bạn sẽ nhận thông báo tự động khi kết nối thành công)_"
        )
        markup = kb_wakeup()
        waiting = context.bot_data.setdefault("waiting_wakeup", [])
        if chat_id not in waiting:
            waiting.append(chat_id)

    if reply_fn:
        await reply_fn(text, parse_mode="Markdown", reply_markup=markup)


# ══════════════════════════════════════════════════════════════════════════════
#  CALLBACK ROUTER
# ══════════════════════════════════════════════════════════════════════════════

async def cb_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = q.data

    if d == "back:main":
        colab_icon = "🟢 Đang chạy" if _is_colab_alive() else "🔴 Chưa kết nối"
        await q.edit_message_text(
            f"📋 *Menu chính:*\n🔌 Colab: *{colab_icon}*",
            parse_mode="Markdown", reply_markup=kb_main()
        )
        return ConversationHandler.END

    if d == "m:wakeup":
        await _do_wakeup(
            q.message.chat_id, context,
            reply_fn=lambda *a, **kw: q.edit_message_text(*a, **kw),
        )
        return

    if d == "m:status":
        from datetime import datetime
        colab_icon  = "🟢 Đang chạy" if _is_colab_alive() else "🔴 Chưa kết nối"
        registered  = colab_state.get("registered_at", "—")
        last_ping   = colab_state.get("last_ping", "—")
        await q.edit_message_text(
            f"📊 *Trạng thái hệ thống*\n\n"
            f"🔌 Colab Worker: *{colab_icon}*\n"
            f"🕐 Kết nối lúc: `{registered}`\n"
            f"💓 Ping cuối: `{last_ping}`\n"
            f"📡 Dispatcher: `✅ Đang chạy`",
            parse_mode="Markdown", reply_markup=kb_back_main(),
        )
        return

    if d == "m:history":
        history = context.bot_data.get("history", [])[-8:]
        if not history:
            text = "📂 *Lịch sử video*\n\nChưa có video nào trong phiên này."
        else:
            lines = ["📂 *Video gần nhất:*\n"]
            for i, item in enumerate(reversed(history), 1):
                lines.append(f"{i}. `{item.get('name','?')[:30]}`\n   📅 {item.get('ts','?')} | 🔧 {item.get('engine','?')}")
                if item.get("url"):
                    lines.append(f"   [📂 Drive]({item['url']})")
            text = "\n".join(lines)
        await q.edit_message_text(text, parse_mode="Markdown",
                                  disable_web_page_preview=True, reply_markup=kb_back_main())
        return

    if d == "m:help":
        await q.edit_message_text(
            "💡 *Hướng dẫn sử dụng*\n\n"
            "🔌 *Trước khi làm video:*\n"
            "   → Nhấn *Đánh Thức Colab* hoặc gõ /wakeup\n"
            "   → Mở notebook, Run All, chờ 3-5 phút\n\n"
            "🎬 *Tạo video:*\n"
            "1️⃣ Gửi ảnh sản phẩm (nền trắng)\n"
            "2️⃣ Gửi ảnh mặt mẫu (chân dung rõ)\n"
            "3️⃣ Nhập `Tên | Giá` hoặc /skip\n"
            "4️⃣ Chọn nền tảng → style → định dạng\n"
            "5️⃣ Xác nhận → chờ 5-15 phút → nhận video!\n\n"
            "📂 Video tự lưu Google Drive theo tháng",
            parse_mode="Markdown", reply_markup=kb_back_main(),
        )
        return

    if d == "run:start":
        await q.edit_message_text("⏳ Đang gửi task lên Colab...")
        await _forward_to_colab(q.message.chat_id, context)
        return


# ══════════════════════════════════════════════════════════════════════════════
#  CONVERSATION FLOW
# ══════════════════════════════════════════════════════════════════════════════

async def cb_start_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data.clear()

    if not _is_colab_alive():
        await q.edit_message_text(
            "⚠️ *Colab chưa kết nối!*\n\n"
            "Cần đánh thức Colab trước khi tạo video.\n"
            "Nhấn nút bên dưới hoặc gõ /wakeup",
            parse_mode="Markdown", reply_markup=kb_wakeup(),
        )
        return ConversationHandler.END

    await q.edit_message_text(
        "📦 *Bước 1/5 — Ảnh sản phẩm*\n\n"
        "Gửi ảnh trang phục trên nền *trắng hoặc sáng*.\n"
        "💡 Ảnh nền trắng → Try-On đẹp hơn nhiều!",
        parse_mode="Markdown",
    )
    return S_PRODUCT_IMG


async def recv_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fid = _photo_id(update.message)
    if not fid:
        await update.message.reply_text("⚠️ Vui lòng gửi ảnh (JPG/PNG). Thử lại!")
        return S_PRODUCT_IMG

    msg = await update.message.reply_text("⏳ Đang tải ảnh sản phẩm...")
    b64 = await _dl_to_b64(context.bot, fid)
    context.user_data["product_b64"] = b64
    await msg.delete()

    await update.message.reply_text(
        "✅ Nhận ảnh sản phẩm!\n\n"
        "👤 *Bước 2/5 — Ảnh mặt mẫu*\n\n"
        "Gửi ảnh *chân dung rõ mặt* của người mẫu.",
        parse_mode="Markdown",
    )
    return S_MODEL_IMG


async def recv_model(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fid = _photo_id(update.message)
    if not fid:
        await update.message.reply_text("⚠️ Vui lòng gửi ảnh mặt mẫu. Thử lại!")
        return S_MODEL_IMG

    msg = await update.message.reply_text("⏳ Đang tải ảnh mặt mẫu...")
    b64 = await _dl_to_b64(context.bot, fid)
    context.user_data["model_b64"] = b64
    await msg.delete()

    await update.message.reply_text(
        "✅ Nhận ảnh mặt mẫu!\n\n"
        "🏷️ *Bước 3/5 — Thông tin sản phẩm*\n\n"
        "Nhập: `Tên sản phẩm | Giá`\n"
        "Ví dụ: `Váy hoa nhí | 299.000đ`\n\n"
        "Hoặc gõ /skip để bỏ qua.",
        parse_mode="Markdown",
    )
    return S_PRODUCT_INFO


async def recv_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt   = update.message.text.strip()
    parts = txt.split("|", 1)
    context.user_data["name"]  = parts[0].strip()
    context.user_data["price"] = parts[1].strip() if len(parts) > 1 else ""
    await update.message.reply_text(
        "📱 *Bước 4/5 — Nền tảng đăng bài*",
        parse_mode="Markdown", reply_markup=kb_platform(),
    )
    return S_PLATFORM


async def recv_skip_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.update({"name": "", "price": ""})
    await update.message.reply_text(
        "📱 *Bước 4/5 — Nền tảng đăng bài*",
        parse_mode="Markdown", reply_markup=kb_platform(),
    )
    return S_PLATFORM


async def recv_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["platform"] = q.data.split(":")[1]
    await q.edit_message_text(
        "✍️ *Bước 5/5 — Style chữ overlay*",
        parse_mode="Markdown", reply_markup=kb_text_style(),
    )
    return S_TEXT_STYLE


async def recv_style(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    raw = q.data.split(":")[1]
    context.user_data["style"] = None if raw == "none" else raw
    await q.edit_message_text(
        "📐 *Định dạng video*",
        parse_mode="Markdown", reply_markup=kb_orientation(),
    )
    return S_ORIENTATION


async def recv_orientation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["orientation"] = q.data.split(":")[1]
    await q.edit_message_text(
        _summary(context.user_data),
        parse_mode="Markdown", reply_markup=kb_confirm(),
    )
    return S_CONFIRM


async def cb_back_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("📱 *Bước 4/5 — Nền tảng*",
                              parse_mode="Markdown", reply_markup=kb_platform())
    return S_PLATFORM


async def cb_back_style(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    await q.edit_message_text("✍️ *Bước 5/5 — Style chữ*",
                              parse_mode="Markdown", reply_markup=kb_text_style())
    return S_TEXT_STYLE


# ══════════════════════════════════════════════════════════════════════════════
#  FORWARD TASK → COLAB
# ══════════════════════════════════════════════════════════════════════════════

async def _forward_to_colab(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    ud = context.user_data

    if not _is_colab_alive():
        await context.bot.send_message(
            chat_id,
            "❌ *Colab đã ngắt kết nối!*\n\nGõ /wakeup để đánh thức lại.",
            parse_mode="Markdown", reply_markup=kb_main(),
        )
        context.user_data.clear()
        return

    payload = {
        "chat_id":      chat_id,
        "product_b64":  ud.get("product_b64", ""),
        "model_b64":    ud.get("model_b64", ""),
        "name":         ud.get("name", ""),
        "price":        ud.get("price", ""),
        "platform":     ud.get("platform", "tiktok"),
        "style":        ud.get("style", "tiktok"),
        "orientation":  ud.get("orientation", "portrait"),
    }

    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                f"{colab_state['url']}/process",
                json=payload,
            ) as resp:
                result = await resp.json()

        if result.get("status") == "queued":
            await context.bot.send_message(
                chat_id,
                "🚀 *Task đã gửi lên Colab!*\n\n"
                "⏳ Đang xử lý (5-15 phút)...\n"
                "Bot sẽ tự gửi video khi xong.\n\n"
                "_Bạn có thể làm việc khác trong lúc chờ_ ☕",
                parse_mode="Markdown",
            )
        else:
            raise Exception(result.get("error", "Unknown error"))

    except Exception as e:
        logger.error(f"Forward to Colab failed: {e}")
        colab_state["url"] = None
        await context.bot.send_message(
            chat_id,
            "❌ *Không thể kết nối Colab!*\n\n"
            f"Lỗi: `{str(e)[:200]}`\n\n"
            "Gõ /wakeup để khởi động lại Colab.",
            parse_mode="Markdown", reply_markup=kb_main(),
        )

    context.user_data.clear()


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN — chạy cả Telegram bot và HTTP server
# ══════════════════════════════════════════════════════════════════════════════

async def run_http_server():
    """HTTP server để Colab kết nối vào."""
    http_app = web.Application()
    http_app.router.add_post("/register", http_register)
    http_app.router.add_post("/callback", http_callback)
    http_app.router.add_post("/ping", http_ping)
    http_app.router.add_get("/health", http_health)

    runner = web.AppRunner(http_app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    logger.info(f"✅ HTTP server đang chạy trên cổng {PORT}")
    return runner


async def main():
    global ptb_app_ref

    if not TOKEN:
        raise ValueError("Chưa set TELEGRAM_BOT_TOKEN!")

    # ── Khởi động HTTP server ──────────────────────────────────────────────
    runner = await run_http_server()

    # ── Khởi động Telegram bot ─────────────────────────────────────────────
    app = Application.builder().token(TOKEN).build()
    ptb_app_ref = app

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
                CallbackQueryHandler(recv_platform,    pattern=r"^plt:"),
                CallbackQueryHandler(cb_router,        pattern=r"^back:main$"),
            ],
            S_TEXT_STYLE:   [
                CallbackQueryHandler(recv_style,       pattern=r"^sty:"),
                CallbackQueryHandler(cb_back_platform, pattern=r"^back:platform$"),
            ],
            S_ORIENTATION:  [
                CallbackQueryHandler(recv_orientation, pattern=r"^ori:"),
                CallbackQueryHandler(cb_back_style,    pattern=r"^back:style$"),
            ],
            S_CONFIRM:      [
                CallbackQueryHandler(cb_router, pattern=r"^(run:|back:main|m:create)"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
        conversation_timeout=900,
    )

    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("menu",   cmd_menu))
    app.add_handler(CommandHandler("wakeup", cmd_wakeup))
    app.add_handler(CommandHandler("cancel", cmd_cancel))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(cb_router, pattern=r"^(back:|m:|set:|run:)"))

    logger.info("🚀 Dispatcher đang chạy...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=["message", "callback_query"])

    # Giữ chạy mãi
    try:
        await asyncio.Event().wait()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
