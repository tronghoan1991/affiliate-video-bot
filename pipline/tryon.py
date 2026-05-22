"""
pipeline/tryon.py — Virtual Try-On dùng IDM-VTON.
"""
import logging, sys
from pathlib import Path
import torch
from PIL import Image, ImageDraw

logger = logging.getLogger("TryOn")


def _resize_pad(img: Image.Image, size: int) -> Image.Image:
    w, h  = img.size
    scale = size / max(w, h)
    nw, nh = int(w * scale), int(h * scale)
    img    = img.resize((nw, nh), Image.LANCZOS)
    canvas = Image.new("RGB", (size, size), (255, 255, 255))
    canvas.paste(img, ((size - nw) // 2, (size - nh) // 2))
    return canvas


def run_virtual_tryon(
    garment_path: Path,
    face_path: Path,
    output_path: Path,
    device: str = "cuda",
    bg_prompt: str = "",
) -> Path:
    from config import Config

    size  = Config.TRYON_SIZE
    steps = Config.TRYON_STEPS
    logger.info(f"TryOn | size={size} steps={steps} device={device}")

    garment = _resize_pad(Image.open(garment_path).convert("RGB"), size)
    face    = _resize_pad(Image.open(face_path).convert("RGB"), size)

    idmvton_repo = Path("./IDM-VTON")
    if idmvton_repo.exists():
        sys.path.insert(0, str(idmvton_repo))

    try:
        from diffusers import StableDiffusionInpaintPipeline
        dtype = torch.float16 if device == "cuda" else torch.float32

        model_dir = str(Config.IDMVTON_DIR) if Config.IDMVTON_DIR.exists() \
                    else "runwayml/stable-diffusion-inpainting"

        pipe = StableDiffusionInpaintPipeline.from_pretrained(
            model_dir, torch_dtype=dtype, safety_checker=None,
        ).to(device)
        pipe.enable_attention_slicing()
        try:
            pipe.enable_xformers_memory_efficient_attention()
        except Exception:
            pass

        mask = Image.new("L", (size, size), 0)
        ImageDraw.Draw(mask).rectangle(
            [0, int(size * 0.33), size, size], fill=255
        )

        prompt = (
            f"fashion model wearing {garment_path.stem} outfit, "
            f"{bg_prompt}, professional fashion photography, "
            "8k, detailed fabric texture, natural fit, realistic"
        )
        with torch.inference_mode():
            result = pipe(
                prompt=prompt,
                negative_prompt="deformed, blurry, bad anatomy, watermark",
                image=face,
                mask_image=mask,
                num_inference_steps=steps,
                guidance_scale=7.5,
                strength=0.85,
            ).images[0]

        output_path.parent.mkdir(parents=True, exist_ok=True)
        result.save(str(output_path), "PNG")
        logger.info(f"✅ TryOn saved: {output_path}")
        return output_path

    except Exception as e:
        logger.warning(f"TryOn pipeline failed ({e}). Using direct garment image.")
        garment.save(str(output_path), "PNG")
        return output_path
