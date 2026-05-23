"""
pipeline/text_overlay.py — Text Overlay Engine v6 (2026)
=============================================================================
3-layer overlay theo timeline 15 giây:
  0s–2.5s  : Hook (top) — câu dừng scroll
  2.5s–6s  : Product + Price (center) — hiện sản phẩm
  6s–10s   : Value Stack (bottom) — freeship, đổi trả
  10s–13s  : CTA + Comment (full) — chốt đơn, tăng reach
  13s–15s  : Loop badge (corner) — seamless loop

Color scheme riêng theo gender:
  Women  : hồng → đỏ | Men: navy → xanh | Kids: vàng | Baby: pastel xanh
=============================================================================
"""
import json
import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger("TextOverlay")

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("Pillow chưa cài — text overlay bị giới hạn")


# ── Color Schemes ─────────────────────────────────────────────────────────────

_COLOR_SCHEMES = {
    "women":    {"hook_bg": (200, 20, 60),  "hook_text": (255, 255, 255), "badge": (255, 50, 100), "price": (255, 220, 0)},
    "men":      {"hook_bg": (20, 30, 100),  "hook_text": (255, 255, 255), "badge": (30, 100, 220), "price": (255, 220, 0)},
    "children": {"hook_bg": (255, 140, 0),  "hook_text": (255, 255, 255), "badge": (255, 80, 160), "price": (255, 240, 0)},
    "baby":     {"hook_bg": (100, 180, 240),"hook_text": (255, 255, 255), "badge": (180, 220, 255),"price": (255, 255, 200)},
    "unisex":   {"hook_bg": (140, 40, 200), "hook_text": (255, 255, 255), "badge": (200, 80, 255), "price": (255, 220, 0)},
}
_DEFAULT_SCHEME = _COLOR_SCHEMES["women"]


def _scheme(gender: str) -> dict:
    return _COLOR_SCHEMES.get(gender, _DEFAULT_SCHEME)


def _hex_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _get_font(size: int):
    if not PIL_AVAILABLE:
        return None
    try:
        from pipeline.drive_manager import drive_mgr
        font_path = drive_mgr.get_font_path("Montserrat-Bold.ttf")
        if font_path:
            return ImageFont.truetype(str(font_path), size)
    except Exception:
        pass
    fallback_paths = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for p in fallback_paths:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _video_info(path: Path) -> Tuple[int, int, float]:
    try:
        r = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", "-show_format", str(path)],
            capture_output=True, text=True
        )
        d = json.loads(r.stdout)
        vs = next((s for s in d["streams"] if s["codec_type"] == "video"), d["streams"][0])
        w, h = int(vs.get("width", 1080)), int(vs.get("height", 1920))
        dur = float(d["format"].get("duration", 15))
        return w, h, dur
    except Exception:
        return 1080, 1920, 15.0


def _wrap_text(text: str, max_chars: int) -> list:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if len(cur + w) <= max_chars:
            cur += w + " "
        else:
            if cur:
                lines.append(cur.strip())
            cur = w + " "
    if cur:
        lines.append(cur.strip())
    return lines or [text]


# ── Frame Generators ─────────────────────────────────────────────────────────

