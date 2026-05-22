# 📖 Hướng Dẫn Deploy Chi Tiết — Affiliate Video Bot v4.0
### Kiến trúc: GitHub → Render (Docker) + cron-job.org (keep-alive) + Google Colab (GPU Worker)

---

## 🗺️ Sơ Đồ Hoạt Động

```
cron-job.org
  │  ping /health mỗi 5 phút (giữ server sống)
  ▼
[Render Web Service — dispatcher.py chạy trong Docker]
  │  Chạy 24/7, MIỄN PHÍ, không cần GPU
  │  Nhận lệnh Telegram, /wakeup, quản lý trạng thái
  │
  │  Khi bạn tạo video:
  │  POST /process (ảnh + thông số qua HTTP)
  ▼
[Google Colab — colab_worker.py] ← Chạy khi cần, GPU T4 miễn phí
  │  Pipeline: CLIP → TryOn → Wan2.1 → ESRGAN → Nhạc → Drive
  │  Gửi video trực tiếp về Telegram
  ▼
Bạn nhận video trong Telegram ✅
```

| Dịch vụ | Vai trò | Chi phí |
|---|---|---|
| **Render** | Chạy bot 24/7 (dispatcher) | Miễn phí (Free tier) |
| **cron-job.org** | Ping Render mỗi 5 phút | Miễn phí |
| **Google Colab** | GPU xử lý video | Miễn phí (T4) |
| **ngrok** | Tunnel Colab ra internet | Miễn phí (1 tunnel) |
| **GitHub** | Lưu code, Render tự deploy | Miễn phí |

> ⚠️ **Giới hạn Render Free:**
> - Ngủ sau 15 phút không có request → **cron-job.org giải quyết vấn đề này**
> - 750 giờ/tháng miễn phí (đủ dùng 1 service liên tục)
> - Mỗi lần deploy mất ~2-5 phút build Docker

---

## PHẦN 1 — Chuẩn Bị Tài Khoản

### 1.1 Tạo Telegram Bot

1. Mở Telegram → tìm **@BotFather**
2. Gửi `/newbot` → đặt tên → đặt username (kết thúc `bot`)
3. Copy **Bot Token** (dạng: `123456789:ABCdefGHI...`) → lưu lại

**Lấy Telegram User ID của bạn:**
1. Tìm **@userinfobot** trên Telegram
2. Gửi tin bất kỳ → bot trả về ID số (vd: `987654321`)
3. Lưu lại số này

### 1.2 Tạo tài khoản ngrok (miễn phí)

