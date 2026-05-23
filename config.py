"""
config.py — Affiliate Video Bot v5 Configuration
=============================================================================
Điền thông tin của bạn bằng environment variables.
Không hard-code token/key vào file này.
=============================================================================
"""
import os
from pathlib import Path

# Google Drive root (tự detect khi chạy trên Colab)
_DRIVE_ROOT = Path("/content/drive/MyDrive/AffiliateBot")


class Config:
    # ── Google Drive ────────────────────────────────────────────────────────
    # Toàn bộ models, music, fonts, outputs → Drive 5TB
    DRIVE_ROOT    = _DRIVE_ROOT
    MODELS_DIR    = _DRIVE_ROOT / "models"
    MUSIC_DIR     = str(_DRIVE_ROOT / "music")
    FONT_PATH     = str(_DRIVE_ROOT / "fonts" / "Montserrat-Bold.ttf")
    FONT_FALLBACK = str(_DRIVE_ROOT / "fonts" / "NotoSans-Bold.ttf")
    OUTPUT_DIR    = _DRIVE_ROOT / "outputs"
    CACHE_DIR     = Path("/tmp/affiliatebot_cache")

    # ── Telegram ─────────────────────────────────────────────────────────────
    TELEGRAM_TOKEN   = os.environ.get("TELEGRAM_TOKEN", "")
    TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

    # ── API Keys ─────────────────────────────────────────────────────────────
    PIXABAY_KEY = os.environ.get("PIXABAY_API_KEY", "")

    # ── Render / Keep-alive ───────────────────────────────────────────────────
    # URL của Render service này (ví dụ: https://affiliate-video-bot.onrender.com)
    # Dùng để Colab gọi lại sau khi hoàn thành task
    RENDER_URL = os.environ.get("RENDER_URL", "")

    # ── Colab Webhook ─────────────────────────────────────────────────────────
    # URL ngrok của Colab (người dùng set bằng /setcolab <url> trong Telegram)
    # Lưu tạm trong memory — reset mỗi khi Render khởi động lại
    # Nếu muốn lưu lâu dài: set env var COLAB_WEBHOOK_URL trong Render Dashboard
    COLAB_WEBHOOK_URL = os.environ.get("COLAB_WEBHOOK_URL", "")

    # ── Video Engine ──────────────────────────────────────────────────────────
    # "auto"      → thử wan21 trước, fallback cogvideox
    # "wan21"     → Wan2.1-I2V-14B (best quality, ~12GB VRAM, T4 đủ)
    # "cogvideox" → CogVideoX-5B (faster, lower VRAM)
    VIDEO_ENGINE = os.environ.get("VIDEO_ENGINE", "auto")

    # ── Video Settings ────────────────────────────────────────────────────────
    VIDEO_FPS        = 16
    VIDEO_FRAMES     = 81      # 81f / 16fps ≈ 5s/loop
    VIDEO_LOOPS      = 3       # 3 × 5s = 15s total
    VIDEO_WIDTH      = 480     # 9:16 portrait (TikTok/Shopee native)
    VIDEO_HEIGHT     = 832
    VIDEO_STEPS      = 30      # Inference steps (20=fast, 30=quality, 50=best)
    VIDEO_CFG        = 7.0     # Guidance scale

    # ── Platform ──────────────────────────────────────────────────────────────
    DEFAULT_PLATFORM = "tiktok"

    # ── Text Overlay Styles ───────────────────────────────────────────────────
    TEXT_STYLES = {
        "tiktok": {"fg": "#FFD700", "stroke": "#000000", "size": 0.055},
        "shopee": {"fg": "#FF6633", "stroke": "#000000", "size": 0.052},
        "men":    {"fg": "#60A5FA", "stroke": "#000000", "size": 0.055},
        "kids":   {"fg": "#FB923C", "stroke": "#000000", "size": 0.055},
        "baby":   {"fg": "#F9A8D4", "stroke": "#000000", "size": 0.055},
        "viral":  {"fg": "#FFFFFF", "stroke": "#000000", "size": 0.060},
    }
