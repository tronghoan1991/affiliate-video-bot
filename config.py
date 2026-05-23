"""
config.py — Cấu hình trung tâm Affiliate Video Bot v6
"""
import os

class Config:
    # ── Telegram ──────────────────────────────────────────────────────────────
    TELEGRAM_TOKEN     = os.getenv("TELEGRAM_TOKEN", "")
    ALLOWED_USER_IDS   = [int(x) for x in os.getenv("ALLOWED_USER_IDS", "").split(",") if x.strip().isdigit()]

    # ── Render / Server ───────────────────────────────────────────────────────
    RENDER_URL         = os.getenv("RENDER_URL", "").rstrip("/")
    PORT               = int(os.getenv("PORT", 5000))
    HOST               = "0.0.0.0"

    # ── Colab ─────────────────────────────────────────────────────────────────
    COLAB_WEBHOOK_URL  = os.getenv("COLAB_WEBHOOK_URL", "")
    COLAB_SECRET       = os.getenv("COLAB_SECRET", "affiliatebot_v6_secret")

    # ── APIs miễn phí ─────────────────────────────────────────────────────────
    PIXABAY_API_KEY    = os.getenv("PIXABAY_API_KEY", "")   # pixabay.com — miễn phí
    FREESOUND_API_KEY  = os.getenv("FREESOUND_API_KEY", "") # freesound.org — miễn phí
    NGROK_AUTH_TOKEN   = os.getenv("NGROK_AUTH_TOKEN", "")  # ngrok.com — miễn phí

    # ── Video Engine ──────────────────────────────────────────────────────────
    VIDEO_ENGINE       = os.getenv("VIDEO_ENGINE", "auto")
    # auto | wan21 | cogvideox | animatediff | moviepy_only
    DEFAULT_PLATFORM   = os.getenv("DEFAULT_PLATFORM", "tiktok")
    VIDEO_DURATION_SEC = 15
    VIDEO_FPS          = 24
    VIDEO_WIDTH        = 1080   # 9:16 portrait
    VIDEO_HEIGHT       = 1920

    # ── Google Drive ──────────────────────────────────────────────────────────
    DRIVE_ROOT         = "/content/drive/MyDrive/AffiliateBot"
    DRIVE_MODELS_DIR   = f"{DRIVE_ROOT}/models"
    DRIVE_MUSIC_DIR    = f"{DRIVE_ROOT}/music"
    DRIVE_FONTS_DIR    = f"{DRIVE_ROOT}/fonts"
    DRIVE_OUTPUTS_DIR  = f"{DRIVE_ROOT}/outputs"
    DRIVE_BG_DIR       = f"{DRIVE_ROOT}/backgrounds"
    DRIVE_ASSETS_DIR   = f"{DRIVE_ROOT}/assets"

    # ── Colab Wake Schedule (tự động ping giữ sống) ───────────────────────────
    COLAB_PING_INTERVAL_MIN = 10   # Ping Colab mỗi N phút để không bị disconnect

    @classmethod
    def validate(cls):
        errors = []
        if not cls.TELEGRAM_TOKEN:
            errors.append("TELEGRAM_TOKEN chưa được set")
        if not cls.RENDER_URL:
            errors.append("RENDER_URL chưa được set (cần cho Colab callback)")
        return errors
