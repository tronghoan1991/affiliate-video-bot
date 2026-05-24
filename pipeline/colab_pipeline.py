"""
pipeline/colab_pipeline.py
Chạy trên Colab GPU — nhận request từ Render, xử lý, callback về
"""
import base64, io, json, logging, os, tempfile, threading, time
from pathlib import Path
import requests
import numpy as np
from PIL import Image

logger = logging.getLogger("ColabPipeline")

DRIVE_ROOT = Path(os.getenv("DRIVE_ROOT", "/content/drive/MyDrive/AffiliateStudio"))


# ═══════════════════════════════════════════════════════════════
# STEP 1: BACKGROUND REMOVAL
# ═══════════════════════════════════════════════════════════════

def remove_background(img_b64: str) -> str:
    """
    Tách nền sản phẩm → ảnh PNG nền trắng.
    Thử theo thứ tự: rembg (local) → remove.bg API → fallback GrabCut
    """
    img_bytes = base64.b64decode(img_b64)
    img_pil   = Image.open(io.BytesIO(img_bytes)).convert("RGBA")

    # ── Method 1: rembg (chạy local trên Colab, miễn phí) ──────────────────
    try:
        from rembg import remove as rembg_remove
        output = rembg_remove(img_pil)
        # Đặt nền trắng
        white_bg = Image.new("RGBA", output.size, (255, 255, 255, 255))
        white_bg.paste(output, mask=output.split()[3])
        result = white_bg.convert("RGB")
        logger.info("✅ BG removed via rembg")
        return _img_to_b64(result)
    except Exception as e:
        logger.warning(f"rembg fail: {e}")

    # ── Method 2: remove.bg API (free: 50 ảnh/tháng) ───────────────────────
    REMOVEBG_KEY = os.getenv("REMOVEBG_API_KEY", "")
    if REMOVEBG_KEY:
        try:
            r = requests.post(
                "https://api.remove.bg/v1.0/removebg",
                files={"image_file": img_bytes},
                data={"size": "auto", "bg_color": "ffffff"},
                headers={"X-Api-Key": REMOVEBG_KEY},
                timeout=30
            )
            if r.status_code == 200:
                result = Image.open(io.BytesIO(r.content)).convert("RGB")
                logger.info("✅ BG removed via remove.bg API")
                return _img_to_b64(result)
        except Exception as e:
            logger.warning(f"remove.bg fail: {e}")

    # ── Method 3: GrabCut fallback (OpenCV) ────────────────────────────────
    try:
        import cv2
        img_cv = np.array(img_pil.convert("RGB"))
        mask   = np.zeros(img_cv.shape[:2], np.uint8)
        bgd    = np.zeros((1, 65), np.float64)
        fgd    = np.zeros((1, 65), np.float64)
        h, w   = img_cv.shape[:2]
        rect   = (int(w*0.05), int(h*0.05), int(w*0.9), int(h*0.9))
        cv2.grabCut(img_cv, mask, rect, bgd, fgd, 5, cv2.GC_INIT_WITH_RECT)
        mask2  = np.where((mask == 2) | (mask == 0), 0, 1).astype("uint8")
        result_cv = img_cv * mask2[:, :, np.newaxis]
        result_cv[mask2 == 0] = [255, 255, 255]
        result = Image.fromarray(result_cv)
        logger.info("✅ BG removed via GrabCut fallback")
        return _img_to_b64(result)
    except Exception as e:
        logger.error(f"GrabCut fail: {e}")
        # Trả về ảnh gốc nếu tất cả fail
        return img_b64


# ═══════════════════════════════════════════════════════════════
# STEP 2: AUTO-SELECT MODEL nếu không có ảnh người mẫu
# ═══════════════════════════════════════════════════════════════

