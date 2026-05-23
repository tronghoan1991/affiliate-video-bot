"""
pipeline/caption_gen.py — Caption Generator v5 (backward-compatible wrapper)
"""
from pipeline.viral_strategy import build_caption, build_viral_content, ViralContent


def generate_caption(name: str = "", price: str = "", garment: str = "", platform: str = "tiktok") -> str:
    return build_caption(name=name, price=price, garment=garment, platform=platform)


def generate_viral_package(name: str = "", price: str = "", garment: str = "", platform: str = "tiktok") -> ViralContent:
    return build_viral_content(name=name, price=price, garment=garment, platform=platform)
