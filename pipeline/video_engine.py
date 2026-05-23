"""
pipeline/video_engine.py — AI Video Engine v7 (2026)
=============================================================================
Engine ưu tiên (tự động chọn theo VRAM có sẵn):
  1. Wan2.1-I2V-14B-480P  — Tốt nhất (12GB VRAM)
  2. CogVideoX-5B          — Nhanh (8GB VRAM)
  3. AnimateDiff XL        — Nhẹ (6GB VRAM)
  4. FLUX.1-schnell + Slideshow — AI image (6GB)
  5. MoviePy               — Không cần GPU (fallback)

Output: 1080×1920 (9:16 TikTok/Reels), 15 giây, 24fps.
=============================================================================
"""
import logging, os, shutil, subprocess, tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger("VideoEngine")

FPS = 24
DURATION_SEC = 15
W, H = 1080, 1920
W_SD, H_SD = 480, 832


def _drive_model(name: str) -> Optional[str]:
    try:
        from pipeline.drive_manager import drive_mgr
        p = drive_mgr.models_dir / name
        return str(p) if p.exists() else None
    except Exception:
        return None


def _hf(model_id: str, local_name: str) -> str:
    return _drive_model(local_name) or model_id


# ── Engine 1: Wan2.1 ─────────────────────────────────────────────────────────
def _wan21(prompt: str, image_path: Optional[str] = None) -> Optional[Path]:
    try:
        import torch
        from diffusers import WanImageToVideoPipeline, AutoencoderKLWan
        from diffusers.utils import export_to_video, load_image
        if not torch.cuda.is_available(): return None
        src = _hf("Wan-AI/Wan2.1-I2V-14B-480P", "wan2.1-i2v-14B-480P")
        pipe = WanImageToVideoPipeline.from_pretrained(
            src, vae=AutoencoderKLWan.from_pretrained(src, subfolder="vae", torch_dtype=torch.float32),
            torch_dtype=torch.bfloat16).to("cuda")
        pipe.enable_model_cpu_offload(); pipe.vae.enable_slicing()
        img = load_image(image_path) if image_path and Path(image_path).exists() else None
        logger.info("⏳ Wan2.1 generating...")
        out = pipe(image=img, prompt=prompt, height=H_SD, width=W_SD, num_frames=81,
                   num_inference_steps=30, guidance_scale=5.0)
        tmp = Path(tempfile.mktemp(suffix="_wan21.mp4"))
        export_to_video(out.frames[0], str(tmp), fps=FPS)
        logger.info(f"✅ Wan2.1: {tmp}"); return tmp
    except Exception as e:
        logger.warning(f"Wan2.1 fail: {e}"); return None


# ── Engine 2: CogVideoX-5B ───────────────────────────────────────────────────
def _cogvideox(prompt: str) -> Optional[Path]:
    try:
        import torch
        from diffusers import CogVideoXPipeline
        from diffusers.utils import export_to_video
        if not torch.cuda.is_available(): return None
        src = _hf("THUDM/CogVideoX-5b", "cogvideox-5b")
        pipe = CogVideoXPipeline.from_pretrained(src, torch_dtype=torch.bfloat16).to("cuda")
        pipe.enable_model_cpu_offload(); pipe.vae.enable_slicing(); pipe.vae.enable_tiling()
        logger.info("⏳ CogVideoX generating...")
        out = pipe(prompt=prompt, num_frames=49, num_inference_steps=30, guidance_scale=6.0, height=480, width=720)
        tmp = Path(tempfile.mktemp(suffix="_cogvx.mp4"))
        export_to_video(out.frames[0], str(tmp), fps=8)
        logger.info(f"✅ CogVideoX: {tmp}"); return tmp
    except Exception as e:
        logger.warning(f"CogVideoX fail: {e}"); return None


