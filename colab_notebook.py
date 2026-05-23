"""
colab_notebook.py — Google Colab Notebook v6
=============================================================================
Copy từng CELL vào Colab notebook theo thứ tự.
Thứ tự: Cell 1 → 2 → 3 → 4 → 5 → 6(production)

Kiến trúc v6:
  Telegram → Render (app.py) → HTTP → Colab (AI GPU)
  Colab xử lý xong → gọi lại Render /colab/callback → Telegram
  HOẶC: Colab tự đăng ký URL về Render (/colab/seturl) khi khởi động
=============================================================================
"""

# ════════════════════════════════════════════════════════════════════════════
# CELL 0 — Điền thông tin cá nhân (PHẢI điền trước khi chạy)
# ════════════════════════════════════════════════════════════════════════════
CELL_0 = """
# ⚠️ ĐIỀN THÔNG TIN CỦA BẠN VÀO ĐÂY TRƯỚC KHI CHẠY
# =======================================================

GITHUB_REPO      = "https://github.com/YOUR_USERNAME/affiliate-video-bot.git"
# Thay YOUR_USERNAME bằng tên GitHub của bạn

NGROK_AUTH_TOKEN = "your_ngrok_token_here"
# Lấy miễn phí tại: https://ngrok.com → Dashboard → Your Authtoken

RENDER_URL       = "https://affiliate-video-bot.onrender.com"
# URL Render service của bạn (sau khi deploy xong)

BOT_SECRET       = "affiliatebot_v6_secret"
# Giữ nguyên hoặc đổi, phải khớp với COLAB_SECRET trên Render

YOUR_TELEGRAM_ID = 0
# ID Telegram của bạn — để bot tự thông báo khi Colab sẵn sàng
# Lấy ID bằng cách nhắn @userinfobot trên Telegram

print("✅ Config OK — Chạy Cell 1 tiếp theo")
"""

# ════════════════════════════════════════════════════════════════════════════
# CELL 1 — Cài dependencies (chạy 1 lần duy nhất, ~5-8 phút)
# ════════════════════════════════════════════════════════════════════════════
CELL_1 = """
# ── Cài ffmpeg (cần cho video processing) ───────────────────────────────────
!apt-get update -q && apt-get install -y ffmpeg libsm6 libxext6 -q

# ── Cài Python packages ──────────────────────────────────────────────────────
!pip install -q \\
    python-telegram-bot==21.6 \\
    Pillow requests flask pyngrok \\
    moviepy imageio imageio-ffmpeg \\
    diffusers transformers accelerate safetensors \\
    open-clip-torch huggingface_hub \\
    tqdm xformers \\
    audiocraft \\
    opencv-python-headless numpy

# ── Clone project từ GitHub ──────────────────────────────────────────────────
import os
if not os.path.exists('/content/affiliate-video-bot'):
    !git clone {GITHUB_REPO} /content/affiliate-video-bot
else:
    !cd /content/affiliate-video-bot && git pull

%cd /content/affiliate-video-bot
import sys
sys.path.insert(0, '/content/affiliate-video-bot')

print("✅ Cài xong! Chạy Cell 2 tiếp theo.")
"""

# ════════════════════════════════════════════════════════════════════════════
# CELL 2 — Mount Google Drive + Tải fonts (chạy 1 lần)
# ════════════════════════════════════════════════════════════════════════════
CELL_2 = """
import sys
sys.path.insert(0, '/content/affiliate-video-bot')

# ── Mount Google Drive ───────────────────────────────────────────────────────
from pipeline.drive_manager import setup_drive
import json

drive = setup_drive()
print("📂 Drive stats:")
print(json.dumps(drive.drive_stats(), indent=2, ensure_ascii=False))

# ── Tải fonts về Drive (1 lần) ───────────────────────────────────────────────
fonts_to_download = [
    "Montserrat-Bold.ttf",
    "Montserrat-ExtraBold.ttf",
    "BeVietnamPro-Bold.ttf",
]
for font in fonts_to_download:
    path = drive.get_font_path(font)
    if path:
        print(f"✅ Font: {font} → {path}")
    else:
        print(f"⚠️ Không tải được font: {font}")

print("\\n✅ Drive sẵn sàng! Chạy Cell 3 tiếp theo.")
"""

