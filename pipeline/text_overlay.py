"""
pipeline/text_overlay.py — Dynamic Text Overlay Engine v7 (2026)
=============================================================================
3-lớp overlay theo timeline 15 giây. Color scheme riêng cho 10 ngành hàng.
=============================================================================
"""
import json, logging, shutil, subprocess, tempfile
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger("TextOverlay")

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_OK = True
except ImportError:
    PIL_OK = False

_COLORS = {
    "fashion":       {"bg":(200,20,60),    "text":(255,255,255), "accent":(255,220,0),  "badge":(255,50,100)},
    "fashion_women": {"bg":(200,20,60),    "text":(255,255,255), "accent":(255,220,0),  "badge":(255,50,100)},
    "fashion_men":   {"bg":(20,30,100),    "text":(255,255,255), "accent":(255,220,0),  "badge":(30,100,220)},
    "beauty":        {"bg":(180,80,100),   "text":(255,255,255), "accent":(255,210,180),"badge":(220,100,130)},
    "health":        {"bg":(30,140,80),    "text":(255,255,255), "accent":(200,255,200),"badge":(50,200,100)},
    "home":          {"bg":(180,100,20),   "text":(255,255,255), "accent":(255,230,150),"badge":(220,150,50)},
    "food":          {"bg":(200,60,20),    "text":(255,255,255), "accent":(255,230,100),"badge":(240,100,50)},
    "tech":          {"bg":(20,60,160),    "text":(255,255,255), "accent":(100,200,255),"badge":(50,120,220)},
    "pet":           {"bg":(120,50,180),   "text":(255,255,255), "accent":(220,180,255),"badge":(170,80,220)},
    "sports":        {"bg":(0,150,150),    "text":(255,255,255), "accent":(150,255,255),"badge":(0,200,200)},
    "baby":          {"bg":(80,160,220),   "text":(255,255,255), "accent":(200,230,255),"badge":(120,190,240)},
    "fashion_kids":  {"bg":(240,150,30),   "text":(255,255,255), "accent":(255,230,100),"badge":(255,180,50)},
}
_DEFAULT_COLOR = _COLORS["fashion"]

def _scheme(category: str, gender: str = "") -> dict:
    key = f"{category}_{gender}" if f"{category}_{gender}" in _COLORS else category
    return _COLORS.get(key, _DEFAULT_COLOR)

def _font(size: int):
    if not PIL_OK: return None
    try:
        from pipeline.drive_manager import drive_mgr
        p = drive_mgr.get_font_path("Montserrat-Bold.ttf")
        if p: return ImageFont.truetype(str(p), size)
    except: pass
    for fp in ["/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
               "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]:
        if Path(fp).exists():
            try: return ImageFont.truetype(fp, size)
            except: pass
    return ImageFont.load_default()

def _vinfo(path: Path):
    try:
        r = subprocess.run(["ffprobe","-v","quiet","-print_format","json",
                            "-show_streams","-show_format",str(path)], capture_output=True, text=True)
        d = json.loads(r.stdout)
        vs = next((s for s in d["streams"] if s["codec_type"]=="video"), d["streams"][0])
        return int(vs.get("width",1080)), int(vs.get("height",1920)), float(d["format"].get("duration",15))
    except: return 1080, 1920, 15.0

def _wrap(text: str, mc: int) -> list:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur+w) <= mc: cur += w+" "
        else:
            if cur: lines.append(cur.strip())
            cur = w+" "
    if cur: lines.append(cur.strip())
    return lines or [text]

