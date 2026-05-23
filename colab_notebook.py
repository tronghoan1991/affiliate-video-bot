"""
colab_notebook.py — Google Colab Notebook Cells
=============================================================================
Copy từng CELL vào Colab notebook để chạy.
Thứ tự: Cell 1 → 2 → 3 → ... → 7 (production run)
=============================================================================
"""

# ════════════════════════════════════════════════════════════
# CELL 1 — Cài dependencies (chạy 1 lần, ~5 phút)
# ════════════════════════════════════════════════════════════
CELL_1 = """
# Install dependencies
!pip install -q python-telegram-bot==21.6 Pillow diffusers transformers accelerate safetensors
!pip install -q open-clip-torch huggingface_hub tqdm imageio imageio-ffmpeg
!apt-get install -y ffmpeg -q

# Clone project từ GitHub
!git clone https://github.com/YOUR_USERNAME/affiliate-video-bot.git /content/affiliate-video-bot
%cd /content/affiliate-video-bot

print("✅ Setup complete!")
"""

# ════════════════════════════════════════════════════════════
# CELL 2 — Mount Google Drive (bắt đầu mỗi session)
# ════════════════════════════════════════════════════════════
CELL_2 = """
import sys
sys.path.insert(0, '/content/affiliate-video-bot')

from pipeline.drive_manager import setup_drive
drive = setup_drive()

import json
print("📊 Drive Stats:")
print(json.dumps(drive.drive_stats(), indent=2, ensure_ascii=False))
"""

# ════════════════════════════════════════════════════════════
# CELL 3 — Tải fonts về Drive (1 lần duy nhất)
# ════════════════════════════════════════════════════════════
CELL_3 = """
from pipeline.drive_manager import drive_mgr
for font in ["Montserrat-Bold.ttf", "Montserrat-ExtraBold.ttf", "NotoSans-Bold.ttf"]:
    p = drive_mgr.get_font_path(font)
    print(f"✅ {font}: {p}")
"""

# ════════════════════════════════════════════════════════════
# CELL 4 — Tải AI model về Drive (1 lần, ~10-20 phút)
# ════════════════════════════════════════════════════════════
CELL_4 = """
from pipeline.video_engine import download_model_to_drive

# Wan2.1-I2V (Image-to-Video) — phù hợp fashion affiliate nhất
model_path = download_model_to_drive(
    model_id="Wan-AI/Wan2.1-I2V-14B-480P",
    local_name="wan2.1-i2v-14B-480P"
)
print(f"✅ Model saved: {model_path}")
print("💡 Model này dùng mãi mãi — không cần tải lại session sau!")
"""

# ════════════════════════════════════════════════════════════
# CELL 5 — Config (điền key của bạn)
# ════════════════════════════════════════════════════════════
CELL_5 = """
import os

# Option A: Dùng Colab Secrets (Recommended — bảo mật hơn)
# Vào: Tools → Secrets → Add secret
from google.colab import userdata
try:
    os.environ["TELEGRAM_TOKEN"]   = userdata.get("TELEGRAM_TOKEN")
    os.environ["PIXABAY_API_KEY"]  = userdata.get("PIXABAY_API_KEY")
    print("✅ Secrets loaded from Colab Secrets")
except Exception:
    # Option B: Điền trực tiếp (không khuyến nghị cho production)
    os.environ["TELEGRAM_TOKEN"]  = "YOUR_BOT_TOKEN_HERE"
    os.environ["PIXABAY_API_KEY"] = "YOUR_PIXABAY_KEY_HERE"
    print("⚠️  Using hardcoded keys — consider using Colab Secrets")
"""

