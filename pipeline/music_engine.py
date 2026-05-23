"""
pipeline/music_engine.py — Music Engine v5
Tất cả nhạc được cache trên Google Drive 5TB.
"""
import json, logging, os, random, shutil, subprocess, tempfile
from pathlib import Path
from typing import Optional
import urllib.request, urllib.parse

logger = logging.getLogger("MusicEngine")

_MOOD_MAP = {
    "women_formal":      ("powerful_cinematic", "cinematic orchestral confident professional"),
    "women_casual":      ("trendy_pop",         "trendy pop upbeat youth viral tiktok 2026"),
    "women_streetwear":  ("phonk_street",       "phonk trap streetwear hype bass"),
    "women_sportswear":  ("energetic_edm",      "workout gym motivation high energy EDM"),
    "women_traditional": ("vietnamese_modern",  "vietnam traditional modern melodic fusion"),
    "women_luxury":      ("luxury_elegant",     "luxury elegant sophisticated minimal piano"),
    "women_swimwear":    ("summer_tropical",    "tropical beach summer happy upbeat"),
    "men_formal":        ("powerful_cinematic", "powerful cinematic orchestral boss confident"),
    "men_casual":        ("casual_hype",        "casual urban youth lifestyle pop hype"),
    "men_streetwear":    ("phonk_street",       "phonk trap streetwear hype bass attitude"),
    "men_sportswear":    ("energetic_edm",      "gym motivation high energy EDM workout"),
    "men_traditional":   ("vietnamese_modern",  "vietnam traditional modern melodic fusion"),
    "kids_casual":       ("feminine_pop",       "cute happy children cheerful upbeat pop"),
    "kids_traditional":  ("vietnamese_modern",  "vietnam traditional melodic gentle"),
    "baby":              ("cozy_aesthetic",     "gentle lullaby soft cozy baby calm"),
    "unisex_couple":     ("trendy_pop",         "romantic pop upbeat couple sweet"),
    "unisex_family":     ("trendy_pop",         "happy family cheerful warm upbeat"),
    "elegant_upbeat":    ("elegant_upbeat",     "fashion elegant piano runway upbeat"),
    "cozy_aesthetic":    ("cozy_aesthetic",     "lofi cozy aesthetic piano gentle chill"),
}
_DEFAULT = ("trendy_pop", "trendy pop upbeat fashion viral tiktok")

_VOLUME = {
    "elegant_upbeat": 0.68, "trendy_pop": 0.75, "summer_tropical": 0.72,
    "corporate_smooth": 0.60, "powerful_cinematic": 0.70, "energetic_edm": 0.80,
    "cozy_aesthetic": 0.58, "vietnamese_modern": 0.65, "phonk_street": 0.78,
    "feminine_pop": 0.72, "casual_hype": 0.75, "luxury_elegant": 0.58,
}


def _local_track(mood: str) -> Optional[Path]:
    try:
        from pipeline.drive_manager import drive_mgr
        return drive_mgr.get_music_path(mood)
    except Exception:
        return None


def _pixabay(query: str, api_key: str, mood: str) -> Optional[str]:
    try:
        url = f"https://pixabay.com/api/music/?key={api_key}&q={urllib.parse.quote(query)}&per_page=15"
        with urllib.request.urlopen(url, timeout=10) as r:
            data = json.loads(r.read())
        hits = data.get("hits", [])
        if not hits:
            return None
        suitable = [h for h in hits if 10 <= h.get("duration", 0) <= 90]
        track = random.choice(suitable or hits)
        track_id = str(track.get("id", "unknown"))
        audio_url = track.get("audio", {}).get("url", "") or track.get("previewURL", "")
        if not audio_url:
            return None
        # Check cache
        try:
            from pipeline.drive_manager import drive_mgr
            cached = drive_mgr.get_pixabay_cached(mood, track_id)
            if cached:
                tmp = tempfile.mktemp(suffix=".mp3")
                shutil.copy2(cached, tmp)
                return tmp
        except Exception:
            pass
        tmp = tempfile.mktemp(suffix=".mp3")
        urllib.request.urlretrieve(audio_url, tmp)
        try:
            from pipeline.drive_manager import drive_mgr
            drive_mgr.save_pixabay_audio(Path(tmp), mood, track_id)
        except Exception:
            pass
        return tmp
    except Exception as e:
        logger.warning(f"Pixabay failed: {e}")
        return None


def _get_video_dur(video: Path) -> float:
    r = subprocess.run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                        "-of", "default=noprint_wrappers=1:nokey=1", str(video)],
                       capture_output=True, text=True)
    try:
        return float(r.stdout.strip())
    except Exception:
        return 15.0


def _attach(video: Path, audio: Path, out: Path, volume: float = 0.75) -> Path:
    dur = _get_video_dur(video)
    out.parent.mkdir(parents=True, exist_ok=True)
    af = f"volume={volume},afade=in:st=0:d=0.5,afade=out:st={max(0,dur-2)}:d=2"
    try:
        subprocess.run([
            "ffmpeg", "-y", "-i", str(video), "-stream_loop", "-1", "-i", str(audio),
            "-filter_complex", f"[1:a]{af}[a]",
            "-map", "0:v", "-map", "[a]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-t", str(dur), "-shortest", str(out),
        ], check=True, capture_output=True)
        return out
    except Exception as e:
        logger.error(f"Audio attach failed: {e}")
        shutil.copy2(video, out)
        return out


def attach_trending_music(video_path: Path, output_path: Path, garment: str = "", mood_override: str = "") -> Path:
    mood_key = mood_override or "trendy_pop"
    mood, query = _MOOD_MAP.get(mood_key, _DEFAULT)

    audio = None
    cleanup = False

    local = _local_track(mood)
    if local:
        audio = str(local)
        logger.info(f"Music: Drive local {local.name}")

    if not audio:
        key = os.environ.get("PIXABAY_API_KEY", "")
        if key:
            fetched = _pixabay(query, key, mood)
            if fetched:
                audio = fetched
                cleanup = True
                logger.info("Music: Pixabay download")

    if not audio:
        logger.warning("No music — silent video")
        shutil.copy2(video_path, output_path)
        return output_path

    vol = _VOLUME.get(mood, 0.72)
    try:
        return _attach(video_path, Path(audio), output_path, vol)
    finally:
        if cleanup and audio and Path(audio).exists():
            Path(audio).unlink(missing_ok=True)
