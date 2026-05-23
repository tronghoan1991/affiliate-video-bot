"""
pipeline/drive_manager.py — Google Drive Asset Manager v7
Quản lý models, music, fonts, outputs trên Drive 5TB.
"""
import json, logging, os, random, shutil, urllib.request
from pathlib import Path
from typing import Optional

logger = logging.getLogger("DriveManager")
DRIVE_ROOT  = Path("/content/drive/MyDrive/AffiliateBot")
COLAB_CACHE = Path("/tmp/affiliatebot_cache")

class DriveManager:
    def __init__(self, root: Path = DRIVE_ROOT):
        self.drive_root = root
        self.cache_dir  = COLAB_CACHE
        self._ensure()

    def _ensure(self):
        for sub in ["models","music","fonts","outputs","backgrounds","assets","cache/pixabay","cache/freesound"]:
            try: (self.drive_root / sub).mkdir(parents=True, exist_ok=True)
            except: pass
        try: self.cache_dir.mkdir(parents=True, exist_ok=True)
        except: pass

    @staticmethod
    def mount_drive(force=False):
        try:
            from google.colab import drive
            if force or not Path("/content/drive/MyDrive").exists():
                drive.mount("/content/drive", force_remount=force)
            logger.info("✅ Drive mounted"); return True
        except ImportError: return False
        except Exception as e: logger.error(f"Mount fail: {e}"); return False

    @property
    def models_dir(self):  return self.drive_root / "models"
    @property
    def music_dir(self):   return self.drive_root / "music"
    @property
    def fonts_dir(self):   return self.drive_root / "fonts"
    @property
    def outputs_dir(self): return self.drive_root / "outputs"

    _FONT_URLS = {
        "Montserrat-Bold.ttf":
            "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Bold.ttf",
        "Montserrat-ExtraBold.ttf":
            "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-ExtraBold.ttf",
        "Montserrat-Black.ttf":
            "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Black.ttf",
        "BeVietnamPro-Bold.ttf":
            "https://github.com/lettersoup/Be-Vietnam-Pro/raw/main/fonts/ttf/BeVietnamPro-Bold.ttf",
    }

    def get_font_path(self, fn="Montserrat-Bold.ttf") -> Optional[Path]:
        cache = self.cache_dir / "fonts" / fn
        drive = self.fonts_dir / fn
        cache.parent.mkdir(parents=True, exist_ok=True)
        if cache.exists(): return cache
        if drive.exists(): shutil.copy2(drive, cache); return cache
        url = self._FONT_URLS.get(fn)
        if url:
            try:
                urllib.request.urlretrieve(url, str(drive))
                shutil.copy2(drive, cache)
                return cache
            except Exception as e: logger.warning(f"Font dl fail {fn}: {e}")
        return None

    def get_music_path(self, mood: str) -> Optional[Path]:
        d = self.music_dir / mood
        if d.exists():
            tracks = list(d.glob("*.mp3")) + list(d.glob("*.wav"))
            if tracks: return random.choice(tracks)
        for ext in [".mp3", ".wav"]:
            p = self.music_dir / f"{mood}{ext}"
            if p.exists(): return p
        return None

    def save_music(self, mood: str, src: Path, fn: str) -> Path:
        dest = self.music_dir / mood / fn
        (self.music_dir / mood).mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest); return dest

    def download_model(self, model_id: str, local_name: str) -> str:
        import subprocess
        dest = str(self.models_dir / local_name)
        if Path(dest).exists(): logger.info(f"Model exists: {local_name}"); return dest
        logger.info(f"Downloading {model_id}...")
        os.makedirs(dest, exist_ok=True)
        subprocess.run(["huggingface-cli","download",model_id,"--local-dir",dest,"--local-dir-use-symlinks","False"], check=True)
        return dest

    def new_output_path(self, prefix="video") -> Path:
        from datetime import datetime
        day = datetime.now().strftime("%Y%m%d")
        d   = self.outputs_dir / day
        d.mkdir(parents=True, exist_ok=True)
        ts  = datetime.now().strftime("%H%M%S")
        return d / f"{prefix}_{ts}.mp4"

    def drive_stats(self) -> dict:
        stats = {}
        for f in ["models","music","fonts","outputs"]:
            d = self.drive_root / f
            if d.exists():
                files = list(d.rglob("*"))
                stats[f] = {"files": len([x for x in files if x.is_file()]),
                            "size_mb": round(sum(x.stat().st_size for x in files if x.is_file())/1_048_576, 1)}
            else: stats[f] = {"files":0,"size_mb":0}
        return stats

def setup_drive(force=False) -> DriveManager:
    DriveManager.mount_drive(force=force)
    mgr = DriveManager()
    logger.info("✅ DriveManager ready")
    return mgr

drive_mgr = DriveManager()
