# Hướng Dẫn Sử Dụng — Affiliate Video Bot v6

> Hệ thống tạo video affiliate tự động cho TikTok & Shopee, hoàn toàn miễn phí, dùng AI mới nhất 2026.

---

## Tổng Quan Hệ Thống

```
[Bạn] → Telegram → [Render.com] → HTTP → [Google Colab GPU]
                        ↑                        |
                   Cron-job                 AI tạo video
                  (giữ sống 24/7)               |
                        └────── callback ────────┘
```

| Thành phần | Vai trò | Chi phí |
|-----------|---------|---------|
| GitHub | Lưu code | Miễn phí |
| Render.com | Host bot Telegram 24/7 | Miễn phí |
| Cron-job.org | Ping giữ Render sống | Miễn phí |
| Google Colab | Xử lý AI, tạo video (GPU) | Miễn phí |
| Google Drive | Lưu model, nhạc, video (5TB) | Miễn phí |
| Telegram | Giao tiếp, ra lệnh | Miễn phí |

---

## BƯỚC 1 — Chuẩn Bị Tài Khoản

### 1.1 Tạo Telegram Bot
1. Mở Telegram → tìm **@BotFather**
2. Gửi `/newbot` → đặt tên → lấy **Token**
3. Lưu token dạng: `1234567890:AAHxxxxxxxxxxxxxxxxxxxx`