def auto_select_model(category: str, gender: str) -> str:
    """
    Tự chọn ảnh người mẫu từ thư viện trên Drive.
    Trả về base64 của ảnh người mẫu được chọn.
    """
    model_dir = DRIVE_ROOT / "models" / category
    # Fallback theo gender nếu không có folder theo category
    if not model_dir.exists():
        gender_dir = DRIVE_ROOT / "models" / gender  # male/female/child/unisex
        if gender_dir.exists():
            model_dir = gender_dir
        else:
            model_dir = DRIVE_ROOT / "models" / "unisex"

    if model_dir.exists():
        imgs = list(model_dir.glob("*.jpg")) + list(model_dir.glob("*.png"))
        if imgs:
            chosen = imgs[int(time.time()) % len(imgs)]  # round-robin
            with open(chosen, "rb") as f:
                logger.info(f"✅ Auto-selected model: {chosen.name}")
                return base64.b64encode(f.read()).decode()

    # Fallback: tải model stock từ internet
    logger.warning("No local models found, using placeholder")
    return _get_placeholder_model(gender)

def _get_placeholder_model(gender: str) -> str:
    """Tạo placeholder figure nếu không có model."""
    from PIL import ImageDraw
    img  = Image.new("RGB", (512, 768), (220, 210, 200))
    draw = ImageDraw.Draw(img)
    # Simple silhouette
    draw.ellipse([180, 40, 332, 192], fill=(180, 160, 140))   # head
    draw.rectangle([200, 192, 312, 480], fill=(100, 100, 120)) # body
    draw.rectangle([160, 480, 230, 700], fill=(80, 80, 100))   # left leg
    draw.rectangle([282, 480, 352, 700], fill=(80, 80, 100))   # right leg
    return _img_to_b64(img)


# ═══════════════════════════════════════════════════════════════
# STEP 3: AI VIRTUAL TRY-ON
# ═══════════════════════════════════════════════════════════════

def ai_tryon(product_b64: str, model_b64: str, category: str) -> str:
    """
    AI Virtual Try-On: model mặc sản phẩm.
    Thử theo thứ tự: IDM-VTON local → OOTDiffusion → composite fallback
    """
    product_img = _b64_to_pil(product_b64)
    model_img   = _b64_to_pil(model_b64)

    # ── Method 1: IDM-VTON (State-of-the-art, chạy trên Colab T4) ──────────
    try:
        result = _tryon_idmvton(product_img, model_img, category)
        if result:
            logger.info("✅ Try-on via IDM-VTON")
            return _img_to_b64(result)
    except Exception as e:
        logger.warning(f"IDM-VTON fail: {e}")

    # ── Method 2: OOTDiffusion (lighter alternative) ────────────────────────
    try:
        result = _tryon_ootd(product_img, model_img, category)
        if result:
            logger.info("✅ Try-on via OOTDiffusion")
            return _img_to_b64(result)
    except Exception as e:
        logger.warning(f"OOTDiffusion fail: {e}")

    # ── Method 3: Smart Composite Fallback ──────────────────────────────────
    logger.warning("Using composite fallback for try-on")
    result = _tryon_composite(product_img, model_img)
    return _img_to_b64(result)


def _tryon_idmvton(product_img: Image.Image, model_img: Image.Image,
                   category: str) -> Image.Image:
    """IDM-VTON virtual try-on."""
    import torch
    from diffusers import AutoPipelineForInpainting

    model_path = str(DRIVE_ROOT / "models" / "idm-vton")
    if not os.path.exists(model_path):
        raise FileNotFoundError("IDM-VTON not downloaded")

    pipe = AutoPipelineForInpainting.from_pretrained(
        model_path, torch_dtype=torch.float16
    ).to("cuda")
    pipe.enable_xformers_memory_efficient_attention()

    # Resize cho consistency
    model_r   = model_img.resize((512, 768))
    product_r = product_img.resize((512, 512))

    # Garment category mapping
    cat_map = {
        "fashion": "upper_body", "fashion_kids": "upper_body",
        "sports": "upper_body",  "baby": "dresses",
        "beauty": "upper_body",  "home": "full_body",
    }
    garment_type = cat_map.get(category, "upper_body")

    prompt = (
        f"professional model wearing {garment_type} garment, "
        "high quality photo, fashion photography, white studio background, "
        "natural lighting, sharp focus, 4k resolution"
    )
    result = pipe(
        prompt=prompt,
        image=model_r,
        mask_image=_create_body_mask(model_r, garment_type),
        ip_adapter_image=product_r,
        strength=0.8,
        guidance_scale=7.5,
        num_inference_steps=30,
    ).images[0]
    return result


