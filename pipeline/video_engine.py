"""
pipeline/video_engine.py — AI Video Generation Engine
=============================================================================
Wrapper cho các AI video generation model:
  1. Wan2.1-I2V-14B-480P (Primary — chất lượng tốt nhất, ~12GB VRAM)
  2. CogVideoX-5B (Secondary — nhanh hơn, VRAM thấp hơn)
  3. AnimateDiff XL (Fallback — nhẹ nhất, phù hợp RAM ít)

Tất cả model weights lưu trên Google Drive — không tải lại mỗi session.
Output video được lưu Drive/outputs/{date}/.

Video pipeline:
  1. Generate base clip từ text/image prompt (AI model)
  2. Loop × 3 để đạt ~15s
  3. Add text overlay (text_overlay.py)
  4. Mix music (music_engine.py)
  5. Save output to Drive
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

# ══════════════════════════════════════════════════════════════════════════════
#  VIDEO SETTINGS
# ══════════════════════════════════════════════════════════════════════════════

DEFAULT_FPS    = 16
DEFAULT_FRAMES = 81     # 81 frames / 16fps ≈ 5s per clip
DEFAULT_LOOPS  = 3      # 3 × 5s = 15s total — DEFAULT_LOOPS = 3
WIDTH_PORTRAIT = 480    # 9:16 TikTok native
HEIGHT_PORTRAIT = 832
STEPS_FAST     = 20     # Faster, lower quality
STEPS_QUALITY  = 30     # Balanced (recommended)
STEPS_BEST     = 50     # Best quality, slow


# ══════════════════════════════════════════════════════════════════════════════
#  MODEL LOADER — Lấy model từ Google Drive
# ══════════════════════════════════════════════════════════════════════════════

def _get_model_path(model_name: str) -> Optional[str]:
    """Lấy model path từ Google Drive."""
    try:
        from pipeline.drive_manager import drive_mgr
        p = drive_mgr.get_model_path(model_name)
        if p:
            return str(p)
    except Exception as e:
        logger.warning(f"Drive lookup failed: {e}")

    # Fallback: Colab typical paths
    colab_paths = [
        f"/content/affiliate-video-bot/models/{model_name}",
        f"/content/models/{model_name}",
        f"/content/drive/MyDrive/AffiliateBot/models/{model_name}",
    ]
    for p in colab_paths:
        if Path(p).exists():
            return p
    return None


def download_model_to_drive(model_id: str, local_name: str) -> str:
    """
    Tải model về Google Drive lần đầu.
    Sau lần đầu, bot tự load từ Drive — không tải lại.
    """
    try:
        from pipeline.drive_manager import drive_mgr
        dest = str(drive_mgr.models_dir / local_name)
        if Path(dest).exists():
            logger.info(f"Model already on Drive: {local_name}")
            return dest
        logger.info(f"Downloading {model_id} to Drive...")
        os.makedirs(dest, exist_ok=True)
        subprocess.run([
            "huggingface-cli", "download", model_id,
            "--local-dir", dest,
            "--local-dir-use-symlinks", "False",
        ], check=True)
        logger.info(f"✅ Model saved to Drive: {dest}")
        return dest
    except Exception as e:
        logger.error(f"Model download failed: {e}")
        raise


# ══════════════════════════════════════════════════════════════════════════════
#  WAN2.1 — Primary Engine (Best Quality)
# ══════════════════════════════════════════════════════════════════════════════

def generate_wan21(
    prompt: str,
    negative_prompt: str = "",
    image_path: Optional[str] = None,
    output_path: Optional[Path] = None,
    num_frames: int = DEFAULT_FRAMES,
    fps: int = DEFAULT_FPS,
    steps: int = STEPS_QUALITY,
    guidance_scale: float = 7.0,
    width: int = WIDTH_PORTRAIT,
    height: int = HEIGHT_PORTRAIT,
) -> Optional[Path]:
    """
    Generate video với Wan2.1-I2V (Image-to-Video) hoặc T2V (Text-to-Video).
    Model path từ Google Drive.
    """
    try:
        import torch
        from diffusers import WanVideoPipeline, AutoencoderKLWan
        from diffusers.utils import export_to_video, load_image

        logger.info("Loading Wan2.1 from Drive...")
        model_path = _get_model_path("wan2.1-i2v-14B-480P") or "Wan-AI/Wan2.1-I2V-14B-480P"

        pipe = WanVideoPipeline.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16,
        )
        pipe.enable_model_cpu_offload()

        device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using device: {device}")

        gen_kwargs = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "num_frames": num_frames,
            "num_inference_steps": steps,
            "guidance_scale": guidance_scale,
            "width": width,
            "height": height,
        }
        if image_path and Path(image_path).exists():
            gen_kwargs["image"] = load_image(image_path)

        logger.info(f"Generating {num_frames} frames...")
        output = pipe(**gen_kwargs)
        frames = output.frames[0]

        if output_path is None:
            tmp = tempfile.mktemp(suffix=".mp4")
            output_path = Path(tmp)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        export_to_video(frames, str(output_path), fps=fps)

        # Free GPU memory
        del pipe
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info(f"✅ Wan2.1 video: {output_path}")
        return output_path

    except ImportError as e:
        logger.warning(f"Wan2.1 not available: {e}")
        return None
    except Exception as e:
        logger.error(f"Wan2.1 generation failed: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  COGVIDEOX — Secondary Engine
# ══════════════════════════════════════════════════════════════════════════════

def generate_cogvideox(
    prompt: str,
    negative_prompt: str = "",
    image_path: Optional[str] = None,
    output_path: Optional[Path] = None,
    num_frames: int = 49,
    fps: int = DEFAULT_FPS,
    steps: int = 50,
    guidance_scale: float = 6.0,
    width: int = WIDTH_PORTRAIT,
    height: int = HEIGHT_PORTRAIT,
) -> Optional[Path]:
    """Generate video với CogVideoX-5B."""
    try:
        import torch
        from diffusers import CogVideoXPipeline, CogVideoXImageToVideoPipeline
        from diffusers.utils import export_to_video, load_image

        logger.info("Loading CogVideoX...")
        model_path = _get_model_path("CogVideoX-5B-I2V") or "THUDM/CogVideoX-5B-I2V"

        if image_path and Path(image_path).exists():
            pipe = CogVideoXImageToVideoPipeline.from_pretrained(
                model_path, torch_dtype=torch.bfloat16,
            )
        else:
            pipe = CogVideoXPipeline.from_pretrained(
                model_path, torch_dtype=torch.bfloat16,
            )

        pipe.enable_sequential_cpu_offload()

        gen_kwargs = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "num_frames": num_frames,
            "num_inference_steps": steps,
            "guidance_scale": guidance_scale,
            "width": width,
            "height": height,
        }
        if image_path and Path(image_path).exists():
            gen_kwargs["image"] = load_image(image_path)

        output = pipe(**gen_kwargs)
        frames = output.frames[0]

        if output_path is None:
            output_path = Path(tempfile.mktemp(suffix=".mp4"))
        export_to_video(frames, str(output_path), fps=fps)

        del pipe
        import torch
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

        logger.info(f"✅ CogVideoX video: {output_path}")
        return output_path

    except ImportError as e:
        logger.warning(f"CogVideoX not available: {e}")
        return None
    except Exception as e:
        logger.error(f"CogVideoX generation failed: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  VIDEO LOOP — Ghép 3 clip lại thành 15s với ffmpeg
# ══════════════════════════════════════════════════════════════════════════════

def loop_video(
    clip_path: Path,
    output_path: Path,
    loops: int = DEFAULT_LOOPS,
    crossfade_duration: float = 0.3,
) -> Path:
    """
    Loop video × N lần để đạt target duration (~15s).
    Crossfade mượt giữa các loop.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Simple concat (fastest)
    concat_content = "\n".join([f"file '{clip_path}'" for _ in range(loops)])
    concat_file = tempfile.mktemp(suffix=".txt")
    with open(concat_file, "w") as f:
        f.write(concat_content)

    try:
        subprocess.run([
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0",
            "-i", concat_file,
            "-c:v", "libx264", "-crf", "17", "-preset", "fast",
            "-pix_fmt", "yuv420p",
            str(output_path),
        ], check=True, capture_output=True)
        logger.info(f"✅ Looped {loops}x: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        logger.error(f"Loop failed: {e.stderr.decode()[:200]}")
        shutil.copy2(clip_path, output_path)
        return output_path
    finally:
        Path(concat_file).unlink(missing_ok=True)


# ══════════════════════════════════════════════════════════════════════════════
#  FULL PIPELINE — Generate + Loop + Overlay + Music + Save to Drive
# ══════════════════════════════════════════════════════════════════════════════

def generate_affiliate_video(
    prompt: str,
    negative_prompt: str,
    product_name: str,
    product_price: str,
    garment_class: str,
    gender: str,
    platform: str = "tiktok",
    image_path: Optional[str] = None,
    output_filename: str = "output.mp4",
    engine: str = "auto",
    hook_text: str = "",
    hook_subtext: str = "",
    urgency_badge: str = "",
    social_proof: str = "",
    value_stack: str = "",
    comment_cta: str = "",
    cta: str = "",
    music_mood: str = "",
    color_scheme: Optional[dict] = None,
) -> dict:
    """
    Pipeline đầy đủ: AI Video → Loop → Overlay → Music → Drive.

    Args:
        engine: "wan21" | "cogvideox" | "auto" (thử wan21 trước, fallback cogvideox)

    Returns:
        dict với video_path, drive_path, caption, viral_content
    """
    import datetime
    from pipeline.drive_manager import drive_mgr

    # ── Step 1: Generate raw AI clip ──────────────────────────────
    clip_path = None
    used_engine = "none"

    if engine in ("auto", "wan21"):
        logger.info("Trying Wan2.1...")
        raw_tmp = Path(tempfile.mktemp(suffix="_raw.mp4"))
        clip_path = generate_wan21(prompt, negative_prompt, image_path, raw_tmp)
        if clip_path:
            used_engine = "wan2.1-i2v-14B"

    if clip_path is None and engine in ("auto", "cogvideox"):
        logger.info("Falling back to CogVideoX...")
        raw_tmp = Path(tempfile.mktemp(suffix="_raw.mp4"))
        clip_path = generate_cogvideox(prompt, negative_prompt, image_path, raw_tmp)
        if clip_path:
            used_engine = "cogvideox-5b"

    if clip_path is None:
        logger.error("All video engines failed — cannot generate video")
        return {"error": "No video engine available. Install diffusers and torch."}

    # ── Step 2: Loop × 3 → ~15 giây ──────────────────────────────
    looped_tmp = Path(tempfile.mktemp(suffix="_looped.mp4"))
    loop_video(clip_path, looped_tmp, loops=DEFAULT_LOOPS)
    clip_path.unlink(missing_ok=True)

    # ── Step 3: Viral content package ─────────────────────────────
    from pipeline.viral_strategy import build_viral_content
    viral = build_viral_content(
        name=product_name,
        price=product_price,
        garment=f"{gender} {garment_class}",
        platform=platform,
    )
    # Override với script writer data nếu có
    final_hook    = hook_text or viral.hook_text
    final_sub     = hook_subtext or viral.hook_subtext
    final_badge   = urgency_badge or viral.urgency_badge
    final_proof   = social_proof or viral.social_proof
    final_value   = value_stack or viral.value_stack
    final_comment = comment_cta or viral.comment_cta
    final_cta     = cta or (viral.cta_tiktok if platform != "shopee" else viral.cta_shopee)
    final_mood    = music_mood or viral.music_mood

    # ── Step 4: Text overlay ──────────────────────────────────────
    from pipeline.text_overlay import add_text_overlay
    overlay_tmp = Path(tempfile.mktemp(suffix="_overlay.mp4"))
    add_text_overlay(
        input_path=looped_tmp,
        output_path=overlay_tmp,
        product_name=product_name,
        product_price=product_price,
        garment_class=garment_class,
        platform=platform,
        hook_text=final_hook,
        hook_subtext=final_sub,
        urgency_badge=final_badge,
        social_proof=final_proof,
        value_stack=final_value,
        comment_cta=final_comment,
        cta=final_cta,
    )
    looped_tmp.unlink(missing_ok=True)

    # ── Step 5: Music ─────────────────────────────────────────────
    from pipeline.music_engine import attach_trending_music
    final_path = Path(tempfile.mktemp(suffix="_final.mp4"))
    attach_trending_music(
        video_path=overlay_tmp,
        output_path=final_path,
        garment=garment_class,
        mood_override=final_mood,
    )
    overlay_tmp.unlink(missing_ok=True)

    # ── Step 6: Save to Google Drive ──────────────────────────────
    date_str = datetime.datetime.now().strftime("%Y-%m-%d")
    final_path_renamed = final_path.parent / output_filename
    shutil.move(str(final_path), str(final_path_renamed))

    drive_path = drive_mgr.save_output_video(final_path_renamed, subfolder=date_str)
    logger.info(f"✅ Video saved to Drive: {drive_path}")

    caption = viral.caption_tiktok if platform != "shopee" else viral.caption_shopee

    return {
        "video_path": str(final_path_renamed),
        "drive_path": str(drive_path),
        "engine": used_engine,
        "hook_text": final_hook,
        "urgency_badge": final_badge,
        "social_proof": final_proof,
        "value_stack": final_value,
        "comment_cta": final_comment,
        "caption": caption,
        "hashtags": viral.hashtags_tiktok,
        "music_mood": final_mood,
    }