1. Vào [ngrok.com](https://ngrok.com) → **Sign up**
2. Dashboard → **Your Authtoken** → copy token

### 1.3 Tạo Google Drive Service Account

> Bot tự lưu video vào Drive của bạn sau mỗi lần xử lý

1. Vào [console.cloud.google.com](https://console.cloud.google.com)
2. **Tạo project mới** → đặt tên `AffiliateBot`
3. **APIs & Services** → **Enable APIs** → tìm `Google Drive API` → **Enable**
4. **IAM & Admin** → **Service Accounts** → **Create Service Account**
   - Tên: `affiliate-bot` → Role: **Editor** → **Done**
5. Click vào service account → tab **Keys** → **Add Key** → **JSON** → tải về
6. Tạo thư mục `AffiliateVideos` trên Google Drive
7. Chuột phải thư mục → **Share** → nhập email service account → **Editor**
8. Copy **Folder ID** từ URL Drive: `.../folders/**FOLDER_ID_Ở_ĐÂY**`

---

## PHẦN 2 — Upload Code Lên GitHub

### 2.1 Tạo GitHub repository

1. Vào [github.com](https://github.com) → đăng nhập → **New repository**
2. Tên: `affiliate-video-bot` → chọn **Private** → **Create**
3. Copy URL repo (dạng: `https://github.com/username/affiliate-video-bot.git`)

### 2.2 Upload code

**Cách nhanh nhất — Upload trực tiếp trên GitHub:**
1. Mở repo vừa tạo → **Add file** → **Upload files**
2. Giải nén `affiliate_bot_v4.zip` → kéo thả **toàn bộ nội dung bên trong** vào trang GitHub
3. Nhấn **Commit changes**

**Cách dùng Git (nếu đã cài):**
```bash
cd affiliate_bot_v4
git init
git add .
git commit -m "Affiliate Video Bot v4.0"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/affiliate-video-bot.git
git push -u origin main
```

**Cấu trúc repo quan trọng (Render chỉ dùng 2 file này để build Docker):**
```
affiliate-video-bot/
├── Dockerfile                  ← Render đọc file này để build
├── render.yaml                 ← Cấu hình deploy tự động
├── dispatcher.py               ← Bot chạy trong container
├── requirements_dispatcher.txt ← Thư viện cho dispatcher
├── .dockerignore               ← Bỏ qua file không cần
├── colab_worker.py             ← Chạy trên Colab
├── run_bot.ipynb               ← Notebook Colab sẵn sàng
├── pipeline/                   ← Pipeline xử lý video (Colab)
└── HUONG_DAN_DEPLOY_VI.md
```

---

## PHẦN 3 — Deploy Lên Render (Docker)

### 3.1 Tạo tài khoản Render

1. Vào [render.com](https://render.com) → **Get Started for Free**
2. Đăng ký bằng **GitHub** (tiện nhất — Render sẽ kết nối với repo)

### 3.2 Tạo Web Service mới

1. Dashboard Render → nhấn **New +** → **Web Service**
2. Chọn **Build and deploy from a Git repository** → **Next**
3. Kết nối GitHub nếu chưa → tìm repo `affiliate-video-bot` → **Connect**
4. Điền thông tin:
   | Trường | Giá trị |
   |---|---|
   | **Name** | `affiliate-bot-dispatcher` |
   | **Region** | Singapore (gần VN nhất) |
   | **Branch** | `main` |
   | **Runtime** | **Docker** ← chọn cái này |
   | **Instance Type** | **Free** |

5. Nhấn **Advanced** → kiểm tra:
   - **Health Check Path**: `/health`
   - **Auto-Deploy**: `Yes`

### 3.3 Set biến môi trường trên Render

Trong phần **Environment Variables** (ngay bên dưới), thêm:

| Key | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token từ BotFather |
| `COLAB_NOTEBOOK_URL` | _(để trống, điền sau ở bước 4)_ |
| `ALLOWED_USER_IDS` | Telegram User ID của bạn (vd: `987654321`) |

> 🔒 Render tự mã hóa các biến này — không ai xem được kể cả bạn sau khi save

### 3.4 Deploy lần đầu

1. Cuộn xuống → nhấn **Create Web Service**
2. Render bắt đầu build Docker (~3-5 phút)
3. Theo dõi log ở tab **Logs** — chờ thấy:
   ```
   🚀 Dispatcher đang chạy...
   ✅ HTTP server đang chạy trên cổng 10000
   ```
4. Render sẽ cấp URL dạng: `https://affiliate-bot-dispatcher.onrender.com`
5. **Copy URL này** → cần dùng cho cron-job và Colab

### 3.5 Test Render đang chạy

Mở trình duyệt, truy cập:
```
https://affiliate-bot-dispatcher.onrender.com/health
```
Phải thấy JSON trả về:
```json
{"status": "running", "colab_connected": false, "colab_url": null, "last_ping": null}
```

Mở Telegram → gửi `/start` cho bot của bạn → bot phải trả lời ngay!

---

## PHẦN 4 — Cài cron-job.org (Giữ Render Sống)

> Render Free tier ngủ sau 15 phút không có request.
> cron-job.org ping mỗi 5 phút → Render không bao giờ ngủ.

### 4.1 Tạo tài khoản

1. Vào [cron-job.org](https://cron-job.org) → **Sign up** (miễn phí hoàn toàn)
2. Xác nhận email

### 4.2 Tạo cronjob giữ Render sống

1. Dashboard → **Create cronjob**
2. Điền:
   | Trường | Giá trị |
   |---|---|
   | **Title** | `Keep Affiliate Bot Alive` |
   | **URL** | `https://affiliate-bot-dispatcher.onrender.com/health` |
   | **Schedule** | Chọn **Every 5 minutes** |
   | **Request method** | `GET` |

3. Nhấn **Create** → xong!

### 4.3 Kiểm tra

1. Sau khi tạo, nhấn **Run now** một lần
2. Xem **Execution log** → phải thấy Status `200 OK`
3. Từ giờ cron-job sẽ tự ping Render mỗi 5 phút

---

## PHẦN 5 — Cài Đặt Google Colab Worker (GPU)

### 5.1 Tạo notebook từ file có sẵn

1. Vào [colab.research.google.com](https://colab.research.google.com)
2. **File** → **Upload notebook** → chọn file `run_bot.ipynb` (trong thư mục bạn giải nén)
3. **File** → **Save a copy in Drive** → đặt tên `Affiliate Video Bot Worker`
4. Copy URL notebook từ thanh địa chỉ trình duyệt → dùng ở bước tiếp theo

### 5.2 Cập nhật COLAB_NOTEBOOK_URL trên Render

1. Render Dashboard → service `affiliate-bot-dispatcher`
2. Tab **Environment** → tìm `COLAB_NOTEBOOK_URL` → **Edit**
3. Paste URL notebook Colab → **Save Changes**
4. Render tự redeploy (~2 phút)

### 5.3 Cấu hình GPU

Trong Colab: **Runtime** → **Change runtime type** → **T4 GPU** → **Save**

### 5.4 Set Secrets trong Colab

Trong Colab → icon 🔑 **Secrets** (sidebar trái):

| Tên | Giá trị |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token từ BotFather |
| `DISPATCHER_URL` | `https://affiliate-bot-dispatcher.onrender.com` |
| `NGROK_AUTH_TOKEN` | Token từ ngrok.com |
| `GDRIVE_CREDENTIALS_JSON` | Nội dung file JSON service account (paste toàn bộ) |
| `GDRIVE_ROOT_FOLDER_ID` | Folder ID Google Drive |

> ⚠️ `GDRIVE_CREDENTIALS_JSON`: Mở file JSON bằng Notepad → Ctrl+A → Ctrl+C → paste vào đây.
> Nội dung phải bắt đầu bằng `{` và kết thúc bằng `}`

### 5.5 Điền GitHub URL trong notebook

1. Mở notebook → tìm cell đầu tiên có ô **Cấu hình**
2. Sửa `GITHUB_REPO` thành URL repo của bạn:
   ```python
   GITHUB_REPO = "https://github.com/YOUR_USERNAME/affiliate-video-bot.git"
   ```
3. Lưu (Ctrl+S)

---

## PHẦN 6 — Chạy Hệ Thống Lần Đầu

### 6.1 Kiểm tra Render đang chạy

```
https://affiliate-bot-dispatcher.onrender.com/health
→ {"status": "running", ...}
```

Telegram → bot → `/start` → bot phải trả lời.

### 6.2 Chạy Colab lần đầu

1. Mở notebook Colab → **Runtime** → **Run all** (Ctrl+F9)
2. Cell 1 (~30 giây): Clone repo từ GitHub
3. Cell 2 (~10 phút): Cài thư viện AI
4. Cell 3 (~30 phút lần đầu / ~3 phút lần sau): Tải/khôi phục models
5. Cell 4 (vài giây): Set Secrets
6. Cell 5 (~30 giây): Khởi động Worker + ngrok

Khi Cell 5 in ra:
```
✅ COLAB WORKER SẴN SÀNG
🌐 Public URL: https://xxxx.ngrok-free.app
```

**Telegram tự báo ngay:** `🟢 Google Colab đã sẵn sàng!`

### 6.3 Test tạo video đầu tiên

1. Telegram → `/menu`
2. Nhấn **🎬 Tạo Video Mới**
3. Gửi ảnh sản phẩm (nền trắng)
4. Gửi ảnh mặt mẫu
5. Nhập `Tên | Giá` hoặc `/skip`
6. Chọn nền tảng, style chữ, định dạng
7. Nhấn **✅ Gửi lên Colab xử lý!**
8. Chờ 5-15 phút → nhận video trong Telegram 🎉

---

## PHẦN 7 — Sử Dụng Hằng Ngày

### Quy trình chuẩn mỗi ngày:

```
1. Mở Telegram → gõ /wakeup
   ↓
   Nếu "🔴 Colab chưa kết nối":
   
2. Nhấn "🚀 Mở Colab Notebook"
   → Tab Colab mở trong trình duyệt
   
3. Runtime → Run all
   → Chờ ~3-5 phút (models đã cache)
   
4. Telegram tự báo: "🟢 Colab đã sẵn sàng!"
   
5. Tạo video bình thường! (/menu → Tạo Video Mới)
```

### Colab sẽ ngắt khi nào?

| Tình huống | Thời gian |
|---|---|
| Không hoạt động | ~30-60 phút |
| Session tối đa (Free) | ~12 giờ |
| Session tối đa (Pro) | ~24 giờ |

**Mẹo giữ Colab sống lâu hơn:**
Chạy thêm cell này song song với Cell 5:
```python
# Anti-disconnect (chạy trong cell riêng)
import time
while True:
    time.sleep(60)
    print("💓", end=" ", flush=True)
```

---

## PHẦN 8 — Cập Nhật Code Khi Có Phiên Bản Mới

### Cập nhật Render (tự động):
1. Push code mới lên GitHub branch `main`
2. Render tự detect và redeploy (~3-5 phút)
3. Không cần làm thêm gì!

### Cập nhật Colab:
Thêm cell này vào đầu notebook, chạy trước Run all:
```python
import subprocess
result = subprocess.run(
    ["git", "-C", "/content/affiliate-video-bot", "pull"],
    capture_output=True, text=True
)
print(result.stdout or "✅ Đã cập nhật code mới nhất!")
```

---

## PHẦN 9 — Xử Lý Sự Cố

### ❌ Render bị ngủ (bot không phản hồi)

**Kiểm tra:** Vào `https://your-service.onrender.com/health`
- Nếu timeout ~30 giây rồi mới load → Render đang thức dậy (lần ping đầu)
- Sau ping cron-job đầu tiên, bot sẽ phản hồi bình thường

**Giải pháp nếu cron-job chưa tạo:**
1. Vào cron-job.org → tạo mới theo hướng dẫn Phần 4
2. Hoặc Render → **Upgrade to Starter** ($7/tháng) để không bao giờ ngủ

### ❌ Render báo "Build failed"

1. Render Dashboard → service → tab **Logs** (Deploys)
2. Click vào lần deploy lỗi → xem log chi tiết
3. Lỗi thường gặp:
   - `requirements_dispatcher.txt not found` → kiểm tra tên file đúng chưa
   - `ModuleNotFoundError` → thiếu thư viện trong `requirements_dispatcher.txt`
   - `PORT` conflict → đã được handle tự động bởi `render.yaml`

### ❌ /wakeup không có nút Colab

**Nguyên nhân:** `COLAB_NOTEBOOK_URL` chưa set

**Cách xử lý:**
1. Render Dashboard → **Environment** → thêm `COLAB_NOTEBOOK_URL`
2. Paste URL notebook Colab → **Save** → Render tự redeploy

### ❌ Colab báo "Dispatcher URL không kết nối được"

**Kiểm tra:**
1. Render service có đang chạy không? → ping `/health`
2. `DISPATCHER_URL` trong Colab Secrets có đúng không?
   - Phải là: `https://affiliate-bot-dispatcher.onrender.com` (không có `/` ở cuối)
3. Cron-job có đang hoạt động không? → xem Execution log

### ❌ Colab ngắt giữa chừng khi xử lý video

**Nguyên nhân:** Inactivity timeout hoặc GPU quota

**Cách tránh:**
- Giữ tab Colab luôn mở trong trình duyệt
- Dùng cell anti-disconnect ở Phần 7
- Nếu hay bị: nâng lên Colab Pro ($10/tháng) để có session dài hơn

### ❌ CUDA out of memory

**Cách xử lý nhanh:**
1. Colab → **Runtime** → **Disconnect and delete runtime**
2. Reconnect → chọn T4 GPU
3. Run all lại từ Cell 4 (bỏ qua Cell 3 nếu models đã lưu Drive)

### ❌ ngrok "too many connections" hoặc "tunnel not found"

**Nguyên nhân:** Ngrok free chỉ cho 1 tunnel đồng thời

**Cách xử lý:**
1. Vào [dashboard.ngrok.com](https://dashboard.ngrok.com) → **Tunnels** → xóa tunnel cũ
2. Colab → chạy lại Cell 5

---

## PHẦN 10 — Tóm Tắt URL & Thông Tin Quan Trọng

| Dịch vụ | URL / Thông tin |
|---|---|
| Render Service | `https://affiliate-bot-dispatcher.onrender.com` |
| Health Check | `https://affiliate-bot-dispatcher.onrender.com/health` |
| Render Register | `https://affiliate-bot-dispatcher.onrender.com/register` |
| cron-job ping URL | `https://affiliate-bot-dispatcher.onrender.com/health` |
| Colab Notebook | URL từ trình duyệt khi mở notebook |
| ngrok Dashboard | [dashboard.ngrok.com](https://dashboard.ngrok.com) |

---

## ✅ Checklist Trước Khi Dùng

- [ ] GitHub repo đã tạo và upload đủ code (có `Dockerfile`, `render.yaml`)
- [ ] Render service đã deploy thành công, `/health` trả về `200 OK`
- [ ] cron-job.org đã tạo, ping mỗi 5 phút, trạng thái `200 OK`
- [ ] Colab Secrets đã điền đủ 5 giá trị
- [ ] `COLAB_NOTEBOOK_URL` đã set trên Render
- [ ] notebook `run_bot.ipynb` đã lưu vào Drive
- [ ] Models đã tải và lưu Drive cache (tránh tải lại)
- [ ] Test: `/start` → `/wakeup` → Colab chạy → tạo 1 video thành công 🎉
