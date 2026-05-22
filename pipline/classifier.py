"""
pipeline/classifier.py — Phân loại trang phục bằng CLIP zero-shot.
"""
import logging
from pathlib import Path
from typing import Optional

import torch
from PIL import Image

logger = logging.getLogger("Classifier")
_model = _proc = None


def _load(device: str = "cpu"):
    global _model, _proc
    if _model is None:
        from transformers import CLIPModel, CLIPProcessor
        logger.info("Loading CLIP for garment classification...")
        _model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(device)
        _proc  = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    return _model, _proc


def classify_garment(
    image_path: Path,
    labels: Optional[list] = None,
    device: str = "cpu",
) -> str:
    from config import Config
    if labels is None:
        labels = Config.GARMENT_LABELS
    try:
        img   = Image.open(image_path).convert("RGB")
        m, p  = _load(device)
        texts = [f"a photo of a {l}" for l in labels]
        inp   = p(text=texts, images=img, return_tensors="pt", padding=True).to(device)
        with torch.no_grad():
            logits = m(**inp).logits_per_image.softmax(dim=1).squeeze()
        best = logits.argmax().item()
        logger.info(f"Garment: '{labels[best]}' ({logits[best]:.1%})")
        return labels[best]
    except Exception as e:
        logger.warning(f"Classifier fallback: {e}")
        return "casual t-shirt"
