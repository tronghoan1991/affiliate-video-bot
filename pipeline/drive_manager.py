"""
pipeline/drive_manager.py — Google Drive 5TB Manager
Quản lý models, outputs, products, fonts, music, addons
"""
import os, io, base64, time, logging, urllib.request
from pathlib import Path
from typing import Optional

logger = logging.getLogger("DriveManager")

DRIVE_ROOT_DEFAULT = "/content/drive/MyDrive/AffiliateStudio"

FOLDER_STRUCTURE = [
    "models/idm-vton",
    "models/wan2.1-i2v-14B-480P",
    "models/cogvideox-5b",
    "models/flux1-schnell",
    "models/musicgen-small",
    "models/fashion",    # thư viện model photos — fashion
    "models/beauty",
    "models/health",
    "models/sports",
    "models/home",
    "models/food",
    "models/pet",
    "models/baby",
    "models/male",
    "models/female",
    "models/child",
    "models/unisex",
    "outputs/videos",
    "outputs/previews",
    "outputs/captions",
    "products",
    "fonts",
    "music",
    "addons",
]

FONTS = {
    "Montserrat-Bold.ttf": (
        "https://github.com/JulietaUla/Montserrat/raw/master"
        "/fonts/ttf/Montserrat-Bold.ttf"
    ),
    "Montserrat-ExtraBold.ttf": (
        "https://github.com/JulietaUla/Montserrat/raw/master"
        "/fonts/ttf/Montserrat-ExtraBold.ttf"
    ),
    "BeVietnamPro-Bold.ttf": (
        "https://github.com/letteratic/Be-Vietnam-Pro/raw/main"
        "/fonts/ttf/BeVietnamPro-Bold.ttf"
    ),
}


class DriveManager:
    def __init__(self, drive_root: str = DRIVE_ROOT_DEFAULT):
        self.drive_root = Path(drive_root)
        self._ensure_structure()

    def _ensure_structure(self):
        for folder in FOLDER_STRUCTURE:
            (self.drive_root / folder).mkdir(parents=True, exist_ok=True)

    # ── Model photos library ──────────────────────────────────────────────
    def get_model_photos(self, category: str, gender: str = "unisex") -> list[Path]:
        """Lấy danh sách ảnh người mẫu từ Drive theo category/gender."""
        dirs_to_check = [
            self.drive_root / "models" / category,
            self.drive_root / "models" / gender,
            self.drive_root / "models" / "unisex",
        ]
        for d in dirs_to_check:
            if d.exists():
                photos = list(d.glob("*.jpg")) + list(d.glob("*.png")) + \
                         list(d.glob("*.jpeg"))
                if photos:
                    return sorted(photos)
        return []

    def add_model_photo(self, img_bytes: bytes, category: str,
                        gender: str = "unisex", name: str = "") -> Path:
        """Thêm ảnh người mẫu vào thư viện Drive."""
        folder = self.drive_root / "models" / category
        folder.mkdir(parents=True, exist_ok=True)
        fname  = name or f"{gender}_{int(time.time())}.jpg"
        path   = folder / fname
        path.write_bytes(img_bytes)
        logger.info(f"✅ Model photo saved: {path}")
        return path

    # ── Outputs ──────────────────────────────────────────────────────────
    def save_video(self, video_path: Path, product_name: str) -> Path:
        out_dir  = self.drive_root / "outputs" / "videos"
        out_dir.mkdir(parents=True, exist_ok=True)
        fname    = f"{product_name.replace(' ','_')}_{int(time.time())}.mp4"
        dst      = out_dir / fname
        import shutil
        shutil.copy2(str(video_path), str(dst))
        return dst

    def save_preview(self, img_bytes: bytes, product_name: str) -> Path:
        out_dir = self.drive_root / "outputs" / "previews"
        out_dir.mkdir(parents=True, exist_ok=True)
        fname   = f"{product_name.replace(' ','_')}_{int(time.time())}.jpg"
        path    = out_dir / fname
        path.write_bytes(img_bytes)
        return path

    def save_caption(self, caption: str, product_name: str) -> Path:
        out_dir = self.drive_root / "outputs" / "captions"
        out_dir.mkdir(parents=True, exist_ok=True)
        fname   = f"{product_name.replace(' ','_')}_{int(time.time())}.txt"
        path    = out_dir / fname
        path.write_text(caption, encoding="utf-8")
        return path

    # ── Fonts ─────────────────────────────────────────────────────────────
    def get_font_path(self, font_name: str) -> Optional[Path]:
        p = self.drive_root / "fonts" / font_name
        if p.exists(): return p
        # Download nếu chưa có
        url = FONTS.get(font_name)
        if url:
            try:
                urllib.request.urlretrieve(url, p)
                logger.info(f"✅ Font downloaded: {font_name}")
                return p
            except Exception as e:
                logger.warning(f"Font download fail {font_name}: {e}")
        return None

    def ensure_fonts(self) -> dict:
        result = {}
        for fname in FONTS:
            result[fname] = self.get_font_path(fname)
        return result

    # ── Stats ─────────────────────────────────────────────────────────────
    def drive_stats(self) -> dict:
        stats = {}
        for section in ["models", "outputs", "products", "music", "addons"]:
            d = self.drive_root / section
            if d.exists():
                files = list(d.rglob("*"))
                files = [f for f in files if f.is_file()]
                size  = sum(f.stat().st_size for f in files) / 1e6
                stats[section] = {
                    "size_mb": round(size, 1),
                    "files":   len(files),
                }
        return stats

    def list_model_library(self) -> dict:
        """Liệt kê tất cả ảnh người mẫu trong Drive."""
        result = {}
        model_root = self.drive_root / "models"
        for folder in model_root.iterdir():
            if folder.is_dir():
                photos = list(folder.glob("*.jpg")) + \
                         list(folder.glob("*.png")) + \
                         list(folder.glob("*.jpeg"))
                if photos:
                    result[folder.name] = len(photos)
        return result


# Singleton
_drive_instance: Optional[DriveManager] = None

def setup_drive(drive_root: str = DRIVE_ROOT_DEFAULT) -> DriveManager:
    global _drive_instance
    if _drive_instance is None:
        _drive_instance = DriveManager(drive_root)
        logger.info(f"✅ DriveManager initialized: {drive_root}")
    return _drive_instance
