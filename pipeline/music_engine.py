"""
pipeline/music_engine.py — Music Engine v6 (2026)
=============================================================================
Nguồn nhạc miễn phí (không dính copyright):
  1. Cache local trên Google Drive (ưu tiên nhất, load ngay)
  2. Pixabay Music API (miễn phí 100%, không cần attribution)
  3. Freesound.org API (miễn phí, CC0 license)
  4. AudioCraft / MusicGen (AI sinh nhạc miễn phí — chỉ trên Colab GPU)
  5. Fallback: silence (video vẫn tạo được)

Cache policy: nhạc tải về → lưu Drive → session sau load từ Drive.
=============================================================================
"""
import json
import logging
import os
import random
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

logger = logging.getLogger("MusicEngine")

# ── Mood → (tên, query tìm kiếm) ─────────────────────────────────────────────
_MOOD_CONFIG = {
    "trendy_pop":       ("trendy_pop",          "trendy pop upbeat youth viral tiktok fashion"),
    "phonk_street":     ("phonk_street",         "phonk trap streetwear hype bass attitude"),
    "energetic_edm":    ("energetic_edm",        "workout gym motivation high energy EDM"),
    "powerful_cinematic":("powerful_cinematic",  "powerful cinematic orchestral confident professional"),
    "vietnamese_modern":("vietnamese_modern",    "vietnam traditional modern melodic fusion"),
    "luxury_elegant":   ("luxury_elegant",       "luxury elegant sophisticated minimal piano strings"),
    "summer_tropical":  ("summer_tropical",      "tropical beach summer happy upbeat vacation"),
    "casual_hype":      ("casual_hype",          "casual urban youth lifestyle pop hype"),
    "cute_pop":         ("cute_pop",             "cute happy children cheerful upbeat kawaii pop"),
    "cozy_lullaby":     ("cozy_lullaby",         "gentle lullaby soft cozy baby calm peaceful"),
    "corporate_smooth": ("corporate_smooth",     "corporate smooth professional background subtle"),
    "lofi_chill":       ("lofi_chill",           "lofi chill relaxing aesthetic study focus"),
}

_DEFAULT_MOOD = "trendy_pop"

# Volume theo mood (0.0 → 1.0)
_VOLUME_MAP = {
    "trendy_pop": 0.75,     "phonk_street": 0.78,    "energetic_edm": 0.80,
    "powerful_cinematic": 0.70, "vietnamese_modern": 0.65, "luxury_elegant": 0.58,
    "summer_tropical": 0.72, "casual_hype": 0.75,    "cute_pop": 0.70,
    "cozy_lullaby": 0.55,   "corporate_smooth": 0.60, "lofi_chill": 0.62,
}


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 1: Google Drive Cache
# ══════════════════════════════════════════════════════════════════════════════

def _from_drive(mood: str) -> Optional[Path]:
    try:
        from pipeline.drive_manager import drive_mgr
        return drive_mgr.get_music_path(mood)
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 2: Pixabay Music API (miễn phí, không cần attribution)
# ══════════════════════════════════════════════════════════════════════════════

def _from_pixabay(mood: str, api_key: str) -> Optional[str]:
    if not api_key:
        return None
    _, query = _MOOD_CONFIG.get(mood, _MOOD_CONFIG[_DEFAULT_MOOD])
    try:
        url = (
            f"https://pixabay.com/api/videos/music/?"
            f"key={api_key}&q={urllib.parse.quote(query)}&per_page=20"
        )
        with urllib.request.urlopen(url, timeout=12) as r:
            data = json.loads(r.read())

        hits = data.get("hits", [])
        if not hits:
            # Thử query đơn giản hơn
            url2 = f"https://pixabay.com/api/videos/music/?key={api_key}&category=music&per_page=20"
            with urllib.request.urlopen(url2, timeout=12) as r2:
                data2 = json.loads(r2.read())
            hits = data2.get("hits", [])

        # Chọn track phù hợp thời lượng (15-60s)
        suitable = [h for h in hits if 10 <= h.get("duration", 0) <= 120]
        if not suitable:
            suitable = hits

        if suitable:
            track = random.choice(suitable[:8])
            audio_url = track.get("audio", {}).get("url") or track.get("previewURL", "")
            return audio_url if audio_url else None

    except Exception as e:
        logger.warning(f"Pixabay API lỗi: {e}")
    return None


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 3: Freesound.org API (miễn phí, CC0/CC-BY)
# ══════════════════════════════════════════════════════════════════════════════

def _from_freesound(mood: str, api_key: str) -> Optional[str]:
    if not api_key:
        return None
    _, query = _MOOD_CONFIG.get(mood, _MOOD_CONFIG[_DEFAULT_MOOD])
    try:
        url = (
            f"https://freesound.org/apiv2/search/text/?"
            f"query={urllib.parse.quote(query)}&token={api_key}"
            f"&filter=duration:[10+TO+120]+license:Creative+Commons+0"
            f"&fields=id,name,previews&page_size=10"
        )
        with urllib.request.urlopen(url, timeout=12) as r:
            data = json.loads(r.read())
        results = data.get("results", [])
        if results:
            item = random.choice(results[:5])
            preview = item.get("previews", {}).get("preview-hq-mp3") or item.get("previews", {}).get("preview-lq-mp3")
            return preview
    except Exception as e:
        logger.warning(f"Freesound API lỗi: {e}")
    return None


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 4: AudioCraft / MusicGen (AI sinh nhạc — chỉ trên Colab GPU)
# ══════════════════════════════════════════════════════════════════════════════

