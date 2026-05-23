"""
pipeline/text_overlay.py — Text Overlay Engine v5 (2026)
3-layer overlay: Hook → Product Info → Value Stack + Comment CTA
Hỗ trợ color scheme riêng theo gender (women/men/kids/baby)
"""
import json, logging, shutil, subprocess, tempfile
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger("TextOverlay")


def _hex_rgb(h: str) -> Tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def _font(size: int) -> ImageFont.FreeTypeFont:
    try:
        from pipeline.drive_manager import drive_mgr
        p = drive_mgr.get_font_path("Montserrat-Bold.ttf")
        if p:
            return ImageFont.truetype(str(p), size)
    except Exception:
        pass
    for p in [
        "/content/affiliate-video-bot/assets/fonts/Montserrat-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]:
        if Path(p).exists():
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _video_info(path: Path) -> Tuple[int, int, float]:
    r = subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json",
                        "-show_streams", "-show_format", str(path)],
                       capture_output=True, text=True)
    d = json.loads(r.stdout)
    vs = next((s for s in d["streams"] if s["codec_type"] == "video"), d["streams"][0])
    return vs["width"], vs["height"], float(d["format"].get("duration", 15))


def _wrap(text: str, max_chars: int) -> list:
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


def _draw_hook(w, h, text, subtext="", alpha=1.0):
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    base = int(h * 0.062)
    f_hook = _font(int(base * 1.12))
    f_sub = _font(int(base * 0.75))
    gh = int(h * 0.30)
    for y in range(gh):
        op = int(170 * (1 - y/gh)**0.8 * alpha)
        draw.rectangle([(0, y), (w, y+1)], fill=(0, 0, 0, op))
    cy = int(h * 0.05)
    for line in _wrap(text, max(16, int(w/(base*0.62))))[:2]:
        draw.text((w//2, cy), line, font=f_hook, fill=(255, 255, 255, int(255*alpha)),
                  stroke_width=4, stroke_fill=(0, 0, 0, int(230*alpha)), anchor="mt")
        cy += int(base * 1.4)
    if subtext and alpha > 0.3:
        draw.text((w//2, cy), subtext, font=f_sub, fill=(255, 225, 80, int(230*alpha)),
                  stroke_width=2, stroke_fill=(0, 0, 0, int(180*alpha)), anchor="mt")
    return canvas


def _draw_badge(w, h, text, bg_color=(220, 38, 38), corner="right", alpha=1.0):
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    base = int(h * 0.042)
    f = _font(base)
    try:
        bbox = f.getbbox(text)
        tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
    except Exception:
        tw, th = len(text)*base//2, base
    px, py = int(base*0.85), int(base*0.5)
    bw, bh = tw+px*2, th+py*2
    x0 = w-bw-int(w*0.025) if corner == "right" else int(w*0.025)
    y0 = int(h * 0.025)
    draw.rounded_rectangle([(x0, y0), (x0+bw, y0+bh)], radius=int(bh*0.4),
                            fill=(*bg_color, int(235*alpha)))
    draw.rounded_rectangle([(x0, y0), (x0+bw, y0+bh)], radius=int(bh*0.4),
                            outline=(255, 255, 255, int(180*alpha)), width=2)
    draw.text((x0+px, y0+py), text, font=f, fill=(255, 255, 255, int(255*alpha)))
    return canvas


def _draw_value_stack(w, h, text, name_color=(255, 215, 0), alpha=1.0):
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    base = int(h * 0.038)
    f = _font(base)
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines:
        return canvas
    try:
        max_w = max(f.getbbox(l)[2]-f.getbbox(l)[0] for l in lines)
    except Exception:
        max_w = max(len(l) for l in lines)*base//2
    lh = int(base*1.5)
    total_h = lh*len(lines)+int(base*0.8)
    bw = max_w+int(base*2)
    bx, by = int(w*0.04), int(h*0.38)
    draw.rounded_rectangle([(bx, by), (bx+bw, by+total_h)], radius=int(base*0.6),
                            fill=(0, 0, 0, int(160*alpha)))
    draw.rectangle([(bx, by), (bx+4, by+total_h)], fill=(*name_color, int(220*alpha)))
    cy = by+int(base*0.4)
    for line in lines:
        draw.text((bx+int(base*0.7), cy), line, font=f, fill=(255, 255, 255, int(240*alpha)))
        cy += lh
    return canvas


def _draw_product_info(w, h, name, price, cta, comment_cta="", name_color=(255,215,0), platform="tiktok", alpha=1.0):
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    base = int(h * 0.052)
    f_name = _font(base)
    f_price = _font(int(base*1.5))
    f_cta = _font(int(base*0.80))
    f_comment = _font(int(base*0.70))
    gh = int(h*0.42)
    for y in range(gh):
        op = int(200*(y/gh)**0.7*alpha)
        draw.rectangle([(0, h-gh+y), (w, h-gh+y+1)], fill=(0, 0, 0, op))
    margin_bottom = int(h*0.21) if platform in ("tiktok","both") else int(h*0.10)
    cy = h-margin_bottom
    if comment_cta:
        draw.text((w//2, cy), comment_cta, font=f_comment, fill=(255,255,100,int(230*alpha)),
                  stroke_width=2, stroke_fill=(0,0,0,int(200*alpha)), anchor="mb")
        cy -= int(base*1.3)
    if cta:
        draw.text((w//2, cy), cta, font=f_cta, fill=(255,220,60,int(245*alpha)),
                  stroke_width=2, stroke_fill=(0,0,0,int(210*alpha)), anchor="mb")
        cy -= int(base*1.7)
    if price:
        draw.text((w//2, cy), f"💰 {price}", font=f_price, fill=(255,55,55,int(255*alpha)),
                  stroke_width=4, stroke_fill=(0,0,0,int(230*alpha)), anchor="mb")
        cy -= int(base*2.0)
    if name:
        for line in reversed(_wrap(name, max(14, int(w/(base*0.62))))[:2]):
            draw.text((w//2, cy), line, font=f_name, fill=(*name_color, int(255*alpha)),
                      stroke_width=3, stroke_fill=(0,0,0,int(220*alpha)), anchor="mb")
            cy -= int(base*1.35)
    return canvas


def _composite(layers):
    result = Image.new("RGBA", layers[0].size, (0, 0, 0, 0))
    for layer in layers:
        result = Image.alpha_composite(result, layer)
    return result


def add_text_overlay(
    input_path: Path, output_path: Path,
    product_name: str = "", product_price: str = "", garment_class: str = "",
    platform: str = "tiktok", style: str = "tiktok", cta: str = None,
    hook_text: str = "", hook_subtext: str = "",
    urgency_badge: str = "", social_proof: str = "",
    value_stack: str = "", comment_cta: str = "",
    gender: str = "women", color_scheme: dict = None,
) -> Path:
    if not product_name and not product_price:
        shutil.copy2(input_path, output_path)
        return output_path

    # Auto-fill if not provided
    if not hook_text or not urgency_badge:
        try:
            from pipeline.viral_strategy import build_viral_content
            vc = build_viral_content(name=product_name, price=product_price,
                                     garment=f"{gender} {garment_class}", platform=platform)
            hook_text = hook_text or vc.hook_text
            hook_subtext = hook_subtext or vc.hook_subtext
            urgency_badge = urgency_badge or vc.urgency_badge
            social_proof = social_proof or vc.social_proof
            value_stack = value_stack or vc.value_stack
            comment_cta = comment_cta or vc.comment_cta
            if cta is None:
                cta = vc.cta_tiktok if platform != "shopee" else vc.cta_shopee
        except Exception as e:
            logger.warning(f"viral_strategy unavailable: {e}")
            if cta is None:
                cta = "🛍️ Link mua ở bio 👆"

    # Color scheme by gender
    if color_scheme is None:
        color_scheme = {
            "women":    (255, 215, 0),    # Gold
            "men":      (96, 165, 250),   # Blue
            "children": (251, 146, 60),   # Orange
            "baby":     (249, 168, 212),  # Pink
            "unisex":   (255, 215, 0),    # Gold
        }.get(gender, (255, 215, 0))
    else:
        nc = color_scheme.get("name", "#FFD700")
        color_scheme = _hex_rgb(nc)

    name_color = color_scheme if isinstance(color_scheme, tuple) else (255, 215, 0)

    w, h, dur = _video_info(input_path)
    logger.info(f"TextOverlay v5 | {w}×{h} | {dur:.1f}s | {gender} | {platform}")

    hook_end    = min(2.5, dur * 0.17)
    value_start = min(6.0, dur * 0.4)
    fade = 0.5

    badge_r  = _draw_badge(w, h, urgency_badge, corner="right")
    badge_l  = _draw_badge(w, h, social_proof, bg_color=(22, 163, 74), corner="left")
    hook_l   = _draw_hook(w, h, hook_text, hook_subtext)
    info_l   = _draw_product_info(w, h, product_name, product_price, cta,
                                  comment_cta=comment_cta, name_color=name_color, platform=platform)
    val_l    = _draw_value_stack(w, h, value_stack, name_color=name_color)

    frame_hook  = _composite([badge_r, badge_l, hook_l])
    frame_info  = _composite([badge_r, badge_l, info_l])
    frame_val   = _composite([badge_r, badge_l, info_l, val_l])

    tmp_a = Path(tempfile.mktemp(suffix="_hook.png"))
    tmp_b = Path(tempfile.mktemp(suffix="_info.png"))
    tmp_c = Path(tempfile.mktemp(suffix="_val.png"))
    frame_hook.save(str(tmp_a)); frame_info.save(str(tmp_b)); frame_val.save(str(tmp_c))
    output_path.parent.mkdir(parents=True, exist_ok=True)

    filter_complex = (
        f"[1:v]fade=in:st=0:d=0.3:alpha=1,fade=out:st={hook_end}:d={fade}:alpha=1[hook];"
        f"[2:v]fade=in:st={hook_end}:d={fade}:alpha=1,fade=out:st={value_start}:d={fade}:alpha=1[info];"
        f"[3:v]fade=in:st={value_start}:d={fade}:alpha=1[val];"
        f"[0:v][hook]overlay=0:0[v1];[v1][info]overlay=0:0[v2];[v2][val]overlay=0:0"
    )
    try:
        subprocess.run([
            "ffmpeg", "-y",
            "-i", str(input_path), "-i", str(tmp_a), "-i", str(tmp_b), "-i", str(tmp_c),
            "-filter_complex", filter_complex,
            "-c:v", "libx264", "-crf", "16", "-preset", "fast", "-pix_fmt", "yuv420p", "-c:a", "copy",
            str(output_path),
        ], check=True, capture_output=True)
    except subprocess.CalledProcessError:
        # Fallback 2-phase
        try:
            f2 = (f"[1:v]fade=in:st=0:d=0.3:alpha=1,fade=out:st={hook_end}:d={fade}:alpha=1[hook];"
                  f"[2:v]fade=in:st={hook_end}:d={fade}:alpha=1[info];"
                  f"[0:v][hook]overlay=0:0[v1];[v1][info]overlay=0:0")
            subprocess.run([
                "ffmpeg", "-y", "-i", str(input_path), "-i", str(tmp_a), "-i", str(tmp_b),
                "-filter_complex", f2, "-c:v", "libx264", "-crf", "17", "-preset", "fast",
                "-pix_fmt", "yuv420p", "-c:a", "copy", str(output_path),
            ], check=True, capture_output=True)
        except Exception:
            shutil.copy2(input_path, output_path)
    finally:
        for t in [tmp_a, tmp_b, tmp_c]:
            t.unlink(missing_ok=True)
    return output_path
