"""
pipeline/video_composer.py — Professional Multi-Scene Video Composer
=====================================================================
Tạo video affiliate chuyên nghiệp từ:
  - Ảnh sản phẩm (đã tách nền)
  - Ảnh try-on (model mặc SP)
  - Script + giọng TTS
  - Background AI

Kỹ thuật quay chuyên nghiệp:
  - Ken Burns zoom & pan
  - Macro close-up (cận cảnh chi tiết)
  - Split-screen before/after
  - Talking head overlay
  - Dynamic transitions
  - Text overlay + caption
  - Nhạc nền fade in/out
"""
import logging, os, random, tempfile
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageEnhance

logger = logging.getLogger("VideoComposer")

# ─── Video specs ──────────────────────────────────────────────────────────────
VIDEO_W, VIDEO_H = 1080, 1920   # TikTok 9:16
FPS              = 30


# ══════════════════════════════════════════════════════════════════════════════
# SCENE RENDERERS — Mỗi loại cảnh có cách render khác nhau
# ══════════════════════════════════════════════════════════════════════════════

def render_hook_scene(
    product_img: Image.Image,
    tryon_img: Optional[Image.Image],
    bg_img: Image.Image,
    text: str,
    duration: float,
    font_bold,
    font_regular,
    color_accent: str = "#FF4D4D",
) -> list:
    """HOOK: Zoom in nhanh + text lớn giật eye-catching."""
    frames = []
    n      = int(duration * FPS)
    size   = (VIDEO_W, VIDEO_H)

    for i in range(n):
        t     = i / n
        frame = bg_img.copy().convert("RGBA")

        # Hiệu ứng zoom in nhanh (1.0 → 1.15 trong 0.5s đầu, giữ nguyên)
        zoom  = 1.0 + min(t * 2, 1.0) * 0.12
        frame = _zoom_frame(frame, zoom)

        # Overlay sản phẩm với fade in
        alpha = min(t * 3, 1.0)
        if tryon_img:
            _paste_centered(frame, tryon_img, scale=0.75,
                            y_offset=int(VIDEO_H * 0.05), alpha=alpha)
        else:
            _paste_centered(frame, product_img, scale=0.65,
                            y_offset=int(VIDEO_H * 0.12), alpha=alpha)

        # Text hook — fade in sau 0.3s
        if t > 0.3:
            text_alpha = min((t - 0.3) * 5, 1.0)
            _draw_hook_text(frame, text, font_bold, color_accent, text_alpha)

        frames.append(np.array(frame.convert("RGB")))

    return frames


def render_unbox_scene(
    product_img: Image.Image,
    bg_img: Image.Image,
    text: str,
    duration: float,
    font_bold,
    font_regular,
    color_accent: str,
) -> list:
    """UNBOX: Pan từ trên xuống, reveal sản phẩm từ từ."""
    frames = []
    n      = int(duration * FPS)

    for i in range(n):
        t     = i / n
        frame = bg_img.copy().convert("RGBA")

        # Pan xuống chậm
        pan_y = int((1.0 - t) * VIDEO_H * 0.06)
        frame = _pan_frame(frame, pan_y=pan_y)

        # Product reveal từ trên xuống (wipe effect)
        reveal_h = int(t * VIDEO_H * 0.7)
        prod_masked = _mask_top(product_img, reveal_h)
        scale = 0.6 + t * 0.05
        _paste_centered(frame, prod_masked, scale=scale,
                        y_offset=int(VIDEO_H * 0.08))

        # Shimmer effect khi reveal xong
        if t > 0.8:
            _add_shimmer(frame, intensity=(t - 0.8) * 2)

        # Text
        _draw_subtitle(frame, text, font_regular, alpha=min(t * 2, 0.9))

        frames.append(np.array(frame.convert("RGB")))

    return frames


