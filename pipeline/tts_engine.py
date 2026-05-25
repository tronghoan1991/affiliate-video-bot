"""
pipeline/tts_engine.py — Free TTS cho tiếng Việt
================================================
Dùng Microsoft Edge TTS (hoàn toàn miễn phí, không cần API key):
  - vi-VN-HoaiMyNeural   — Giọng nữ, truyền cảm, tự nhiên
  - vi-VN-NamMinhNeural  — Giọng nam, ấm, chuyên nghiệp

Fallback: gTTS (Google TTS, miễn phí)
"""
import asyncio, logging, os, re, tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger("TTSEngine")

# ── Voice profiles ────────────────────────────────────────────────────────────
VOICE_PROFILES = {
    "female": {
        "voice":   "vi-VN-HoaiMyNeural",
        "rate":    "+8%",     # Hơi nhanh hơn bình thường — tự nhiên
        "pitch":   "+2Hz",    # Cao hơn chút — dễ nghe
        "volume":  "+10%",
    },
    "male": {
        "voice":   "vi-VN-NamMinhNeural",
        "rate":    "+5%",
        "pitch":   "-2Hz",    # Thấp hơn — ấm hơn
        "volume":  "+10%",
    },
    "child": {
        "voice":   "vi-VN-HoaiMyNeural",
        "rate":    "+15%",    # Nhanh hơn, vui hơn
        "pitch":   "+5Hz",
        "volume":  "+10%",
    },
}


async def _tts_async(script: str, voice: str, rate: str,
                     pitch: str, volume: str, output_path: str):
    """Tạo audio từ script dùng edge-tts."""
    import edge_tts
    communicate = edge_tts.Communicate(
        script, voice, rate=rate, pitch=pitch, volume=volume
    )
    await communicate.save(output_path)


def generate_voiceover(
    script: str,
    gender: str = "female",
    output_path: Optional[str] = None,
    speed_multiplier: float = 1.0,
) -> Optional[str]:
    """
    Tạo file audio MP3 từ script tiếng Việt.
    Returns: đường dẫn file MP3, hoặc None nếu lỗi.
    """
    if not output_path:
        output_path = tempfile.mktemp(suffix=".mp3")

    profile = VOICE_PROFILES.get(gender, VOICE_PROFILES["female"])

    # Điều chỉnh rate nếu cần speed khác
    if speed_multiplier != 1.0:
        base_rate = int(profile["rate"].replace("%", "").replace("+", ""))
        adj_rate  = int(base_rate + (speed_multiplier - 1.0) * 20)
        rate_str  = f"+{adj_rate}%" if adj_rate >= 0 else f"{adj_rate}%"
    else:
        rate_str = profile["rate"]

    # ── Method 1: edge-tts ────────────────────────────────────────────────────
    try:
        asyncio.run(_tts_async(
            script, profile["voice"], rate_str,
            profile["pitch"], profile["volume"], output_path
        ))
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            duration = _get_audio_duration(output_path)
            logger.info(f"✅ TTS (edge-tts): {duration:.1f}s | {output_path}")
            return output_path
    except Exception as e:
        logger.warning(f"edge-tts fail: {e}")

    # ── Method 2: gTTS fallback ────────────────────────────────────────────────
    try:
        from gtts import gTTS
        tts = gTTS(text=script, lang="vi", slow=False)
        tts.save(output_path)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            duration = _get_audio_duration(output_path)
            logger.info(f"✅ TTS (gTTS fallback): {duration:.1f}s")
            return output_path
    except Exception as e:
        logger.warning(f"gTTS fail: {e}")

    logger.error("TTS failed — cả edge-tts và gTTS đều lỗi")
    return None


def _get_audio_duration(path: str) -> float:
    """Lấy thời lượng audio (giây)."""
    try:
        from moviepy.editor import AudioFileClip
        clip = AudioFileClip(path)
        d    = clip.duration
        clip.close()
        return d
    except Exception:
        return 0.0


def split_script_to_segments(script: str) -> list[dict]:
    """
    Tách script thành các segment có timing.
    Mỗi segment = 1 cảnh quay trong video.
    Returns: [{"text": str, "scene": str, "duration_hint": float}]
    """
    # Tách theo dấu câu / dòng mới
    raw_parts = re.split(r"(?<=[.!?…])\s+|\n+", script.strip())
    segments  = []
    for part in raw_parts:
        part = part.strip()
        if len(part) < 5:
            continue
        # Ước tính thời gian nói (~130 từ/phút tiếng Việt)
        word_count    = len(part.split())
        duration_hint = max(2.0, word_count / 2.2)

        # Gắn scene hint dựa trên nội dung
        scene = _detect_scene_type(part)
        segments.append({
            "text":          part,
            "scene":         scene,
            "duration_hint": duration_hint,
        })

    return segments


def _detect_scene_type(text: str) -> str:
    """Phát hiện loại cảnh phù hợp với đoạn script."""
    text_lower = text.lower()
    if any(w in text_lower for w in ["nhìn", "xem", "đây", "này", "cận", "chi tiết", "texture"]):
        return "close_up"       # Cảnh cận cảnh sản phẩm
    elif any(w in text_lower for w in ["mặc", "đội", "đeo", "dùng", "dùng thử", "thử"]):
        return "wearing"        # Cảnh người mặc sản phẩm
    elif any(w in text_lower for w in ["trước", "sau", "thay đổi", "kết quả", "khác biệt"]):
        return "before_after"   # Cảnh so sánh
    elif any(w in text_lower for w in ["link", "đặt", "mua", "order", "giá", "freeship"]):
        return "cta"            # Cảnh CTA
    elif any(w in text_lower for w in ["tôi", "mình", "thật ra", "nói thật", "thực tế"]):
        return "talking_head"   # Cảnh người nói chuyện
    else:
        return "product_showcase"  # Default: hiển thị sản phẩm
