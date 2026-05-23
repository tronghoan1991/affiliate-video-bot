"""
pipeline/video_engine.py — AI Video Generation Engine v6 (2026)
=============================================================================
Công cụ AI sinh video miễn phí — ưu tiên theo thứ tự:

  1. Wan2.1-I2V-14B-480P (Alibaba) — TỐT NHẤT, miễn phí HuggingFace
     → Image-to-Video, chất lượng cinematic, ~12GB VRAM
  2. CogVideoX-5B (Tsinghua) — nhanh hơn, miễn phí HuggingFace
     → Text-to-Video, 8GB VRAM
  3. AnimateDiff XL + SDXL — nhẹ nhất, 6GB VRAM
     → Text-to-Video, dùng khi VRAM thấp
  4. Stable Video Diffusion (SVD) — ổn định, 8GB VRAM
  5. MoviePy only — không cần GPU, dùng ảnh tĩnh ghép slideshow
     → Fallback cuối cùng, chạy mọi nơi

Tất cả weights lưu Google Drive — không tải lại mỗi session.
Output 9:16 (1080×1920) hoặc (480×832) cho TikTok/Reels.
=============================================================================
"""
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger("VideoEngine")

# ── Settings ──────────────────────────────────────────────────────────────────
FPS           = 24
DURATION_SEC  = 15
LOOPS         = 3
WIDTH_HD      = 1080
HEIGHT_HD     = 1920
WIDTH_SD      = 480
HEIGHT_SD     = 832
STEPS_FAST    = 20
STEPS_QUALITY = 30
STEPS_BEST    = 50


# ══════════════════════════════════════════════════════════════════════════════
#  MODEL LOADER
# ══════════════════════════════════════════════════════════════════════════════

def _get_model_path(name: str) -> Optional[str]:
    try:
        from pipeline.drive_manager import drive_mgr
        p = drive_mgr.get_model_path(name)
        if p:
            return str(p)
    except Exception:
        pass
    colab_paths = [
        f"/content/affiliate-video-bot/models/{name}",
        f"/content/models/{name}",
        f"/content/drive/MyDrive/AffiliateBot/models/{name}",
    ]
    for p in colab_paths:
        if Path(p).exists():
            return p
    return None


def download_model_to_drive(model_id: str, local_name: str) -> str:
    """Tải HuggingFace model về Drive lần đầu (sau đó load từ Drive)."""
    from pipeline.drive_manager import drive_mgr
    dest = str(drive_mgr.models_dir / local_name)
    if Path(dest).exists():
        logger.info(f"Model đã có: {local_name}")
        return dest
    logger.info(f"Đang tải {model_id} về Drive (~15 phút lần đầu)...")
    os.makedirs(dest, exist_ok=True)
    subprocess.run([
        "huggingface-cli", "download", model_id,
        "--local-dir", dest,
        "--local-dir-use-symlinks", "False"
    ], check=True)
    logger.info(f"✅ Model {model_id} đã lưu Drive")
    return dest


# ══════════════════════════════════════════════════════════════════════════════
#  ENGINE 1: Wan2.1-I2V (Image-to-Video — TỐTNHẤT)
# ══════════════════════════════════════════════════════════════════════════════

