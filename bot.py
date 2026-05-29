import os
import logging
from io import BytesIO
from PIL import Image
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from flask import Flask
from threading import Thread

# ==========================================
# 1. CẤU HÌNH API KEYS & BIẾN MÔI TRƯỜNG
# ==========================================
# Trên Render, bạn sẽ nhập các biến này trong phần Environment Variables
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "ĐIỀN_TOKEN_TELEGRAM_CỦA_BẠN_VÀO_ĐÂY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "ĐIỀN_API_KEY_CỦA_BẠN_VÀO_ĐÂY")

genai.configure(api_key=GEMINI_API_KEY)
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ==========================================
# 2. CƠ CHẾ TỰ ĐỘNG DÒ TÌM MODEL (Fix lỗi 404)
# ==========================================
model_name = 'gemini-1.5-flash' # Mặc định dự phòng
try:
    # Quét tất cả các model mà API Key của bạn được phép truy cập
    available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    
    if available_models:
        # Ưu tiên lấy model 1.5 flash hoặc 1.5 pro nếu có trong danh sách
        if any('gemini-1.5-flash' in m for m in available_models):
            model_name = next(m for m in available_models if 'gemini-1.5-flash' in m)
        elif any('gemini-1.5-pro' in m for m in available_models):
            model_name = next(m for m in available_models if 'gemini-1.5-pro' in m)
        else:
            model_name = available_models[0]
            
    logging.info(f"✅ Bot đã kết nối thành công với model: {model_name}")
except Exception as e:
    logging.warning(f"⚠️ Không thể tự động quét danh sách model, dùng mặc định. Chi tiết lỗi: {e}")

# Khởi tạo AI Model
model = genai.GenerativeModel(model_name)

# Định nghĩa các bước trạng thái
MODEL_PHOTO, PRODUCT_PHOTO, BACKGROUND = range(3)

# ==========================================
# 3. FLASK SERVER (KEEP-ALIVE DÀNH CHO RENDER)
# ==========================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running!"

@app.route('/ping')
def ping():
    # Route này để cron-job.org gọi vào mỗi 14 phút
    return "Pong! Bot is alive.", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# ==========================================
# 4. LUỒNG TRÒ CHUYỆN TELEGRAM BOT
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.message.reply_text(
        "Chào Ngọc! Hệ thống hỗ trợ Affiliate đã sẵn sàng.\n\n"
        "Bước 1: Gửi cho mình **Ảnh CÔ GÁI (Người mẫu)**.",
        parse_mode='Markdown'
    )
    return MODEL_PHOTO

async def receive_model_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    context.user_data['model_photo'] = Image.open(BytesIO(photo_bytes))
    
    await update.message.reply_text(
        "Đã nhận ảnh mẫu! 📸\n"
        "Bước 2: Gửi cho mình **Ảnh SẢN PHẨM**.",
        parse_mode='Markdown'
    )
    return PRODUCT_PHOTO

async def receive_product_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photo_file = await update.message.photo[-1].get_file()
    photo_bytes = await photo_file.download_as_bytearray()
    context.user_data['product_photo'] = Image.open(BytesIO(photo_bytes))
    
    await update.message.reply_text(
        "Đã nhận sản phẩm! 👗\n"
        "Bước 3: Nhập **Bối cảnh (Background)** mong muốn (VD: Biển xanh nắng vàng, studio phong cách Hàn Quốc...).",
        parse_mode='Markdown'
    )
    return BACKGROUND