# ════════════════════════════════════════════════════════════════════════════
# CELL 3 — Tải AI models về Drive (lần đầu ~15-30 phút, sau đó load từ Drive)
# ════════════════════════════════════════════════════════════════════════════
CELL_3 = """
import sys
sys.path.insert(0, '/content/affiliate-video-bot')
from pipeline.drive_manager import setup_drive

drive = setup_drive()

# ── Chọn model muốn tải ─────────────────────────────────────────────────────
# Uncomment dòng model bạn muốn tải.
# Chỉ cần tải 1 model — bot sẽ tự dùng model nào có sẵn.

# Model 1: Wan2.1-I2V-14B-480P — TỐT NHẤT (cần 12GB VRAM, ~25GB disk)
# drive.download_model("Wan-AI/Wan2.1-I2V-14B-480P", "wan2.1-i2v-14B-480P")

# Model 2: CogVideoX-5B — Nhanh hơn (cần 8GB VRAM, ~18GB disk)
# drive.download_model("THUDM/CogVideoX-5b", "cogvideox-5b")

# Model 3: FLUX.1-schnell — Sinh ảnh nhanh (4 steps, ~8GB disk)
# drive.download_model("black-forest-labs/FLUX.1-schnell", "flux1-schnell")

# Model 4: AnimateDiff SDXL — Nhẹ nhất (6GB VRAM, ~7GB disk)
# drive.download_model("guoyww/animatediff-motion-adapter-sdxl-beta", "animatediff-sdxl")

# ── Tải AudioCraft (MusicGen) cho nhạc AI ────────────────────────────────────
# Nhỏ hơn (300MB), chạy nhanh, sinh nhạc nền miễn phí
# drive.download_model("facebook/musicgen-small", "musicgen-small")

print("✅ Model đã có trên Drive — chạy Cell 4 để khởi động server")
print("   (Nếu chưa tải model nào, bot sẽ dùng MoviePy fallback — không cần GPU)")
"""