def render_detail_scene(
    product_img: Image.Image,
    bg_img: Image.Image,
    text: str,
    duration: float,
    font_bold,
    font_regular,
    color_accent: str,
    detail_zone: str = "center",   # center | top | bottom | left | right
) -> list:
    """DETAIL (MACRO): Zoom cực gần chi tiết sản phẩm — như reviewer chuyên nghiệp."""
    frames = []
    n      = int(duration * FPS)

    # Chọn vùng crop để zoom vào
    zones = {
        "center": (0.25, 0.25, 0.75, 0.75),
        "top":    (0.1,  0.0,  0.9,  0.5),
        "bottom": (0.1,  0.5,  0.9,  1.0),
        "left":   (0.0,  0.1,  0.5,  0.9),
        "right":  (0.5,  0.1,  1.0,  0.9),
    }
    crop_box = zones.get(detail_zone, zones["center"])

    # Crop và upscale product để tạo macro
    pw, ph = product_img.size
    cx1 = int(crop_box[0] * pw)
    cy1 = int(crop_box[1] * ph)
    cx2 = int(crop_box[2] * pw)
    cy2 = int(crop_box[3] * ph)
    macro_img = product_img.crop((cx1, cy1, cx2, cy2))

    # Sharpen để giả lập ống kính macro
    macro_img = macro_img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=180, threshold=2))
    macro_img = macro_img.resize((VIDEO_W, VIDEO_H), Image.LANCZOS)

    for i in range(n):
        t     = i / n
        frame = Image.new("RGBA", (VIDEO_W, VIDEO_H))

        # Blend: bg mờ + macro sản phẩm
        bg_blurred = bg_img.copy().filter(ImageFilter.GaussianBlur(radius=15)).convert("RGBA")
        bg_blurred.putalpha(180)
        frame.paste(bg_blurred, (0, 0))

        # Macro product — slow drift (micro pan)
        drift_x = int(np.sin(t * np.pi) * 30)
        drift_y = int(t * 20)
        zoomed  = macro_img.convert("RGBA")
        # Tạo slight zoom in suốt cảnh
        zoom_scale = 1.0 + t * 0.08
        zoomed = _zoom_pil(zoomed, zoom_scale)
        x_off  = (VIDEO_W - zoomed.width)  // 2 + drift_x
        y_off  = (VIDEO_H - zoomed.height) // 2 + drift_y
        frame.paste(zoomed, (x_off, y_off), zoomed)

        # Vignette overlay (tạo cảm giác ống kính)
        _add_vignette(frame)

        # Focus ring animation
        if 0.2 < t < 0.5:
            _draw_focus_ring(frame, alpha=(t - 0.2) * 5)

        # Text
        _draw_detail_label(frame, text, font_regular, color_accent,
                           alpha=min((t - 0.1) * 3, 0.95))

        frames.append(np.array(frame.convert("RGB")))

    return frames


def render_wearing_scene(
    tryon_img: Image.Image,
    bg_img: Image.Image,
    text: str,
    duration: float,
    font_bold,
    font_regular,
    color_accent: str,
) -> list:
    """WEARING: Model mặc sản phẩm — medium shot với slow walk pan."""
    frames = []
    n      = int(duration * FPS)

    for i in range(n):
        t     = i / n
        frame = bg_img.copy().convert("RGBA")

        # Slow zoom out (wide → medium) + slight pan
        zoom  = 1.08 - t * 0.08
        frame = _zoom_frame(frame, zoom)

        # Pan horizontal nhẹ (giả lập camera theo người)
        pan_x = int(np.sin(t * np.pi * 0.7) * 25)
        frame = _pan_frame(frame, pan_x=pan_x)

        # Model
        scale = 0.78 + t * 0.03
        _paste_centered(frame, tryon_img, scale=scale,
                        y_offset=int(VIDEO_H * 0.02))

        # Breathing effect (scale micro)
        breath = 1.0 + np.sin(t * np.pi * 4) * 0.004
        _paste_centered(frame, tryon_img,
                        scale=scale * breath,
                        y_offset=int(VIDEO_H * 0.02))

        # Text overlay phía dưới
        _draw_subtitle(frame, text, font_regular,
                       position="bottom", alpha=min(t * 2, 0.9))

        frames.append(np.array(frame.convert("RGB")))

    return frames