def _tryon_ootd(product_img: Image.Image, model_img: Image.Image,
                category: str) -> Image.Image:
    """OOTDiffusion try-on."""
    import torch
    ootd_path = str(DRIVE_ROOT / "models" / "ootdiffusion")
    if not os.path.exists(ootd_path):
        raise FileNotFoundError("OOTDiffusion not downloaded")

    # Simplified OOTDiffusion pipeline
    from diffusers import StableDiffusionInpaintPipeline
    pipe = StableDiffusionInpaintPipeline.from_pretrained(
        ootd_path, torch_dtype=torch.float16
    ).to("cuda")

    model_r   = model_img.resize((512, 768))
    product_r = product_img.resize((512, 512))

    prompt = (
        "photorealistic model wearing the garment, "
        "fashion photo shoot, studio lighting, high resolution"
    )
    result = pipe(
        prompt=prompt,
        image=model_r,
        mask_image=_create_body_mask(model_r, "upper_body"),
        strength=0.75,
        guidance_scale=8.0,
        num_inference_steps=25,
    ).images[0]
    return result


def _create_body_mask(model_img: Image.Image, area: str) -> Image.Image:
    """Tạo mask vùng cần inpaint (thân người)."""
    w, h = model_img.size
    mask = Image.new("L", (w, h), 0)
    from PIL import ImageDraw
    draw = ImageDraw.Draw(mask)
    if area == "upper_body":
        draw.rectangle([int(w*0.2), int(h*0.2), int(w*0.8), int(h*0.6)], fill=255)
    elif area == "dresses":
        draw.rectangle([int(w*0.15), int(h*0.15), int(w*0.85), int(h*0.85)], fill=255)
    else:  # full_body
        draw.rectangle([int(w*0.1), int(h*0.1), int(w*0.9), int(h*0.9)], fill=255)
    return mask


def _tryon_composite(product_img: Image.Image,
                     model_img: Image.Image) -> Image.Image:
    """Fallback: composite đơn giản — đặt ảnh sản phẩm lên model."""
    model_r   = model_img.resize((512, 768)).convert("RGBA")
    product_r = product_img.convert("RGBA")

    # Scale sản phẩm vừa phần thân
    pw = int(model_r.width * 0.65)
    ph = int(model_r.height * 0.45)
    product_s = product_r.resize((pw, ph), Image.LANCZOS)

    # Tăng transparency
    r, g, b, a = product_s.split()
    a = a.point(lambda x: int(x * 0.85))
    product_s = Image.merge("RGBA", (r, g, b, a))

    # Paste vào giữa thân
    px = (model_r.width - pw) // 2
    py = int(model_r.height * 0.22)
    model_r.paste(product_s, (px, py), product_s)
    return model_r.convert("RGB")


# ═══════════════════════════════════════════════════════════════
# STEP 4: BACKGROUND SELECTION + SCENE COMPOSITION
# ═══════════════════════════════════════════════════════════════