### 1.2 Đăng ký ngrok (miễn phí)
1. Vào [ngrok.com](https://ngrok.com) → Sign up
2. Vào Dashboard → **Your Authtoken**
3. Copy token (dùng ở Cell 0 của Colab)

### 1.3 Đăng ký Pixabay API (nhạc nền miễn phí)
1. Vào [pixabay.com/api](https://pixabay.com/api/docs/) → Sign up miễn phí
2. Copy **API Key** (dùng làm env var trên Render)

### 1.4 Lấy Telegram User ID
- Nhắn tin cho **@userinfobot** trên Telegram
- Copy số ID (dùng ở Cell 0 của Colab)

---

## BƯỚC 2 — Đẩy Code Lên GitHub

### 2.1 Tạo repository
1. Vào [github.com](https://github.com) → **New repository**
2. Đặt tên: `affiliate-video-bot`
3. Để Private (không public API keys)

### 2.2 Push code lên GitHub
```bash
# Trên máy tính của bạn:
cd affiliate_video_bot_v6
git init
git add .
git commit -m "Affiliate Video Bot v6"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/affiliate-video-bot.git
git push -u origin main
```

> Thay `YOUR_USERNAME` bằng tên GitHub của bạn.

---

## BƯỚC 3 — Deploy Lên Render

### 3.1 Tạo Web Service bằng Blueprint (nhanh nhất)
1. Vào [render.com](https://render.com) → Đăng ký miễn phí
2. **New** → **Blueprint**
3. Kết nối GitHub → chọn repo `affiliate-video-bot`
4. Render tự đọc `render.yaml` và tạo service

### 3.2 Hoặc tạo thủ công
1. **New** → **Web Service**
2. Chọn repo GitHub
3. Cài đặt:
   - **Runtime**: Docker
   - **Branch**: `main`
   - **Region**: Singapore (gần Việt Nam)
   - **Plan**: Free

### 3.3 Thêm Environment Variables
Vào **Environment** tab trong Render Dashboard, thêm:

| Key | Value | Bắt buộc |
|-----|-------|----------|
| `TELEGRAM_TOKEN` | Token từ @BotFather | ✅ |
| `RENDER_URL` | URL service, ví dụ: `https://affiliate-video-bot.onrender.com` | ✅ |
| `PIXABAY_API_KEY` | Key từ pixabay.com | ⬜ |
| `NGROK_AUTH_TOKEN` | Token từ ngrok.com | ⬜ |
| `COLAB_SECRET` | `affiliatebot_v6_secret` | ✅ |
| `VIDEO_ENGINE` | `auto` | ⬜ |
| `DEFAULT_PLATFORM` | `tiktok` | ⬜ |

4. Click **Deploy** → Đợi 3-5 phút

### 3.4 Kiểm tra deploy
```
https://affiliate-video-bot.onrender.com/ping
```
Phải trả về: `{"status": "alive", ...}`

---

## BƯỚC 4 — Cài Cron-job Giữ Bot Sống 24/7

Render Free tier ngủ sau 15 phút. Dùng Cron-job để ping mỗi 14 phút:

1. Vào [cron-job.org](https://cron-job.org) → Đăng ký miễn phí
2. **Create Cronjob**:
   - **Title**: Keep Render Alive
   - **URL**: `https://affiliate-video-bot.onrender.com/ping`
   - **Schedule**: Custom → `*/14 * * * *` (mỗi 14 phút)
   - **Method**: GET
3. **Save** → bật **Active**

✅ Bot sẽ luôn online 24/7.

---

## BƯỚC 5 — Cài Colab (Bộ Não AI)

### 5.1 Mở Google Colab
1. Vào [colab.research.google.com](https://colab.research.google.com)
2. **New notebook**
3. Đổi Runtime: **Runtime** → **Change runtime type** → **T4 GPU**

### 5.2 Copy từng Cell vào Colab

Mở file `colab_notebook.py`, copy từng CELL theo thứ tự:

#### Cell 0 — Điền thông tin cá nhân
```python
GITHUB_REPO      = "https://github.com/YOUR_USERNAME/affiliate-video-bot.git"
NGROK_AUTH_TOKEN = "your_ngrok_token"
RENDER_URL       = "https://affiliate-video-bot.onrender.com"
BOT_SECRET       = "affiliatebot_v6_secret"
YOUR_TELEGRAM_ID = 123456789  # ID Telegram của bạn
```

#### Cell 1 — Cài deps (chạy 1 lần, ~8 phút)
```python
!apt-get install -y ffmpeg -q
!pip install -q python-telegram-bot Pillow diffusers transformers ...
!git clone GITHUB_REPO /content/affiliate-video-bot
```

#### Cell 2 — Mount Drive + fonts (chạy 1 lần)
```python
from pipeline.drive_manager import setup_drive
drive = setup_drive()
drive.get_font_path("Montserrat-Bold.ttf")
```

#### Cell 3 — Tải AI model (1 lần, tùy chọn)
```python
# Chọn 1 model phù hợp với VRAM Colab của bạn:
# T4 (15GB): Wan2.1-I2V hoặc CogVideoX-5B
# Không tải cũng được (bot dùng MoviePy fallback)
```

#### Cell 4 — Khởi động server (chạy MỖI session)
```python
# Tự động:
# 1. Mount Drive
# 2. Khởi động Flask server
# 3. Tạo ngrok tunnel
# 4. Đăng ký URL về Render (không cần copy-paste thủ công!)
# 5. Gửi thông báo về Telegram của bạn
```

---

## BƯỚC 6 — Kết Nối Colab Với Telegram

### Cách 1: Tự động (Cell 4 làm sẵn)
Khi chạy Cell 4, Colab tự đăng ký URL về Render và gửi thông báo Telegram:
```
🤖 Colab đã tự kết nối!
🔗 URL: https://xxxx.ngrok-free.app
✅ Sẵn sàng nhận task. Dùng /tao để tạo video ngay.
```

### Cách 2: Thủ công (nếu cách 1 không được)
Sau khi Cell 4 chạy xong, bạn thấy:
```
🔗 ngrok URL: https://xxxx.ngrok-free.app
```
Gửi vào Telegram:
```
/setcolab https://xxxx.ngrok-free.app
```

---

## Sử Dụng Hàng Ngày

### Quy trình mỗi ngày
1. Mở Colab notebook (tab đang có sẵn)
2. Nếu runtime đã disconnect → **Reconnect** → chạy lại **Cell 4**
3. Telegram tự nhận thông báo Colab ready
4. Gửi lệnh `/tao` để tạo video

### Các lệnh Telegram

| Lệnh | Mô tả |
|------|-------|
| `/tao Tên \| Giá \| Mô tả \| platform` | Tạo video affiliate |
| `/wake` | Kiểm tra Colab có sống không |
| `/setcolab <url>` | Đăng ký URL ngrok thủ công |
| `/colabstatus` | Trạng thái chi tiết kết nối |
| `/autocolab on` | Bật tự ping giữ Colab sống |
| `/drive` | Xem dung lượng Google Drive |
| `/status` | Trạng thái bot + Render |
| `/clear` | Xóa task đang chờ |
| `/help` | Hướng dẫn đầy đủ |

### Ví dụ tạo video
```
/tao Váy maxi hoa nhí | 299k | Váy nữ vải lụa mềm tay dài | tiktok
/tao Suit nam xanh navy | 850k | Vest công sở slim fit | both
/tao Set bé gái 3-8t | 185k | Bộ đồ trẻ em cotton | shopee
/tao Bodysuit sơ sinh | 125k | Bodysuit bé 0-12 tháng | shopee
/tao Áo đôi matching | 299k | Đồ đôi couple unisex | tiktok
/tao Áo dài nữ lụa | 650k | Áo dài truyền thống lễ Tết | tiktok
```

Platform: `tiktok` | `shopee` | `both`

### Gửi ảnh sản phẩm
Gửi ảnh + caption theo format:
```
Tên sản phẩm | Giá | Mô tả ngắn
```
AI sẽ tự phân tích ảnh và tạo video phù hợp.

---

## AI Tools Miễn Phí Được Tích Hợp (2026)

### Video Generation
| Tool | Chất lượng | VRAM | Tốc độ |
|------|-----------|------|--------|
| **Wan2.1-I2V-14B** (Alibaba) | ⭐⭐⭐⭐⭐ | 12GB | ~5 phút |
| **CogVideoX-5B** (Tsinghua) | ⭐⭐⭐⭐ | 8GB | ~3 phút |
| **AnimateDiff XL** | ⭐⭐⭐ | 6GB | ~2 phút |
| **Stable Video Diffusion** | ⭐⭐⭐ | 8GB | ~3 phút |
| **MoviePy** (no GPU) | ⭐⭐ | 0GB | ~30 giây |

### Image Generation (cho slideshow)
| Tool | Chất lượng | VRAM | Tốc độ |
|------|-----------|------|--------|
| **FLUX.1-schnell** (Black Forest) | ⭐⭐⭐⭐⭐ | 6GB | ~30 giây |
| **SDXL Base** (Stability AI) | ⭐⭐⭐⭐ | 6GB | ~1 phút |

### Music Generation
| Tool | Loại | Ghi chú |
|------|------|---------|
| **AudioCraft MusicGen** (Meta) | AI sinh nhạc | Miễn phí, cần GPU |
| **Pixabay Music API** | Thư viện nhạc | Miễn phí, 20k+ bài |
| **Freesound.org API** | CC0 audio | Miễn phí, không attribution |

### AI Analysis
| Tool | Vai trò | Ghi chú |
|------|---------|---------|
| **CLIP ViT-L/14** (OpenAI) | Nhận diện ảnh | Miễn phí HuggingFace |
| **Keyword Matching** | Fallback | Không cần GPU |

---

## Timeline Video 15 Giây (Chuẩn Viral 2026)

```
0s ─── 2.5s ─── 6s ─── 10s ─── 13s ─── 15s
│        │       │        │       │       │
HOOK   PRODUCT  VALUE    CTA    LOOP   END
(stop  +PRICE   STACK  +COMMENT BACK
scroll) (desire) (+conv)  (×4 reach)
```

- **0–2.5s HOOK**: Câu dừng scroll, emoji, tạo tò mò
- **2.5–6s PRODUCT**: Tên SP + giá + badge viral
- **6–10s VALUE**: Freeship, đổi trả, review
- **10–13s CTA**: Mua ngay + Comment để nhận link (tăng reach ×4)
- **13–15s LOOP**: Seamless loop về đầu

---

## Câu Hỏi Thường Gặp

### Render bị ngủ (sleep) không?
Có — Render Free tier ngủ sau 15 phút idle. Cron-job ping mỗi 14 phút giữ nó luôn thức.

### Colab bị disconnect không?
Có — Colab Free disconnect sau ~12 giờ hoặc tab đóng quá lâu. Khi đó:
1. Reconnect Colab runtime
2. Chạy lại Cell 4 (tự lấy URL mới và đăng ký về Render)
3. Telegram tự nhận thông báo — không cần làm gì thêm

### Ngrok URL có thay đổi mỗi lần không?
Có (nếu dùng miễn phí). Nhưng Cell 4 tự xử lý: mỗi lần chạy Colab, nó tự đăng ký URL mới về Render qua `/colab/seturl`.

Nếu muốn URL cố định: Đăng ký [ngrok static domain](https://ngrok.com/blog-post/free-static-domains-ngrok-users) (miễn phí 1 domain).

### Video chất lượng kém khi không có GPU?
Bot dùng MoviePy fallback (gradient + text) khi không có GPU. Chất lượng đủ dùng. Để video AI đẹp cần chạy Cell 4 với T4 GPU.

### Colab Free có đủ để chạy không?
Đủ cho CogVideoX-5B và AnimateDiff. Wan2.1 cần T4 15GB (Colab Free có T4). Nếu VRAM không đủ, bot tự dùng engine nhẹ hơn.

### Cần Google Drive dung lượng bao nhiêu?
- Fonts: ~50MB
- AI model (1 cái): 7–25GB
- Nhạc nền (cache): ~100MB
- Video output: ~50MB/video

Drive 5TB hoàn toàn đủ cho nhiều năm sử dụng.

---

## Cấu Trúc Thư Mục

```
affiliate_video_bot_v6/
├── app.py                    ← Bot Telegram + Flask server (Render)
├── config.py                 ← Cấu hình tập trung
├── colab_notebook.py         ← Notebook Colab (copy cell vào Colab)
├── Dockerfile                ← Docker build (Render dùng)
├── render.yaml               ← Render deployment config
├── requirements.txt          ← Python dependencies
├── HUONG_DAN.md              ← File này
└── pipeline/
    ├── ai_analyzer.py        ← Phân tích sản phẩm (CLIP + keyword)
    ├── background.py         ← AI video prompts (Wan2.1, CogVideoX)
    ├── caption_gen.py        ← Sinh caption nhanh
    ├── drive_manager.py      ← Quản lý Google Drive 5TB
    ├── music_engine.py       ← Nhạc nền AI (Pixabay, Freesound, AudioCraft)
    ├── script_writer.py      ← Viết kịch bản video 15 giây
    ├── text_overlay.py       ← Overlay text + badge lên video
    ├── video_engine.py       ← AI video generation (5 engines)
    └── viral_strategy.py     ← Hook, caption, hashtag viral
```

### Google Drive Structure
```
MyDrive/AffiliateBot/
├── models/                   ← AI model weights (Wan2.1, CogVideoX, FLUX...)
├── music/                    ← Nhạc nền theo mood (cache từ Pixabay)
├── fonts/                    ← Font chữ (Montserrat, BeVietnamPro)
├── outputs/                  ← Video đầu ra (theo ngày)
│   └── 20260523/
│       └── video_143022.mp4
├── backgrounds/              ← Ảnh nền (nếu có)
└── cache/                    ← Cache tạm
    ├── pixabay/
    └── freesound/
```

---

## Lưu Ý Quan Trọng

1. **Không commit** `.env` hay token vào GitHub
2. **Thay `YOUR_USERNAME`** trong Cell 0 bằng tên GitHub thật
3. **Giữ Colab tab mở** — đóng tab = Colab ngủ sau ~90 phút
4. **Colab Free** có giới hạn GPU/ngày — dùng tiết kiệm, tạo xong thì tắt
5. **Render Free** có 750 giờ/tháng — đủ cho 1 service chạy liên tục
6. **Video output** lưu Drive — download về máy để đăng TikTok/Shopee

---

*Hệ thống được xây dựng với tất cả công cụ AI miễn phí, tối ưu cho thị trường Affiliate Việt Nam 2026.*