def render_review_scene(
    tryon_img: Image.Image,
    bg_img: Image.Image,
    text: str,
    duration: float,
    font_bold,
    font_regular,
    color_accent: str,
) -> list:
    """REVIEW/TALKING HEAD: Medium close-up, stable, subtitle như interview."""
    frames = []
    n      = int(duration * FPS)

    for i in range(n):
        t     = i / n
        frame = bg_img.copy().convert("RGBA")

        # Stable shot — zoom vừa phải (talking head)
        zoom = 1.05 + np.sin(t * np.pi * 0.3) * 0.01  # Micro breathing
        frame = _zoom_frame(frame, zoom)

        # Model — upper half focus
        _paste_centered(frame, tryon_img, scale=0.80,
                        y_offset=int(VIDEO_H * 0.01))

        # Dark gradient bottom để text rõ
        _add_bottom_gradient(frame, height=int(VIDEO_H * 0.3))

        # Subtitle style text (giống Netflix)
        _draw_netflix_subtitle(frame, text, font_regular, alpha=0.97)

        # Speaker indicator dot (blink)
        if int(t * 4) % 2 == 0:
            _draw_speaker_dot(frame, color_accent)

        frames.append(np.array(frame.convert("RGB")))

    return frames


def render_cta_scene(
    product_img: Image.Image,
    tryon_img: Optional[Image.Image],
    bg_img: Image.Image,
    text: str,
    price: str,
    duration: float,
    font_bold,
    font_regular,
    color_accent: str,
) -> list:
    """CTA: Bounce animation + giá lớn + nút mua."""
    frames = []
    n      = int(duration * FPS)

    for i in range(n):
        t     = i / n
        frame = bg_img.copy().convert("RGBA")

        # BG mờ
        bg_blur = bg_img.copy().filter(ImageFilter.GaussianBlur(8)).convert("RGBA")
        bg_blur.putalpha(200)
        frame.paste(bg_blur, (0, 0), bg_blur)

        # Product bounce
        bounce_y = int(abs(np.sin(t * np.pi * 2)) * 20)
        img_to_show = tryon_img if tryon_img else product_img
        scale = 0.55 + abs(np.sin(t * np.pi * 1.5)) * 0.02
        _paste_centered(frame, img_to_show, scale=scale,
                        y_offset=int(VIDEO_H * 0.05) - bounce_y)

        # Giá lớn
        _draw_price_badge(frame, price, font_bold, color_accent,
                          alpha=min(t * 3, 1.0))

        # CTA text
        _draw_cta_button(frame, "🛒 Đặt ngay — Freeship", font_bold,
                         alpha=min((t - 0.2) * 4, 1.0))

        # Arrow animation
        if t > 0.4:
            _draw_arrow(frame, t, color_accent)

        frames.append(np.array(frame.convert("RGB")))

    return frames


def render_social_proof_scene(
    product_img: Image.Image,
    bg_img: Image.Image,
    text: str,
    duration: float,
    font_bold,
    font_regular,
    color_accent: str,
) -> list:
    """SOCIAL PROOF: Text cards với counter animation."""
    frames = []
    n      = int(duration * FPS)

    for i in range(n):
        t     = i / n
        frame = bg_img.copy().convert("RGBA")
        bg_blur = bg_img.copy().filter(ImageFilter.GaussianBlur(20)).convert("RGBA")
        bg_blur.putalpha(210)
        frame.paste(bg_blur, (0, 0), bg_blur)

        # Product nhỏ phía trên
        _paste_centered(frame, product_img, scale=0.4,
                        y_offset=int(VIDEO_H * 0.08),
                        alpha=min(t * 2, 1.0))

        # Social proof card slide in
        slide_x = int((1.0 - min(t * 3, 1.0)) * VIDEO_W)
        _draw_social_card(frame, text, font_bold, font_regular,
                          x_offset=slide_x, alpha=min(t * 3, 1.0))

        frames.append(np.array(frame.convert("RGB")))

    return frames


