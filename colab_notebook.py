"""
colab_notebook.py — Google Colab Notebook Cells
=============================================================================
Copy từng CELL vào Colab notebook để chạy.
Thứ tự: Cell 1 → 2 → 3 → 4 → 5 → 6 (production run)

Kiến trúc mới (v5 + Render):
  Render (Telegram bot + web server) → HTTP → Colab (AI GPU)
  Colab xử lý xong → gọi lại Render /colab/callback → gửi về Telegram
=============================================================================
"""

# ════════════════════════════════════════════════════════════
# CELL 1 — Cài dependencies (chạy 1 lần, ~5 phút)
# ════════════════════════════════════════════════════════════
CELL_1 = """
# Cài ffmpeg
!apt-get install -y ffmpeg -q

# Cài Python packages
!pip install -q python-telegram-bot==21.6 Pillow diffusers transformers accelerate safetensors
!pip install -q open-clip-torch huggingface_hub tqdm imageio imageio-ffmpeg pydub
!pip install -q flask requests pyngrok

# Clone project từ GitHub
!git clone https://github.com/YOUR_USERNAME/affiliate-video-bot.git /content/affiliate-video-bot
%cd /content/affiliate-video-bot

print("✅ Setup complete! Chạy Cell 2 tiếp theo.")
"""

# ════════════════════════════════════════════════════════════
# CELL 2 — Mount Google Drive + khởi động ngrok server
# ════════════════════════════════════════════════════════════
CELL_2 = """
import sys, os, json, threading
sys.path.insert(0, '/content/affiliate-video-bot')

# ── Mount Drive ─────────────────────────────────────────────
from pipeline.drive_manager import setup_drive
drive = setup_drive()
print("📂 Drive:", json.dumps(drive.drive_stats(), indent=2, ensure_ascii=False))

# ── Flask server nhận task từ Render ────────────────────────
from flask import Flask, request, jsonify
import requests as req_lib

colab_flask = Flask("colab_server")
_render_callback_url = ""   # Sẽ được set từ payload của Render

@colab_flask.route("/ping")
def colab_ping():
    return jsonify({"status": "alive", "gpu": _check_gpu()}), 200

@colab_flask.route("/generate", methods=["POST"])
def colab_generate():
    \"\"\"Nhận task từ Render → chạy AI pipeline → gọi lại Render.\"\"\"
    global _render_callback_url
    data = request.get_json(silent=True) or {}
    
    user_id      = data.get("user_id")
    name         = data.get("name", "Sản phẩm")
    price        = data.get("price", "Liên hệ")
    description  = data.get("description", name)
    platform     = data.get("platform", "tiktok")
    callback_url = data.get("callback_url", "")
    _render_callback_url = callback_url
    
    print(f"📥 Task nhận từ Render: {name} | {price} | {platform}")
    
    # Chạy pipeline trong thread riêng (không block HTTP response)
    threading.Thread(
        target=_run_ai_pipeline,
        args=(user_id, name, price, description, platform, callback_url),
        daemon=True,
    ).start()
    
    return jsonify({"status": "accepted", "message": "Task đang được xử lý..."}), 200

def _check_gpu():
    try:
        import torch
        return torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU only"
    except Exception:
        return "unknown"

def _run_ai_pipeline(user_id, name, price, description, platform, callback_url):
    \"\"\"Chạy toàn bộ AI pipeline (Wan2.1 / CogVideoX) rồi callback về Render.\"\"\"
    try:
        print(f"🎬 Bắt đầu pipeline: {name}")
        
        # Step 1: AI Analysis
        from pipeline.ai_analyzer import analyze_product
        analysis = analyze_product(product_name=name, product_description=description)
        print(f"✅ AI Analysis: {analysis.gender} | {analysis.garment_type}")
        
        # Step 2: Script Writer
        from pipeline.script_writer import write_video_script
        script = write_video_script(analysis, name, price, platform)
        
        # Step 3: Viral Strategy
        from pipeline.viral_strategy import build_viral_content
        content = build_viral_content(analysis, script, platform)
        
        # Step 4: Video Generation
        from pipeline.video_engine import generate_video_auto
        from pipeline.background import get_full_prompt
        prompt = get_full_prompt(analysis, script)
        
        import tempfile
        video_tmp = tempfile.mktemp(suffix=".mp4")
        video_path = generate_video_auto(
            prompt=prompt,
            output_path=video_tmp,
        )
        
        # Step 5: Text Overlay
        if video_path:
            from pipeline.text_overlay import add_text_overlay
            final_path = video_path.replace(".mp4", "_final.mp4")
            add_text_overlay(str(video_path), script, final_path, platform)
            video_path = final_path
        
        # Step 6: Music
        if video_path:
            from pipeline.music_engine import mix_music
            with_music = video_path.replace(".mp4", "_music.mp4")
            mix_music(str(video_path), with_music, script.music_mood)
            video_path = with_music
        
        # Step 7: Lưu Drive
        from pipeline.drive_manager import drive_mgr
        drive_out = drive_mgr.save_output(video_path, name)
        print(f"💾 Saved to Drive: {drive_out}")
        
        # Step 8: Callback về Render
        if callback_url:
            req_lib.post(callback_url, json={
                "user_id": user_id,
                "status":  "done",
                "message": "Video hoàn thành!",
                "caption": content.caption,
                "hashtags": content.hashtags,
            }, timeout=30)
            print(f"✅ Callback sent to Render: {callback_url}")
        else:
            print("⚠️ Không có callback_url — Render sẽ không nhận kết quả tự động.")
        
    except Exception as e:
        print(f"❌ Pipeline error: {e}")
        if callback_url:
            try:
                req_lib.post(callback_url, json={
                    "user_id": user_id,
                    "status": "error",
                    "message": str(e),
                }, timeout=10)
            except Exception:
                pass

# ── Khởi động Flask + ngrok ──────────────────────────────────
def _start_flask():
    colab_flask.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)

flask_thread = threading.Thread(target=_start_flask, daemon=True)
flask_thread.start()

# ngrok expose port 5000
from pyngrok import ngrok
ngrok.kill()  # Đóng tunnel cũ nếu có

NGROK_AUTH_TOKEN = ""  # Điền ngrok auth token của bạn (miễn phí tại ngrok.com)
if NGROK_AUTH_TOKEN:
    ngrok.set_auth_token(NGROK_AUTH_TOKEN)

public_url = ngrok.connect(5000).public_url
print("\\n" + "="*60)
print(f"✅ Colab server đang chạy!")
print(f"🔗 ngrok URL: {public_url}")
print("="*60)
print("\\n📋 Bước tiếp theo:")
print(f"  Gửi lệnh này trong Telegram:")
print(f"  /setcolab {public_url}")
print("="*60)
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
# CELL 5 — Config secrets (điền key của bạn)
# ════════════════════════════════════════════════════════════
CELL_5 = """
import os