def _generate_wan21(
    prompt: str,
    image_path: Optional[str] = None,
    steps: int = STEPS_QUALITY,
    width: int = WIDTH_SD,
    height: int = HEIGHT_SD,
    num_frames: int = 81,
) -> Optional[Path]:
    """
    Wan2.1 Image-to-Video — chất lượng tốt nhất.
    Model: Wan-AI/Wan2.1-I2V-14B-480P (miễn phí HuggingFace)
    Cần ~12GB VRAM (T4 Colab đủ), thời gian ~3-5 phút.
    """
    try:
        import torch
        from diffusers import WanImageToVideoPipeline, AutoencoderKLWan
        from diffusers.utils import export_to_video, load_image

        if not torch.cuda.is_available():
            logger.warning("Wan2.1 cần GPU — bỏ qua")
            return None

        model_path = _get_model_path("wan2.1-i2v-14B-480P") or "Wan-AI/Wan2.1-I2V-14B-480P"
        logger.info(f"Đang load Wan2.1 từ: {model_path}")

        pipe = WanImageToVideoPipeline.from_pretrained(
            model_path,
            vae=AutoencoderKLWan.from_pretrained(model_path, subfolder="vae", torch_dtype=torch.float32),
            torch_dtype=torch.bfloat16,
        ).to("cuda")
        pipe.enable_model_cpu_offload()
        pipe.vae.enable_slicing()

        if image_path and Path(image_path).exists():
            img = load_image(image_path)
        else:
            img = None

        logger.info("⏳ Wan2.1 đang sinh video (~3-5 phút)...")
        result = pipe(
            image=img,
            prompt=prompt,
            height=height,
            width=width,
            num_frames=num_frames,
            num_inference_steps=steps,
            guidance_scale=5.0,
        )

        tmp = Path(tempfile.mktemp(suffix="_wan21.mp4"))
        export_to_video(result.frames[0], str(tmp), fps=FPS)
        logger.info(f"✅ Wan2.1 hoàn thành: {tmp}")
        return tmp

    except ImportError as e:
        logger.warning(f"Wan2.1 không có (thiếu thư viện): {e}")
        return None
    except Exception as e:
        logger.warning(f"Wan2.1 lỗi: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  ENGINE 2: CogVideoX-5B (Text-to-Video)
# ══════════════════════════════════════════════════════════════════════════════

def _generate_cogvideox(
    prompt: str,
    steps: int = STEPS_QUALITY,
    width: int = 480,
    height: int = 720,
    num_frames: int = 49,
) -> Optional[Path]:
    """
    CogVideoX-5B — nhanh hơn Wan2.1, cần ~8GB VRAM.
    Model: THUDM/CogVideoX-5b (miễn phí HuggingFace)
    """
    try:
        import torch
        from diffusers import CogVideoXPipeline
        from diffusers.utils import export_to_video

        if not torch.cuda.is_available():
            return None

        model_path = _get_model_path("cogvideox-5b") or "THUDM/CogVideoX-5b"
        logger.info(f"Đang load CogVideoX từ: {model_path}")

        pipe = CogVideoXPipeline.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16,
        ).to("cuda")
        pipe.enable_model_cpu_offload()
        pipe.vae.enable_slicing()
        pipe.vae.enable_tiling()

        logger.info("⏳ CogVideoX đang sinh video (~2-3 phút)...")
        result = pipe(
            prompt=prompt,
            num_videos_per_prompt=1,
            num_inference_steps=steps,
            num_frames=num_frames,
            guidance_scale=6.0,
            height=height,
            width=width,
        )

        tmp = Path(tempfile.mktemp(suffix="_cogvx.mp4"))
        export_to_video(result.frames[0], str(tmp), fps=8)
        logger.info(f"✅ CogVideoX hoàn thành: {tmp}")
        return tmp

    except ImportError as e:
        logger.warning(f"CogVideoX không có: {e}")
        return None
    except Exception as e:
        logger.warning(f"CogVideoX lỗi: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  ENGINE 3: AnimateDiff (Fallback nhẹ)
# ══════════════════════════════════════════════════════════════════════════════

def _generate_animatediff(
    prompt: str,
    steps: int = STEPS_FAST,
    width: int = 512,
    height: int = 768,
) -> Optional[Path]:
    """
    AnimateDiff + SDXL — nhẹ nhất (6GB VRAM).
    Chất lượng thấp hơn nhưng nhanh hơn.
    """
    try:
        import torch
        from diffusers import AnimateDiffSDXLPipeline, MotionAdapter, DDIMScheduler
        from diffusers.utils import export_to_gif, export_to_video

        if not torch.cuda.is_available():
            return None

        adapter_path = _get_model_path("animatediff-sdxl") or "guoyww/animatediff-motion-adapter-sdxl-beta"
        adapter = MotionAdapter.from_pretrained(adapter_path, torch_dtype=torch.float16)

        pipe = AnimateDiffSDXLPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0",
            motion_adapter=adapter,
            torch_dtype=torch.float16,
        ).to("cuda")
        pipe.scheduler = DDIMScheduler.from_config(pipe.scheduler.config)
        pipe.enable_vae_slicing()

        logger.info("⏳ AnimateDiff đang sinh video (~1-2 phút)...")
        result = pipe(
            prompt=prompt,
            num_inference_steps=steps,
            height=height,
            width=width,
            num_frames=16,
        )

        tmp = Path(tempfile.mktemp(suffix="_animdiff.mp4"))
        export_to_video(result.frames[0], str(tmp), fps=8)
        logger.info(f"✅ AnimateDiff hoàn thành: {tmp}")
        return tmp

    except Exception as e:
        logger.warning(f"AnimateDiff lỗi: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  ENGINE 4: AI Image Generation (Flux/SDXL) + MoviePy Slideshow
# ══════════════════════════════════════════════════════════════════════════════

def _generate_image_flux(prompt: str, width: int = 1024, height: int = 1024) -> Optional[Path]:
    """Dùng FLUX.1-schnell (4-step, rất nhanh, miễn phí) để tạo ảnh sản phẩm."""
    try:
        import torch
        from diffusers import FluxPipeline

        if not torch.cuda.is_available():
            return None

        model_path = _get_model_path("flux1-schnell") or "black-forest-labs/FLUX.1-schnell"
        pipe = FluxPipeline.from_pretrained(model_path, torch_dtype=torch.bfloat16).to("cuda")
        pipe.enable_model_cpu_offload()

        logger.info("⏳ FLUX.1 đang tạo ảnh (~30 giây)...")
        result = pipe(
            prompt=prompt,
            num_inference_steps=4,
            height=height,
            width=width,
            guidance_scale=0.0,
        )
        tmp = Path(tempfile.mktemp(suffix="_flux.png"))
        result.images[0].save(str(tmp))
        logger.info(f"✅ FLUX.1 tạo ảnh xong: {tmp}")
        return tmp

    except Exception as e:
        logger.warning(f"FLUX.1 lỗi: {e}")
        return None


def _generate_image_sdxl(prompt: str, width: int = 1024, height: int = 1024) -> Optional[Path]:
    """SDXL fallback khi FLUX không có."""
    try:
        import torch
        from diffusers import StableDiffusionXLPipeline

        if not torch.cuda.is_available():
            return None

        pipe = StableDiffusionXLPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0",
            torch_dtype=torch.float16,
        ).to("cuda")
        pipe.enable_vae_slicing()

        result = pipe(prompt=prompt, num_inference_steps=20, height=height, width=width)
        tmp = Path(tempfile.mktemp(suffix="_sdxl.png"))
        result.images[0].save(str(tmp))
        return tmp

    except Exception as e:
        logger.warning(f"SDXL lỗi: {e}")
        return None