# ══════════════════════════════════════════════════════════════════════════════
# TRANSITION EFFECTS
# ══════════════════════════════════════════════════════════════════════════════

def make_transition(frame_a: np.ndarray, frame_b: np.ndarray,
                    style: str = "fade", n_frames: int = 9) -> list:
    """Tạo transition giữa 2 cảnh."""
    frames = []
    for i in range(n_frames):
        t = i / n_frames
        if style == "fade":
            blended = (frame_a * (1 - t) + frame_b * t).astype(np.uint8)
        elif style == "wipe_left":
            blended = frame_a.copy()
            cut_x   = int(t * VIDEO_W)
            blended[:, :cut_x] = frame_b[:, :cut_x]
        elif style == "zoom_fade":
            zoom  = 1.0 + t * 0.05
            zoomed = _zoom_np(frame_a, zoom)
            blended = (zoomed * (1 - t) + frame_b * t).astype(np.uint8)
        else:
            blended = (frame_a * (1 - t) + frame_b * t).astype(np.uint8)
        frames.append(blended)
    return frames


# ══════════════════════════════════════════════════════════════════════════════
# MAIN COMPOSER
# ══════════════════════════════════════════════════════════════════════════════

def compose_video(
    scenes_data: list,          # Từ script_generator VideoScript.scenes
    product_img_pil: Image.Image,
    tryon_img_pil: Optional[Image.Image],
    bg_img_pil: Image.Image,
    audio_path: str,
    drive_root: Path,
    product_name: str,
    price: str,
    color_accent: str = "#FF4D4D",
    progress_cb=None,
) -> Path:
    """
    Compose toàn bộ video từ các scenes.
    Returns: Path to final MP4.
    """
    from moviepy.editor import (ImageSequenceClip, AudioFileClip,
                                 concatenate_videoclips, CompositeAudioClip)

    def pb(msg):
        if progress_cb: progress_cb(msg)

    # ── Load fonts ─────────────────────────────────────────────────────────
    font_bold    = _load_font(drive_root, "Montserrat-Bold.ttf", 52)
    font_bold_lg = _load_font(drive_root, "Montserrat-ExtraBold.ttf", 72)
    font_regular = _load_font(drive_root, "BeVietnamPro-Bold.ttf", 38)

    # ── Prepare images ─────────────────────────────────────────────────────
    size   = (VIDEO_W, VIDEO_H)
    bg     = _fit_image(bg_img_pil, size)
    prod   = _fit_image(product_img_pil, (int(VIDEO_W * 0.7), int(VIDEO_H * 0.65)))
    tryon  = _fit_image(tryon_img_pil, (int(VIDEO_W * 0.85), VIDEO_H)) \
             if tryon_img_pil else None

    # ── Render từng scene ──────────────────────────────────────────────────
    pb("🎬 Render scenes...")
    all_frames    = []
    detail_zones  = ["center", "top", "bottom", "left", "right"]
    prev_frames   = None
    transitions   = ["fade", "zoom_fade", "wipe_left", "fade"]

    scene_renderers = {
        "hook":          lambda s: render_hook_scene(
                             prod, tryon, bg, s["text"],
                             s["duration_hint"], font_bold_lg, font_regular, color_accent),
        "unbox":         lambda s: render_unbox_scene(
                             prod, bg, s["text"],
                             s["duration_hint"], font_bold, font_regular, color_accent),
        "detail":        lambda s, z=None: render_detail_scene(
                             prod, bg, s["text"],
                             s["duration_hint"], font_bold, font_regular, color_accent,
                             z or "center"),
        "wearing":       lambda s: render_wearing_scene(
                             tryon or prod, bg, s["text"],
                             s["duration_hint"], font_bold, font_regular, color_accent),
        "review":        lambda s: render_review_scene(
                             tryon or prod, bg, s["text"],
                             s["duration_hint"], font_bold, font_regular, color_accent),
        "social_proof":  lambda s: render_social_proof_scene(
                             prod, bg, s["text"],
                             s["duration_hint"], font_bold, font_regular, color_accent),
        "cta":           lambda s: render_cta_scene(
                             prod, tryon, bg, s["text"], price,
                             s["duration_hint"], font_bold_lg, font_regular, color_accent),
        "transformation": lambda s: render_wearing_scene(
                             tryon or prod, bg, s["text"],
                             s["duration_hint"], font_bold, font_regular, color_accent),
        "identity":      lambda s: render_review_scene(
                             tryon or prod, bg, s["text"],
                             s["duration_hint"], font_bold, font_regular, color_accent),
        "urgency":       lambda s: render_social_proof_scene(
                             prod, bg, s["text"],
                             s["duration_hint"], font_bold, font_regular, color_accent),
        "loop":          lambda s: render_hook_scene(
                             prod, tryon, bg, s["text"],
                             s["duration_hint"], font_bold_lg, font_regular, color_accent),
    }

    detail_idx = 0
    trans_idx  = 0

    for scene in scenes_data:
        scene_type = scene["scene_type"]
        pb(f"   🎞️  Render: {scene_type} ({scene['duration_hint']:.1f}s)")

        if scene_type == "detail":
            zone   = detail_zones[detail_idx % len(detail_zones)]
            frames = render_detail_scene(
                prod, bg, scene["text"],
                scene["duration_hint"], font_bold, font_regular, color_accent, zone)
            detail_idx += 1
        elif scene_type in scene_renderers:
            frames = scene_renderers[scene_type](scene)
        else:
            frames = render_review_scene(
                tryon or prod, bg, scene["text"],
                scene["duration_hint"], font_bold, font_regular, color_accent)

        # Thêm transition
        if prev_frames and len(prev_frames) > 0:
            trans_style = transitions[trans_idx % len(transitions)]
            trans_frames = make_transition(
                prev_frames[-1], frames[0], trans_style, n_frames=8)
            all_frames.extend(trans_frames)
            trans_idx += 1

        all_frames.extend(frames)
        prev_frames = frames

    pb(f"📼 Render {len(all_frames)} frames ({len(all_frames)/FPS:.1f}s)...")

    # ── Build video clip ───────────────────────────────────────────────────
    video_clip = ImageSequenceClip(all_frames, fps=FPS)

    # ── Add audio ──────────────────────────────────────────────────────────
    if audio_path and os.path.exists(audio_path):
        pb("🔊 Mix audio...")
        voice_clip = AudioFileClip(audio_path)

        # Lặp lại audio nếu video dài hơn TTS
        if video_clip.duration > voice_clip.duration:
            loops = int(video_clip.duration / voice_clip.duration) + 1
            from moviepy.audio.AudioClip import concatenate_audioclips
            voice_clip = concatenate_audioclips([voice_clip] * loops)
        voice_clip = voice_clip.subclip(0, video_clip.duration)

        # Nhạc nền
        music_path = _get_background_music(drive_root)
        if music_path:
            music_clip  = AudioFileClip(music_path).volumex(0.25)
            if music_clip.duration < video_clip.duration:
                loops = int(video_clip.duration / music_clip.duration) + 1
                from moviepy.audio.AudioClip import concatenate_audioclips
                music_clip = concatenate_audioclips([music_clip] * loops)
            music_clip = music_clip.subclip(0, video_clip.duration)
            audio_mix  = CompositeAudioClip([voice_clip, music_clip])
        else:
            audio_mix = voice_clip

        video_clip = video_clip.set_audio(audio_mix)

    # ── Export ─────────────────────────────────────────────────────────────
    pb("💾 Xuất file MP4...")
    out_dir  = drive_root / "outputs" / "videos"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{product_name.replace(' ','_')[:30]}_{_ts()}.mp4"

    video_clip.write_videofile(
        str(out_path),
        fps=FPS,
        codec="libx264",
        audio_codec="aac",
        bitrate="4000k",       # High quality
        audio_bitrate="192k",
        ffmpeg_params=[
            "-crf", "18",      # Chất lượng cao (0=lossless, 23=default, 18=cao)
            "-preset", "slow", # Encode chậm hơn = nén tốt hơn
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",  # Web-optimized
        ],
        logger=None,
    )

    size_mb = out_path.stat().st_size / 1e6
    logger.info(f"✅ Video: {out_path} ({size_mb:.1f}MB, {len(all_frames)/FPS:.1f}s)")
    return out_path