# ════════════════════════════════════════════════════════════════════════════
# CELL 4 — Khởi động ngrok + Flask server (chạy mỗi session)
# ════════════════════════════════════════════════════════════════════════════
CELL_4 = """
import sys, os, json, threading, time, requests as req_lib
sys.path.insert(0, '/content/affiliate-video-bot')

# Config từ Cell 0
NGROK_AUTH_TOKEN = "{NGROK_AUTH_TOKEN}"
RENDER_URL       = "{RENDER_URL}"
BOT_SECRET       = "{BOT_SECRET}"
YOUR_TELEGRAM_ID = {YOUR_TELEGRAM_ID}

# ── Mount Drive ──────────────────────────────────────────────────────────────
from pipeline.drive_manager import setup_drive
drive = setup_drive()

# ── Flask server ─────────────────────────────────────────────────────────────
from flask import Flask, request, jsonify

colab_app = Flask("colab_server")

def _check_gpu():
    try:
        import torch
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            mem  = round(torch.cuda.get_device_properties(0).total_memory / 1e9, 1)
            return f"{name} ({mem}GB)"
        return "CPU only"
    except Exception:
        return "Unknown"

@colab_app.route("/ping")
def colab_ping():
    return jsonify({"status": "alive", "gpu": _check_gpu()}), 200

@colab_app.route("/info")
def colab_info():
    return jsonify({
        "status": "alive",
        "gpu": _check_gpu(),
        "drive": drive.drive_stats(),
    }), 200

@colab_app.route("/generate", methods=["POST"])
def colab_generate():
    \"\"\"Nhận task từ Render → chạy AI pipeline → gọi lại Render.\"\"\"
    data = request.get_json(silent=True) or {}
    secret = data.get("secret", "")
    if secret != BOT_SECRET:
        return jsonify({"error": "Unauthorized"}), 403

    user_id      = data.get("user_id")
    name         = data.get("name", "Sản phẩm")
    price        = data.get("price", "Liên hệ")
    description  = data.get("description", name)
    platform     = data.get("platform", "tiktok")
    callback_url = data.get("callback_url", "")

    print(f"\\n📥 Task từ Render: {name} | {price} | {platform}")

    # Chạy pipeline trong background thread
    threading.Thread(
        target=_run_pipeline,
        args=(user_id, name, price, description, platform, callback_url),
        daemon=True,
    ).start()

    return jsonify({"status": "accepted", "message": "Đang xử lý..."}), 200


def _run_pipeline(user_id, name, price, description, platform, callback_url):
    \"\"\"Chạy toàn bộ AI video pipeline.\"\"\"
    try:
        from pipeline.ai_analyzer import analyze_product
        from pipeline.script_writer import write_video_script
        from pipeline.video_engine import generate_video
        from pipeline.caption_gen import generate_caption

        print(f"🔍 Phân tích sản phẩm: {name}")
        analysis = analyze_product(name, description)

        print(f"📝 Viết script...")
        script = write_video_script(analysis, name, price, platform)

        print(f"🎬 Tạo video (engine=auto)...")
        output_path = generate_video(
            script=script,
            product_name=name,
            price=price,
            gender=analysis.gender,
            engine="auto",
        )

        if output_path and output_path.exists():
            print(f"✅ Video xong: {output_path}")
            caption = script.caption

            # Gửi callback về Render
            if callback_url:
                _send_callback(callback_url, {
                    "user_id":   user_id,
                    "status":    "success_drive",
                    "video_url": str(output_path),
                    "caption":   caption[:900],
                    "error":     "",
                })

            # Hiển thị video trong Colab notebook
            from IPython.display import Video, display
            display(Video(str(output_path), width=360))
            print(f"📋 Caption:\\n{caption[:300]}")

        else:
            _send_callback(callback_url, {
                "user_id": user_id,
                "status":  "error",
                "error":   "Video generation failed — check logs",
            })

    except Exception as e:
        import traceback
        err_msg = str(e)
        print(f"❌ Pipeline lỗi: {err_msg}")
        traceback.print_exc()
        if callback_url:
            _send_callback(callback_url, {
                "user_id": user_id,
                "status":  "error",
                "error":   err_msg[:200],
            })


def _send_callback(url: str, payload: dict):
    \"\"\"Gửi kết quả về Render.\"\"\"
    try:
        headers = {"X-Bot-Secret": BOT_SECRET, "Content-Type": "application/json"}
        req_lib.post(url, json=payload, headers=headers, timeout=15)
        print(f"✅ Callback gửi OK → {url}")
    except Exception as e:
        print(f"⚠️ Callback thất bại: {e}")


# ── Khởi động ngrok ──────────────────────────────────────────────────────────
from pyngrok import ngrok, conf as ngrok_conf

if NGROK_AUTH_TOKEN:
    ngrok_conf.get_default().auth_token = NGROK_AUTH_TOKEN
else:
    print("⚠️ Chưa điền NGROK_AUTH_TOKEN — URL sẽ expire sau 2 giờ")

# Chạy Flask trong thread
flask_thread = threading.Thread(
    target=lambda: colab_app.run(host="0.0.0.0", port=5001, use_reloader=False),
    daemon=True,
)
flask_thread.start()
time.sleep(2)

# Tạo ngrok tunnel
tunnel = ngrok.connect(5001, bind_tls=True)
ngrok_url = tunnel.public_url
print(f"\\n{'='*55}")
print(f"✅ Colab server đang chạy!")
print(f"🔗 ngrok URL: {ngrok_url}")
print(f"🖥️ GPU: {_check_gpu()}")
print(f"{'='*55}")
print(f"\\n📱 Gửi lệnh này vào Telegram:")
print(f"/setcolab {ngrok_url}")
print(f"{'='*55}")

# ── Tự đăng ký URL về Render (không cần copy-paste thủ công) ────────────────
if RENDER_URL:
    try:
        resp = req_lib.post(
            f"{RENDER_URL}/colab/seturl",
            json={{"url": ngrok_url, "notify_user_id": YOUR_TELEGRAM_ID}},
            headers={{"X-Bot-Secret": BOT_SECRET}},
            timeout=15,
        )
        if resp.status_code == 200:
            print(f"✅ Đã tự đăng ký URL về Render — Telegram sẽ nhận thông báo!")
        else:
            print(f"⚠️ Tự đăng ký thất bại ({resp.status_code}) — gửi thủ công qua /setcolab")
    except Exception as e:
        print(f"⚠️ Không tự đăng ký được: {{e}} — gửi thủ công qua /setcolab")

print("\\n📌 Notebook này phải giữ mở để Colab tiếp tục chạy!")
"""