def _slideshow_from_images(
    image_paths: list,
    duration_per_image: float = 3.0,
    target_duration: float = 15.0,
    width: int = WIDTH_HD,
    height: int = HEIGHT_HD,
) -> Optional[Path]:
    """Tạo video slideshow từ danh sách ảnh dùng ffmpeg (không cần GPU)."""
    if not image_paths:
        return None
    try:
        tmp = Path(tempfile.mktemp(suffix="_slideshow.mp4"))
        # Tạo file list
        list_file = Path(tempfile.mktemp(suffix=".txt"))
        with open(list_file, "w") as f:
            for img_path in image_paths:
                f.write(f"file '{img_path}'\n")
                f.write(f"duration {duration_per_image}\n")
            f.write(f"file '{image_paths[-1]}'\n")

        subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", str(list_file),
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                   f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black,"
                   f"zoompan=z='min(zoom+0.0015,1.15)':d={int(duration_per_image*25)}:s={width}x{height}",
            "-t", str(target_duration),
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-r", str(FPS),
            str(tmp)
        ], capture_output=True, check=True)
        list_file.unlink(missing_ok=True)
        return tmp
    except subprocess.CalledProcessError as e:
        logger.error(f"Slideshow lỗi: {e.stderr.decode()[:300]}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  ENGINE 5: MoviePy Fallback (không GPU)
# ══════════════════════════════════════════════════════════════════════════════

def _generate_moviepy_fallback(
    prompt: str,
    product_name: str = "Sản phẩm",
    price: str = "",
    gender: str = "women",
    width: int = WIDTH_HD,
    height: int = HEIGHT_HD,
) -> Optional[Path]:
    """
    Tạo video đơn giản bằng MoviePy — không cần GPU.
    Dùng màu gradient + text overlay thay cho ảnh AI.
    Fallback cuối cùng khi không có GPU.
    """
    try:
        from moviepy.editor import (
            ColorClip, TextClip, CompositeVideoClip, concatenate_videoclips
        )
        import numpy as np

        colors = {
            "women":   [(200, 30, 80),    (255, 100, 150)],
            "men":     [(20,  40, 120),   (60,  100, 220)],
            "children":[(255, 150, 0),    (255, 200, 100)],
            "baby":    [(100, 180, 240),  (200, 230, 255)],
            "unisex":  [(140, 40, 200),   (200, 100, 255)],
        }
        c1, c2 = colors.get(gender, colors["women"])

        clips = []
        segments = [
            (product_name, 3.0, 120),
            (price, 3.0, 100),
            ("✅ Freeship\n✅ Đổi trả 7 ngày", 4.0, 80),
            ("👆 Link ở BIO", 3.0, 90),
            (product_name, 2.0, 70),
        ]

        for text, dur, font_size in segments:
            bg = ColorClip(size=(width, height), color=c1, duration=dur)
            txt = TextClip(
                text, fontsize=font_size, color="white",
                font="DejaVu-Sans-Bold", size=(width - 80, None),
                method="caption", align="center",
            ).set_duration(dur).set_position("center")
            clips.append(CompositeVideoClip([bg, txt]))

        final = concatenate_videoclips(clips, method="compose")
        tmp = Path(tempfile.mktemp(suffix="_moviepy.mp4"))
        final.write_videofile(
            str(tmp), fps=FPS,
            codec="libx264", audio=False, logger=None, preset="fast"
        )
        logger.info(f"✅ MoviePy fallback video: {tmp}")
        return tmp

    except Exception as e:
        logger.error(f"MoviePy fallback lỗi: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  POST-PROCESSING
# ══════════════════════════════════════════════════════════════════════════════

def _loop_video(src: Path, target_sec: float = 15.0) -> Path:
    """Loop video để đạt đủ thời lượng target_sec."""
    try:
        out = Path(tempfile.mktemp(suffix="_looped.mp4"))
        subprocess.run([
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", str(src),
            "-t", str(target_sec),
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-an",
            str(out)
        ], capture_output=True, check=True)
        return out
    except subprocess.CalledProcessError:
        return src


def _mix_audio(video_path: Path, audio_path: Optional[Path], output_path: Path) -> Path:
    """Trộn nhạc nền vào video."""
    if not audio_path or not audio_path.exists():
        shutil.copy2(video_path, output_path)
        return output_path
    try:
        subprocess.run([
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-i", str(audio_path),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-shortest",
            str(output_path)
        ], capture_output=True, check=True)
        return output_path
    except subprocess.CalledProcessError as e:
        logger.warning(f"Mix audio lỗi: {e.stderr.decode()[:200]}")
        shutil.copy2(video_path, output_path)
        return output_path


def _resize_9_16(src: Path, width: int = WIDTH_HD, height: int = HEIGHT_HD) -> Path:
    """Resize về chuẩn 9:16 TikTok."""
    try:
        out = Path(tempfile.mktemp(suffix="_resized.mp4"))
        subprocess.run([
            "ffmpeg", "-y", "-i", str(src),
            "-vf", f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                   f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-an",
            str(out)
        ], capture_output=True, check=True)
        return out
    except Exception:
        return src


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API — Main Generate
# ══════════════════════════════════════════════════════════════════════════════

def generate_video(
    script,                      # VideoScript object
    product_name: str,
    price: str,
    gender: str = "women",
    image_path: Optional[str] = None,
    engine: str = "auto",
    output_path: Optional[Path] = None,
) -> Optional[Path]:
    """
    Tạo video AI đầy đủ:
      1. Sinh video AI (Wan2.1 → CogVideoX → AnimateDiff → Slideshow → MoviePy)
      2. Loop về 15 giây
      3. Resize về 9:16 (1080×1920)
      4. Áp dụng text overlay
      5. Trộn nhạc nền

    engine: "auto" | "wan21" | "cogvideox" | "animatediff" | "slideshow" | "moviepy"
    """
    from pipeline.text_overlay import apply_text_overlay
    from pipeline.music_engine import get_music

    prompt = script.ai_prompt_main
    logger.info(f"🎬 Bắt đầu tạo video: {product_name} [{engine}]")

    # ── Bước 1: Sinh base video ──────────────────────────────────────────────
    base_video: Optional[Path] = None

    if engine in ("auto", "wan21"):
        base_video = _generate_wan21(prompt, image_path)

    if base_video is None and engine in ("auto", "cogvideox"):
        base_video = _generate_cogvideox(prompt)

    if base_video is None and engine in ("auto", "animatediff"):
        base_video = _generate_animatediff(prompt)

    if base_video is None and engine in ("auto", "slideshow"):
        # Thử tạo ảnh AI trước
        img_ai = _generate_image_flux(script.ai_prompt_hook) or _generate_image_sdxl(script.ai_prompt_hook)
        if img_ai:
            base_video = _slideshow_from_images(
                [str(img_ai)] * 5,
                duration_per_image=3.0,
                target_duration=DURATION_SEC,
                width=WIDTH_SD, height=HEIGHT_SD,
            )

    if base_video is None:
        logger.info("Dùng MoviePy fallback (không cần GPU)")
        base_video = _generate_moviepy_fallback(
            prompt, product_name, price, gender,
            width=WIDTH_SD, height=HEIGHT_SD,
        )

    if base_video is None or not base_video.exists():
        logger.error("Không thể tạo video — tất cả engine đều thất bại")
        return None

    # ── Bước 2: Loop về 15 giây ───────────────────────────────────────────────
    looped = _loop_video(base_video, DURATION_SEC)

    # ── Bước 3: Resize 9:16 ───────────────────────────────────────────────────
    resized = _resize_9_16(looped, WIDTH_HD, HEIGHT_HD)

    # ── Bước 4: Text overlay ──────────────────────────────────────────────────
    vc = script  # VideoScript
    overlaid = apply_text_overlay(
        video_path   = resized,
        product_name = product_name,
        price        = price,
        value_stack  = vc.value_scene.hook_text,
        cta          = vc.cta_scene.hook_text,
        comment_cta  = vc.cta_scene.subtext,
        badge        = vc.loop_scene.hook_text,
        gender       = gender,
    )

    # ── Bước 5: Mix nhạc ──────────────────────────────────────────────────────
    music = get_music(script.music_mood, DURATION_SEC)

    if output_path is None:
        try:
            from pipeline.drive_manager import drive_mgr
            output_path = drive_mgr.new_output_path(product_name[:20].replace(" ", "_"))
        except Exception:
            output_path = Path(tempfile.mktemp(suffix="_final.mp4"))

    final = _mix_audio(overlaid, music, output_path)
    logger.info(f"✅ Video hoàn thành: {final}")
    return final