# ══════════════════════════════════════════════════════════════════════════════
# DRAWING UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def _load_font(drive_root: Path, name: str, size: int):
    try:
        p = drive_root / "fonts" / name
        if p.exists():
            return ImageFont.truetype(str(p), size)
    except Exception:
        pass
    try:
        # Fallback system fonts
        for path in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                     "/content/drive/MyDrive/AffiliateStudio/fonts/Montserrat-Bold.ttf"]:
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
    except Exception:
        pass
    return ImageFont.load_default()


def _fit_image(img: Optional[Image.Image], size: tuple) -> Optional[Image.Image]:
    if img is None: return None
    img = img.convert("RGBA")
    img.thumbnail(size, Image.LANCZOS)
    return img


def _zoom_frame(frame: Image.Image, scale: float) -> Image.Image:
    w, h   = frame.size
    nw, nh = int(w * scale), int(h * scale)
    zoomed = frame.resize((nw, nh), Image.LANCZOS)
    x      = (nw - w) // 2
    y      = (nh - h) // 2
    return zoomed.crop((x, y, x + w, y + h))


def _zoom_pil(img: Image.Image, scale: float) -> Image.Image:
    nw = int(img.width  * scale)
    nh = int(img.height * scale)
    return img.resize((nw, nh), Image.LANCZOS)


