"""
pipeline/music_engine.py — Free Music Engine v8
================================================
Hoàn toàn miễn phí: Pixabay → FreeSound → yt-dlp → Procedural
"""
import logging, os, random, tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger("MusicEngine")

MOOD_QUERIES = {
    "elegant_upbeat":   "fashion upbeat positive",
    "trendy_pop":       "trendy pop upbeat catchy",
    "feminine_soft":    "soft feminine gentle piano",
    "luxury_ambient":   "luxury ambient elegant",
    "energetic_sport":  "energetic sport motivation",
    "uplifting_power":  "uplifting powerful motivation",
    "morning_fresh":    "morning fresh positive energy",
    "workout_pump":     "workout pump electronic",
    "cozy_warm":        "cozy warm acoustic",
    "lifestyle_chill":  "chill lifestyle lofi",
    "positive_bright":  "positive bright happy",
    "happy_appetizing": "happy appetizing upbeat",
    "cute_playful":     "cute playful children happy",
    "gentle_caring":    "gentle caring soft lullaby",
    "emotional_touch":  "emotional touching heartfelt",
    "viral_hook":       "viral catchy hook pop",
}

CATEGORY_MOODS = {
    "fashion":      ["trendy_pop", "elegant_upbeat", "viral_hook"],
    "beauty":       ["feminine_soft", "elegant_upbeat", "luxury_ambient"],
    "health":       ["morning_fresh", "uplifting_power", "energetic_sport"],
    "home":         ["cozy_warm", "lifestyle_chill", "positive_bright"],
    "food":         ["happy_appetizing", "cozy_warm", "positive_bright"],
    "tech":         ["energetic_sport", "uplifting_power", "lifestyle_chill"],
    "sports":       ["energetic_sport", "workout_pump", "uplifting_power"],
    "pet":          ["cute_playful", "cozy_warm", "positive_bright"],
    "baby":         ["gentle_caring", "cute_playful", "cozy_warm"],
    "fashion_kids": ["cute_playful", "happy_appetizing", "positive_bright"],
}


def get_music(mood: str, category: str = "fashion",
              duration: float = 60.0,
              drive_root: Optional[Path] = None) -> Optional[str]:
    if drive_root:
        cached = _get_cached(mood, category, drive_root)
        if cached:
            return cached

    result = _pixabay(mood, category, duration, drive_root)
    if result: return result

    key = os.getenv("FREESOUND_API_KEY", "")
    if key:
        result = _freesound(mood, key, drive_root)
        if result: return result

    result = _ytdlp(mood, category, drive_root)
    if result: return result

    return _procedural(mood, duration)


def _get_cached(mood, category, drive_root):
    d = drive_root / "music"
    if not d.exists(): return None
    files = (list(d.glob(f"*{mood[:10]}*.mp3")) +
             list(d.glob(f"*{category}*.mp3")) +
             list(d.glob("*.mp3")) + list(d.glob("*.wav")))
    return str(random.choice(files)) if files else None


def _pixabay(mood, category, duration, drive_root):
    import requests
    key = os.getenv("PIXABAY_API_KEY", "")
    if not key: return None
    moods = CATEGORY_MOODS.get(category, ["trendy_pop"])
    q     = MOOD_QUERIES.get(random.choice(moods), "upbeat")
    try:
        url  = (f"https://pixabay.com/api/videos/music/"
                f"?key={key}&q={q.replace(' ','+')}&per_page=10&min_duration=30")
        hits = requests.get(url, timeout=10).json().get("hits", [])
        if not hits: return None
        best = min(hits[:5], key=lambda x: abs(x.get("duration",0) - duration))
        mp3  = best.get("url", "")
        if not mp3: return None
        data = requests.get(mp3, timeout=30).content
        tmp  = tempfile.mktemp(suffix=".mp3")
        open(tmp, "wb").write(data)
        if os.path.getsize(tmp) > 5000:
            if drive_root: _cache(tmp, mood, category, drive_root)
            logger.info(f"✅ Pixabay music OK")
            return tmp
    except Exception as e:
        logger.warning(f"Pixabay music: {e}")
    return None


