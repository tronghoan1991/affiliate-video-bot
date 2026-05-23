"""
pipeline/music_engine.py — Music Engine v7
Nguồn: Drive cache → Pixabay → Freesound → AudioCraft AI → silence
"""
import json, logging, os, random, shutil, subprocess, tempfile, urllib.parse, urllib.request
from pathlib import Path
from typing import Optional

logger = logging.getLogger("MusicEngine")

_MOODS = {
    "trendy_pop":          "trendy pop upbeat youth viral tiktok fashion",
    "phonk_street":        "phonk trap streetwear hype bass attitude",
    "energetic_edm":       "workout gym motivation high energy EDM",
    "powerful_cinematic":  "powerful cinematic orchestral confident professional",
    "vietnamese_modern":   "vietnam traditional modern melodic fusion",
    "luxury_elegant":      "luxury elegant sophisticated minimal piano strings",
    "summer_tropical":     "tropical beach summer happy upbeat vacation",
    "casual_hype":         "casual urban youth lifestyle pop hype",
    "cute_pop":            "cute happy children cheerful upbeat kawaii pop",
    "cozy_lullaby":        "gentle lullaby soft cozy baby calm peaceful",
    "corporate_smooth":    "corporate smooth professional background subtle",
    "lofi_chill":          "lofi chill relaxing aesthetic study focus",
    "appetite":            "upbeat fun cooking food tasty delicious pop",
    "tech_minimal":        "minimal electronic tech modern digital beats",
    "nature_calm":         "nature peaceful calm pets animals gentle",
}
_VOL = {
    "trendy_pop":0.75,"phonk_street":0.78,"energetic_edm":0.80,
    "powerful_cinematic":0.70,"vietnamese_modern":0.65,"luxury_elegant":0.58,
    "summer_tropical":0.72,"casual_hype":0.75,"cute_pop":0.70,
    "cozy_lullaby":0.55,"corporate_smooth":0.60,"lofi_chill":0.62,
    "appetite":0.72,"tech_minimal":0.65,"nature_calm":0.60,
}

def _from_drive(mood):
    try:
        from pipeline.drive_manager import drive_mgr
        return drive_mgr.get_music_path(mood)
    except: return None

def _from_pixabay(mood, key):
    if not key: return None
    q = _MOODS.get(mood, mood)
    try:
        url = f"https://pixabay.com/api/videos/music/?key={key}&q={urllib.parse.quote(q)}&per_page=20"
        with urllib.request.urlopen(url, timeout=12) as r: data = json.loads(r.read())
        hits = data.get("hits",[])
        if not hits:
            url2 = f"https://pixabay.com/api/videos/music/?key={key}&category=music&per_page=20"
            with urllib.request.urlopen(url2, timeout=12) as r2: hits = json.loads(r2.read()).get("hits",[])
        suitable = [h for h in hits if 10 <= h.get("duration",0) <= 120] or hits
        if suitable:
            t = random.choice(suitable[:8])
            return t.get("audio",{}).get("url") or t.get("previewURL","") or None
    except Exception as e: logger.warning(f"Pixabay: {e}")
    return None

def _from_freesound(mood, key):
    if not key: return None
    q = _MOODS.get(mood, mood)
    try:
        url = (f"https://freesound.org/apiv2/search/text/?query={urllib.parse.quote(q)}&token={key}"
               f"&filter=duration:[10+TO+120]+license:Creative+Commons+0&fields=id,name,previews&page_size=10")
        with urllib.request.urlopen(url, timeout=12) as r: data = json.loads(r.read())
        results = data.get("results",[])
        if results:
            item = random.choice(results[:5])
            return item.get("previews",{}).get("preview-hq-mp3") or item.get("previews",{}).get("preview-lq-mp3")
    except Exception as e: logger.warning(f"Freesound: {e}")
    return None

def _from_audiocraft(mood, dur=15):
    try:
        from audiocraft.models import MusicGen
        from audiocraft.data.audio import audio_write
        import torch
        if not torch.cuda.is_available(): return None
        q = _MOODS.get(mood, mood)
        model = MusicGen.get_pretrained("facebook/musicgen-small")
        model.set_generation_params(duration=min(dur,30))
        wav = model.generate([q])
        tmp = Path(tempfile.mktemp(suffix=".wav"))
        audio_write(str(tmp.with_suffix("")), wav[0].cpu(), model.sample_rate, strategy="loudness")
        return tmp
    except Exception as e: logger.warning(f"AudioCraft: {e}"); return None

def _dl(url, dest):
    try:
        req = urllib.request.Request(url, headers={"User-Agent":"Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as r, open(dest,"wb") as f:
            shutil.copyfileobj(r,f)
        return dest.stat().st_size > 5000
    except: return False

def _trim(src, secs=15, vol=0.72):
    try:
        out = Path(tempfile.mktemp(suffix=".aac"))
        subprocess.run(["ffmpeg","-y","-stream_loop","-1","-i",str(src),
            "-t",str(secs),"-af",f"volume={vol},afade=t=out:st={max(0,secs-2)}:d=2",
            "-c:a","aac","-b:a","128k",str(out)], capture_output=True, check=True)
        return out
    except: return src

def _save_drive(mood, src):
    try:
        from pipeline.drive_manager import drive_mgr
        drive_mgr.save_music(mood, src, f"{mood}_{random.randint(1000,9999)}.mp3")
    except: pass

def get_music(mood: str, dur=15, pixabay_key="", freesound_key="", use_ai=True) -> Optional[Path]:
    pixabay_key  = pixabay_key  or os.getenv("PIXABAY_API_KEY","")
    freesound_key= freesound_key or os.getenv("FREESOUND_API_KEY","")
    vol = _VOL.get(mood, 0.72)

    cached = _from_drive(mood)
    if cached: return _trim(cached, dur, vol)

    if pixabay_key:
        url = _from_pixabay(mood, pixabay_key)
        if url:
            tmp = Path(tempfile.mktemp(suffix=".mp3"))
            if _dl(url, tmp): _save_drive(mood, tmp); return _trim(tmp, dur, vol)

    if freesound_key:
        url = _from_freesound(mood, freesound_key)
        if url:
            tmp = Path(tempfile.mktemp(suffix=".mp3"))
            if _dl(url, tmp): _save_drive(mood, tmp); return _trim(tmp, dur, vol)

    if use_ai:
        p = _from_audiocraft(mood, dur)
        if p and p.exists(): _save_drive(mood, p); return _trim(p, dur, vol)

    logger.warning(f"No music for mood: {mood}")
    return None