BACKGROUND_THEMES = {
    "fashion": [
        "minimalist white studio, soft shadows, fashion photography",
        "modern boutique store interior, warm lighting",
        "urban street style background, bokeh",
        "pink aesthetic bedroom, pastel colors",
    ],
    "fashion_kids": [
        "bright colorful playground, natural light",
        "white studio with toys, cheerful",
        "park outdoor, green grass, sunny day",
    ],
    "beauty": [
        "marble vanity table, soft pink lighting, luxury",
        "bathroom counter, natural window light",
        "minimalist white background, clean aesthetic",
    ],
    "health": [
        "gym interior, motivational, bright",
        "kitchen counter, morning light, wellness",
        "outdoor yoga mat, nature background",
    ],
    "sports": [
        "gym with equipment, energetic lighting",
        "outdoor track, dynamic motion blur",
        "sports court, action background",
    ],
    "home": [
        "cozy living room, warm lighting",
        "modern apartment interior, clean",
        "aesthetic desk setup, lifestyle",
    ],
    "food": [
        "kitchen counter, bright natural light",
        "cafe table, cozy atmosphere",
        "picnic outdoor, fresh and bright",
    ],
    "pet": [
        "cozy home with pet accessories, warm",
        "garden outdoor, sunny and bright",
    ],
    "baby": [
        "nursery room, soft pastel colors, safe",
        "white studio with baby props, gentle light",
    ],
    "tech": [
        "modern desk setup, RGB lighting, tech aesthetic",
        "minimalist workspace, clean white",
    ],
}

def select_background_prompt(category: str, gender: str) -> str:
    import random
    options = BACKGROUND_THEMES.get(category, BACKGROUND_THEMES["fashion"])
    base    = random.choice(options)
    gender_tag = {
        "female": "beautiful woman, elegant",
        "male":   "handsome man, confident",
        "child":  "cute child, happy",
        "unisex": "person, confident",
    }.get(gender, "person")
    return f"{gender_tag}, {base}, 4K, professional photo"


def generate_scene_background(prompt: str, size=(1080, 1920)) -> Image.Image:
    """Tạo background AI cho scene."""
    try:
        import torch
        from diffusers import StableDiffusionPipeline
        model_path = str(DRIVE_ROOT / "models" / "flux1-schnell")
        if not os.path.exists(model_path):
            model_path = "stabilityai/stable-diffusion-2-1"  # fallback HF

        pipe = StableDiffusionPipeline.from_pretrained(
            model_path, torch_dtype=torch.float16
        ).to("cuda")
        result = pipe(prompt, width=size[0]//2, height=size[1]//2,
                      num_inference_steps=20).images[0]
        return result.resize(size, Image.LANCZOS)
    except Exception as e:
        logger.warning(f"BG generation fail: {e}, using gradient fallback")
        return _gradient_bg(size)

def _gradient_bg(size=(1080, 1920)) -> Image.Image:
    w, h = size
    img  = Image.new("RGB", size)
    for y in range(h):
        r = int(255 * (1 - y/h) * 0.9 + 20)
        g = int(180 * (1 - y/h) * 0.8 + 30)
        b = int(220 * (y/h) * 0.7 + 80)
        for x in range(w):
            img.putpixel((x, y), (r, g, b))
    return img


# ═══════════════════════════════════════════════════════════════
# STEP 5: TALKING VIDEO GENERATION
# ═══════════════════════════════════════════════════════════════

