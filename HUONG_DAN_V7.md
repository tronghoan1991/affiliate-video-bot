# 🤖 Hướng Dẫn Affiliate Video Bot v7 — 2026

## 📊 Research Thị Trường 2026

### Tại Sao Video Affiliate Viral?

Sau khi phân tích **34,635 video TikTok** (OpusClip Q1/2026) + dữ liệu Shopee Vietnam:

| Yếu tố | Tác động |
|--------|----------|
| **2 giây đầu quyết định** 70% retention | Hook phải gây shock/tò mò ngay lập tức |
| **Comment bait** ("Comment 'MUA' để nhận link") | Tăng reach **×4** — TikTok ưu tiên video có comment |
| **Loop seamless** (0→15s không cắt đứng) | Completion rate cao → thuật toán đẩy nhiều hơn |
| **Transformation** (trước/sau) | CTR cao nhất trong tất cả ngành hàng |
| **Social proof** cụ thể (số liệu thật) | Tăng conversion rate 2.3× |

### Số Liệu Thị Trường

- 🇻🇳 TikTok Shop Vietnam H1/2025: **$3.57 tỷ GMV (+148% YoY)**
- 📊 TikTok chiếm **42%** toàn bộ e-commerce GMV Việt Nam
- 💰 Market affiliate VN 2024: **$700M–$1 tỷ**, tăng **30x** từ 2022
- 🚀 Social commerce VN 2026: dự kiến **$20.98 tỷ**

---

## 🎯 7-Trigger Emotional Framework

Bot v7 dùng 7 trigger tâm lý để tạo video mua hàng:

| Trigger | Mô tả | Thời điểm dùng |
|---------|-------|----------------|
| 🔴 **FOMO** | Sợ bỏ lỡ, sắp hết hàng | Hook + CTA |
| 💛 **SOCIAL PROOF** | Số lượng người đã mua | Reveal |
| 🟣 **CURIOSITY** | Tò mò, câu chuyện chưa kể xong | Hook (loop) |
| 💚 **TRANSFORMATION** | Trước/sau rõ rệt | Value |
| 🔵 **AUTHENTICITY** | Thật, không sponsored | Trust |
| 🟤 **IDENTITY** | "Sản phẩm này là tôi" | Deep connection |
| ⚡ **URGENCY** | Giới hạn thời gian/số lượng | CTA |

### Timeline 15 Giây Tối Ưu

```
0–2s   [HOOK]     CURIOSITY + FOMO → Stop the scroll
2–6s   [REVEAL]   SOCIAL PROOF + TRANSFORMATION → Create desire  
6–10s  [VALUE]    AUTHENTICITY + IDENTITY → Build trust
10–13s [CTA]      URGENCY + FOMO + Comment bait → Drive action
13–15s [LOOP]     CURIOSITY hook → Seamless back to start
```

---

## ⚙️ Deploy Lần Đầu

### Bước 1: Push lên GitHub

```bash
git init
git add .
git commit -m "feat: affiliate video bot v7"
git remote add origin https://github.com/YOUR_USERNAME/affiliate-video-bot.git
git push -u origin main
```

### Bước 2: Deploy lên Render

