"""
pipeline/caption_gen.py — Caption Generator v6
Wrapper tiện lợi để sinh caption và viral package.
"""
from pipeline.viral_strategy import build_viral_content, ViralContent


def generate_caption(
    name: str,
    price: str,
    description: str,
    platform: str = "tiktok",
    gender_override: str = "",
) -> str:
    """Sinh caption nhanh cho 1 platform."""
    vc = build_viral_content(name, price, description, platform, gender_override)
    return vc.caption_tiktok if platform == "tiktok" else vc.caption_shopee


def generate_viral_package(
    name: str,
    price: str,
    description: str,
    platform: str = "tiktok",
    gender_override: str = "",
) -> ViralContent:
    """Sinh gói viral đầy đủ: caption + hook + CTA + hashtags + music mood."""
    return build_viral_content(name, price, description, platform, gender_override)
