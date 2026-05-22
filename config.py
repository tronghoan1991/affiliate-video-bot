"""
config.py — Affiliate Video Bot v4.0
Cấu hình tập trung. Đọc từ biến môi trường / .env file.
"""
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


class Config:
    # ══════════════════════════════════════════════════════════
    #  TELEGRAM
    # ══════════════════════════════════════════════════════════
    TELEGRAM_BOT_TOKEN: str  = os.getenv("TELEGRAM_BOT_TOKEN", "")
    ALLOWED_USER_IDS: list   = [
        int(x) for x in os.getenv("ALLOWED_USER_IDS", "").split(",") if x.strip()
    ]

    # ══════════════════════════════════════════════════════════
    #  VIDEO ENGINE  (100% miễn phí)
    #  "auto" | "wan21" | "animatediff" | "cloud"
    # ══════════════════════════════════════════════════════════
    VIDEO_ENGINE: str        = os.getenv("VIDEO_ENGINE", "auto")

    # --- Wan2.1 I2V (Engine CHÍNH) ---
    WAN_MODEL_480P: str      = "Wan-AI/Wan2.1-I2V-14B-480P-Diffusers"
    WAN_MODEL_720P: str      = "Wan-AI/Wan2.1-I2V-14B-720P-Diffusers"
    WAN_NUM_FRAMES: int      = 81
    WAN_FPS: int             = 16
    WAN_STEPS: int           = 50
    WAN_GUIDANCE: float      = 5.0
    WAN_WIDTH_480: int       = 832
    WAN_HEIGHT_480: int      = 480
    WAN_WIDTH_9_16: int      = 480
    WAN_HEIGHT_9_16: int     = 832

    # --- AnimateDiff fallback ---
    ANIM_BASE_MODEL: str     = "runwayml/stable-diffusion-v1-5"
    ANIM_MOTION_MODULE: str  = "guoyww/animatediff-motion-adapter-v1-5-2"
    ANIM_FRAMES: int         = 16
    ANIM_WIDTH: int          = 512
    ANIM_HEIGHT: int         = 768
    ANIM_STEPS: int          = 25
    ANIM_GUIDANCE: float     = 7.5

    # --- HF Spaces cloud backup ---
    HF_TOKEN: str            = os.getenv("HF_TOKEN", "")

    # ══════════════════════════════════════════════════════════
    #  REAL-ESRGAN UPSCALE
    # ══════════════════════════════════════════════════════════
    MODELS_DIR: Path         = Path(os.getenv("MODELS_DIR", "./models"))
    REALESRGAN_PATH: Path    = MODELS_DIR / "realesrgan" / "RealESRGAN_x4plus.pth"
    REALESRGAN_SCALE: int    = int(os.getenv("REALESRGAN_SCALE", "2"))
    REALESRGAN_TILE: int     = 512

    # ══════════════════════════════════════════════════════════
    #  IDM-VTON (Virtual Try-On)
    # ══════════════════════════════════════════════════════════
    IDMVTON_DIR: Path        = MODELS_DIR / "idm-vton"
    TRYON_SIZE: int          = int(os.getenv("TRYON_SIZE", "768"))
    TRYON_STEPS: int         = 30

    # ══════════════════════════════════════════════════════════
    #  GOOGLE DRIVE
    # ══════════════════════════════════════════════════════════
    GDRIVE_CREDENTIALS: str  = os.getenv("GDRIVE_CREDENTIALS_JSON", "")
    GDRIVE_FOLDER_ID: str    = os.getenv("GDRIVE_ROOT_FOLDER_ID", "")
    GDRIVE_AUTO_FOLDER: bool = True

    # ══════════════════════════════════════════════════════════
    #  TEXT OVERLAY
    # ══════════════════════════════════════════════════════════
    FONT_PATH: str           = os.getenv("FONT_PATH", "./assets/fonts/Montserrat-Bold.ttf")
    FONT_FALLBACK: str       = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

    TEXT_STYLES: dict        = {
        "viral":  {"fg": "#FFD700", "stroke": "#000000", "size": 0.065},
        "tiktok": {"fg": "#FFFFFF", "stroke": "#000000", "size": 0.058},
        "shopee": {"fg": "#FF6633", "stroke": "#FFFFFF", "size": 0.055},
    }

    # ══════════════════════════════════════════════════════════
    #  MUSIC ENGINE
    # ══════════════════════════════════════════════════════════
    MUSIC_DIR: str           = os.getenv("MUSIC_DIR", "./assets/music")
    PIXABAY_KEY: str         = os.getenv("PIXABAY_API_KEY", "")
    MUSIC_VOLUME: float      = 0.72
    MUSIC_FADE: float        = 1.5

    # ══════════════════════════════════════════════════════════
    #  GARMENT LABELS & MISC
    # ══════════════════════════════════════════════════════════
    GARMENT_LABELS: list     = [
        "formal office shirt", "business suit", "casual t-shirt",
        "dress evening gown", "swimwear bikini", "sportswear activewear",
        "winter coat jacket", "traditional ao dai", "jeans pants",
        "skirt mini maxi", "hoodie streetwear", "luxury accessories",
    ]
    TEMP_DIR: str            = "./tmp"
    MAX_TG_VIDEO_MB: int     = 50
