# Affiliate Video Bot v5 — AI Fashion Video Generator 2026

> Bot AI tự động tạo video affiliate viral cho **toàn bộ ngành thời trang**:  
> 👗 Nữ · 👔 Nam · 👶 Trẻ em / Baby · 💕 Đôi / Gia đình · 🌀 Unisex

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Platform](https://img.shields.io/badge/Platform-Google%20Colab-orange.svg)](https://colab.research.google.com)
[![Storage](https://img.shields.io/badge/Storage-Google%20Drive%205TB-green.svg)](https://drive.google.com)
[![AI](https://img.shields.io/badge/AI-CLIP%20%2B%20Wan2.1-purple.svg)](https://huggingface.co/Wan-AI)

---

## Tính năng nổi bật

| Tính năng | Chi tiết |
|---|---|
| **AI nhận diện trang phục** | CLIP zero-shot phân loại 50+ loại sản phẩm |
| **Tự viết kịch bản** | Script Writer AI cho mọi gender × style × platform |
| **Viral hooks 2026** | Authentic review format — tăng stop rate x3 |
| **Value Stack overlay** | Hiện rõ "bạn nhận được gì" — +67% conversion |
| **Comment CTA** | "Comment MUA để nhận link" — tăng reach x4 |
| **Micro-story caption** | Vấn đề → Giải pháp → Kết quả |
| **Google Drive 5TB** | Toàn bộ models/music/fonts trên Drive — không tốn Colab storage |
| **Đa ngành thời trang** | Women / Men / Children / Baby / Unisex / Couple / Family |

---

## Cấu trúc dự án

```
affiliate-video-bot/
├── app.py                   ← Telegram Bot (entry point)
├── config.py                ← Cấu hình
├── requirements.txt
├── colab_notebook.py        ← Copy vào Colab cells
├── pipeline/
│   ├── ai_analyzer.py       ← CLIP garment & face recognition
│   ├── script_writer.py     ← AI video script generator
│   ├── video_engine.py      ← Wan2.1 / CogVideoX wrapper
│   ├── viral_strategy.py    ← Viral content engine 2026
│   ├── background.py        ← AI video prompts (all categories)
│   ├── text_overlay.py      ← Video text overlay (3-layer)
│   ├── music_engine.py      ← Music selection + Drive cache
│   ├── caption_gen.py       ← Caption generator wrapper
│   └── drive_manager.py     ← Google Drive asset manager
└── tests/
    └── test_pipeline.py     ← Full test suite (no GPU needed)
```

---

## Google Drive Structure

```
MyDrive/
└── AffiliateBot/
    ├── models/              ← AI model weights (tải 1 lần, dùng mãi)
    │   └── wan2.1-i2v-14B-480P/
    ├── music/               ← Nhạc nền theo mood (12 categories)
    │   ├── elegant_upbeat/
    │   ├── phonk_street/
    │   ├── trendy_pop/
    │   └── ...
    ├── fonts/               ← Fonts (tự động tải lần đầu)
    ├── outputs/             ← Video đã hoàn thành (theo ngày)
    │   └── 2026-05-23/
    └── cache/pixabay/       ← Nhạc Pixabay cache (không tải lại)
```

---

## AI Video Pipeline

```
📸 Ảnh/Tên SP  →  🧠 CLIP Analyzer  →  📝 Script Writer
                        ↓                      ↓
                  GarmentAnalysis        VideoScript
                  (gender/style)      (5 scenes × timing)
                        ↓                      ↓
              🎬 Wan2.1 Video Gen  ←  AI Prompt Builder
                        ↓
              📐 Text Overlay (3-layer)
                  Hook → Info → Value Stack + Comment CTA
                        ↓
              🎵 Music Engine (Drive cache)
                        ↓
              💾 Save to Google Drive → 📱 Telegram
```

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

## Setup (Google Colab)

### Bước 1: Clone & Cài

```python
!git clone https://github.com/YOUR_USERNAME/affiliate-video-bot.git /content/affiliate-video-bot
!pip install -q -r /content/affiliate-video-bot/requirements.txt
!apt-get install -y ffmpeg -q
```

### Bước 2: Mount Drive (đầu mỗi session)

```python
from pipeline.drive_manager import setup_drive
drive = setup_drive()
```

### Bước 3: Tải model về Drive (1 lần)

```python
from pipeline.video_engine import download_model_to_drive
download_model_to_drive("Wan-AI/Wan2.1-I2V-14B-480P", "wan2.1-i2v-14B-480P")
```

### Bước 4: Chạy bot

```python
# Telegram bot
import os
os.environ["TELEGRAM_TOKEN"] = "YOUR_TOKEN"
from app import main
main()

# Hoặc quick test
from pipeline.ai_analyzer import analyze_product
from pipeline.script_writer import write_video_script

analysis = analyze_product("Váy maxi hoa nhí", "Váy nữ vải lụa mềm")
script = write_video_script(analysis, "Váy maxi hoa nhí", "299k", "tiktok")
print(script.hook_scene.hook_text)
```

---

## Telegram Bot Usage

```
/tao Tên SP | Giá | Mô tả | platform

Ví dụ:
/tao Váy maxi hoa nhí | 299k | Váy nữ vải lụa mềm | tiktok
/tao Suit nam xanh navy | 850k | Vest nam công sở slim fit | both
/tao Set bé gái 3-8t | 185k | Bộ đồ trẻ em cotton | shopee
/tao Bodysuit sơ sinh | 125k | Bodysuit bé 0-12 tháng | shopee
/tao Đồ đôi matching | 299k | Áo đôi couple unisex | tiktok
/tao Set gia đình | 490k | Đồ gia đình matching 4 người | tiktok

Hoặc: Gửi ảnh sản phẩm + caption để AI tự phân tích
```

---

## Phân loại sản phẩm (50+ categories)

### Nữ giới (Women)
Váy dạ hội, váy casual, váy midi/maxi/mini, áo dài, bikini/swimwear,
đồ gym/activewear, hoodie, áo khoác, vest/suit, jeans, chân váy,
túi xách, giày cao gót, trang sức, đồ ngủ...

### Nam giới (Men)
Áo thun, polo, sơ mi, suit/vest, blazer, jeans, shorts, chinos,
hoodie, streetwear, áo khoác, đồ gym, đồ bơi, giày, phụ kiện,
áo dài nam...

### Trẻ em (Children / Baby)
Bodysuit sơ sinh, set bé, romper, áo thun bé, váy bé gái,
đồng phục học sinh, đồ tập trẻ em, đồ ngủ bé, áo khoác bé,
đồ bơi trẻ em, giày bé, áo dài bé...

### Unisex / Couple / Family
Hoodie unisex, áo thun unisex, đồ đôi couple, set gia đình matching...

---

## Video Engine Comparison

| Engine | VRAM | Speed | Quality | Colab T4 |
|---|---|---|---|---|
| **Wan2.1-I2V 14B** | ~12GB | ~5min | ⭐⭐⭐⭐⭐ | ✅ Đủ |
| CogVideoX-5B | ~8GB | ~3min | ⭐⭐⭐⭐ | ✅ Thoải mái |
| AnimateDiff XL | ~6GB | ~2min | ⭐⭐⭐ | ✅ Dễ chạy |

---

## Music Moods Library

| Mood | Sản phẩm | BPM |
|---|---|---|
| `elegant_upbeat` | Váy dạ hội, luxury | 95-110 |
| `trendy_pop` | Casual, everyday | 110-125 |
| `phonk_street` | Streetwear, hoodie | 130-155 |
| `energetic_edm` | Gym, activewear | 125-140 |
| `vietnamese_modern` | Áo dài | 85-100 |
| `summer_tropical` | Bikini, beachwear | 100-115 |
| `powerful_cinematic` | Suit, formal | 90-110 |
| `cozy_aesthetic` | Áo khoác, baby | 70-90 |
| `feminine_pop` | Chân váy, kids | 105-120 |
| `casual_hype` | Jeans, casual nam | 110-130 |
| `luxury_elegant` | Phụ kiện cao cấp | 80-95 |
| `corporate_smooth` | Công sở, smart casual | 85-100 |

---

## Chạy Tests

```bash
# Test toàn bộ pipeline (không cần GPU)
python tests/test_pipeline.py

# Hoặc với pytest
python -m pytest tests/test_pipeline.py -v
```

---

## Environment Variables

| Variable | Mô tả | Bắt buộc |
|---|---|---|
| `TELEGRAM_TOKEN` | Bot token từ @BotFather | ✅ |
| `PIXABAY_API_KEY` | Pixabay API (miễn phí) | ⬜ |
| `VIDEO_ENGINE` | `auto` / `wan21` / `cogvideox` | ⬜ |

---

## License

MIT License — Free for personal and commercial use.

---

*Built with ❤️ for Vietnamese fashion affiliate marketers*