# ════════════════════════════════════════════════════════════
# CELL 6 — Chạy thử pipeline (test không cần GPU)
# ════════════════════════════════════════════════════════════
CELL_6 = """
# Test AI analyzer + script writer (không cần GPU)
from pipeline.ai_analyzer import analyze_product
from pipeline.script_writer import write_video_script
from pipeline.viral_strategy import build_viral_content
from pipeline.background import get_full_prompt

test_products = [
    ("Váy dạ hội lụa đỏ",    "850k",  "Váy nữ lụa dài cổ V",              "women"),
    ("Suit nam xanh navy",   "1.2tr", "Vest nam slim fit công sở",          "men"),
    ("Set bé gái hoa nhí",   "185k",  "Bộ đồ bé gái cotton 3-8 tuổi",    "children"),
    ("Bodysuit sơ sinh",     "125k",  "Bodysuit bé 0-12 tháng organic",    "baby"),
    ("Đồ đôi couple",        "299k",  "Áo thun couple matching unisex",     "unisex"),
]

for name, price, desc, gender in test_products:
    print(f"\\n{'='*50}")
    print(f"🧪 Testing: {name} [{gender}]")

    # AI Analysis
    analysis = analyze_product(name, desc, gender_hint=gender)
    print(f"  🧠 Gender: {analysis.gender} | Style: {analysis.style_category}")
    print(f"  🎯 Target: {analysis.target_customer}")

    # Script
    script = write_video_script(analysis, name, price, "tiktok")
    print(f"  🎬 Hook: {script.hook_scene.hook_text[:60]}...")
    print(f"  🎵 Music: {script.music_mood}")

    # Viral content
    vc = build_viral_content(name, price, desc, "tiktok", gender_override=gender)
    print(f"  💬 Comment CTA: {vc.comment_cta}")
    print(f"  💎 Value: {vc.value_stack[:60]}...")

    # AI Prompt preview
    prompt = get_full_prompt(analysis.garment_key, gender)
    print(f"  📝 AI Prompt ({len(prompt)} chars): {prompt[:80]}...")

print("\\n✅ All pipeline tests passed!")
"""

# ════════════════════════════════════════════════════════════
# CELL 7 — Tạo video thực (cần GPU T4)
# ════════════════════════════════════════════════════════════
CELL_7 = """
from pipeline.ai_analyzer import analyze_product
from pipeline.script_writer import write_video_script
from pipeline.video_engine import generate_affiliate_video
from pipeline.background import get_negative_prompt
from IPython.display import Video, display

# ── Sản phẩm cần tạo video ────────────────────────────────
PRODUCT_NAME     = "Váy maxi hoa nhí"  # ← Đổi thành sản phẩm của bạn
PRODUCT_PRICE    = "299,000đ"
PRODUCT_DESC     = "Váy nữ maxi hoa nhí vải lụa mềm mại thoáng mát"
PRODUCT_GENDER   = "women"  # women | men | children | baby | unisex
PLATFORM         = "tiktok"  # tiktok | shopee | both
PRODUCT_IMAGE    = None  # Hoặc "/content/product.jpg" nếu có ảnh

# ── Phân tích AI ──────────────────────────────────────────
analysis = analyze_product(PRODUCT_NAME, PRODUCT_DESC,
                           image_path=PRODUCT_IMAGE,
                           gender_hint=PRODUCT_GENDER)
print(f"🧠 AI Analysis:")
print(f"  Gender: {analysis.gender} | Style: {analysis.style_category}")
print(f"  USP: {analysis.usp}")
print(f"  Target: {analysis.target_customer}")

# ── Viết kịch bản ─────────────────────────────────────────
script = write_video_script(analysis, PRODUCT_NAME, PRODUCT_PRICE, PLATFORM)
print(f"\\n🎬 Script:")
print(f"  Hook: {script.hook_scene.hook_text}")
print(f"  Value: {script.value_scene.hook_text[:60]}...")
print(f"  CTA: {script.cta_scene.hook_text}")
print(f"  Comment: {script.cta_scene.subtext}")
print(f"  Music: {script.music_mood}")

# ── Tạo video ─────────────────────────────────────────────
print("\\n⏳ Đang tạo video AI... (~3-5 phút)")
result = generate_affiliate_video(
    prompt=script.ai_prompt_main,
    negative_prompt=get_negative_prompt(),
    product_name=PRODUCT_NAME,
    product_price=PRODUCT_PRICE,
    garment_class=analysis.garment_key,
    gender=analysis.gender,
    platform=PLATFORM,
    image_path=PRODUCT_IMAGE,
    output_filename=f"{PRODUCT_NAME.replace(' ','_')}_{PLATFORM}.mp4",
    hook_text=script.hook_scene.hook_text,
    hook_subtext=script.hook_scene.subtext,
    value_stack=script.value_scene.hook_text,
    comment_cta=script.cta_scene.subtext,
    cta=script.cta_scene.hook_text,
    music_mood=script.music_mood,
)

if "error" in result:
    print(f"❌ Error: {result['error']}")
else:
    print(f"\\n✅ Video xong!")
    print(f"  Engine: {result['engine']}")
    print(f"  Drive: {result['drive_path']}")
    print(f"\\n📝 Caption TikTok:")
    print(result['caption'])
    display(Video(result['video_path'], width=320))
"""

if __name__ == "__main__":
    print("Đây là file hướng dẫn — copy từng CELL vào Google Colab để chạy.")
    print("Thứ tự: CELL_1 → CELL_2 → CELL_3 → CELL_4 → CELL_5 → CELL_6 → CELL_7")
