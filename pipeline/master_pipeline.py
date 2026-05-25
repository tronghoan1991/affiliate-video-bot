"""
pipeline/master_pipeline.py — Master Orchestrator
===================================================
Điều phối toàn bộ pipeline:
  1. Phân tích sản phẩm
  2. Tách nền (rembg)
  3. AI Try-On (IDM-VTON / OOTDiffusion / composite)
  4. Tạo background (SD / Pixabay / gradient)
  5. Sinh script + TTS giọng Việt
  6. Compose video đa cảnh chuyên nghiệp
  7. Mix nhạc
  8. Export 1080p
"""
import base64, io, logging, time, traceback
from pathlib import Path
from typing import Optional, Callable
from PIL import Image

logger = logging.getLogger("MasterPipeline")


def run_full_pipeline(
    product_b64:   str,
    model_b64:     Optional[str],
    product_info:  dict,
    drive_root:    Path,
    callback_url:  str,
    progress_url:  str,
    user_id:       int,
    bot_secret:    str,
) -> dict:
    """
    Entry point từ Colab Flask server.
    Returns: {"video_path": str, "caption": str} hoặc {"error": str}
    """
    import requests

    def pb(msg: str):
        if progress_url:
            try:
                requests.post(progress_url,
                              json={"user_id": user_id, "message": msg},
                              headers={"X-Bot-Secret": bot_secret},
                              timeout=5)
            except Exception:
                pass
        logger.info(msg)

    def callback(step: str, data: dict):
        if callback_url:
            try:
                payload = {"step": step, "user_id": user_id, **data}
                requests.post(callback_url, json=payload,
                              headers={"X-Bot-Secret": bot_secret},
                              timeout=15)
            except Exception as e:
                logger.warning(f"Callback fail: {e}")

    try:
        # ── Imports ───────────────────────────────────────────────────────
        from pipeline.product_analyzer    import analyze_product
        from pipeline.emotional_engine    import build_emotional_package
        from pipeline.script_generator    import generate_full_script
        from pipeline.tts_engine          import generate_voiceover
        from pipeline.background_generator import get_background, COLOR_SCHEMES
        from pipeline.colab_pipeline      import (remove_background,
                                                   auto_select_model, ai_tryon)
        from pipeline.video_composer      import compose_video
        from pipeline.music_engine        import get_music, CATEGORY_MOODS

        name     = product_info.get("name", "Sản phẩm")
        price    = product_info.get("price", "")
        desc     = product_info.get("description", name)
        platform = product_info.get("platform", "tiktok")

        # ═══════════════════════════════════════════════
        # STEP 1: Phân tích sản phẩm
        # ═══════════════════════════════════════════════
        pb("🔍 *Bước 1/8* — Phân tích sản phẩm...")
        analysis  = analyze_product(name, desc, price)
        emotional = build_emotional_package(
            name, analysis.category, analysis.gender, price)
        category  = analysis.category
        gender    = analysis.gender
        logger.info(f"Category: {category} | Gender: {gender} | "
                    f"Tier: {analysis.price_tier}")

        # ═══════════════════════════════════════════════
        # STEP 2: Tách nền sản phẩm
        # ═══════════════════════════════════════════════
        pb("✂️ *Bước 2/8* — Tách nền sản phẩm...")
        product_clean_b64 = remove_background(product_b64)
        product_img       = _b64_to_pil(product_clean_b64)

        # Gửi preview tách nền
        callback("bg_removed", {"image_b64": product_clean_b64,
                                 "product_info": product_info})

        # ═══════════════════════════════════════════════
        # STEP 3: Chọn / xử lý ảnh người mẫu
        # ═══════════════════════════════════════════════
        pb("👤 *Bước 3/8* — Xử lý ảnh người mẫu...")
        if not model_b64:
            model_b64 = auto_select_model(category, gender)
            pb(f"   → Auto-chọn model từ thư viện ({category}/{gender})")

        # ═══════════════════════════════════════════════
        # STEP 4: AI Virtual Try-On
        # ═══════════════════════════════════════════════
        pb("👗 *Bước 4/8* — AI Try-On (model mặc sản phẩm)...\n"
           "   ⏱️ ~3-5 phút")
        tryon_b64 = ai_tryon(product_clean_b64, model_b64, category)
        tryon_img = _b64_to_pil(tryon_b64)

        # Gửi preview try-on
        callback("tryon_preview", {"image_b64": tryon_b64})

        # ═══════════════════════════════════════════════
        # STEP 5: Tạo background AI
        # ═══════════════════════════════════════════════
        pb("🎨 *Bước 5/8* — Tạo background scene AI...")
        # Detect nếu có SD model
        has_sd = (drive_root / "models" / "flux1-schnell").exists() or \
                 (drive_root / "models" / "stable-diffusion-2-1").exists()
        bg_img = get_background(category, gender, drive_root, use_ai=has_sd)

        # ═══════════════════════════════════════════════
        # STEP 6: Sinh script + TTS
        # ═══════════════════════════════════════════════
        pb("📝 *Bước 6/8* — Sinh script reviewer + giọng TTS...")
        script_obj = generate_full_script(
            product_info, analysis, emotional, platform)

        pb(f"   → Script: {len(script_obj.scenes)} cảnh | "
           f"~{script_obj.duration_est:.0f}s")

        audio_path = generate_voiceover(
            script     = script_obj.full_text,
            gender     = gender,
            speed_multiplier = 1.05,
        )
        if audio_path:
            pb("   → TTS: ✅ Giọng tiếng Việt")
        else:
            pb("   → TTS: ⚠️ Lỗi, video sẽ không có giọng nói")

        # ═══════════════════════════════════════════════
        # STEP 7: Nhạc nền
        # ═══════════════════════════════════════════════
        pb("🎵 *Bước 7/8* — Lấy nhạc nền phù hợp...")
        moods      = CATEGORY_MOODS.get(category, ["trendy_pop"])
        music_mood = emotional.emotional_music or moods[0]
        music_path = get_music(
            mood       = music_mood,
            category   = category,
            duration   = script_obj.duration_est + 5,
            drive_root = drive_root,
        )
        pb(f"   → Nhạc: {'✅' if music_path else '⚠️ fallback procedural'}")

        # ═══════════════════════════════════════════════
        # STEP 8: Compose video đa cảnh
        # ═══════════════════════════════════════════════
        pb("🎬 *Bước 8/8* — Render video chuyên nghiệp...\n"
           "   ⏱️ ~5-10 phút")

        # Merge audio: voice + music
        final_audio = _merge_audio(audio_path, music_path, script_obj.duration_est)

        # Color accent theo ngành hàng
        color_accent = COLOR_SCHEMES.get(
            category, COLOR_SCHEMES["fashion"])["accent"]

        video_path = compose_video(
            scenes_data  = script_obj.scenes,
            product_img_pil = product_img,
            tryon_img_pil   = tryon_img,
            bg_img_pil      = bg_img,
            audio_path      = final_audio,
            drive_root      = drive_root,
            product_name    = name,
            price           = price,
            color_accent    = color_accent,
            progress_cb     = pb,
        )

        size_mb = video_path.stat().st_size / 1e6
        pb(f"✅ *Video hoàn tất!*\n"
           f"   📹 {video_path.name}\n"
           f"   📦 {size_mb:.1f} MB\n"
           f"   ⏱️ ~{script_obj.duration_est:.0f} giây")

        # Lưu caption
        caption_path = drive_root / "outputs" / "captions" / \
                       f"{name.replace(' ','_')}_{int(time.time())}.txt"
        caption_path.parent.mkdir(parents=True, exist_ok=True)
        caption_path.write_text(script_obj.caption, encoding="utf-8")

        return {
            "video_path": str(video_path),
            "caption":    script_obj.caption,
            "duration":   script_obj.duration_est,
            "scenes":     len(script_obj.scenes),
        }

    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)[:300]}