def generate_talking_video(
    tryon_img_b64: str,
    script: str,
    product_info: dict,
    category: str,
    gender: str,
    drive: object,
    progress_cb=None,
) -> Path:
    """
    Tạo video hoàn chỉnh:
    1. Tạo background scene
    2. Composite model+product lên scene
    3. Animate (talking) → HeyGen hoặc Wav2Lip
    4. Overlay text, caption, CTA
    5. Add music
    6. Lưu Drive → trả về Path
    """
    from pipeline.video_engine import build_video_from_frames
    from pipeline.music_engine import get_music
    from pipeline.text_overlay import add_overlays
    from pipeline.viral_caption import generate_viral_caption
    from pipeline.emotional_engine import build_emotional_package
    from pipeline.product_analyzer import analyze_product

    if progress_cb: progress_cb("🎨 Phân tích sản phẩm và cảm xúc...")

    name  = product_info.get("name", "Sản phẩm")
    price = product_info.get("price", "")
    desc  = product_info.get("description", name)
    plat  = product_info.get("platform", "tiktok")

    analysis  = analyze_product(name, desc, price)
    emotional = build_emotional_package(name, category, gender, price)
    vc        = generate_viral_caption(name, price, category, gender, emotional, plat)

    if progress_cb: progress_cb("🖼️ Tạo background scene...")
    bg_prompt = select_background_prompt(category, gender)
    bg_img    = generate_scene_background(bg_prompt, size=(1080, 1920))

    if progress_cb: progress_cb("👗 Ghép model lên scene...")
    tryon_img = _b64_to_pil(tryon_img_b64).resize((700, 1050), Image.LANCZOS)
    scene_img = bg_img.copy()
    # Paste model vào giữa-dưới scene
    px = (1080 - 700) // 2
    py = 1920 - 1050 - 80
    scene_img.paste(tryon_img, (px, py))

    if progress_cb: progress_cb("🎬 Tạo animation video...")
    # Tạo video base từ scene_img + animation
    video_path = _animate_scene(scene_img, script, gender, emotional, drive, progress_cb)

    if progress_cb: progress_cb("🎵 Thêm nhạc nền...")
    music_path = get_music(emotional.emotional_music, duration=15)
    if music_path:
        video_path = _mix_audio(video_path, music_path)

    if progress_cb: progress_cb("📝 Thêm text overlay & caption...")
    video_path = add_overlays(
        video_path=video_path,
        hook_text=emotional.hook_curiosity[:60],
        product_name=name, price=price,
        cta_text=vc.cta_bio,
        badge_text=emotional.urgency_line[:35],
    )

    # Lưu vào Drive
    output_dir  = drive.drive_root / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)
    final_path  = output_dir / f"{name.replace(' ','_')}_{int(time.time())}.mp4"
    import shutil
    shutil.copy2(str(video_path), str(final_path))
    logger.info(f"✅ Video saved: {final_path}")

    return final_path, vc.tiktok if plat == "tiktok" else vc.shopee


def _animate_scene(scene_img: Image.Image, script: str, gender: str,
                   emotional, drive, progress_cb=None) -> Path:
    """
    Animate scene: thử Wav2Lip → stable video diffusion → ken burns fallback.
    """
    tmp_scene = tempfile.mktemp(suffix=".jpg")
    scene_img.save(tmp_scene, quality=95)

    # ── Method 1: Wan2.1-I2V (Image to Video) ──────────────────────────────
    try:
        model_path = str(drive.drive_root / "models" / "wan2.1-i2v-14B-480P")
        if os.path.exists(model_path):
            if progress_cb: progress_cb("🎬 Wan2.1 Image-to-Video đang render...")
            return _animate_wan21(tmp_scene, script, model_path)
    except Exception as e:
        logger.warning(f"Wan2.1 fail: {e}")

    # ── Method 2: CogVideoX ─────────────────────────────────────────────────
    try:
        model_path = str(drive.drive_root / "models" / "cogvideox-5b")
        if os.path.exists(model_path):
            if progress_cb: progress_cb("🎬 CogVideoX đang render...")
            return _animate_cogvideox(tmp_scene, script, model_path)
    except Exception as e:
        logger.warning(f"CogVideoX fail: {e}")

    # ── Method 3: Ken Burns + MoviePy fallback ──────────────────────────────
    if progress_cb: progress_cb("🎬 MoviePy ken burns render...")
    return _animate_kenburns(scene_img, script, gender, emotional)


