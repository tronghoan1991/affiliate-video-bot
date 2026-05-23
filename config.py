"""config.py — Affiliate Video Bot v7 (2026)"""
import os

class Config:
    TELEGRAM_TOKEN          = os.getenv("TELEGRAM_TOKEN", "")
    ALLOWED_USER_IDS        = [int(x) for x in os.getenv("ALLOWED_USER_IDS", "").split(",") if x.strip().isdigit()]
    RENDER_URL              = os.getenv("RENDER_URL", "").rstrip("/")
    PORT                    = int(os.getenv("PORT", 5000))
    HOST                    = "0.0.0.0"
    COLAB_WEBHOOK_URL       = os.getenv("COLAB_WEBHOOK_URL", "")
    COLAB_SECRET            = os.getenv("COLAB_SECRET", "affiliatebot_v7_secret")
    PIXABAY_API_KEY         = os.getenv("PIXABAY_API_KEY", "")
    FREESOUND_API_KEY       = os.getenv("FREESOUND_API_KEY", "")
    NGROK_AUTH_TOKEN        = os.getenv("NGROK_AUTH_TOKEN", "")
    VIDEO_ENGINE            = os.getenv("VIDEO_ENGINE", "auto")
    DEFAULT_PLATFORM        = os.getenv("DEFAULT_PLATFORM", "tiktok")
    VIDEO_DURATION_SEC      = 15
    VIDEO_FPS               = 24
    VIDEO_WIDTH             = 1080
    VIDEO_HEIGHT            = 1920
    DRIVE_ROOT              = "/content/drive/MyDrive/AffiliateBot"
    COLAB_PING_INTERVAL_MIN = 10
    AB_TEST_VARIANTS        = 3          # Số hook variants cho A/B test

    @classmethod
    def validate(cls):
        errors = []
        if not cls.TELEGRAM_TOKEN:
            errors.append("TELEGRAM_TOKEN chưa set")
        if not cls.RENDER_URL:
            errors.append("RENDER_URL chưa set")
        return errors
