"""
pipeline/drive_manager.py — Google Drive Asset Manager v6
=============================================================================
Quản lý toàn bộ assets: models, music, fonts, outputs, backgrounds trên Drive 5TB.
Colab chỉ dùng /tmp làm cache ngắn hạn trong session để tăng tốc đọc/ghi.
=============================================================================
"""
import json
import logging
import os
import random
import shutil
import urllib.request
from pathlib import Path
from typing import Optional

logger = logging.getLogger("DriveManager")

DRIVE_ROOT  = Path("/content/drive/MyDrive/AffiliateBot")
COLAB_CACHE = Path("/tmp/affiliatebot_cache")


class DriveManager:
    def __init__(self, drive_root: Path = DRIVE_ROOT):
        self.drive_root = drive_root
        self.cache_dir  = COLAB_CACHE
        self._ensure_dirs()

    def _ensure_dirs(self):
        subdirs = ["models", "music", "fonts", "outputs", "backgrounds", "assets", "cache/pixabay", "cache/freesound"]
        for sub in subdirs:
            try:
                (self.drive_root / sub).mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    @staticmethod
    def mount_drive(force: bool = False) -> bool:
        try:
            from google.colab import drive
            if force or not Path("/content/drive/MyDrive").exists():
                drive.mount("/content/drive", force_remount=force)
            logger.info("✅ Google Drive mounted")
            return True
        except ImportError:
            logger.info("Không ở trong Colab — bỏ qua mount Drive")
            return False
        except Exception as e:
            logger.error(f"Mount Drive thất bại: {e}")
            return False

    # ── Paths ──────────────────────────────────────────────────────────────────
    @property
    def models_dir(self)    -> Path: return self.drive_root / "models"
    @property
    def music_dir(self)     -> Path: return self.drive_root / "music"
    @property
    def fonts_dir(self)     -> Path: return self.drive_root / "fonts"
    @property
    def outputs_dir(self)   -> Path: return self.drive_root / "outputs"
    @property
    def bg_dir(self)        -> Path: return self.drive_root / "backgrounds"
    @property
    def assets_dir(self)    -> Path: return self.drive_root / "assets"
    @property
    def pixabay_cache(self) -> Path: return self.drive_root / "cache" / "pixabay"
    @property
    def freesound_cache(self) -> Path: return self.drive_root / "cache" / "freesound"

    # ── Fonts ──────────────────────────────────────────────────────────────────
    _FONT_URLS = {
        "Montserrat-Bold.ttf":
            "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Bold.ttf",
        "Montserrat-ExtraBold.ttf":
            "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-ExtraBold.ttf",
        "Montserrat-Black.ttf":
            "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Black.ttf",
        "NotoSans-Bold.ttf":
            "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSans/NotoSans-Bold.ttf",
        "BeVietnamPro-Bold.ttf":
            "https://github.com/lettersoup/Be-Vietnam-Pro/raw/main/fonts/ttf/BeVietnamPro-Bold.ttf",
    }

    def get_font_path(self, filename: str = "Montserrat-Bold.ttf") -> Optional[Path]:
        cache = self.cache_dir / "fonts" / filename
        drive = self.fonts_dir / filename
        cache.parent.mkdir(parents=True, exist_ok=True)

        if cache.exists():
            return cache
        if drive.exists():
            shutil.copy2(drive, cache)
            return cache

        url = self._FONT_URLS.get(filename)
        if url:
            try:
                logger.info(f"Tải font {filename}...")
                urllib.request.urlretrieve(url, str(drive))
                shutil.copy2(drive, cache)
                logger.info(f"✅ Font {filename} đã tải về Drive")
                return cache
            except Exception as e:
                logger.warning(f"Không tải được font {filename}: {e}")
        return None

    # ── Music ──────────────────────────────────────────────────────────────────
    def get_music_path(self, mood: str) -> Optional[Path]:
        """Tìm nhạc nền theo mood trong Drive."""
        mood_dir = self.music_dir / mood
        if mood_dir.exists():
            tracks = list(mood_dir.glob("*.mp3")) + list(mood_dir.glob("*.wav"))
            if tracks:
                return random.choice(tracks)
        # Thử file trực tiếp
        for ext in [".mp3", ".wav"]:
            p = self.music_dir / f"{mood}{ext}"
            if p.exists():
                return p
        return None

    def save_music(self, mood: str, src_path: Path, filename: str) -> Path:
        """Lưu nhạc mới tải về Drive."""
        dest_dir = self.music_dir / mood
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / filename
        shutil.copy2(src_path, dest)
        return dest

    # ── Models ─────────────────────────────────────────────────────────────────
    def get_model_path(self, model_name: str) -> Optional[Path]:
        p = self.models_dir / model_name
        return p if p.exists() else None

    def download_model(self, model_id: str, local_name: str) -> str:
        """Tải HuggingFace model về Drive lần đầu. Các lần sau load từ Drive."""
        import subprocess
        dest = str(self.models_dir / local_name)
        if Path(dest).exists():
            logger.info(f"Model đã có trên Drive: {local_name}")
            return dest
        logger.info(f"Đang tải model {model_id} về Drive (lần đầu)...")
        os.makedirs(dest, exist_ok=True)
        subprocess.run([
            "huggingface-cli", "download", model_id,
            "--local-dir", dest,
            "--local-dir-use-symlinks", "False"
        ], check=True)
        logger.info(f"✅ Model {model_id} đã lưu vào Drive")
        return dest

    # ── Outputs ────────────────────────────────────────────────────────────────
    def new_output_path(self, prefix: str = "video") -> Path:
        from datetime import datetime
        day = datetime.now().strftime("%Y%m%d")
        day_dir = self.outputs_dir / day
        day_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime("%H%M%S")
        return day_dir / f"{prefix}_{ts}.mp4"

    # ── Drive Stats ────────────────────────────────────────────────────────────
    def drive_stats(self) -> dict:
        stats = {}
        for folder in ["models", "music", "fonts", "outputs", "backgrounds"]:
            d = self.drive_root / folder
            if d.exists():
                files = list(d.rglob("*"))
                total_bytes = sum(f.stat().st_size for f in files if f.is_file())
                stats[folder] = {
                    "files": len([f for f in files if f.is_file()]),
                    "size_mb": round(total_bytes / 1_048_576, 1),
                }
            else:
                stats[folder] = {"files": 0, "size_mb": 0}
        return stats


def setup_drive(force_remount: bool = False) -> DriveManager:
    """Khởi động DriveManager, mount Google Drive nếu đang ở Colab."""
    DriveManager.mount_drive(force=force_remount)
    mgr = DriveManager()
    logger.info("✅ DriveManager sẵn sàng")
    return mgr


# Singleton instance
drive_mgr = DriveManager()