# ── Engine 3: AnimateDiff ────────────────────────────────────────────────────
def _animatediff(prompt: str) -> Optional[Path]:
    try:
        import torch
        from diffusers import AnimateDiffSDXLPipeline, MotionAdapter, DDIMScheduler
        from diffusers.utils import export_to_video
        if not torch.cuda.is_available(): return None
        adapter = MotionAdapter.from_pretrained(
            _hf("guoyww/animatediff-motion-adapter-sdxl-beta", "animatediff-sdxl"),
            torch_dtype=torch.float16)
        pipe = AnimateDiffSDXLPipeline.from_pretrained(
            "stabilityai/stable-diffusion-xl-base-1.0",
            motion_adapter=adapter, torch_dtype=torch.float16).to("cuda")
        pipe.scheduler = DDIMScheduler.from_config(pipe.scheduler.config)
        pipe.enable_vae_slicing()
        logger.info("⏳ AnimateDiff generating...")
        out = pipe(prompt=prompt, num_frames=16, num_inference_steps=20, height=512, width=768)
        tmp = Path(tempfile.mktemp(suffix="_animdiff.mp4"))
        export_to_video(out.frames[0], str(tmp), fps=8)
        logger.info(f"✅ AnimateDiff: {tmp}"); return tmp
    except Exception as e:
        logger.warning(f"AnimateDiff fail: {e}"); return None


# ── Engine 4: FLUX.1 → Slideshow ─────────────────────────────────────────────
def _flux_image(prompt: str) -> Optional[Path]:
    try:
        import torch
        from diffusers import FluxPipeline
        if not torch.cuda.is_available(): return None
        pipe = FluxPipeline.from_pretrained(
            _hf("black-forest-labs/FLUX.1-schnell", "flux1-schnell"),
            torch_dtype=torch.bfloat16).to("cuda")
        pipe.enable_model_cpu_offload()
        out = pipe(prompt=prompt, num_inference_steps=4, height=1024, width=1024, guidance_scale=0.0)
        tmp = Path(tempfile.mktemp(suffix="_flux.png"))
        out.images[0].save(str(tmp)); return tmp
    except Exception as e:
        logger.warning(f"FLUX fail: {e}"); return None


def _slideshow(images: list, dur_per=3.0, total=15.0) -> Optional[Path]:
    if not images: return None
    try:
        list_f = Path(tempfile.mktemp(suffix=".txt"))
        with open(list_f, "w") as f:
            for img in images:
                f.write(f"file '{img}'\nduration {dur_per}\n")
            f.write(f"file '{images[-1]}'\n")
        tmp = Path(tempfile.mktemp(suffix="_slide.mp4"))
        subprocess.run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(list_f),
            "-vf",f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black,"
                  f"zoompan=z='min(zoom+0.001,1.1)':d={int(dur_per*25)}:s={W}x{H}",
            "-t",str(total),"-c:v","libx264","-preset","fast","-crf","23","-r",str(FPS),str(tmp)],
            capture_output=True, check=True)
        list_f.unlink(missing_ok=True)
        return tmp
    except subprocess.CalledProcessError as e:
        logger.error(f"Slideshow fail: {e.stderr.decode()[:200]}"); return None


# ── Engine 5: MoviePy fallback ────────────────────────────────────────────────
def _moviepy(product_name: str, price: str, category: str = "fashion") -> Optional[Path]:
    try:
        from moviepy.editor import ColorClip, TextClip, CompositeVideoClip, concatenate_videoclips
        colors = {
            "fashion":"#E01455","beauty":"#D4856A","health":"#2ECC71",
            "home":"#F39C12","food":"#E74C3C","tech":"#2980B9",
            "pet":"#9B59B6","sports":"#1ABC9C","baby":"#AED6F1",
        }
        bg_hex = colors.get(category, "#E01455")
        r, g, b = int(bg_hex[1:3],16), int(bg_hex[3:5],16), int(bg_hex[5:7],16)
        segs = [(product_name,3,100),(price,3,120),("✅ Freeship\n✅ Đổi trả 7 ngày",4,80),("👆 Link BIO",3,90),(product_name,2,70)]
        clips = []
        for text, dur, fs in segs:
            bg  = ColorClip((W_SD,H_SD), color=(r,g,b), duration=dur)
            txt = TextClip(text, fontsize=fs, color="white", font="DejaVu-Sans-Bold",
                           size=(W_SD-80,None), method="caption", align="center").set_duration(dur).set_position("center")
            clips.append(CompositeVideoClip([bg,txt]))
        final = concatenate_videoclips(clips, method="compose")
        tmp   = Path(tempfile.mktemp(suffix="_mpy.mp4"))
        final.write_videofile(str(tmp), fps=FPS, codec="libx264", audio=False, logger=None, preset="fast")
        logger.info(f"✅ MoviePy: {tmp}"); return tmp
    except Exception as e:
        logger.error(f"MoviePy fail: {e}"); return None


