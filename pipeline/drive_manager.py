"""
pipeline/drive_manager.py — Google Drive Asset Manager v5
=============================================================================
Quản lý toàn bộ add-ons: models, music, fonts, outputs trên Google Drive 5TB.
Colab chỉ dùng /tmp làm cache ngắn hạn trong session.
=============================================================================
"""
import json, logging, os, random, shutil
from pathlib import Path
from typing import Optional

logger = logging.getLogger("DriveManager")

DRIVE_ROOT  = Path("/content/drive/MyDrive/AffiliateBot")
COLAB_CACHE = Path("/tmp/affiliatebot_cache")


class DriveManager:
    def __init__(self, drive_root: Path = DRIVE_ROOT):
        self.drive_root = drive_root
        self.cache_dir = COLAB_CACHE
        self._ensure_dirs()

    def _ensure_dirs(self):
        for sub in ["models", "music", "fonts", "outputs", "cache/pixabay"]:
            (self.drive_root / sub).mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def mount_drive(force: bool = False) -> bool:
        try:
            from google.colab import drive
            if force or not Path("/content/drive/MyDrive").exists():
                drive.mount("/content/drive", force_remount=force)
            logger.info("✅ Google Drive mounted")
            return True
        except ImportError:
            logger.info("Not in Colab — Drive mount skipped")
            return False
        except Exception as e:
            logger.error(f"Drive mount failed: {e}")
            return False

    @property
    def models_dir(self) -> Path:
        return self.drive_root / "models"

    @property
    def music_dir(self) -> Path:
        return self.drive_root / "music"

    @property
    def fonts_dir(self) -> Path:
        return self.drive_root / "fonts"

    @property
    def outputs_dir(self) -> Path:
        return self.drive_root / "outputs"

    @property
    def pixabay_cache_dir(self) -> Path:
        return self.drive_root / "cache" / "pixabay"

    def get_font_path(self, filename: str = "Montserrat-Bold.ttf") -> Optional[Path]:
        drive_path = self.fonts_dir / filename
        cache_path = self.cache_dir / "fonts" / filename
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        if cache_path.exists():
            return cache_path
        if drive_path.exists():
            shutil.copy2(drive_path, cache_path)
            return cache_path
        downloaded = self._download_font(filename, drive_path)
        if downloaded and drive_path.exists():
            shutil.copy2(drive_path, cache_path)
            return cache_path
        return None

    def _download_font(self, filename: str, dest: Path) -> bool:
        import urllib.request
        urls = {
            "Montserrat-Bold.ttf":      "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Bold.ttf",
            "Montserrat-ExtraBold.ttf": "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-ExtraBold.ttf",
            "NotoSans-Bold.ttf":        "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSans/NotoSans-Bold.ttf",
        }
        url = urls.get(filename)
        if not url:
            return False
        try:
            dest.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(url, str(dest))
            logger.info(f"✅ Font saved to Drive: {filename}")
            return True
        except Exception as e:
            logger.error(f"Font download failed: {e}")
            return False

    def get_music_path(self, mood: str) -> Optional[Path]:
        mood_dir = self.music_dir / mood
        mood_dir.mkdir(parents=True, exist_ok=True)
        tracks = list(mood_dir.glob("*.mp3")) + list(mood_dir.glob("*.m4a"))
        if not tracks:
            all_tracks = list(self.music_dir.rglob("*.mp3")) + list(self.music_dir.rglob("*.m4a"))
            tracks = all_tracks
        if not tracks:
            return None
        chosen = random.choice(tracks)
        cache_path = self.cache_dir / "music" / chosen.name
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        if not cache_path.exists():
            shutil.copy2(chosen, cache_path)
        return cache_path

    def save_pixabay_audio(self, src: Path, mood: str, track_id: str) -> Path:
        dest = self.pixabay_cache_dir / f"{mood}_{track_id}.mp3"
        if not dest.exists():
            shutil.copy2(src, dest)
        return dest

    def get_pixabay_cached(self, mood: str, track_id: str) -> Optional[Path]:
        p = self.pixabay_cache_dir / f"{mood}_{track_id}.mp3"
        return p if p.exists() else None

    def save_output_video(self, src: Path, subfolder: str = "") -> Path:
        import datetime
        sf = subfolder or datetime.datetime.now().strftime("%Y-%m-%d")
        dest_dir = self.outputs_dir / sf
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / src.name
        shutil.copy2(src, dest)
        logger.info(f"✅ Output saved: Drive/outputs/{sf}/{src.name}")
        return dest

    def get_output_dir(self, subfolder: str = "") -> Path:
        import datetime
        sf = subfolder or datetime.datetime.now().strftime("%Y-%m-%d")
        d = self.outputs_dir / sf
        d.mkdir(parents=True, exist_ok=True)
        return d

    def get_model_path(self, model_name: str) -> Optional[Path]:
        p = self.models_dir / model_name
        return p if p.exists() else None

    def model_exists(self, model_name: str) -> bool:
        return (self.models_dir / model_name).exists()

    def load_config(self) -> dict:
        p = self.drive_root / "config.json"
        if p.exists():
            try:
                return json.loads(p.read_text())
            except Exception:
                pass
        return {}

    def save_config(self, config: dict):
        p = self.drive_root / "config.json"
        p.write_text(json.dumps(config, ensure_ascii=False, indent=2))

    def drive_stats(self) -> dict:
        def sz(p: Path) -> int:
            return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        stats = {}
        for sub in ["models", "music", "fonts", "outputs", "cache"]:
            d = self.drive_root / sub
            if d.exists():
                mb = sz(d) / (1024 * 1024)
                cnt = sum(1 for _ in d.rglob("*") if _.is_file())
                stats[sub] = {"size_mb": round(mb, 1), "files": cnt}
        return stats

    def clear_colab_cache(self):
        if self.cache_dir.exists():
            shutil.rmtree(self.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)


drive_mgr = DriveManager()


def setup_drive() -> DriveManager:
    DriveManager.mount_drive()
    mgr = DriveManager()
    stats = mgr.drive_stats()
    logger.info(f"📊 Drive ready: {mgr.drive_root}")
    for folder, info in stats.items():
        logger.info(f"  {folder}: {info['size_mb']}MB | {info['files']} files")
    return mgr