# Option A: Dùng Colab Secrets (Recommended)
# Vào: Tools → Secrets → Add secret
from google.colab import userdata
try:
    os.environ["TELEGRAM_TOKEN"]   = userdata.get("TELEGRAM_TOKEN")
    os.environ["PIXABAY_API_KEY"]  = userdata.get("PIXABAY_API_KEY")
    # URL của Render service (để Colab gọi lại sau khi xong)
    os.environ["RENDER_URL"]       = userdata.get("RENDER_URL")
    print("✅ Secrets loaded from Colab Secrets")
except Exception:
    # Option B: Điền trực tiếp (không khuyến nghị production)
    os.environ["TELEGRAM_TOKEN"]  = "YOUR_BOT_TOKEN_HERE"
    os.environ["PIXABAY_API_KEY"] = "YOUR_PIXABAY_KEY_HERE"
    os.environ["RENDER_URL"]      = "https://your-app.onrender.com"
    print("⚠️  Using hardcoded keys")
"""

# ════════════════════════════════════════════════════════════
# CELL 6 — Test pipeline (không cần GPU, verify setup)
# ════════════════════════════════════════════════════════════
CELL_6 = """
import sys
sys.path.insert(0, '/content/affiliate-video-bot')

from pipeline.ai_analyzer import analyze_product
from pipeline.script_writer import write_video_script
from pipeline.viral_strategy import build_viral_content

test_products = [
    ("Váy maxi hoa nhí", "Váy nữ vải lụa mềm", "tiktok"),
    ("Suit nam xanh navy", "Vest nam công sở", "tiktok"),
    ("Set bé gái 3-8 tuổi", "Bộ đồ trẻ em cotton", "shopee"),
]

for name, desc, platform in test_products:
    print(f"\\n{'='*50}")
    print(f"Test: {name}")
    analysis = analyze_product(name, desc)
    script   = write_video_script(analysis, name, "299k", platform)
    content  = build_viral_content(analysis, script, platform)
    print(f"  Gender: {analysis.gender} | Style: {analysis.style_category}")
    print(f"  Hook: {script.hook_scene.hook_text}")
    print(f"  Caption: {content.caption[:80]}...")
    print(f"  Hashtags: {' '.join(content.hashtags[:5])}")
    print("  ✅ OK")

print("\\n✅ Tất cả test pass! Server đã sẵn sàng nhận task từ Render.")
print("Nhớ gửi /setcolab <ngrok_url> trong Telegram nếu chưa làm.")
"""
