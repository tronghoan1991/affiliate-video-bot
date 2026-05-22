"""
pipeline/video_engine.py
Engine video 100% miễn phí — tự động chọn tốt nhất theo VRAM.

Thứ tự ưu tiên (mode auto):
  1. Wan2.1-I2V-14B-480P  — tốt nhất (VAE 1080P native, ~13GB VRAM)
  2. AnimateDiff v2        — fallback nhẹ (~8GB VRAM)
  3. HF Spaces API         — cloud backup (0 VRAM cần)
"""
import asyncio
import gc
import logging
import subprocess
import tempfile
from pathlib import Path

import torch
from PIL import Image

from config import Config
from pipeline.background import get_full_prompt, get_negative_prompt

logger = logging.getLogger("VideoEngine")


def _vram_gb() -> float:
    if torch.cuda.is_available():
        return torch.cuda.get_device_properties(0).total_memory / 1e9
    return 0.0


def _free():
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()


def _frames_to_mp4(frames: list, out: Path, fps: int = 16):
    """List[PIL.Image] → MP4 qua ffmpeg (loop 3×)."""
    tmp = Path(tempfile.mkdtemp())
    for i, f in enumerate(frames):
        if not isinstance(f, Image.Image):
            f = Image.fromarray(f)
        f.save(str(tmp / f"f_{i:05d}.png"))

    concat = tmp / "list.txt"
    with open(concat, "w") as fh:
        for _ in range(3):
            for p in sorted(tmp.glob("f_*.png")):
                fh.write(f"file '{p}'\n")

    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "18", "-preset", "slow",
        "-movflags", "+faststart",
        str(out),
    ], check=True, capture_output=True)

    import shutil; shutil.rmtree(tmp, ignore_errors=True)


# ══════════════════════════════════════════════════════════════
#  ENGINE 1: Wan2.1-I2V  (CHÍNH — chất lượng cao nhất miễn phí)
# ══════════════════════════════════════════════════════════════