def _from_audiocraft(mood: str, duration: int = 15) -> Optional[Path]:
    """
    Dùng Meta AudioCraft MusicGen để sinh nhạc nền AI.
    Chỉ chạy trên Colab GPU. Hoàn toàn miễn phí.
    Model: facebook/musicgen-small (300MB) hoặc facebook/musicgen-medium (1.5GB)
    """
    try:
        from audiocraft.models import MusicGen
        from audiocraft.data.audio import audio_write
        import torch

        if not torch.cuda.is_available():
            logger.info("AudioCraft cần GPU — bỏ qua")
            return None

        _, query = _MOOD_CONFIG.get(mood, _MOOD_CONFIG[_DEFAULT_MOOD])

        logger.info(f"Đang sinh nhạc bằng AudioCraft: {query}")
        model = MusicGen.get_pretrained("facebook/musicgen-small")
        model.set_generation_params(duration=min(duration, 30))

        wav = model.generate([query])
        tmp = Path(tempfile.mktemp(suffix=".wav"))
        audio_write(str(tmp.with_suffix("")), wav[0].cpu(), model.sample_rate, strategy="loudness")
        logger.info(f"✅ AudioCraft sinh nhạc thành công: {tmp}")
        return tmp

    except ImportError:
        logger.info("AudioCraft chưa cài — cần: pip install audiocraft")
        return None
    except Exception as e:
        logger.warning(f"AudioCraft lỗi: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  DOWNLOAD + PROCESS
# ══════════════════════════════════════════════════════════════════════════════

def _download_audio(url: str, dest: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r, open(dest, "wb") as f:
            shutil.copyfileobj(r, f)
        return dest.stat().st_size > 5000
    except Exception as e:
        logger.warning(f"Không tải được audio: {e}")
        return False


def _loop_and_trim(src: Path, target_sec: int = 15, volume: float = 0.72) -> Path:
    """Loop và cắt audio về đúng thời lượng target_sec, điều chỉnh volume."""
    try:
        out = Path(tempfile.mktemp(suffix=".aac"))
        subprocess.run([
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", str(src),
            "-t", str(target_sec),
            "-af", f"volume={volume},afade=t=out:st={max(0, target_sec-2)}:d=2",
            "-c:a", "aac",
            "-b:a", "128k",
            str(out)
        ], capture_output=True, check=True)
        return out
    except subprocess.CalledProcessError as e:
        logger.warning(f"ffmpeg loop/trim lỗi: {e.stderr.decode()[:200]}")
        return src


def _save_to_drive(mood: str, src: Path):
    try:
        from pipeline.drive_manager import drive_mgr
        filename = f"{mood}_{random.randint(1000,9999)}.mp3"
        drive_mgr.save_music(mood, src, filename)
        logger.info(f"✅ Nhạc đã lưu Drive: {mood}/{filename}")
    except Exception as e:
        logger.warning(f"Không lưu được nhạc vào Drive: {e}")


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def get_music(
    mood: str,
    duration_sec: int = 15,
    pixabay_key: str = "",
    freesound_key: str = "",
    use_ai: bool = True,
) -> Optional[Path]:
    """
    Lấy nhạc nền theo mood.
    Ưu tiên: Drive cache → Pixabay → Freesound → AudioCraft → None
    """
    if not pixabay_key:
        pixabay_key = os.getenv("PIXABAY_API_KEY", "")
    if not freesound_key:
        freesound_key = os.getenv("FREESOUND_API_KEY", "")

    volume = _VOLUME_MAP.get(mood, 0.72)

    # 1. Drive cache
    cached = _from_drive(mood)
    if cached:
        logger.info(f"✅ Nhạc từ Drive: {cached}")
        return _loop_and_trim(cached, duration_sec, volume)

    # 2. Pixabay
    if pixabay_key:
        audio_url = _from_pixabay(mood, pixabay_key)
        if audio_url:
            tmp = Path(tempfile.mktemp(suffix=".mp3"))
            if _download_audio(audio_url, tmp):
                logger.info(f"✅ Nhạc từ Pixabay: {mood}")
                _save_to_drive(mood, tmp)
                return _loop_and_trim(tmp, duration_sec, volume)

    # 3. Freesound
    if freesound_key:
        audio_url = _from_freesound(mood, freesound_key)
        if audio_url:
            tmp = Path(tempfile.mktemp(suffix=".mp3"))
            if _download_audio(audio_url, tmp):
                logger.info(f"✅ Nhạc từ Freesound: {mood}")
                _save_to_drive(mood, tmp)
                return _loop_and_trim(tmp, duration_sec, volume)

    # 4. AudioCraft (AI generation — cần GPU)
    if use_ai:
        ai_path = _from_audiocraft(mood, duration_sec)
        if ai_path and ai_path.exists():
            logger.info(f"✅ Nhạc AI từ AudioCraft: {mood}")
            _save_to_drive(mood, ai_path)
            return _loop_and_trim(ai_path, duration_sec, volume)

    logger.warning(f"Không tìm được nhạc cho mood: {mood} — video sẽ không có nhạc nền")
    return None