def _animate_wan21(img_path: str, script: str, model_path: str) -> Path:
    import torch
    from diffusers import WanImageToVideoPipeline
    pipe = WanImageToVideoPipeline.from_pretrained(
        model_path, torch_dtype=torch.bfloat16
    ).to("cuda")
    pipe.enable_model_cpu_offload()

    prompt = (
        f"fashion model moving naturally, walking, posing, reviewing product, "
        f"talking to camera. {script[:100]}. "
        "smooth motion, cinematic, TikTok style vertical video"
    )
    img   = Image.open(img_path).resize((480, 832))
    video = pipe(image=img, prompt=prompt, num_frames=49,
                 guidance_scale=5.0).frames[0]

    tmp_out = Path(tempfile.mktemp(suffix=".mp4"))
    from moviepy.editor import ImageSequenceClip
    clip = ImageSequenceClip([np.array(f) for f in video], fps=16)
    clip.write_videofile(str(tmp_out), codec="libx264", audio=False, logger=None)
    return tmp_out


def _animate_cogvideox(img_path: str, script: str, model_path: str) -> Path:
    import torch
    from diffusers import CogVideoXImageToVideoPipeline
    pipe = CogVideoXImageToVideoPipeline.from_pretrained(
        model_path, torch_dtype=torch.bfloat16
    ).to("cuda")
    pipe.enable_model_cpu_offload()

    prompt = (
        "fashion model naturally moving, product showcase, "
        "talking to camera, TikTok vertical video, authentic style"
    )
    img    = Image.open(img_path).resize((480, 720))
    video  = pipe(image=img, prompt=prompt, num_frames=49,
                  guidance_scale=6.0).frames[0]

    tmp_out = Path(tempfile.mktemp(suffix=".mp4"))
    from moviepy.editor import ImageSequenceClip
    clip = ImageSequenceClip([np.array(f) for f in video], fps=16)
    clip.write_videofile(str(tmp_out), codec="libx264", audio=False, logger=None)
    return tmp_out


def _animate_kenburns(scene_img: Image.Image, script: str,
                      gender: str, emotional) -> Path:
    """Ken Burns zoom/pan effect — luôn hoạt động."""
    from moviepy.editor import (ImageClip, CompositeVideoClip,
                                 concatenate_videoclips)
    import numpy as np

    duration = 15
    fps      = 24
    size     = (1080, 1920)

    arr  = np.array(scene_img.resize(size, Image.LANCZOS))
    clip = ImageClip(arr).set_duration(duration)

    def zoom_effect(get_frame, t):
        scale  = 1 + 0.05 * (t / duration)
        frame  = Image.fromarray(get_frame(t))
        w_new  = int(size[0] * scale)
        h_new  = int(size[1] * scale)
        zoomed = frame.resize((w_new, h_new), Image.LANCZOS)
        ox     = (w_new - size[0]) // 2
        oy     = (h_new - size[1]) // 2
        return np.array(zoomed.crop((ox, oy, ox + size[0], oy + size[1])))

    animated = clip.fl(zoom_effect)

    tmp_out = Path(tempfile.mktemp(suffix=".mp4"))
    animated.write_videofile(
        str(tmp_out), fps=fps, codec="libx264",
        audio=False, logger=None,
        ffmpeg_params=["-crf", "23", "-preset", "fast"]
    )
    return tmp_out


def _mix_audio(video_path: Path, music_path: str) -> Path:
    """Mix nhạc nền vào video."""
    try:
        from moviepy.editor import VideoFileClip, AudioFileClip
        video = VideoFileClip(str(video_path))
        music = AudioFileClip(music_path).volumex(0.35).subclip(0, video.duration)
        final = video.set_audio(music)
        tmp   = Path(tempfile.mktemp(suffix=".mp4"))
        final.write_videofile(str(tmp), codec="libx264",
                               audio_codec="aac", logger=None)
        return tmp
    except Exception as e:
        logger.warning(f"Audio mix fail: {e}")
        return video_path


# ═══════════════════════════════════════════════════════════════
# SCRIPT GENERATOR — Nội dung video chạm cảm xúc
# ═══════════════════════════════════════════════════════════════

