# Affiliate Video Bot v5 — AI Fashion Video Generator 2026

> Bot AI tự động tạo video affiliate viral cho **toàn bộ ngành thời trang**:  
> 👗 Nữ · 👔 Nam · 👶 Trẻ em / Baby · 💕 Đôi / Gia đình · 🌀 Unisex

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Render](https://img.shields.io/badge/Deploy-Render-46E3B7.svg)](https://render.com)
[![Colab](https://img.shields.io/badge/AI_GPU-Google%20Colab-orange.svg)](https://colab.research.google.com)
[![Storage](https://img.shields.io/badge/Storage-Google%20Drive%205TB-green.svg)](https://drive.google.com)

---

## Kiến trúc hệ thống

```
┌─────────────┐     /tao lệnh      ┌──────────────────────────────┐
│   Telegram  │ ←────────────────→ │  Render Web Service (Docker)  │
│    User     │                    │  • Flask /ping  (keep-alive)  │
└─────────────┘                    │  • Telegram Bot (polling)     │
                                   │  • /setcolab, /wake           │
                                   └──────────┬───────────────────┘
                                              │ HTTP POST /generate
                                              ▼
                                   ┌──────────────────────────────┐
                                   │  Google Colab (GPU T4/L4)     │
                                   │  • ngrok expose port 5000    │
                                   │  • Wan2.1 / CogVideoX AI     │
                                   │  • Text overlay + Music      │
                                   │  • Lưu Drive → callback Render│
                                   └──────────────────────────────┘
                                              │
                                              ▼
                                   ┌──────────────────────────────┐
                                   │  Google Drive 5TB             │
                                   │  models / music / outputs    │
                                   └──────────────────────────────┘

Cron-job.org → GET /ping mỗi 14 phút → Render không bị sleep
```

---

## Cấu trúc dự án

```
affiliate-video-bot/
├── app.py                   ← Telegram Bot + Flask web server (entry point)
├── config.py                ← Cấu hình (env vars)
├── requirements.txt
├── Dockerfile               ← Docker image cho Render
├── render.yaml              ← Render Blueprint config
├── colab_notebook.py        ← Copy vào Colab cells
├── pipeline/
│   ├── ai_analyzer.py       ← CLIP garment recognition
│   ├── script_writer.py     ← AI video script generator
│   ├── video_engine.py      ← Wan2.1 / CogVideoX wrapper
│   ├── viral_strategy.py    ← Viral content engine 2026
│   ├── background.py        ← AI video prompts
│   ├── text_overlay.py      ← Video text overlay (3-layer)
│   ├── music_engine.py      ← Music + Drive cache
│   ├── caption_gen.py       ← Caption generator
│   └── drive_manager.py     ← Google Drive asset manager
└── tests/
    └── test_pipeline.py
```

---

## Hướng dẫn Deploy đầy đủ

### BƯỚC 1 — Upload lên GitHub

```bash
# Tạo repo mới trên github.com rồi:
git init
git add .
git commit -m "feat: affiliate video bot v5"
git remote add origin https://github.com/YOUR_USERNAME/affiliate-video-bot.git
git push -u origin main
```

---

### BƯỚC 2 — Deploy lên Render bằng Docker

1. Vào [render.com](https://render.com) → **New** → **Blueprint**
2. Kết nối GitHub account → chọn repo `affiliate-video-bot`
3. Render tự đọc `render.yaml` và tạo service

**Hoặc tạo thủ công:**
1. **New** → **Web Service**
2. Chọn repo GitHub của bạn
3. Settings:
   - **Runtime**: Docker
   - **Dockerfile Path**: `./Dockerfile`
   - **Branch**: `main`
   - **Plan**: Free (hoặc Starter nếu cần)
   - **Region**: Singapore (gần Vietnam nhất)

4. Thêm **Environment Variables** trong Render Dashboard:

| Key | Value |
|-----|-------|
| `TELEGRAM_TOKEN` | Token từ @BotFather |
| `PIXABAY_API_KEY` | Key từ pixabay.com (miễn phí) |
| `RENDER_URL` | URL service này, ví dụ: `https://affiliate-video-bot.onrender.com` |
| `VIDEO_ENGINE` | `auto` |

5. Click **Deploy** → Đợi ~3-5 phút

---

### BƯỚC 3 — Cài Cron-job để giữ bot sống 24/7

Render Free tier sẽ sleep sau 15 phút không có request.  
Dùng Cron-job.org để ping mỗi 14 phút:

1. Vào [cron-job.org](https://cron-job.org) → Đăng ký miễn phí
2. **Create Cronjob**:
   - **URL**: `https://your-app.onrender.com/ping`
   - **Schedule**: Every 14 minutes (*/14 * * * *)
   - **Method**: GET
3. Save → Enable

✅ Bot sẽ luôn alive 24/7, không bị sleep.

---

### BƯỚC 4 — Cài Colab lần đầu

> Colab xử lý AI nặng (GPU) — chỉ cần khi tạo video thật sự.

1. Mở [Google Colab](https://colab.research.google.com)
2. Chọn Runtime: **T4 GPU** (hoặc L4 nếu có Colab Pro)
3. Copy từng cell từ file `colab_notebook.py` vào Colab

**Cell 1** — Cài dependencies (1 lần duy nhất):
```python
!apt-get install -y ffmpeg -q
!pip install -q python-telegram-bot==21.6 Pillow diffusers transformers ...
!git clone https://github.com/YOUR_USERNAME/affiliate-video-bot.git /content/affiliate-video-bot
```

**Cell 3** — Tải fonts về Drive (1 lần):
```python
from pipeline.drive_manager import drive_mgr
drive_mgr.get_font_path("Montserrat-Bold.ttf")
```

**Cell 4** — Tải AI model về Drive (1 lần, ~15 phút):
```python
from pipeline.video_engine import download_model_to_drive
download_model_to_drive("Wan-AI/Wan2.1-I2V-14B-480P", "wan2.1-i2v-14B-480P")
```

---

### BƯỚC 5 — Đánh thức Colab từ Telegram

Mỗi khi muốn tạo video, bạn cần Colab đang chạy:

1. **Mở Colab** → kết nối Runtime T4 GPU
2. **Chạy Cell 2** (ngrok server) — lấy URL ngrok:
   ```
   ✅ Colab server đang chạy!
   🔗 ngrok URL: https://xxxx.ngrok-free.app
   ```
3. **Gửi lệnh trong Telegram**:
   ```
   /setcolab https://xxxx.ngrok-free.app
   ```
4. Bot xác nhận kết nối → bạn sẵn sàng tạo video!

**Sau đó dùng:**
- `/wake` — Kiểm tra Colab có đang chạy không
- `/tao Váy maxi | 299k | Váy lụa | tiktok` — Tạo video

---

## Các lệnh Telegram

| Lệnh | Mô tả |
|------|-------|
| `/tao Tên \| Giá \| Mô tả \| platform` | Tạo video (gửi sang Colab xử lý) |
| `/setcolab <url>` | Đăng ký URL ngrok của Colab |
| `/wake` | Kiểm tra / ping Colab |
| `/colabstatus` | Chi tiết trạng thái Colab |
| `/status` | Trạng thái bot và Render |
| `/drive` | Thống kê Google Drive |
| `/clear` | Xóa task đang chờ |
| `/help` | Hướng dẫn chi tiết |

**Platform options:** `tiktok` | `shopee` | `both`

**Ví dụ:**
```
/tao Váy maxi hoa nhí | 299k | Váy nữ vải lụa mềm | tiktok
/tao Suit nam xanh navy | 850k | Vest nam công sở slim fit | both
/tao Set bé gái 3-8t | 185k | Bộ đồ trẻ em cotton | shopee
/tao Bodysuit sơ sinh | 125k | Bodysuit bé 0-12 tháng | shopee
/tao Đồ đôi matching | 299k | Áo đôi couple unisex | tiktok
```
Hoặc: Gửi **ảnh sản phẩm** kèm caption để AI tự phân tích.

---

## Endpoints (Render Web Service)

| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/ping` | GET | Keep-alive cho Cron-job, health check cho Render |
| `/health` | GET | Trạng thái chi tiết (colab_connected, v.v.) |
| `/colab/callback` | POST | Colab gọi về sau khi xong video |

---

## Endpoints (Colab ngrok server)

| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/ping` | GET | Kiểm tra Colab alive |
| `/generate` | POST | Nhận task từ Render, chạy AI pipeline |

---

## Cài ngrok (để Colab expose ra internet)

1. Đăng ký miễn phí tại [ngrok.com](https://ngrok.com)
2. Lấy Auth Token trong Dashboard
3. Điền vào Cell 2 của Colab:
   ```python
   NGROK_AUTH_TOKEN = "your_token_here"
   ```

> Không có ngrok token vẫn chạy được nhưng URL có thể thay đổi.

---

## Environment Variables đầy đủ

| Variable | Mô tả | Bắt buộc |
|----------|-------|----------|
| `TELEGRAM_TOKEN` | Bot token từ @BotFather | ✅ |
| `RENDER_URL` | URL Render service (cho Colab callback) | ✅ |
| `PIXABAY_API_KEY` | Pixabay API (miễn phí) | ⬜ |
| `VIDEO_ENGINE` | `auto` / `wan21` / `cogvideox` | ⬜ |
| `COLAB_WEBHOOK_URL` | Preset ngrok URL (nếu muốn) | ⬜ |

---

## Timeline Video 2026 (15 giây)

```
0s ──── 2.5s ──── 6.0s ──── 10.0s ──── 13s ──── 15s
│         │         │           │          │        │
HOOK    PRODUCT   VALUE      CTA +      LOOP    SEAMLESS
(stop   +PRICE    STACK    COMMENT     BACK       LOOP
scroll) (desire) (+67%    (x4 reach)
                 conv)
```

---

## FAQ

**Q: Render free tier có bị sleep không?**  
A: Có — sleep sau 15 phút idle. Dùng Cron-job ping `/ping` mỗi 14 phút để giữ alive.

**Q: Colab có bị disconnect không?**  
A: Có — Colab Free disconnect sau ~12h hoặc khi tab đóng lâu. Khi đó chạy lại Cell 2 và `/setcolab <url_moi>`.

**Q: Ngrok URL có thay đổi không?**  
A: Có — mỗi lần chạy Cell 2 sẽ có URL mới. Nhớ `/setcolab <url_moi>` mỗi lần.  
Ngrok Pro ($0 miễn phí 1 domain tĩnh) sẽ giữ URL cố định.

**Q: Bot vẫn nhận lệnh khi Colab offline không?**  
A: Có — Render luôn online. Chỉ là video AI sẽ không được tạo. Bot sẽ thông báo cho bạn biết.

---

*Built with ❤️ for Vietnamese fashion affiliate marketers*