def _pan_frame(frame: Image.Image, pan_x: int = 0, pan_y: int = 0) -> Image.Image:
    w, h   = frame.size
    canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    canvas.paste(frame, (pan_x, pan_y))
    return canvas


def _zoom_np(arr: np.ndarray, scale: float) -> np.ndarray:
    h, w = arr.shape[:2]
    img  = Image.fromarray(arr)
    return np.array(_zoom_frame(img.convert("RGBA"), scale).convert("RGB"))


def _paste_centered(frame: Image.Image, img: Image.Image,
                    scale: float = 1.0, y_offset: int = 0, alpha: float = 1.0):
    if img is None: return
    tw = int(img.width  * scale)
    th = int(img.height * scale)
    img_scaled = img.resize((tw, th), Image.LANCZOS)
    if alpha < 1.0:
        r, g, b, a = img_scaled.split()
        a = a.point(lambda x: int(x * alpha))
        img_scaled = Image.merge("RGBA", (r, g, b, a))
    x = (frame.width  - tw) // 2
    y = (frame.height - th) // 2 + y_offset - int(frame.height * 0.05)
    frame.paste(img_scaled, (x, max(0, y)), img_scaled)


def _mask_top(img: Image.Image, reveal_h: int) -> Image.Image:
    result = img.convert("RGBA").copy()
    mask   = Image.new("L", img.size, 255)
    draw   = ImageDraw.Draw(mask)
    if reveal_h < img.height:
        draw.rectangle([0, reveal_h, img.width, img.height], fill=0)
    result.putalpha(mask)
    return result


def _add_shimmer(frame: Image.Image, intensity: float = 0.5):
    enhancer = ImageEnhance.Brightness(frame)
    shimmer  = enhancer.enhance(1.0 + 0.15 * intensity * abs(np.sin(intensity * 10)))
    frame.paste(shimmer, (0, 0))


def _add_vignette(frame: Image.Image):
    vignette = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw     = ImageDraw.Draw(vignette)
    cx, cy   = frame.width // 2, frame.height // 2
    for r in range(min(cx, cy), 0, -2):
        alpha = int((1 - r / min(cx, cy)) * 90)
        draw.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(0, 0, 0, alpha))
    frame.paste(vignette, (0, 0), vignette)