def _freesound(mood, key, drive_root):
    import requests
    q = MOOD_QUERIES.get(mood, "background music")
    try:
        url  = (f"https://freesound.org/apiv2/search/text/"
                f"?query={q.replace(' ','+')}&filter=duration:[30+TO+180]"
                f"&fields=id,name,previews&token={key}&page_size=5")
        res  = requests.get(url, timeout=10).json().get("results", [])
        if not res: return None
        mp3  = random.choice(res[:5]).get("previews",{}).get("preview-hq-mp3","")
        if not mp3: return None
        data = requests.get(mp3, timeout=30).content
        tmp  = tempfile.mktemp(suffix=".mp3")
        open(tmp,"wb").write(data)
        if os.path.getsize(tmp) > 5000:
            if drive_root: _cache(tmp, mood, "general", drive_root)
            return tmp
    except Exception as e:
        logger.warning(f"FreeSound: {e}")
    return None


def _ytdlp(mood, category, drive_root):
    try:
        import subprocess
        q   = MOOD_QUERIES.get(mood, "background music no copyright")
        tmp = tempfile.mkdtemp()
        cmd = ["yt-dlp","--no-playlist","-x","--audio-format","mp3",
               "--audio-quality","192K","--match-filter","duration < 200",
               "--output",f"{tmp}/%(id)s.%(ext)s","--quiet","--no-warnings",
               f"ytsearch3:YouTube Audio Library {q} no copyright"]
        subprocess.run(cmd, capture_output=True, timeout=60)
        files = list(Path(tmp).glob("*.mp3"))
        if files:
            f = str(files[0])
            if drive_root: _cache(f, mood, category, drive_root)
            logger.info("✅ yt-dlp music OK")
            return f
    except Exception as e:
        logger.warning(f"yt-dlp: {e}")
    return None


def _procedural(mood: str, duration: float = 60.0) -> Optional[str]:
    """Tạo nhạc procedural bằng numpy — luôn hoạt động."""
    try:
        import numpy as np, wave
        SR  = 44100
        n   = int(duration * SR)
        t   = np.linspace(0, duration, n)
        cfg = {
            "trendy_pop":      (128, 440.0),
            "elegant_upbeat":  (115, 392.0),
            "energetic_sport": (140, 523.25),
            "cozy_warm":       (90,  349.23),
            "feminine_soft":   (100, 440.0),
            "emotional_touch": (80,  329.63),
            "cute_playful":    (120, 523.25),
        }.get(mood, (110, 440.0))
        bpm, base = cfg
        beat  = 60.0 / bpm
        audio = np.zeros(n)
        # Simple melody + harmony
        for i, ratio in enumerate([1.0, 1.25, 1.5, 2.0] * int(duration/beat/4 + 2)):
            s = int(i * beat * SR)
            e = min(s + int(beat * SR), n)
            if s >= n: break
            tc = t[s:e] - t[s]
            env = np.exp(-tc * 1.5) * 0.18
            audio[s:e] += np.sin(2*np.pi*base*ratio*tc) * env
        # Kick pattern
        for i in range(int(duration/beat)):
            s = int(i * beat * SR)
            e = min(s + int(0.08 * SR), n)
            if s >= n: break
            tc = t[s:e] - t[s]
            audio[s:e] += np.sin(2*np.pi*60*tc) * np.exp(-tc*40) * 0.3
        # Fade in/out
        fi = int(SR * 1.5)
        audio[:fi]  *= np.linspace(0, 1, fi)
        audio[-fi:] *= np.linspace(1, 0, fi)
        mx = np.max(np.abs(audio))
        if mx > 0: audio = audio / mx * 0.7
        tmp = tempfile.mktemp(suffix=".wav")
        with wave.open(tmp, "w") as wf:
            wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(SR)
            wf.writeframes((audio*32767).astype(np.int16).tobytes())
        logger.info(f"✅ Procedural music: {duration:.0f}s {mood}")
        return tmp
    except Exception as e:
        logger.error(f"Procedural music: {e}")
        return None


def _cache(src, mood, category, drive_root):
    import shutil, time
    d = drive_root / "music"
    d.mkdir(parents=True, exist_ok=True)
    files = list(d.glob("*.mp3")) + list(d.glob("*.wav"))
    if len(files) >= 30: files[0].unlink()
    ext = Path(src).suffix
    shutil.copy2(src, d / f"{category}_{mood[:12]}_{int(time.time())}{ext}")