def _b64_to_pil(b64: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGBA")


def _merge_audio(voice_path: Optional[str], music_path: Optional[str],
                 duration: float) -> Optional[str]:
    """Merge voice + music với volume balance chuẩn."""
    import tempfile, os
    if not voice_path and not music_path:
        return None
    if not voice_path:
        return music_path
    if not music_path:
        return voice_path

    try:
        from moviepy.editor import AudioFileClip, CompositeAudioClip
        from moviepy.audio.AudioClip import concatenate_audioclips

        voice = AudioFileClip(voice_path).volumex(1.0)
        music = AudioFileClip(music_path).volumex(0.22)  # Nhạc nhỏ hơn giọng

        # Loop nếu cần
        for clip in [voice, music]:
            pass  # Reference để không bị GC

        if music.duration < duration:
            loops = int(duration / music.duration) + 1
            music = concatenate_audioclips([music] * loops)

        voice = voice.subclip(0, min(voice.duration, duration))
        music = music.subclip(0, duration)

        mixed   = CompositeAudioClip([voice, music])
        tmp     = tempfile.mktemp(suffix=".mp3")
        mixed.write_audiofile(tmp, fps=44100,
                              nbytes=2, bitrate="192k",
                              logger=None)
        return tmp
    except Exception as e:
        logger.warning(f"Audio merge fail: {e}")
        return voice_path or music_path
