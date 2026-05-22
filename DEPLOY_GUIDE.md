# Hướng dẫn Deploy — Affiliate Video Bot v4.0

## Yêu cầu tối thiểu

| Thành phần | Yêu cầu |
|---|---|
| GPU | NVIDIA ≥13GB VRAM (T4 16GB, A100 40GB) |
| RAM | 32GB+ (CPU offload Wan2.1) |
| Disk | 35GB+ trống |
| Python | 3.10 hoặc 3.11 |
| CUDA | 12.1 |

> **Khuyến nghị:** Google Colab Pro/Pro+ với runtime **A100** hoặc **T4 High-RAM**.

---

## Bước 1 — Cài system dependencies

Chạy cell đầu tiên trong Colab:

```bash
!apt-get update -qq
!apt-get install -y ffmpeg fonts-liberation libgl1
```

---

## Bước 2 — Cài PyTorch với CUDA 12.1

```bash
!pip install torch==2.4.0 torchvision \
    --index-url https://download.pytorch.org/whl/cu121 \
    --quiet
```

> ⚠️ Phải cài PyTorch **trước** diffusers để tránh xung đột version.

---

## Bước 3 — Cài diffusers từ source (bắt buộc cho Wan2.1)

```bash
!pip install git+https://github.com/huggingface/diffusers \
    transformers accelerate safetensors \
    imageio imageio-ffmpeg ftfy einops \
    --quiet
```

---

## Bước 4 — Cài các thư viện còn lại

```bash
!pip install -r requirements.txt \
    --ignore-installed torch torchvision \
    --quiet
```

---

## Bước 5 — Tải models

Chạy cell tải model (khoảng 15-30 phút lần đầu, sau đó cache):

```python
import os
from pathlib import Path
from huggingface_hub import snapshot_download

MODELS_DIR = Path("./models")

# Wan2.1 I2V 480P (~13GB) — engine chính
print("Tải Wan2.1 I2V-14B-480P...")
snapshot_download(
    repo_id="Wan-AI/Wan2.1-I2V-14B-480P-Diffusers",
    local_dir=str(MODELS_DIR / "wan21"),
    ignore_patterns=["*.msgpack", "*.h5"],
)

# Real-ESRGAN (~64MB)
print("Tải Real-ESRGAN x4plus...")
os.makedirs(MODELS_DIR / "realesrgan", exist_ok=True)
import urllib.request
urllib.request.urlretrieve(
    "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
    str(MODELS_DIR / "realesrgan" / "RealESRGAN_x4plus.pth"),
)

print("✅ Tải model xong!")
```

---

## Bước 6 — Cấu hình Google Drive Service Account

### 6a. Tạo Service Account