def _layer_hook(w,h,text,scheme,alpha=1.0):
    if not PIL_OK: return None
    c = Image.new("RGBA",(w,h),(0,0,0,0)); d = ImageDraw.Draw(c)
    bs = int(h*0.055); f = _font(int(bs*1.1))
    gh = int(h*0.3)
    for y in range(gh):
        op = int(180*(1-y/gh)**0.7*alpha)
        d.rectangle([(0,y),(w,y+1)],fill=(0,0,0,op))
    yp = int(h*0.04)
    for ln in _wrap(text, max(14, int(w/(bs*0.6))))[:2]:
        d.text((w//2,yp),ln,font=f,fill=(*scheme["text"],int(255*alpha)),
               stroke_width=5,stroke_fill=(0,0,0,int(220*alpha)),anchor="mt")
        yp += int(bs*1.35)
    return c

def _layer_product(w,h,name,price,badge,scheme,alpha=1.0):
    if not PIL_OK: return None
    c = Image.new("RGBA",(w,h),(0,0,0,0)); d = ImageDraw.Draw(c)
    bs = int(h*0.05); fn = _font(int(bs*1.0)); fp = _font(int(bs*1.35)); fb = _font(int(bs*0.7))
    cy = int(h*0.37)
    bw,bh = int(w*0.55),int(bs*1.25); bx=(w-bw)//2
    for y in range(bh):
        r,g,b = scheme["badge"]; d.rectangle([(bx,cy+y),(bx+bw,cy+y+1)],fill=(r,g,b,int(210*alpha)))
    d.text((w//2,cy+bh//2),badge,font=fb,fill=(255,255,255,int(255*alpha)),anchor="mm")
    cy += bh+int(bs*0.4)
    for ln in _wrap(name,max(14,int(w/(bs*0.62))))[:2]:
        d.text((w//2,cy),ln,font=fn,fill=(255,255,255,int(255*alpha)),
               stroke_width=4,stroke_fill=(0,0,0,int(200*alpha)),anchor="mt")
        cy += int(bs*1.3)
    d.text((w//2,cy),f"💰 {price}",font=fp,fill=(*scheme["accent"],int(255*alpha)),
           stroke_width=5,stroke_fill=(0,0,0,int(220*alpha)),anchor="mt")
    return c

def _layer_value(w,h,value,alpha=1.0):
    if not PIL_OK: return None
    c = Image.new("RGBA",(w,h),(0,0,0,0)); d = ImageDraw.Draw(c)
    bs = int(h*0.044); f = _font(int(bs*0.92))
    gh = int(h*0.35)
    for y in range(gh):
        op = int(160*(y/gh)**0.75*alpha)
        d.rectangle([(0,h-gh+y),(w,h-gh+y+1)],fill=(0,0,0,op))
    yp = int(h*0.70)
    for ln in [l for l in value.split("\n") if l.strip()][:4]:
        d.text((int(w*0.07),yp),ln,font=f,fill=(255,255,255,int(250*alpha)),
               stroke_width=3,stroke_fill=(0,0,0,int(180*alpha)),anchor="lt")
        yp += int(bs*1.3)
    return c

def _layer_cta(w,h,cta,comment_cta,scheme,alpha=1.0):
    if not PIL_OK: return None
    c = Image.new("RGBA",(w,h),(0,0,0,0)); d = ImageDraw.Draw(c)
    bs = int(h*0.05); fc = _font(int(bs*1.1)); fs = _font(int(bs*0.82))
    d.rectangle([(0,0),(w,h)],fill=(0,0,0,int(145*alpha)))
    cy = int(h*0.41)
    d.text((w//2,cy),cta,font=fc,fill=(255,230,0,int(255*alpha)),
           stroke_width=5,stroke_fill=(0,0,0,int(230*alpha)),anchor="mt")
    cy += int(bs*1.6)
    d.text((w//2,cy),comment_cta,font=fs,fill=(255,255,255,int(250*alpha)),
           stroke_width=3,stroke_fill=(0,0,0,int(200*alpha)),anchor="mt")
    return c

def _save_png(img,path:Path):
    if img: img.save(str(path),"PNG"); return True
    return False

def apply_text_overlay(
    video_path: Path, product_name: str, price: str,
    value_stack: str, cta: str, comment_cta: str, badge: str,
    category: str = "fashion", gender: str = "women",
    output_path: Optional[Path] = None,
) -> Path:
    if output_path is None:
        output_path = Path(tempfile.mktemp(suffix="_ov.mp4"))
    w, h, dur = _vinfo(video_path)
    sc = _scheme(category, gender)

    if not PIL_OK:
        shutil.copy2(video_path, output_path); return output_path

    tmp_dir = Path(tempfile.mkdtemp())
    layers = {
        "hook":    (0,    2.5,  _layer_hook(w,h,product_name,sc)),
        "product": (2.5,  6.0,  _layer_product(w,h,product_name,price,badge,sc)),
        "value":   (6.0,  10.0, _layer_value(w,h,value_stack)),
        "cta":     (10.0, 13.0, _layer_cta(w,h,cta,comment_cta,sc)),
    }
    saved = {}
    for name,(ts,te,img) in layers.items():
        p = tmp_dir/f"{name}.png"
        if _save_png(img,p): saved[name]=(ts,te,str(p))

    if not saved:
        shutil.copy2(video_path, output_path)
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return output_path

    inputs = ["-i", str(video_path)]
    filters = []; prev = "0:v"; idx = 1
    for name,(ts,te,p) in saved.items():
        inputs += ["-i", p]
        out_l = f"v{idx}"
        filters.append(f"[{prev}][{idx}:v]overlay=0:0:enable='between(t,{ts},{te})'[{out_l}]")
        prev = out_l; idx += 1

    cmd = (["ffmpeg","-y"] + inputs +
           ["-filter_complex",";".join(filters),
            "-map",f"[{prev}]","-map","0:a?",
            "-c:v","libx264","-preset","fast","-crf","22",
            "-c:a","aac","-b:a","128k",str(output_path)])
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        logger.info(f"✅ Overlay done: {output_path}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Overlay fail: {e.stderr.decode()[:200]}")
        shutil.copy2(video_path, output_path)
    shutil.rmtree(tmp_dir, ignore_errors=True)
    return output_path