def _add_bottom_gradient(frame: Image.Image, height: int):
    gradient = Image.new("RGBA", (frame.width, height), (0, 0, 0, 0))
    draw     = ImageDraw.Draw(gradient)
    for y in range(height):
        alpha = int(200 * y / height)
        draw.line([(0, y), (frame.width, y)], fill=(0, 0, 0, alpha))
    frame.paste(gradient, (0, frame.height - height), gradient)


def _draw_focus_ring(frame: Image.Image, alpha: float = 1.0):
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)
    cx, cy  = frame.width // 2, frame.height // 2
    r = 120
    a = int(200 * alpha)
    draw.ellipse([cx-r, cy-r, cx+r, cy+r], outline=(255, 255, 255, a), width=3)
    frame.paste(overlay, (0, 0), overlay)


def _draw_hook_text(frame: Image.Image, text: str, font,
                    color_accent: str, alpha: float):
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)
    # Background card
    card_y  = int(frame.height * 0.72)
    card_h  = int(frame.height * 0.22)
    card_a  = int(180 * alpha)
    draw.rectangle([0, card_y, frame.width, card_y + card_h],
                   fill=(0, 0, 0, card_a))
    # Text
    lines   = _wrap_text(text, font, frame.width - 60)
    y       = card_y + 20
    for line in lines[:3]:
        _draw_text_shadow(draw, line, font, (frame.width - draw.textlength(line, font=font)) // 2,
                          y, color_accent, alpha)
        _, lh = _text_size(draw, line, font)
        y += lh + 8
    frame.paste(overlay, (0, 0), overlay)


def _draw_subtitle(frame: Image.Image, text: str, font,
                   position: str = "bottom", alpha: float = 0.9):
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)
    lines   = _wrap_text(text, font, frame.width - 80)
    total_h = sum(_text_size(draw, l, font)[1] + 6 for l in lines)
    if position == "bottom":
        y = frame.height - total_h - 80
    else:
        y = 40
    bg_a = int(160 * alpha)
    draw.rectangle([20, y - 12, frame.width - 20, y + total_h + 12],
                   fill=(0, 0, 0, bg_a), radius=12)
    for line in lines:
        tw, th = _text_size(draw, line, font)
        _draw_text_shadow(draw, line, font, (frame.width - tw) // 2, y,
                          (255, 255, 255), alpha)
        y += th + 6
    frame.paste(overlay, (0, 0), overlay)


def _draw_netflix_subtitle(frame: Image.Image, text: str, font, alpha: float):
    """Netflix-style subtitle ở giữa-dưới màn hình."""
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)
    lines   = _wrap_text(text, font, frame.width - 60)[-3:]
    total_h = sum(_text_size(draw, l, font)[1] + 5 for l in lines)
    y       = frame.height - total_h - 100
    for line in lines:
        tw, th = _text_size(draw, line, font)
        x      = (frame.width - tw) // 2
        # Text shadow cho readability
        for dx, dy in [(-2, 2), (2, 2), (-2, -2), (2, -2)]:
            draw.text((x + dx, y + dy), line, font=font,
                      fill=(0, 0, 0, int(220 * alpha)))
        draw.text((x, y), line, font=font,
                  fill=(255, 255, 255, int(250 * alpha)))
        y += th + 5
    frame.paste(overlay, (0, 0), overlay)


def _draw_detail_label(frame: Image.Image, text: str, font,
                       color_accent: str, alpha: float):
    if alpha <= 0: return
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)
    short   = text[:60] + "..." if len(text) > 60 else text
    tw, th  = _text_size(draw, short, font)
    x       = (frame.width - tw) // 2
    y       = frame.height - th - 60
    draw.rectangle([x - 20, y - 10, x + tw + 20, y + th + 10],
                   fill=(0, 0, 0, int(160 * alpha)), radius=8)
    draw.text((x, y), short, font=font,
              fill=(*_hex_to_rgb(color_accent), int(255 * alpha)))
    frame.paste(overlay, (0, 0), overlay)