1. Đăng nhập [render.com](https://render.com) → New → Web Service
2. Kết nối GitHub repo → Branch: `main`
3. Runtime: **Docker** (tự detect `Dockerfile`)
4. Điền env vars:

| Key | Value |
|-----|-------|
| `TELEGRAM_TOKEN` | Token từ @BotFather |
| `RENDER_URL` | URL service sau deploy |
| `PIXABAY_API_KEY` | Lấy tại pixabay.com/api |
| `NGROK_AUTH_TOKEN` | Lấy tại ngrok.com |
| `COLAB_SECRET` | `affiliatebot_v7_secret` |
| `VIDEO_ENGINE` | `auto` |

5. Deploy → Lấy URL dạng `https://affiliate-video-bot-v7.onrender.com`
6. Copy URL này → điền vào `RENDER_URL` + vào Cell 0 của notebook

### Bước 3: Setup Cron-job (Giữ Render sống 24/7)

Vào [cron-job.org](https://cron-job.org) → Tạo job:
- URL: `https://YOUR_RENDER_URL/ping`
- Interval: **Mỗi 10 phút**
- Method: GET

---

## 🎬 Dùng Hàng Ngày

### Quy trình mỗi ngày

```
1. Mở notebook → Runtime → T4 GPU
2. Chạy Cell 0 (điền thông tin — đã có sẵn)
3. Chạy Cell 4 (Server tự khởi động + đăng ký về Render)
4. Telegram nhận thông báo "Colab ready!"
5. Gửi lệnh /tao để tạo video
```

### Lệnh Telegram

| Lệnh | Mô tả |
|------|-------|
| `/tao Tên \| Giá \| Mô tả \| platform` | Tạo video (gửi sang Colab GPU) |
| `/caption Tên \| Giá \| Mô tả` | Sinh caption ngay (không cần Colab) |
| `/abtest Tên \| Giá \| Mô tả` | Sinh 3 hook để A/B test |
| `/trending` | Ngành hàng hot nhất 2026 |
| `/wake` | Kiểm tra Colab còn sống không |
| `/setcolab <url>` | Cập nhật URL ngrok thủ công |
| `/autocolab on` | Tự ping Colab mỗi 10 phút |
| `/drive` | Xem thống kê Google Drive |
| `/status` | Trạng thái hệ thống |

### Ví dụ tạo video

```
/tao Serum Vitamin C | 350k | Serum trắng da niacinamide 10% | tiktok

/tao Váy maxi hoa nhí | 299k | Váy nữ lụa mềm tay dài | shopee

/tao Collagen uống | 890k | Collagen peptide Nhật 10000mg | both

/tao Ốp iPhone 15 | 89k | Ốp magsafe trong suốt chống sốc | tiktok

/tao Thức ăn mèo | 65k | Pate mèo vị cá hồi 400g | shopee
```

---

## 🤖 AI Engines (Tự động chọn theo VRAM)

| Engine | VRAM cần | Chất lượng | Thời gian |
|--------|----------|-----------|-----------|
| **Wan2.1-I2V-14B** | 12GB | ⭐⭐⭐⭐⭐ Cinematic | ~4-6 phút |
| **CogVideoX-5B** | 8GB | ⭐⭐⭐⭐ Tốt | ~3-5 phút |
| **AnimateDiff XL** | 6GB | ⭐⭐⭐ Ổn | ~2-3 phút |
| **FLUX + Slideshow** | 6GB | ⭐⭐⭐ Ảnh AI | ~1-2 phút |
| **MoviePy** | 0GB | ⭐⭐ Cơ bản | ~30 giây |

Colab T4 Free = **15GB VRAM** → Wan2.1 hoặc CogVideoX đều OK.

---

## 🏷️ 10 Ngành Hàng Hỗ Trợ

| Ngành | Commission | Target | Trigger chính |
|-------|-----------|--------|---------------|
| 💆 **Beauty/Skincare** | 10-15% | Nữ 18-40 | Transformation |
| 💊 **Health/Supplement** | 12-20% | Nữ 25-45, Nam 22-40 | Transformation + Auth |
| 👗 **Fashion** | 7-12% | Gen Z 16-28 | FOMO + Identity |
| 🏠 **Home & Living** | 8-12% | Nữ 22-40 | Curiosity + Social |
| 🍱 **Food/Snack** | 5-10% | 16-35 | Curiosity + Auth |
| 📱 **Tech Accessories** | 5-8% | Nam 18-35 | Social + FOMO |
| 🐾 **Pet Products** | 8-15% | 20-40 | Authenticity + Identity |
| 💪 **Sports** | 7-10% | 20-40 | Transformation |
| 👶 **Baby/Kids** | 8-15% | Mẹ 22-38 | Authenticity |
| 🎀 **Fashion Kids** | 7-12% | Ba mẹ 25-40 | Social + Auth |

---

## ❓ Troubleshooting

**Colab không kết nối:**
- `/wake` để ping → nếu fail: chạy lại Cell 4
- ngrok hết session (2h) → chạy lại Cell 4 → URL mới tự đăng ký

**Video fail:**
- Bot tự fallback MoviePy (không cần GPU)
- Thử `/caption` để lấy caption trước

**Render sleep (free tier):**
- Cron-job ping mỗi 10 phút giữ Render sống
- Nếu vẫn ngủ: mở URL Render một lần để wake up

**"Chưa điền NGROK_AUTH_TOKEN":**
- [ngrok.com](https://ngrok.com) → Sign up free → Dashboard → Authtoken
- Điền vào Cell 0 → chạy lại Cell 4
