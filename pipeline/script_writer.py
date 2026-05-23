"""
pipeline/script_writer.py — Video Script Writer v6
=============================================================================
Nhận GarmentAnalysis → sinh VideoScript hoàn chỉnh cho 15s video.
Timeline chuẩn 2026 viral format:
  0–2.5s   : HOOK — dừng scroll
  2.5–6s   : PRODUCT REVEAL — tên + giá
  6–10s    : VALUE STACK — lý do mua
  10–13s   : CTA + COMMENT — chốt đơn + tăng reach x4
  13–15s   : LOOP — seamless loop
=============================================================================
"""
import random
from pipeline.ai_analyzer import GarmentAnalysis, VideoScript, SceneBlock
from pipeline.viral_strategy import (
    build_viral_content, _MUSIC_MOOD, _VALUE_STACKS,
    _COMMENT_CTAS, _CTA_TIKTOK, _CTA_SHOPEE,
    _URGENCY_BADGES, _SOCIAL_PROOF_POOL,
)
from pipeline.background import get_full_prompt, get_hook_frame_prompt, get_loop_prompt


def write_video_script(
    analysis: GarmentAnalysis,
    product_name: str,
    price: str,
    platform: str = "tiktok",
) -> VideoScript:
    """
    Sinh VideoScript hoàn chỉnh từ GarmentAnalysis.
    Tự động chọn hook, value stack, CTA, music mood, AI prompt.
    """
    vc = build_viral_content(
        name=product_name,
        price=price,
        garment=analysis.raw_description or analysis.garment_type,
        platform=platform,
        gender_override=analysis.gender,
    )

    gender = analysis.gender
    gkey   = analysis.garment_key
    badge  = random.choice(_URGENCY_BADGES)
    proof  = random.choice(_SOCIAL_PROOF_POOL)

    # ── Cảnh HOOK ──────────────────────────────────────────────────────────────
    hook_scene = SceneBlock(
        hook_text    = vc.hook_text,
        subtext      = vc.hook_subtext,
        duration     = 2.5,
        transition   = "zoom_in",
        overlay_style= "hook_top",
    )

    # ── Cảnh PRODUCT REVEAL ────────────────────────────────────────────────────
    reveal_scene = SceneBlock(
        hook_text    = f"{product_name} — {proof}",
        subtext      = f"💰 {price}",
        duration     = 3.5,
        transition   = "slide_up",
        overlay_style= "product_mid",
    )

    # ── Cảnh VALUE STACK ───────────────────────────────────────────────────────
    value_scene = SceneBlock(
        hook_text    = vc.value_stack,
        subtext      = vc.micro_story[:80] if vc.micro_story else "",
        duration     = 4.0,
        transition   = "fade",
        overlay_style= "value_bottom",
    )

    # ── Cảnh CTA ───────────────────────────────────────────────────────────────
    cta = vc.cta_tiktok if platform == "tiktok" else vc.cta_shopee
    cta_scene = SceneBlock(
        hook_text    = cta,
        subtext      = vc.comment_cta,
        duration     = 3.0,
        transition   = "zoom_out",
        overlay_style= "cta_full",
    )

    # ── Cảnh LOOP ──────────────────────────────────────────────────────────────
    loop_scene = SceneBlock(
        hook_text    = badge,
        subtext      = "Link ở BIO 👆",
        duration     = 2.0,
        transition   = "fade",
        overlay_style= "badge_corner",
    )

    # ── AI Prompts ─────────────────────────────────────────────────────────────
    prompt_main = get_full_prompt(
        gkey, gender,
        product_name=product_name,
        colors=analysis.color_palette,
        material=analysis.material_feel,
    )
    prompt_hook = get_hook_frame_prompt(gkey, gender)
    prompt_loop = get_loop_prompt(gkey, gender)

    # ── Caption ────────────────────────────────────────────────────────────────
    caption = vc.caption_tiktok if platform == "tiktok" else vc.caption_shopee

    return VideoScript(
        title           = product_name,
        duration_seconds= 15.0,
        platform        = platform,
        hook_scene      = hook_scene,
        reveal_scene    = reveal_scene,
        value_scene     = value_scene,
        cta_scene       = cta_scene,
        loop_scene      = loop_scene,
        ai_prompt_main  = prompt_main,
        ai_prompt_hook  = prompt_hook,
        caption         = caption,
        music_mood      = vc.music_mood,
        hashtags        = vc.hashtags_tiktok if platform == "tiktok" else vc.hashtags_shopee,
    )