def run_wan21(
    image_path: Path,
    output_path: Path,
    prompt: str,
    device: str = "cuda",
    orientation: str = "portrait",
) -> Path:
    """
    Wan2.1 Image-to-Video (14B, 480P).
    Tham chiếu: https://huggingface.co/Wan-AI/Wan2.1-I2V-14B-480P-Diffusers
    """
    from diffusers import AutoencoderKLWan, WanImageToVideoPipeline
    from diffusers.utils import export_to_video
    from transformers import CLIPVisionModel

    vram = _vram_gb()
    model_id = Config.WAN_MODEL_480P
    logger.info(f"Wan2.1 I2V | model={model_id} | VRAM={vram:.1f}GB | device={device}")

    logger.info("Loading image_encoder (float32)...")
    image_encoder = CLIPVisionModel.from_pretrained(
        model_id, subfolder="image_encoder",
        torch_dtype=torch.float32,
        cache_dir=str(Config.MODELS_DIR / "wan21"),
    )
    logger.info("Loading VAE (float32)...")
    vae = AutoencoderKLWan.from_pretrained(
        model_id, subfolder="vae",
        torch_dtype=torch.float32,
        cache_dir=str(Config.MODELS_DIR / "wan21"),
    )
    logger.info("Loading pipeline (bfloat16)...")
    pipe = WanImageToVideoPipeline.from_pretrained(
        model_id,
        vae=vae,
        image_encoder=image_encoder,
        torch_dtype=torch.bfloat16,
        cache_dir=str(Config.MODELS_DIR / "wan21"),
    )

    pipe.enable_model_cpu_offload()
    pipe.vae.enable_tiling()
    pipe.vae.enable_slicing()

    if orientation == "portrait":
        w, h = Config.WAN_WIDTH_9_16, Config.WAN_HEIGHT_9_16
    else:
        w, h = Config.WAN_WIDTH_480, Config.WAN_HEIGHT_480

    image = Image.open(image_path).convert("RGB").resize((w, h), Image.LANCZOS)
    neg = get_negative_prompt()

    logger.info(f"Generating {Config.WAN_NUM_FRAMES} frames @ {w}×{h}...")
    with torch.inference_mode():
        output = pipe(
            image=image,
            prompt=prompt,
            negative_prompt=neg,
            height=h,
            width=w,
            num_frames=Config.WAN_NUM_FRAMES,
            num_inference_steps=Config.WAN_STEPS,
            guidance_scale=Config.WAN_GUIDANCE,
            generator=torch.Generator(device="cpu").manual_seed(42),
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    export_to_video(output.frames[0], str(output_path), fps=Config.WAN_FPS)
    logger.info(f"✅ Wan2.1 done → {output_path}")
    return output_path


# ══════════════════════════════════════════════════════════════
#  ENGINE 2: AnimateDiff (Fallback nhẹ hơn, ~8GB VRAM)
# ══════════════════════════════════════════════════════════════

def run_animatediff(
    image_path: Path,
    output_path: Path,
    prompt: str,
    device: str = "cuda",
) -> Path:
    """AnimateDiff v2 — text2video, 512×768, 16 frames, loop 3×."""
    from diffusers import AnimateDiffPipeline, MotionAdapter, DDIMScheduler

    logger.info("AnimateDiff text2video fallback...")
    dtype = torch.float16 if device == "cuda" else torch.float32

    adapter = MotionAdapter.from_pretrained(
        Config.ANIM_MOTION_MODULE, torch_dtype=dtype,
        cache_dir=str(Config.MODELS_DIR / "animatediff"),
    )
    pipe = AnimateDiffPipeline.from_pretrained(
        Config.ANIM_BASE_MODEL, motion_adapter=adapter,
        torch_dtype=dtype, cache_dir=str(Config.MODELS_DIR / "sd15"),
    )
    pipe.scheduler = DDIMScheduler.from_config(
        pipe.scheduler.config,
        beta_schedule="linear", clip_sample=False,
        timestep_spacing="linspace", steps_offset=1,
    )
    pipe = pipe.to(device)
    pipe.enable_attention_slicing()
    try:
        pipe.enable_xformers_memory_efficient_attention()
    except Exception:
        pass

    with torch.inference_mode():
        out = pipe(
            prompt=prompt,
            negative_prompt=get_negative_prompt(),
            num_frames=Config.ANIM_FRAMES,
            guidance_scale=Config.ANIM_GUIDANCE,
            num_inference_steps=Config.ANIM_STEPS,
            generator=torch.Generator(device=device).manual_seed(42),
        )

    frames = list(out.frames[0]) * 3
    output_path.parent.mkdir(parents=True, exist_ok=True)
    _frames_to_mp4(frames, output_path, fps=24)
    logger.info(f"✅ AnimateDiff done → {output_path}")
    return output_path


# ══════════════════════════════════════════════════════════════
#  ENGINE 3: HF Spaces (Cloud backup, 0 VRAM, miễn phí)
# ══════════════════════════════════════════════════════════════

async def run_hf_spaces(
    image_path: Path,
    output_path: Path,
    prompt: str,
) -> Path:
    """Gọi CogVideoX-5B qua HuggingFace Spaces Gradio API (miễn phí)."""
    import httpx
    from gradio_client import Client, handle_file

    logger.info("HF Spaces cloud fallback (no GPU needed)...")
    client = Client(
        "THUDM/CogVideoX-5B-Space",
        hf_token=Config.HF_TOKEN or None,
    )
    result = client.predict(
        prompt=prompt,
        image=handle_file(str(image_path)),
        num_inference_steps=50,
        guidance_scale=6.0,
        api_name="/generate_video",
    )
    video_url = result if isinstance(result, str) else result[0]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    async with httpx.AsyncClient(timeout=300) as c:
        r = await c.get(video_url)
        r.raise_for_status()
        output_path.write_bytes(r.content)

    logger.info(f"✅ HF Spaces done → {output_path}")
    return output_path


# ══════════════════════════════════════════════════════════════
#  ORCHESTRATOR
# ══════════════════════════════════════════════════════════════

async def run_video_pipeline(
    image_path: Path,
    output_path: Path,
    bg_prompt: str,
    garment_class: str,
    orientation: str = "portrait",
    device: str = "cuda",
) -> str:
    """
    Tự động chọn engine tốt nhất và tạo video.
    Returns: tên engine đã dùng.
    """
    prompt  = get_full_prompt(garment_class, bg_prompt)
    engine  = Config.VIDEO_ENGINE
    vram    = _vram_gb()

    logger.info(f"Pipeline | engine={engine} | vram={vram:.1f}GB | orientation={orientation}")

    if engine == "wan21":
        run_wan21(image_path, output_path, prompt, device, orientation)
        return "wan21"

    if engine == "animatediff":
        run_animatediff(image_path, output_path, prompt, device)
        return "animatediff"

    if engine == "cloud":
        await run_hf_spaces(image_path, output_path, prompt)
        return "hf_spaces"

    if vram >= 13 or device == "cpu":
        try:
            logger.info("Auto → thử Wan2.1 I2V (best quality)...")
            run_wan21(image_path, output_path, prompt, device, orientation)
            return "wan21"
        except torch.cuda.OutOfMemoryError:
            logger.warning("Wan2.1 OOM → thử AnimateDiff...")
            _free()

    if vram >= 7:
        try:
            logger.info("Auto → thử AnimateDiff (lighter)...")
            run_animatediff(image_path, output_path, prompt, device)
            return "animatediff"
        except torch.cuda.OutOfMemoryError:
            logger.warning("AnimateDiff OOM → HF Spaces cloud...")
            _free()

    logger.info("Auto → HF Spaces cloud (no GPU)...")
    await run_hf_spaces(image_path, output_path, prompt)
    return "hf_spaces"
