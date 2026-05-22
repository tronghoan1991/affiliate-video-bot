"""
pipeline/upscale.py — Upscale video bằng Real-ESRGAN.
480P × 2 = 960P (~Full-HD)  |  480P × 4 = 1920P (4K-ish)
"""
import logging, shutil, subprocess, tempfile
from pathlib import Path
from typing import Optional
import torch, numpy as np
from PIL import Image

logger = logging.getLogger("Upscale")


def _ffprobe(video: Path, field: str) -> str:
    r = subprocess.run([
        "ffprobe", "-v", "quiet", "-select_streams", "v:0",
        "-show_entries", f"stream={field}",
        "-of", "default=noprint_wrappers=1:nokey=1", str(video),
    ], capture_output=True, text=True)
    return r.stdout.strip()


def _get_fps(video: Path) -> int:
    s = _ffprobe(video, "r_frame_rate")
    try:
        n, d = s.split("/"); return round(int(n) / int(d))
    except Exception:
        return 16


def _extract_frames(video: Path, out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run([
        "ffmpeg", "-y", "-i", str(video),
        "-q:v", "1", str(out_dir / "frame_%06d.png"),
    ], check=True, capture_output=True)
    return len(list(out_dir.glob("frame_*.png")))


def _merge_frames(frames_dir: Path, output: Path, fps: int):
    subprocess.run([
        "ffmpeg", "-y", "-framerate", str(fps),
        "-i", str(frames_dir / "frame_%06d.png"),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-crf", "16", "-preset", "slow", "-movflags", "+faststart",
        str(output),
    ], check=True, capture_output=True)


def run_realesrgan_video(
    input_path: Path,
    output_path: Path,
    scale: int = 2,
    device: str = "cuda",
    model_path: Optional[Path] = None,
) -> Path:
    """
    Upscale toàn bộ video qua Real-ESRGAN frame-by-frame.
    Dùng tile=512 để tránh OOM.
    """
    from basicsr.archs.rrdbnet_arch import RRDBNet
    from realesrgan import RealESRGANer
    from config import Config

    if model_path is None:
        model_path = Config.REALESRGAN_PATH
    if not model_path.exists():
        raise FileNotFoundError(
            f"Real-ESRGAN model không tìm thấy: {model_path}\n"
            "Chạy Cell 'Download Models' trong Colab."
        )

    fps = _get_fps(input_path)
    tmp = Path(tempfile.mkdtemp(prefix="esrgan_"))
    frames_in  = tmp / "in"
    frames_out = tmp / "out"
    frames_out.mkdir(parents=True)

    logger.info(f"ESRGAN {scale}× | {input_path.name} | fps={fps}")

    n = _extract_frames(input_path, frames_in)
    logger.info(f"  Extracted {n} frames")

    netscale = 4
    model_nn = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64,
                       num_block=23, num_grow_ch=32, scale=4)
    upsamp = RealESRGANer(
        scale=netscale, model_path=str(model_path), model=model_nn,
        tile=Config.REALESRGAN_TILE, tile_pad=10, pre_pad=0,
        half=(device == "cuda"),
    )

    frames_list = sorted(frames_in.glob("frame_*.png"))
    for i, fp in enumerate(frames_list):
        if i % 20 == 0:
            logger.info(f"  ESRGAN: {i}/{len(frames_list)}")
        img_bgr = np.array(Image.open(fp).convert("RGB"))[:, :, ::-1]
        enhanced, _ = upsamp.enhance(img_bgr, outscale=scale)
        if scale != netscale:
            h, w = enhanced.shape[:2]
            nh = int(h * scale / netscale)
            nw = int(w * scale / netscale)
            enhanced = np.array(Image.fromarray(
                enhanced[:, :, ::-1]).resize((nw, nh), Image.LANCZOS))[:, :, ::-1]
        Image.fromarray(enhanced[:, :, ::-1]).save(str(frames_out / fp.name))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    _merge_frames(frames_out, output_path, fps)
    shutil.rmtree(tmp, ignore_errors=True)

    mb = output_path.stat().st_size / 1e6
    logger.info(f"✅ ESRGAN done: {output_path} ({mb:.1f}MB)")
    return output_path
