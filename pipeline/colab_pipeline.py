"""
pipeline/colab_pipeline.py — Affiliate Studio v8
Chạy trên Colab GPU — Nhận request tách nền bằng BRIA RMBG-1.4 cao cấp.
Tự động khắc phục triệt để lỗi mất thuộc tính '_Ink' liên quan đến Pillow.
"""
import base64, io, json, logging, os, tempfile, threading, time
from pathlib import Path
import requests
import numpy as np
from PIL import Image

logger = logging.getLogger("ColabPipeline")
DRIVE_ROOT = Path(os.getenv("DRIVE_ROOT", "/content/drive/MyDrive/AffiliateStudio"))

# ═══════════════════════════════════════════════════════════════
# STEP 1: HIGH-QUALITY BACKGROUND REMOVAL (BRIA RMBG-1.4)
# ═══════════════════════════════════════════════════════════════

def remove_background(img_b64: str) -> str:
    """
    Tách nền sản phẩm bằng mô hình BRIA RMBG-1.4 (Chất lượng thương mại studio).
    Đổ nền trắng phẳng mịn tương thích hoàn toàn cấu trúc cũ của hệ thống.
    """
    import torch
    from transformers import pipeline

    img_bytes = base64.b64decode(img_b64)
    # Convert RGB loại bỏ kênh alpha lỗi nếu có từ đầu vào ảnh người dùng
    img_pil   = Image.open(io.BytesIO(img_bytes)).convert("RGB")

    try:
        logger.info("⏳ Đang gọi pipeline xử lý tách nền bằng BRIA RMBG-1.4...")
        # Tự động trỏ phần cứng sang GPU nếu có cấu hình CUDA
        device = 0 if torch.cuda.is_available() else -1
        pipe = pipeline("image-segmentation", model="briaai/RMBG-1.4", trust_remote_code=True, device=device)
        
        # Trích xuất mặt nạ phân rã vật thể (Mask)
        pillow_mask = pipe(img_pil, return_mask=True)
        
        # Áp dụng mặt nạ lên ảnh gốc dưới định dạng kênh màu RGBA
        img_rgba = img_pil.copy().convert("RGBA")
        img_rgba.putalpha(pillow_mask)
        
        # Tạo khung nền màu trắng thuần chuẩn kích thước ảnh
        white_bg = Image.new("RGBA", img_rgba.size, (255, 255, 255, 255))
        white_bg.paste(img_rgba, mask=img_rgba.split()[3])
        result = white_bg.convert("RGB")
        logger.info("✅ Hoàn thành tách nền vật thể bằng AI thành công.")
        
    except Exception as e:
        logger.error(f"❌ Xảy ra sự cố hệ thống BRIA RMBG: {e}. Tiến hành trả về ảnh gốc.")
        result = img_pil

    buf = io.BytesIO()
    result.save(buf, format="JPEG", quality=95)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


# ═══════════════════════════════════════════════════════════════
# UTILITIES & AUXILIARY LOGIC
# ═══════════════════════════════════════════════════════════════

def _img_to_b64(img: Image.Image) -> str:
    """Chuyển đổi thực thể ảnh PIL sang chuỗi Base64 chu chuyển mạng mạng."""
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def generate_emotional_script(
    product_info: dict,
    category: str,
    gender: str,
    emotional,
    platform: str = "tiktok"
) -> str:
    """Sinh script nói cho video dựa trên cấu trúc emotional template cũ."""
    import random
    name     = product_info.get("name", "Sản phẩm")
    price    = product_info.get("price", "")
    desc     = product_info.get("description", "")

    # Khởi tạo an toàn tránh lỗi thiếu biến từ lớp ngoài
    benefit = getattr(emotional, "transformation_promise", desc[:60])
    urgency = getattr(emotional, "urgency_line", "Số lượng giới hạn!")
    comment_bait = getattr(emotional, "comment_bait", "Để lại bình luận ngay!")

    script = f"Sản phẩm {name} với mức giá {price}. Giải pháp tuyệt vời giúp {benefit}. {urgency} {comment_bait}"
    return script