# ── Post-processing ───────────────────────────────────────────────────────────
def _loop(src: Path, secs: float = 15.0) -> Path:
    try:
        out = Path(tempfile.mktemp(suffix="_loop.mp4"))
        subprocess.run(["ffmpeg","-y","-stream_loop","-1","-i",str(src),
            "-t",str(secs),"-c:v","libx264","-preset","fast","-crf","22","-an",str(out)],
            capture_output=True, check=True)
        return out
    except: return src

def _resize(src: Path) -> Path:
    try:
        out = Path(tempfile.mktemp(suffix="_rs.mp4"))
        subprocess.run(["ffmpeg","-y","-i",str(src),
            "-vf",f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:black",
            "-c:v","libx264","-preset","fast","-crf","22","-an",str(out)],
            capture_output=True, check=True)
        return out
    except: return src

def _mix_audio(video: Path, audio: Optional[Path], out: Path) -> Path:
    if not audio or not audio.exists():
        shutil.copy2(video, out); return out
    try:
        subprocess.run(["ffmpeg","-y","-i",str(video),"-i",str(audio),
            "-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-shortest",str(out)],
            capture_output=True, check=True)
        return out
    except: shutil.copy2(video, out); return out


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def generate_video(
    ai_prompt: str,
    hook_prompt: str,
    product_name: str,
    price: str,
    category: str = "fashion",
    music_mood: str = "trendy_pop",
    image_path: Optional[str] = None,
    engine: str = "auto",
    output_path: Optional[Path] = None,
    value_stack: str = "",
    cta: str = "",
    badge: str = "🔥 HOT 2026",
    gender: str = "women",
) -> Optional[Path]:
    """
    Tạo video affiliate hoàn chỉnh:
    1. AI video generation (Wan2.1 → CogVideoX → AnimateDiff → Slideshow → MoviePy)
    2. Loop → Resize 9:16
    3. Text overlay (hook + product + value + CTA)
    4. Mix nhạc nền
    """
    from pipeline.text_overlay import apply_text_overlay
    from pipeline.music_engine import get_music

    logger.info(f"🎬 Start video: {product_name} | engine={engine} | category={category}")

    base: Optional[Path] = None
    if engine in ("auto","wan21"):      base = _wan21(ai_prompt, image_path)
    if base is None and engine in ("auto","cogvideox"):  base = _cogvideox(ai_prompt)
    if base is None and engine in ("auto","animatediff"):base = _animatediff(ai_prompt)
    if base is None and engine in ("auto","slideshow"):
        img = _flux_image(hook_prompt)
        if img: base = _slideshow([str(img)]*5)
    if base is None:
        base = _moviepy(product_name, price, category)

    if base is None or not base.exists():
        logger.error("All engines failed"); return None

    looped  = _loop(base, DURATION_SEC)
    resized = _resize(looped)

    # Text overlay
    overlaid = apply_text_overlay(
        video_path=resized, product_name=product_name, price=price,
        value_stack=value_stack or "✅ Freeship\n✅ Đổi trả 7 ngày",
        cta=cta or "👆 Link ở BIO", comment_cta="Comment 'MUA' để nhận link 👇",
        badge=badge, category=category, gender=gender,
    )

    # Music
    music = get_music(music_mood, DURATION_SEC)

    if output_path is None:
        try:
            from pipeline.drive_manager import drive_mgr
            output_path = drive_mgr.new_output_path(product_name[:20].replace(" ","_"))
        except Exception:
            output_path = Path(tempfile.mktemp(suffix="_final.mp4"))

    final = _mix_audio(overlaid, music, output_path)
    logger.info(f"✅ Video done: {final}")
    return final