SCRIPT_TEMPLATES = {
    "fashion": [
        "Trời ơi! {name} này {price} mà chất như hàng triệu! "
        "Chị em ơi xem xem, {benefit}. "
        "Mình mặc đi cafe, đi chơi đều được hết. "
        "Comment 'muốn' để mình tag link nhé! {urgency}",

        "Đây là lần đầu mình mặc mà được khen nhiều vậy 🥹 "
        "{name} - {price} thôi mà ai cũng hỏi mua đâu. "
        "{benefit}. Freeship hôm nay, đặt ngay kẻo hết size!",
    ],
    "beauty": [
        "Sau 7 ngày dùng {name} {price}... da mình như thế này nè! "
        "{benefit}. Không phải filter không phải kem nền. "
        "Đừng bỏ qua nếu bạn đang tìm giải pháp cho da. {urgency}",

        "Người ta hỏi mình dùng gì mà da căng mịn vậy 😭 "
        "Bí quyết chỉ là {name} thôi! {price} mà hiệu quả như spa. "
        "{benefit}. Link trong bio, order ngay hôm nay!",
    ],
    "health": [
        "30 ngày uống {name} — đây là kết quả thật của mình. "
        "{benefit}. {price} cho 1 tháng khoẻ mạnh không đáng sao? "
        "Tặng kèm quà khi order hôm nay! {urgency}",
    ],
    "sports": [
        "Set gym {name} {price} này chuẩn không cần chỉnh! "
        "{benefit}. Mặc tập mà ai cũng ngoái nhìn 💪 "
        "Flash sale hôm nay thôi, đặt liền kẻo hết!",
    ],
    "baby": [
        "Mẹ ơi! {name} {price} cho bé mà mình xài rồi không thể thiếu. "
        "{benefit}. An toàn 100% cho bé từ 0 tháng. "
        "Các mẹ comment 'bé' để mình tag link nhé! {urgency}",
    ],
    "home": [
        "Nhà mình từ khi có {name} {price} thay đổi hoàn toàn! "
        "{benefit}. Đặt hôm nay có freeship và quà tặng kèm. {urgency}",
    ],
    "food": [
        "{name} {price} này ngon không tưởng! "
        "{benefit}. Ăn một lần là ghiền, mua cho cả nhà luôn đi! "
        "Flash deal hôm nay, order ngay! {urgency}",
    ],
    "pet": [
        "Boss nhà mình THÍCH {name} {price} này lắm! "
        "{benefit}. Thú cưng của bạn xứng đáng được yêu thương nhất. "
        "Link trong bio, freeship toàn quốc! {urgency}",
    ],
    "tech": [
        "{name} {price} này vừa setup xong mà năng suất tăng gấp đôi! "
        "{benefit}. Dân tech không thể thiếu cái này. "
        "Grab it now! {urgency}",
    ],
}

def generate_talking_script(
    product_info: dict,
    category: str,
    gender: str,
    emotional,
    platform: str = "tiktok"
) -> str:
    """Sinh script nói cho video — chạm cảm xúc, push purchase intent."""
    import random
    name     = product_info.get("name", "Sản phẩm")
    price    = product_info.get("price", "")
    desc     = product_info.get("description", "")

    templates = SCRIPT_TEMPLATES.get(category, SCRIPT_TEMPLATES["fashion"])
    template  = random.choice(templates)

    # Extract benefit từ emotional package
    benefit = getattr(emotional, "transformation_promise",
                      getattr(emotional, "key_benefit", desc[:60]))
    urgency = getattr(emotional, "urgency_line", "Số lượng có hạn!")

    script = template.format(
        name=name, price=price,
        benefit=benefit[:80], urgency=urgency[:50],
    )

    # 2026 trend: thêm comment bait trigger tương tác
    comment_bait = getattr(emotional, "comment_bait",
                            "Bình luận nếu bạn muốn biết thêm!")
    script = script + f"\n{comment_bait}"

    return script


# ═══════════════════════════════════════════════════════════════
# UTILITIES
# ═══════════════════════════════════════════════════════════════

def _img_to_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return base64.b64encode(buf.getvalue()).decode()

def _b64_to_pil(b64: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
