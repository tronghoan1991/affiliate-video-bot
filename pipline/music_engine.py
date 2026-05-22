"""
pipeline/music_engine.py
Auto-select & attach trending music by garment mood.
Nguồn: local cache → Pixabay API → silent fallback.
"""
import json, logging, random, shutil, subprocess, tempfile
from pathlib import Path
from typing import Optional
import urllib.request

logger = logging.getLogger("Music")

MOOD_MAP = {
    "dress evening gown":   ("elegant",      "fashion runway elegant piano"),
    "casual t-shirt":       ("casual_trendy", "trendy pop upbeat youth"),
    "swimwear bikini":      ("summer",        "tropical beach summer happy"),
    "formal office shirt":  ("corporate",     "smooth jazz corporate professional"),
    "business suit":        ("powerful",      "powerful cinematic confident boss"),
    "sportswear activewear":("energetic",     "workout gym motivation EDM"),
    "winter coat jacket":   ("cozy",          "lofi cozy aesthetic chill winter"),
    "traditional ao dai":   ("vietnamese",    "vietnam traditional modern fusion"),
    "hoodie streetwear":    ("street",        "phonk trap streetwear hype bass"),
    "skirt":                ("feminine",      "girly pop cute feminine"),
    "jeans pants":          ("urban",         "indie pop urban cool"),
}
DEFAULT_MOOD = ("fashion", "fashion trendy pop style")


def _mood(garment: str):
    lower = garment.lower()
    for k, v in MOOD_MAP.items():
        if any(w in lower for w in k.split()):
            return v
    return DEFAULT_MOOD


def _local(music_dir: Path, mood_name: str) -> Optional[Path]:
    if not music_dir.exists(): return None
    files = list(music_dir.glob(f"{mood_name}_*.mp3")) or list(music_dir.glob("*.mp3"))
    return random.choice(files) if files else None


def _pixabay(query: str, dest: Path) -> Optional[Path]:
    from config import Config
    key = Config.PIXABAY_KEY
    if not key: return None
    try:
        import urllib.parse
        params = urllib.parse.urlencode({"key": key, "q": query,
                                         "media_type": "music", "per_page": 5})
        req = urllib.request.Request(
            f"https://pixabay.com/api/?{params}",
            headers={"User-Agent": "AffiliateBot/4.0"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            hits = json.loads(r.read()).get("hits", [])
        if not hits: return None
        hit = random.choice(hits[:5])
        url = hit.get("previewURL") or hit.get("audioURL")
        if not url: return None
        dest.mkdir(parents=True, exist_ok=True)
        out = dest / f"pixabay_{hit['id']}.mp3"
        if not out.exists():
            urllib.request.urlretrieve(url, str(out))
        return out
    except Exception as e:
        logger.warning(f"Pixabay download failed: {e}")
        return None


def _duration(path: Path) -> float:
    r = subprocess.run([
        "ffprobe", "-v", "quiet", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", str(path),
    ], capture_output=True, text=True)
    try: return float(r.stdout.strip())
    except: return 30.0


def _video_duration(path: Path) -> float:
    return _duration(path)


def attach_trending_music(
    video_path: Path,
    output_path: Path,
    garment_class: str = "",
    platform: str = "tiktok",
    music_override: Optional[Path] = None,
) -> Path:
    from config import Config
    music_dir = Path(Config.MUSIC_DIR)
    volume    = Config.MUSIC_VOLUME
    fade      = Config.MUSIC_FADE

    mood_name, pixabay_q = _mood(garment_class)
    vid_dur = _video_duration(video_path)

    music = music_override
    if music is None: music = _local(music_dir, mood_name)
    if music is None: music = _pixabay(pixabay_q, music_dir)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if music is None:
        tmp_silent = Path(tempfile.mktemp(suffix=".aac"))
        subprocess.run([
            "ffmpeg", "-y", "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=stereo",
            "-t", str(vid_dur), "-c:a", "aac", str(tmp_silent),
        ], check=True, capture_output=True)
        music = tmp_silent

    mus_dur = _duration(music)
    loops   = int(vid_dur / mus_dur) + 2 if mus_dur < vid_dur else 1

    af = (
        f"[1:a]aloop=loop={loops}:size=2000000000,"
        f"atrim=duration={vid_dur},"
        f"afade=in:d={fade},afade=out:st={max(0,vid_dur-fade)}:d={fade},"
        f"volume={volume}[aout]"
    )

    try:
        subprocess.run([
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-stream_loop", "-1", "-i", str(music),
            "-filter_complex", af,
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
            "-shortest", str(output_path),
        ], check=True, capture_output=True)
        logger.info(f"✅ Music attached: {output_path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Music attach error: {e.stderr.decode()[:200]}")
        shutil.copy2(video_path, output_path)

    return output_path