# ════════════════════════════════════════════════════════════════════════════
# CELL 5 — Test nhanh pipeline (tùy chọn)
# ════════════════════════════════════════════════════════════════════════════
CELL_5 = """
# Test pipeline mà không cần Telegram
from pipeline.ai_analyzer import analyze_product
from pipeline.script_writer import write_video_script
from pipeline.caption_gen import generate_viral_package

# Ví dụ test
name        = "Váy maxi hoa nhí"
price       = "299k"
description = "Váy nữ vải lụa mềm, tay dài, dáng A"
platform    = "tiktok"

print("🔍 Phân tích sản phẩm...")
analysis = analyze_product(name, description)
print(f"  Gender: {analysis.gender} | Style: {analysis.style_category}")
print(f"  USP: {analysis.usp}")

print("\\n📝 Sinh viral content...")
vc = generate_viral_package(name, price, description, platform)
print(f"  Hook: {vc.hook_text}")
print(f"  Music: {vc.music_mood}")
print(f"  Badge: {vc.urgency_badge}")
print(f"  Proof: {vc.social_proof}")

print("\\n📋 Caption TikTok:")
print(vc.caption_tiktok[:400])

print("\\n✅ Test OK — Pipeline hoạt động bình thường!")
"""

# ════════════════════════════════════════════════════════════════════════════
# CELL 6 — Tạo video thử (test GPU)
# ════════════════════════════════════════════════════════════════════════════
CELL_6 = """
# Tạo 1 video thử để kiểm tra toàn bộ pipeline
from pipeline.ai_analyzer import analyze_product
from pipeline.script_writer import write_video_script
from pipeline.video_engine import generate_video
from IPython.display import Video, display

name        = "Váy maxi hoa nhí"
price       = "299k"
description = "Váy nữ vải lụa mềm tay dài"

print("🎬 Đang tạo video thử...")
analysis = analyze_product(name, description)
script   = write_video_script(analysis, name, price, "tiktok")

output = generate_video(
    script=script,
    product_name=name,
    price=price,
    gender=analysis.gender,
    engine="auto",  # Tự chọn engine tốt nhất có GPU
)

if output and output.exists():
    print(f"✅ Video OK: {output}")
    print(f"📏 Kích thước: {output.stat().st_size / 1024 / 1024:.1f} MB")
    display(Video(str(output), width=360))
else:
    print("❌ Tạo video thất bại — xem log ở trên")
"""


if __name__ == "__main__":
    print("📋 Copy từng CELL vào Colab notebook theo thứ tự:")
    print("  Cell 0: Điền config")
    print("  Cell 1: Cài deps (1 lần)")
    print("  Cell 2: Mount Drive + fonts (1 lần)")
    print("  Cell 3: Tải AI models (1 lần, tùy chọn)")
    print("  Cell 4: Khởi động ngrok + Flask server ← CHẠY MỖI SESSION")
    print("  Cell 5: Test pipeline (tùy chọn)")
    print("  Cell 6: Tạo video thử (tùy chọn)")
