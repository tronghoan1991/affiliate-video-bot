"""
pipeline/text_overlay.py
Text overlay thông minh lên video: tên SP, giá, CTA, platform badge.
Dùng Pillow tạo overlay PNG → ghép vào video qua ffmpeg.
"""
import logging, shutil, subprocess, tempfile
from pathlib import Path
from typing import Tuple
from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("TextOverlay")


def _hex_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _font(size: int) -> ImageFont.FreeTypeFont:
    from config import Config
    for p in [Config.FONT_PATH, Config.FONT_FALLBACK,
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
        try:
            from pathlib import Path as P
            if P(p).exists():
                return ImageFont.truetype(p, size)
        except Exception:
            pass
    return ImageFont.load_default()


def _video_info(path: Path) -> Tuple[int, int, float]:
    import json
    r = subprocess.run([
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_streams", "-show_format", str(path),
    ], capture_output=True, text=True)
    d = json.loads(r.stdout)
    vs = next((s for s in d["streams"] if s["codec_type"] == "video"), d["streams"][0])
    dur = float(d["format"].get("duration", 5))
    return vs["width"], vs["height"], dur


def _draw_overlay(
    w: int, h: int,
    name: str, price: str, cta: str,
    style: str, platform: str,
    alpha: float = 1.0,
) -> Image.Image:
    from config import Config
    cfg  = Config.TEXT_STYLES.get(style, Config.TEXT_STYLES["tiktok"])
    fg   = _hex_rgb(cfg["fg"])   + (int(255 * alpha),)
    stk  = _hex_rgb(cfg["stroke"]) + (int(200 * alpha),)
    base = int(h * cfg["size"])

    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw   = ImageDraw.Draw(canvas)

    f_name  = _font(base)
    f_price = _font(int(base * 1.35))
    f_cta   = _font(int(base * 0.80))
    f_badge = _font(int(base * 0.65))

    gh = int(h * 0.32)
    for y in range(gh):
        op = int(170 * (y / gh) * alpha)
        draw.rectangle([(0, h - gh + y), (w, h - gh + y + 1)], fill=(0,0,0,op))

    margin = int(h * 0.18) if platform in ("tiktok", "both") else int(h * 0.10)
    cy = h - margin

    if cta:
        draw.text((w//2, cy), cta, font=f_cta, fill=fg,
                  stroke_width=2, stroke_fill=stk, anchor="mb")
        cy -= int(base * 1.5)

    if price:
        draw.text((w//2, cy), f"💰 {price}", font=f_price,
                  fill=_hex_rgb("#FF3333")+(int(255*alpha),),
                  stroke_width=3, stroke_fill=stk, anchor="mb")
        cy -= int(base * 1.7)

    if name:
        max_chars = max(16, int(w / (base * 0.62)))
        words, lines, cur = name.split(), [], ""
        for wd in words:
            if len(cur + wd) <= max_chars: cur += wd + " "
            else: lines.append(cur.strip()); cur = wd + " "
        if cur: lines.append(cur.strip())
        for ln in reversed(lines):
            draw.text((w//2, cy), ln, font=f_name, fill=fg,
                      stroke_width=2, stroke_fill=stk, anchor="mb")
            cy -= int(base * 1.3)

    if platform in ("shopee", "both"):
        bx, by = w - 15, int(h * 0.055)
        draw.rounded_rectangle(
            [(bx - 110, by - 6), (bx + 5, by + 32)],
            radius=12, fill=(255, 102, 51, int(210 * alpha)),
        )
        draw.text((bx - 52, by + 13), "🛒 Shopee",
                  font=f_badge, fill=(255,255,255,255), anchor="mm")

    return canvas


def add_text_overlay(
    input_path: Path,
    output_path: Path,
    product_name: str = "",
    product_price: str = "",
    garment_class: str = "",
    platform: str = "tiktok",
    style: str = "tiktok",
    cta: str = None,
) -> Path:
    if not product_name and not product_price:
        shutil.copy2(input_path, output_path)
        return output_path

    if cta is None:
        cta = _auto_cta(platform, garment_class)

    w, h, dur = _video_info(input_path)
    logger.info(f"TextOverlay | {w}×{h} | dur={dur:.1f}s | style={style}")

    overlay = _draw_overlay(w, h, product_name, product_price, cta, style, platform)
    tmp_png  = Path(tempfile.mktemp(suffix="_ov.png"))
    overlay.save(str(tmp_png), "PNG")

    fade = min(0.5, dur * 0.08)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run([
            "ffmpeg", "-y",
            "-i", str(input_path),
            "-i", str(tmp_png),
            "-filter_complex",
            f"[1:v]fade=in:st=0:d={fade}:alpha=1[ov];[0:v][ov]overlay=0:0",
            "-c:v", "libx264", "-crf", "17", "-preset", "fast",
            "-pix_fmt", "yuv420p", "-c:a", "copy", str(output_path),
        ], check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"ffmpeg overlay error: {e.stderr.decode()[:300]}")
        shutil.copy2(input_path, output_path)
    finally:
        tmp_png.unlink(missing_ok=True)

    return output_path


def _auto_cta(platform: str, garment: str) -> str:
    if platform == "shopee":
        return "🛒 Mua ngay trên Shopee ↗"
    cta_map = {
        "dress": "💃 Shop link bio 👆",
        "swimwear": "☀️ Link mua ở bio 👆",
        "ao dai": "🌸 Đặt hàng ngay 👆",
        "suit": "💼 Xem thêm tại bio 👆",
    }
    for k, v in cta_map.items():
        if k in garment.lower(): return v
    return "🛍️ Link mua hàng ở bio 👆"
