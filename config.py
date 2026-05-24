"""config.py — Affiliate Studio v8"""
import os

class Config:
    TELEGRAM_TOKEN          = os.getenv("TELEGRAM_TOKEN", "")
    ALLOWED_USER_IDS        = [int(x) for x in os.getenv("ALLOWED_USER_IDS", "").split(",") if x.strip().isdigit()]
    RENDER_URL              = os.getenv("RENDER_URL", "").rstrip("/")
    RENDER_DEPLOY_HOOK      = os.getenv("RENDER_DEPLOY_HOOK", "")   # Render deploy hook URL
    PORT                    = int(os.getenv("PORT", 5000))
    HOST                    = "0.0.0.0"
    COLAB_WEBHOOK_URL       = os.getenv("COLAB_WEBHOOK_URL", "")
    COLAB_SECRET            = os.getenv("COLAB_SECRET", "affiliatestudio_v8_secret")
    PIXABAY_API_KEY         = os.getenv("PIXABAY_API_KEY", "")
    FREESOUND_API_KEY       = os.getenv("FREESOUND_API_KEY", "")
    NGROK_AUTH_TOKEN        = os.getenv("NGROK_AUTH_TOKEN", "")
    HEYGEN_API_KEY          = os.getenv("HEYGEN_API_KEY", "")       # Optional: avatar talking video
    COLAB_PING_INTERVAL_MIN = 10
    DRIVE_ROOT              = "/content/drive/MyDrive/AffiliateStudio"

    @classmethod
    def validate(cls):
        errors = []
        if not cls.TELEGRAM_TOKEN: errors.append("TELEGRAM_TOKEN chưa set")
        if not cls.RENDER_URL:     errors.append("RENDER_URL chưa set")
        return errors