def _draw_price_badge(frame: Image.Image, price: str, font,
                      color_accent: str, alpha: float):
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)
    text    = f"💰 {price}"
    tw, th  = _text_size(draw, text, font)
    x       = (frame.width - tw - 40) // 2
    y       = int(frame.height * 0.68)
    r, g, b = _hex_to_rgb(color_accent)
    draw.rectangle([x, y, x + tw + 40, y + th + 20],
                   fill=(r, g, b, int(230 * alpha)), radius=12)
    draw.text((x + 20, y + 10), text, font=font,
              fill=(255, 255, 255, int(255 * alpha)))
    frame.paste(overlay, (0, 0), overlay)


def _draw_cta_button(frame: Image.Image, text: str, font, alpha: float):
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)
    tw, th  = _text_size(draw, text, font)
    x       = (frame.width - tw - 60) // 2
    y       = int(frame.height * 0.80)
    draw.rectangle([x, y, x + tw + 60, y + th + 24],
                   fill=(255, 255, 255, int(230 * alpha)), radius=16)
    draw.text((x + 30, y + 12), text, font=font,
              fill=(30, 30, 30, int(255 * alpha)))
    frame.paste(overlay, (0, 0), overlay)


def _draw_arrow(frame: Image.Image, t: float, color_accent: str):
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)
    cy      = int(frame.height * 0.88)
    cx      = frame.width // 2
    offset  = int(abs(np.sin(t * np.pi * 3)) * 15)
    r, g, b = _hex_to_rgb(color_accent)
    draw.polygon([(cx - 20, cy + offset),
                  (cx + 20, cy + offset),
                  (cx, cy + 35 + offset)],
                 fill=(r, g, b, 200))
    frame.paste(overlay, (0, 0), overlay)


def _draw_social_card(frame: Image.Image, text: str, font_bold, font_regular,
                      x_offset: int = 0, alpha: float = 1.0):
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)
    cw, ch  = frame.width - 80, 180
    cx      = 40 + x_offset
    cy      = int(frame.height * 0.55)
    draw.rounded_rectangle([cx, cy, cx + cw, cy + ch],
                           fill=(255, 255, 255, int(240 * alpha)), radius=20)
    short = text[:100]
    draw.text((cx + 20, cy + 20), short, font=font_regular,
              fill=(30, 30, 30, int(255 * alpha)))
    frame.paste(overlay, (0, 0), overlay)


def _draw_speaker_dot(frame: Image.Image, color_accent: str):
    overlay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)
    r, g, b = _hex_to_rgb(color_accent)
    draw.ellipse([40, frame.height - 130, 56, frame.height - 114],
                 fill=(r, g, b, 200))
    frame.paste(overlay, (0, 0), overlay)


def _draw_text_shadow(draw: ImageDraw.Draw, text: str, font,
                      x: float, y: float, color, alpha: float):
    if isinstance(color, str):
        r, g, b = _hex_to_rgb(color)
    elif len(color) == 3:
        r, g, b = color
    else:
        r, g, b = color[:3]
    # Shadow
    for dx, dy in [(-2, 2), (2, 2)]:
        draw.text((x + dx, y + dy), text, font=font,
                  fill=(0, 0, 0, int(180 * alpha)))
    draw.text((x, y), text, font=font, fill=(r, g, b, int(255 * alpha)))


def _wrap_text(text: str, font, max_width: int) -> list:
    words  = text.split()
    lines  = []
    curr   = ""
    dummy  = ImageDraw.Draw(Image.new("RGBA", (1, 1)))
    for word in words:
        test = (curr + " " + word).strip()
        if dummy.textlength(test, font=font) <= max_width:
            curr = test
        else:
            if curr: lines.append(curr)
            curr = word
    if curr: lines.append(curr)
    return lines


def _text_size(draw: ImageDraw.Draw, text: str, font) -> tuple:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _hex_to_rgb(hex_color: str) -> tuple:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def _get_background_music(drive_root: Path) -> Optional[str]:
    music_dir = drive_root / "music"
    if music_dir.exists():
        files = list(music_dir.glob("*.mp3")) + list(music_dir.glob("*.wav"))
        if files:
            return str(random.choice(files))
    return None


def _ts() -> str:
    import time
    return str(int(time.time()))[-6:]