def _draw_hook_frame(w: int, h: int, text: str, subtext: str, scheme: dict, alpha: float = 1.0):
    """Vẽ layer hook phía trên màn hình."""
    if not PIL_AVAILABLE:
        return None
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    base_size = int(h * 0.056)
    f_main = _get_font(int(base_size * 1.1))
    f_sub  = _get_font(int(base_size * 0.72))

    grad_h = int(h * 0.28)
    for y in range(grad_h):
        op = int(175 * (1 - y / grad_h) ** 0.75 * alpha)
        draw.rectangle([(0, y), (w, y + 1)], fill=(0, 0, 0, op))

    y_pos = int(h * 0.045)
    for line in _wrap_text(text, max(14, int(w / (base_size * 0.6))))[:2]:
        draw.text(
            (w // 2, y_pos), line,
            font=f_main, fill=(*scheme["hook_text"], int(255 * alpha)),
            stroke_width=5, stroke_fill=(0, 0, 0, int(220 * alpha)), anchor="mt"
        )
        y_pos += int(base_size * 1.35)

    if subtext and alpha > 0.3:
        draw.text(
            (w // 2, y_pos), subtext,
            font=f_sub, fill=(255, 230, 80, int(230 * alpha)),
            stroke_width=3, stroke_fill=(0, 0, 0, int(180 * alpha)), anchor="mt"
        )
    return canvas


def _draw_product_frame(w: int, h: int, name: str, price: str, badge: str, scheme: dict, alpha: float = 1.0):
    """Vẽ layer tên sản phẩm + giá ở giữa."""
    if not PIL_AVAILABLE:
        return None
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    base = int(h * 0.052)
    f_name  = _get_font(int(base * 1.05))
    f_price = _get_font(int(base * 1.4))
    f_badge = _get_font(int(base * 0.72))

    cy = int(h * 0.38)

    # Badge nền
    bw = int(w * 0.52)
    bh = int(base * 1.3)
    bx = (w - bw) // 2
    for y in range(bh):
        op = int(210 * alpha)
        r_bg, g_bg, b_bg = scheme["badge"]
        draw.rectangle([(bx, cy + y), (bx + bw, cy + y + 1)], fill=(r_bg, g_bg, b_bg, op))

    draw.text((w // 2, cy + bh // 2), badge, font=f_badge,
              fill=(255, 255, 255, int(255 * alpha)), anchor="mm")
    cy += bh + int(base * 0.4)

    # Tên sản phẩm
    for line in _wrap_text(name, max(14, int(w / (base * 0.62))))[:2]:
        draw.text((w // 2, cy), line, font=f_name,
                  fill=(255, 255, 255, int(255 * alpha)),
                  stroke_width=4, stroke_fill=(0, 0, 0, int(200 * alpha)), anchor="mt")
        cy += int(base * 1.3)

    # Giá
    draw.text((w // 2, cy), f"💰 {price}", font=f_price,
              fill=(*scheme["price"], int(255 * alpha)),
              stroke_width=5, stroke_fill=(0, 0, 0, int(220 * alpha)), anchor="mt")

    return canvas


def _draw_value_frame(w: int, h: int, value_stack: str, alpha: float = 1.0):
    """Vẽ layer value stack phía dưới."""
    if not PIL_AVAILABLE:
        return None
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    base = int(h * 0.045)
    font = _get_font(int(base * 0.95))

    # Gradient dưới lên
    grad_h = int(h * 0.35)
    for y in range(grad_h):
        op = int(165 * (y / grad_h) ** 0.75 * alpha)
        draw.rectangle([(0, h - grad_h + y), (w, h - grad_h + y + 1)], fill=(0, 0, 0, op))

    lines = [ln for ln in value_stack.split("\n") if ln.strip()]
    y_pos = int(h * 0.70)
    for line in lines[:4]:
        draw.text((int(w * 0.08), y_pos), line, font=font,
                  fill=(255, 255, 255, int(250 * alpha)),
                  stroke_width=3, stroke_fill=(0, 0, 0, int(180 * alpha)), anchor="lt")
        y_pos += int(base * 1.3)
    return canvas


def _draw_cta_frame(w: int, h: int, cta: str, comment_cta: str, scheme: dict, alpha: float = 1.0):
    """Vẽ layer CTA chốt đơn."""
    if not PIL_AVAILABLE:
        return None
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    base = int(h * 0.05)
    f_cta  = _get_font(int(base * 1.1))
    f_comm = _get_font(int(base * 0.82))

    overlay_op = int(140 * alpha)
    draw.rectangle([(0, 0), (w, h)], fill=(0, 0, 0, overlay_op))

    cy = int(h * 0.42)
    draw.text((w // 2, cy), cta, font=f_cta,
              fill=(255, 230, 0, int(255 * alpha)),
              stroke_width=5, stroke_fill=(0, 0, 0, int(230 * alpha)), anchor="mt")
    cy += int(base * 1.6)
    draw.text((w // 2, cy), comment_cta, font=f_comm,
              fill=(255, 255, 255, int(250 * alpha)),
              stroke_width=3, stroke_fill=(0, 0, 0, int(200 * alpha)), anchor="mt")
    return canvas


def _frame_to_png(frame_img, path: Path):
    if frame_img:
        frame_img.save(str(path), "PNG")
        return True
    return False


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API — Apply overlay lên video
# ══════════════════════════════════════════════════════════════════════════════

def apply_text_overlay(
    video_path: Path,
    product_name: str,
    price: str,
    value_stack: str,
    cta: str,
    comment_cta: str,
    badge: str,
    gender: str = "women",
    output_path: Optional[Path] = None,
) -> Path:
    """
    Áp dụng text overlay 3 lớp lên video.
    Timeline: Hook(0-2.5s) → Product(2.5-6s) → Value(6-10s) → CTA(10-13s) → Loop(13-15s)
    """
    if output_path is None:
        output_path = Path(tempfile.mktemp(suffix="_overlay.mp4"))

    w, h, duration = _video_info(video_path)
    scheme = _scheme(gender)

    if not PIL_AVAILABLE:
        logger.warning("Pillow không có — bỏ qua text overlay, copy nguyên video")
        shutil.copy2(video_path, output_path)
        return output_path

    # Tạo các overlay image
    tmp_dir = Path(tempfile.mkdtemp())
    frames = {
        "hook":    _draw_hook_frame(w, h, product_name, "Xem ngay 👆", scheme),
        "product": _draw_product_frame(w, h, product_name, price, badge, scheme),
        "value":   _draw_value_frame(w, h, value_stack),
        "cta":     _draw_cta_frame(w, h, cta, comment_cta, scheme),
    }

    overlay_files = {}
    for name, frame in frames.items():
        p = tmp_dir / f"{name}.png"
        if _frame_to_png(frame, p):
            overlay_files[name] = str(p)

    # Compose với ffmpeg filter_complex
    filter_parts = []
    inputs = [f"-i {video_path}"]
    idx = 1

    timeline = [
        ("hook",    0,    2.5),
        ("product", 2.5,  6.0),
        ("value",   6.0,  10.0),
        ("cta",     10.0, 13.0),
    ]

    prev_label = "0:v"
    for layer_name, t_start, t_end in timeline:
        if layer_name in overlay_files:
            inputs.append(f"-i {overlay_files[layer_name]}")
            out_label = f"v{idx}"
            filter_parts.append(
                f"[{prev_label}][{idx}:v]overlay=0:0:enable='between(t,{t_start},{t_end})'[{out_label}]"
            )
            prev_label = out_label
            idx += 1

    if filter_parts:
        filter_complex = ";".join(filter_parts)
        cmd = (
            ["ffmpeg", "-y"]
            + " ".join(inputs).split()
            + ["-filter_complex", filter_complex,
               "-map", f"[{prev_label}]",
               "-map", "0:a?",
               "-c:v", "libx264", "-preset", "fast", "-crf", "22",
               "-c:a", "aac", "-b:a", "128k",
               str(output_path)]
        )
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            logger.info(f"✅ Text overlay xong: {output_path}")
        except subprocess.CalledProcessError as e:
            logger.error(f"ffmpeg overlay lỗi: {e.stderr.decode()[:300]}")
            shutil.copy2(video_path, output_path)
    else:
        shutil.copy2(video_path, output_path)

    shutil.rmtree(tmp_dir, ignore_errors=True)
    return output_path