1. Vào [Google Cloud Console](https://console.cloud.google.com/) → chọn project (hoặc tạo mới)
2. **APIs & Services** → **Enable APIs** → bật **Google Drive API**
3. **IAM & Admin** → **Service Accounts** → **Create Service Account**
4. Đặt tên (vd: `affiliate-bot`) → **Create and Continue**
5. Role: **Editor** → **Done**
6. Click vào service account vừa tạo → tab **Keys** → **Add Key** → **JSON**
7. File JSON sẽ tải về máy — đây là `credentials.json`

### 6b. Chia sẻ thư mục Drive

1. Tạo thư mục mới trên Google Drive, đặt tên `AffiliateVideos`
2. Chuột phải → **Share** → nhập email của service account (dạng `xxx@xxx.iam.gserviceaccount.com`)
3. Cấp quyền **Editor** → **Share**
4. Lấy **Folder ID** từ URL Drive: `drive.google.com/drive/folders/**<FOLDER_ID>**`

---

## Bước 7 — Set Secrets trong Colab

Mở **Secrets** (biểu tượng 🔑 ở sidebar trái) và thêm các giá trị sau:

| Tên Secret | Giá trị | Bắt buộc |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Token từ [@BotFather](https://t.me/BotFather) | ✅ |
| `GDRIVE_CREDENTIALS_JSON` | **Nội dung** file JSON (paste toàn bộ) | ✅ |
| `GDRIVE_ROOT_FOLDER_ID` | Folder ID lấy ở Bước 6b | ✅ |
| `HF_TOKEN` | Token từ huggingface.co/settings/tokens | Khuyến nghị |
| `PIXABAY_API_KEY` | API key từ pixabay.com/api/docs | Tùy chọn |
| `VIDEO_ENGINE` | `auto` / `wan21` / `animatediff` / `cloud` | Tùy chọn |
| `REALESRGAN_SCALE` | `2` (960P) hoặc `4` (1920P) | Tùy chọn |

### Đọc Secrets vào env trong Colab:

```python
import os
from google.colab import userdata

os.environ["TELEGRAM_BOT_TOKEN"]      = userdata.get("TELEGRAM_BOT_TOKEN")
os.environ["GDRIVE_CREDENTIALS_JSON"] = userdata.get("GDRIVE_CREDENTIALS_JSON")
os.environ["GDRIVE_ROOT_FOLDER_ID"]   = userdata.get("GDRIVE_ROOT_FOLDER_ID")

# Tùy chọn
hf = userdata.get("HF_TOKEN")
if hf: os.environ["HF_TOKEN"] = hf

pix = userdata.get("PIXABAY_API_KEY")
if pix: os.environ["PIXABAY_API_KEY"] = pix
```

---

## Bước 8 — Upload code lên Colab

**Cách 1 — Upload thư mục** (nhanh nhất):

```python
# Zip toàn bộ thư mục dự án, upload lên Colab rồi:
!unzip affiliate_bot.zip -d /content/affiliate_bot
%cd /content/affiliate_bot
```

**Cách 2 — Clone từ GitHub:**

```bash
!git clone https://github.com/YOUR_USERNAME/affiliate-video-bot.git
%cd affiliate-video-bot
```

Đảm bảo cấu trúc thư mục đúng:

```
affiliate_bot/
├── app.py
├── config.py
├── requirements.txt
├── pipeline/
│   ├── __init__.py
│   ├── background.py
│   ├── caption_gen.py
│   ├── classifier.py
│   ├── gdrive.py
│   ├── music_engine.py
│   ├── text_overlay.py
│   ├── tryon.py
│   ├── upscale.py
│   └── video_engine.py
├── models/          ← tạo tự động ở Bước 5
├── assets/
│   ├── fonts/       ← tùy chọn: Montserrat-Bold.ttf
│   └── music/       ← tùy chọn: file .mp3 nhạc nền
└── tmp/             ← tạo tự động
```

---

## Bước 9 — Chạy Bot

```python
!python app.py
```

Output thành công sẽ thấy:
```
INFO - 🚀 Affiliate Bot v4.0 đang chạy...
```

> **Lưu ý:** Colab sẽ ngắt kết nối sau ~12 giờ (Pro) hoặc ~1 giờ (Free).  
> Dùng Colab Pro+ với **background execution** để chạy liên tục.

---

## Xử lý sự cố thường gặp

### ❌ `CUDA out of memory`
```
# Giải pháp 1: Đổi sang AnimateDiff (nhẹ hơn)
os.environ["VIDEO_ENGINE"] = "animatediff"

# Giải pháp 2: Đổi sang cloud (không cần GPU)
os.environ["VIDEO_ENGINE"] = "cloud"

# Giải pháp 3: Trong Colab → Runtime → Disconnect → Reconnect → chọn A100
```

### ❌ `FileNotFoundError: Real-ESRGAN model không tìm thấy`
```bash
# Chạy lại cell tải model ở Bước 5
```

### ❌ `google.auth.exceptions.DefaultCredentialsError`
```
# Kiểm tra: nội dung GDRIVE_CREDENTIALS_JSON có phải JSON hợp lệ không
# Dán thử vào https://jsonlint.com để kiểm tra
```

### ❌ `ValueError: Chưa set TELEGRAM_BOT_TOKEN`
```
# Đảm bảo đã chạy cell ở Bước 7 trước khi chạy app.py
```

### ❌ Bot chạy nhưng không nhận được ảnh
```
# Kiểm tra TELEGRAM_BOT_TOKEN đúng chưa (lấy lại từ @BotFather)
# Gõ /start trong Telegram để reset
```

### ❌ Video tạo xong nhưng bị lỗi khi ghép nhạc
```
# Kiểm tra ffmpeg đã cài chưa: !ffmpeg -version
# Nếu chưa: !apt-get install -y ffmpeg
```

---

## Cấu hình nâng cao (tùy chọn)

### Thêm nhạc nền riêng

```bash
# Tạo thư mục music và đặt file .mp3 theo format: <mood>_<tên>.mp3
mkdir -p /content/affiliate_bot/assets/music

# Ví dụ:
# assets/music/elegant_piano01.mp3
# assets/music/casual_trendy_pop01.mp3
# assets/music/summer_tropical01.mp3
```

Mood hợp lệ: `elegant`, `casual_trendy`, `summer`, `corporate`, `powerful`, `energetic`, `cozy`, `vietnamese`, `street`, `feminine`, `urban`, `fashion`

### Thêm font tùy chỉnh

```bash
# Tải Montserrat Bold (khuyến nghị)
!wget -q -O /content/affiliate_bot/assets/fonts/Montserrat-Bold.ttf \
  "https://github.com/google/fonts/raw/main/ofl/montserrat/Montserrat-Bold.ttf"
```

### Giới hạn user được dùng bot

```python
# Thêm vào Secrets:
# ALLOWED_USER_IDS = "123456789,987654321"  (Telegram user ID, phân cách bằng dấu phẩy)
# Lấy user ID của bạn: nhắn tin cho @userinfobot trên Telegram
```

---

## Checklist trước khi chạy

- [ ] GPU runtime đang hoạt động (Runtime → Change runtime type → GPU)
- [ ] `ffmpeg` đã cài (`!ffmpeg -version`)
- [ ] Models đã tải xong (thư mục `models/` không trống)
- [ ] `TELEGRAM_BOT_TOKEN` đã set và hợp lệ
- [ ] `GDRIVE_CREDENTIALS_JSON` và `GDRIVE_ROOT_FOLDER_ID` đã set
- [ ] Drive folder đã được share với Service Account email
- [ ] Đã chạy cell đọc Secrets (Bước 7) trước khi chạy `app.py`
