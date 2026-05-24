# 🎬 Affiliate Studio v8

AI tạo video affiliate TikTok — người mẫu mặc sản phẩm, talking review, viral hook.

---

## Kiến trúc hệ thống

```
Telegram ←→ Render (Flask Bot)  ←→  Colab GPU (AI Pipeline)
                                         ↓
                                  Google Drive 5TB
                                  (models, outputs, fonts)
                                         ↓
                              GitHub ←→ render.yaml → redeploy
```

### Quy trình tạo video

```
User gửi ảnh SP  →  Bot nhận
       ↓
Colab: rembg tách nền → preview ảnh nền trắng
       ↓
User gửi ảnh model (hoặc /skip → Drive library)
       ↓
Colab: IDM-VTON / OOTDiffusion → model mặc SP
       ↓
Colab: Tạo background AI (FLUX / Wan2.1)
       ↓
Colab: Wan2.1-I2V / CogVideoX → animate scene
       ↓
Colab: Script cảm xúc + text overlay + CTA + nhạc
       ↓
Drive: lưu video → Telegram gửi về user
```

---

## Setup lần đầu (30 phút)

### 1. GitHub

```bash
git clone https://github.com/YOUR_USERNAME/affiliate-studio-v8
cd affiliate-studio-v8
```

### 2. Render

1. Vào [render.com](https://render.com) → New → Web Service → Connect GitHub repo
2. Render tự đọc `render.yaml` → tạo service `affiliate-studio-v8`
3. Environment variables → Add:

| Key | Value |
|-----|-------|
| `TELEGRAM_TOKEN` | Token từ @BotFather |
| `ALLOWED_USER_IDS` | Telegram ID của bạn |
| `RENDER_URL` | `https://affiliate-studio-v8.onrender.com` |
| `COLAB_SECRET` | `affiliatestudio_v8_secret` |
| `RENDER_DEPLOY_HOOK` | Từ Render → Settings → Deploy Hooks |

4. GitHub Actions → Settings → Secrets → Add:
   - `RENDER_URL` = URL của service

### 3. Colab

1. Upload `notebooks/affiliate_studio_v8.ipynb` lên Google Colab
2. Runtime → T4 GPU
3. Cell 0: điền `GITHUB_REPO`, `GITHUB_TOKEN`, `NGROK_AUTH_TOKEN`, `YOUR_TELEGRAM_ID`
4. Cell 1 → 2 → 3 (tải models) → Cell 4 (start server)

### 4. Telegram Bot

Gửi `/start` → `/new` → Bắt đầu tạo video

---

## Lệnh Telegram

| Lệnh | Mô tả |
|------|--------|
| `/new` | Bắt đầu session tạo video mới |
| `/skip` | Bỏ qua ảnh model, bot tự chọn |
| `/cancel` | Hủy session hiện tại |
| `/status` | Xem trạng thái Render + Colab |
| `/wake` | Kiểm tra / đánh thức Colab |
| `/setcolab <url>` | Cập nhật ngrok URL thủ công |
| `/autocolab on/off` | Bật/tắt auto-ping giữ Colab sống |
| `/drive` | Xem Google Drive stats |
| `/github <msg>` | Push code lên GitHub |
| `/deploy` | Trigger Render redeploy |

---

## Google Drive 5TB Structure

```
AffiliateStudio/
├── models/
│   ├── idm-vton/           ← AI try-on model (~8GB)
│   ├── wan2.1-i2v-14B-480P/← Image→Video (~25GB)
│   ├── cogvideox-5b/       ← Image→Video alt (~18GB)
│   ├── flux1-schnell/      ← Background gen (~8GB)
│   ├── musicgen-small/     ← Nhạc AI (~300MB)
│   ├── fashion/            ← Thư viện ảnh model (fashion)
│   ├── beauty/             ← Thư viện ảnh model (beauty)
│   ├── male/female/child/unisex/  ← Phân theo gender
│   └── ...10 ngành hàng
├── outputs/
│   ├── videos/             ← Video đã tạo
│   ├── previews/           ← Try-on preview images
│   └── captions/           ← Caption text files
├── products/               ← Product photo cache
├── fonts/                  ← Montserrat, BeVietnamPro
├── music/                  ← Nhạc nền cache
└── addons/                 ← Plugins, templates
```

---

## AI Models — Chọn theo GPU

| Model | Tác dụng | VRAM | T4 Free |
|-------|----------|------|---------|
| **rembg** | Tách nền | CPU | ✅ Auto |
| **IDM-VTON** | Try-on tốt nhất | 10GB | ✅ |
| **CogVideoX-5B** | Video (nhanh) | 8GB | ✅ |
| **Wan2.1-I2V** | Video (cinematic) | 12GB | ✅ |
| **FLUX.1-schnell** | Background AI | 6GB | ✅ |
| **MusicGen** | Nhạc AI | 4GB | ✅ |

> Colab Free T4 = 15GB VRAM → Chạy được tất cả (không cùng lúc)

---

## Keep Render Alive (Free Plan)

Render free ngủ sau 15 phút. 3 cách giải quyết:

**Cách 1: GitHub Actions** (tự động, khuyến nghị)
→ `.github/workflows/keep_alive.yml` ping mỗi 10 phút miễn phí

**Cách 2: Script local**
```bash
python scripts/keep_alive.py --render https://affiliate-studio-v8.onrender.com
```

**Cách 3: /autocolab on** trong Telegram
→ Colab sẽ tự ping Render mỗi 10 phút