async def generate_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    background_text = update.message.text
    await update.message.reply_text("⏳ Đang phân tích và đóng gói Prompt chuẩn Gemini Omni... Đợi xíu nhé!")
    
    img_model = context.user_data['model_photo']
    img_product = context.user_data['product_photo']
    
    # PROMPT CHỈ ĐẠO CHO HỆ THỐNG
    system_instruction = f"""
    Bạn là một chuyên gia Prompt Engineering cho các mô hình AI tạo ảnh và video (Imagen 3 / Veo).
    Tôi cung cấp 2 bức ảnh: Ảnh 1 là khuôn mặt người mẫu, Ảnh 2 là trang phục. Bối cảnh: {background_text}.
    
    Hãy viết MỘT đoạn Prompt DUY NHẤT (bằng tiếng Việt, ngữ điệu rõ ràng, dùng format Markdown) để tôi copy và dán vào Gemini. Đoạn prompt của bạn sinh ra PHẢI có cấu trúc như sau:

    **[BẮT ĐẦU PROMPT]**
    Tôi tải lên 2 bức ảnh. Ảnh 1 là người mẫu. Ảnh 2 là trang phục. Hãy đóng vai trò là một nhiếp ảnh gia và đạo diễn video chuyên nghiệp, thực hiện chính xác các yêu cầu sau:

    **PHẦN 1: TẠO HÌNH ẢNH SẢN PHẨM (YÊU CẦU 5-6 ẢNH)**
    * **Mục tiêu:** Tạo ra bộ ảnh lookbook thời trang cực kỳ chân thực (photorealistic, 8k resolution, cinematic lighting).
    * **Chủ thể:** Giữ nguyên vẹn các đường nét khuôn mặt, kiểu tóc và thần thái của người mẫu trong Ảnh 1.
    * **Trang phục:** Mặc cho người mẫu bộ trang phục chính xác như trong Ảnh 2 (giữ đúng form dáng, họa tiết, màu sắc và chất liệu).
    * **Bối cảnh (Background):** [Tự động điền bối cảnh mà người dùng yêu cầu dựa trên {background_text}, miêu tả thêm về ánh sáng để bức ảnh sống động].
    * **Các góc máy yêu cầu (Render từng ảnh một):**
        1. Toàn thân, chụp chính diện.
        2. Chụp góc nghiêng 45 độ, người mẫu đang bước đi nhẹ nhàng.
        3. Mặt sau, khoe chi tiết phía sau của trang phục.
        4. Cận cảnh (Close-up) nửa người trên, nụ cười tự nhiên, rõ chất liệu vải.
        5. Tạo dáng tự do, phong cách Lifestyle tự tin.

    **PHẦN 2: TẠO VIDEO AFFILIATE (DỌC 9:16)**
    * Dựa trên tạo hình hoàn chỉnh từ Phần 1, hãy tạo một video ngắn có tỷ lệ khung hình dọc 9:16 (dành cho Reels/TikTok).
    * **Chuyển động:** Máy quay pan nhẹ nhàng. Người mẫu mỉm cười tự nhiên, xoay nhẹ người trước ống kính để thể hiện độ rủ của vải, có các cử động tay chân tự nhiên (như vén tóc, cầm ly cafe, hoặc chỉnh kính).
    * **Yêu cầu kỹ thuật:** Video không bị méo hình, duy trì tính nhất quán của trang phục và khuôn mặt trong suốt thời lượng video.
    **[KẾT THÚC PROMPT]**
    
    Chỉ in ra đoạn text từ [BẮT ĐẦU PROMPT] đến [KẾT THÚC PROMPT], không giải thích gì thêm.
    """
    
    try:
        # Gọi API sinh Content
        response = model.generate_content([system_instruction, img_model, img_product])
        
        # Xóa các tag điều hướng để hiển thị văn bản gọn gàng
        clean_prompt = response.text.replace('[BẮT ĐẦU PROMPT]', '').replace('[KẾT THÚC PROMPT]', '').strip()
        
        final_message = (
            "🎯 **PROMPT HOÀN CHỈNH CỦA BẠN ĐÂY:**\n\n"
            "```text\n"
            f"{clean_prompt}\n"
            "```\n\n"
            "👉 Hãy Copy đoạn trên, đính kèm 2 bức ảnh của bạn và gửi cho Gemini App nhé!"
        )
        await update.message.reply_text(final_message, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Có lỗi API: {str(e)}\n\nLỗi này có thể do định dạng ảnh hoặc lỗi kết nối. Hãy thử lại.")
        
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Đã hủy quá trình. Gõ /start để làm lại.")
    context.user_data.clear()
    return ConversationHandler.END

# ==========================================
# 5. HÀM MAIN
# ==========================================
def main() -> None:
    # 1. Chạy Flask Server ở một Thread riêng
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # 2. Chạy Telegram Bot
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MODEL_PHOTO: [MessageHandler(filters.PHOTO, receive_model_photo)],
            PRODUCT_PHOTO: [MessageHandler(filters.PHOTO, receive_product_photo)],
            BACKGROUND: [MessageHandler(filters.TEXT & ~filters.COMMAND, generate_prompt)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(conv_handler)
    
    logging.info("🚀 Bot đang khởi động...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
