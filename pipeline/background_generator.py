"""
pipeline/background_generator.py — AI Background Scene Generator
=================================================================
Tạo background đẹp cho từng ngành hàng, hoàn toàn miễn phí:
  1. Stable Diffusion (local Colab GPU) — chất lượng cao nhất
  2. Pixabay API (free tier 5000 req/tháng) — ảnh thật
  3. Gradient generator — luôn hoạt động, không cần internet
"""
import logging, os, random, tempfile
from pathlib import Path
from typing import Optional
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageEnhance

logger = logging.getLogger("BackgroundGenerator")

VIDEO_W, VIDEO_H = 1080, 1920

# ══════════════════════════════════════════════════════════════════════════════
# BACKGROUND PROMPTS — Theo ngành hàng & gender
# ══════════════════════════════════════════════════════════════════════════════

BG_PROMPTS = {
    "fashion": {
        "female": [
            "luxury boutique interior, soft pink lighting, white marble floor, fashion studio",
            "modern minimalist bedroom, pastel colors, natural light through window, aesthetic",
            "rooftop city view sunset, golden hour lighting, urban fashion background",
            "cozy cafe interior, warm lighting, wooden table, aesthetic background",
            "white studio fashion photography, soft box lighting, clean minimal",
        ],
        "male": [
            "modern urban street, bokeh background, city night lights",
            "minimalist studio grey background, dramatic lighting, fashion editorial",
            "industrial loft space, brick wall, warm mood lighting",
            "rooftop city skyline, golden hour, urban male fashion",
        ],
        "child": [
            "colorful playground, bright sunny day, soft bokeh",
            "pastel nursery room, soft lighting, cute background",
            "park with green grass, natural light, cheerful",
        ],
        "unisex": [
            "modern clean studio, white background, soft lighting",
            "urban street style, bokeh city lights, lifestyle",
            "minimalist indoor setting, natural window light",
        ],
    },
    "beauty": {
        "female": [
            "luxury vanity table, rose gold accessories, soft pink bokeh, beauty studio",
            "marble bathroom counter, morning sunlight, clean aesthetic, skincare flat lay",
            "modern beauty studio, ring light, white and gold, professional",
            "botanical garden, soft natural light, flowers, fresh beauty aesthetic",
            "minimalist white shelf, beauty products display, clean and premium",
        ],
        "male": [
            "modern bathroom, clean lines, morning light, grooming aesthetic",
            "minimalist grey background, soft lighting, men grooming studio",
        ],
        "unisex": [
            "clean white marble background, soft lighting, premium beauty aesthetic",
            "botanical fresh background, green leaves, natural skincare",
        ],
    },
    "health": {
        "female": [
            "bright kitchen counter, morning sunlight, healthy lifestyle, vitamins setup",
            "yoga studio, wooden floor, natural light, wellness atmosphere",
            "outdoor morning run, park greenery, fresh healthy background",
            "clean white health studio, supplement display, professional",
        ],
        "male": [
            "modern gym interior, motivational, bright lighting, sports atmosphere",
            "outdoor track, dynamic background, sports performance aesthetic",
            "clean kitchen, meal prep setup, healthy lifestyle background",
        ],
        "unisex": [
            "wellness studio, clean white, soft natural lighting, health products",
            "outdoor nature background, fresh green, healthy lifestyle",
        ],
    },
    "home": [
        "cozy living room, warm amber lighting, modern interior design, bokeh",
        "minimalist apartment interior, clean lines, natural light",
        "aesthetic desk setup, plants, warm mood lighting, home office",
        "modern kitchen interior, clean, bright, lifestyle photography",
        "bedroom with fairy lights, cozy atmosphere, home decor aesthetic",
    ],
    "food": [
        "rustic wooden table, natural lighting, food photography setup",
        "cafe interior, warm aesthetic, coffee shop background, cozy",
        "kitchen marble counter, fresh ingredients, food styling background",
        "outdoor picnic setup, green grass, sunny day, food lifestyle",
        "restaurant interior, bokeh lighting, warm tones, food background",
    ],
    "tech": [
        "modern desk setup, RGB lighting, tech aesthetic, clean workspace",
        "minimalist white background, technology product display",
        "dark mode workspace, neon accents, tech vibe",
        "modern office interior, clean lines, tech lifestyle",
    ],
    "sports": [
        "modern gym with equipment, energetic bright lighting",
        "outdoor sports track, dynamic motion background",
        "fitness studio, mirrors, motivational, athletic background",
        "nature trail running background, bokeh trees, outdoor sports",
    ],
    "pet": [
        "cozy home with warm lighting, pet-friendly interior",
        "garden outdoor, sunny day, green grass, pet lifestyle",
        "modern living room, soft colors, comfortable home background",
    ],
    "baby": [
        "soft pastel nursery, gentle lighting, baby room aesthetic",
        "white studio with baby props, minimal, safe, gentle",
        "bright playroom, colorful but soft, baby photography background",
    ],
    "fashion_kids": [
        "colorful kids room, bright pastel colors, playful background",
        "outdoor playground, sunny day, green trees, children fashion",
        "white studio with colorful props, children photography",
    ],
}

# Color schemes theo ngành hàng
COLOR_SCHEMES = {
    "fashion":      {"accent": "#FF4D8D", "bg1": (255, 240, 245), "bg2": (200, 160, 180)},
    "beauty":       {"accent": "#FFB347", "bg1": (255, 248, 240), "bg2": (220, 180, 150)},
    "health":       {"accent": "#4CAF50", "bg1": (240, 255, 240), "bg2": (150, 200, 160)},
    "home":         {"accent": "#FF8C42", "bg1": (255, 245, 235), "bg2": (200, 160, 120)},
    "food":         {"accent": "#FF6B6B", "bg1": (255, 245, 240), "bg2": (210, 160, 140)},
    "tech":         {"accent": "#00BFFF", "bg1": (220, 235, 255), "bg2": (100, 140, 200)},
    "sports":       {"accent": "#FF4500", "bg1": (255, 240, 235), "bg2": (200, 120, 100)},
    "pet":          {"accent": "#FFD700", "bg1": (255, 252, 230), "bg2": (200, 180, 100)},
    "baby":         {"accent": "#87CEEB", "bg1": (235, 248, 255), "bg2": (160, 200, 230)},
    "fashion_kids": {"accent": "#FF69B4", "bg1": (255, 240, 250), "bg2": (220, 170, 200)},
}


def get_background(
    category: str,
    gender: str,
    drive_root: Path,
    size: tuple = (VIDEO_W, VIDEO_H),
    use_ai: bool = True,
) -> Image.Image:
    """
    Lấy background phù hợp. Ưu tiên: AI → Pixabay → gradient.
    """
    # Thử AI trước nếu có model
    if use_ai:
        ai_bg = _try_stable_diffusion(category, gender, drive_root, size)
        if ai_bg:
            return ai_bg

    # Thử cache từ Drive
    cached = _get_cached_bg(category, drive_root, size)
    if cached:
        return cached

    # Thử Pixabay
    pixabay_key = os.getenv("PIXABAY_API_KEY", "")
    if pixabay_key:
        pixabay_bg = _fetch_pixabay(category, gender, pixabay_key, drive_root, size)
        if pixabay_bg:
            return pixabay_bg

    # Fallback: gradient đẹp
    return _make_gradient_bg(category, size)


def _try_stable_diffusion(category: str, gender: str,
                           drive_root: Path, size: tuple) -> Optional[Image.Image]:
    """Dùng FLUX hoặc SD nếu đã tải về Drive."""
    model_paths = [
        drive_root / "models" / "flux1-schnell",
        drive_root / "models" / "stable-diffusion-2-1",
    ]
    model_path = next((str(p) for p in model_paths if p.exists()
                       and any(p.iterdir())), None)
    if not model_path:
        return None

    try:
        import torch
        from diffusers import StableDiffusionPipeline, FluxPipeline

        prompts = _get_prompts(category, gender)
        prompt  = random.choice(prompts)
        prompt  = f"{prompt}, 8K quality, professional photography, cinematic lighting"

        # Detect model type
        if "flux" in model_path.lower():
            pipe = FluxPipeline.from_pretrained(
                model_path, torch_dtype=torch.bfloat16)
        else:
            pipe = StableDiffusionPipeline.from_pretrained(
                model_path, torch_dtype=torch.float16,
                safety_checker=None)

        pipe.to("cuda")
        pipe.enable_attention_slicing()

        # Generate ở half resolution rồi upscale (tiết kiệm VRAM)
        out = pipe(prompt, width=540, height=960,
                   num_inference_steps=20,
                   guidance_scale=7.0).images[0]
        pipe.to("cpu")  # Giải phóng VRAM

        result = out.resize(size, Image.LANCZOS)
        result = _enhance_bg(result)

        # Cache lại
        _cache_bg(result, category, drive_root)
        logger.info(f"✅ AI background: {category}")
        return result

    except Exception as e:
        logger.warning(f"SD background fail: {e}")
        return None


def _fetch_pixabay(category: str, gender: str, api_key: str,
                   drive_root: Path, size: tuple) -> Optional[Image.Image]:
    """Lấy ảnh từ Pixabay API (5000 req/tháng free)."""
    import requests
    queries = {
        "fashion":      "fashion boutique interior elegant",
        "beauty":       "beauty skincare aesthetic vanity",
        "health":       "healthy lifestyle wellness kitchen",
        "home":         "modern interior cozy living room",
        "food":         "food photography aesthetic cafe",
        "tech":         "modern workspace technology desk",
        "sports":       "gym fitness workout modern",
        "pet":          "cozy home pet friendly interior",
        "baby":         "nursery room baby pastel soft",
        "fashion_kids": "colorful playground kids bright",
    }
    q = queries.get(category, "lifestyle aesthetic background")

    try:
        url = (f"https://pixabay.com/api/?key={api_key}"
               f"&q={q.replace(' ', '+')}"
               f"&image_type=photo&orientation=vertical"
               f"&min_width=1080&per_page=10&safesearch=true")
        resp = requests.get(url, timeout=10)
        hits = resp.json().get("hits", [])
        if not hits:
            return None

        # Chọn random từ top 5
        hit      = random.choice(hits[:5])
        img_url  = hit["largeImageURL"]
        img_resp = requests.get(img_url, timeout=20)

        from io import BytesIO
        img    = Image.open(BytesIO(img_resp.content)).convert("RGB")
        result = _crop_to_ratio(img, size)
        result = _enhance_bg(result)
        _cache_bg(result, category, drive_root)
        logger.info(f"✅ Pixabay background: {category}")
        return result

    except Exception as e:
        logger.warning(f"Pixabay fail: {e}")
        return None


def _get_cached_bg(category: str, drive_root: Path,
                   size: tuple) -> Optional[Image.Image]:
    """Lấy background từ cache trong Drive."""
    cache_dir = drive_root / "backgrounds" / category
    if not cache_dir.exists():
        return None
    imgs = list(cache_dir.glob("*.jpg")) + list(cache_dir.glob("*.png"))
    if not imgs:
        return None
    chosen = random.choice(imgs)
    try:
        img = Image.open(chosen).convert("RGB")
        return _crop_to_ratio(img, size)
    except Exception:
        return None


def _cache_bg(img: Image.Image, category: str, drive_root: Path):
    """Cache background vào Drive để tái sử dụng."""
    import time
    cache_dir = drive_root / "backgrounds" / category
    cache_dir.mkdir(parents=True, exist_ok=True)
    # Giữ tối đa 10 ảnh mỗi category
    existing = list(cache_dir.glob("*.jpg"))
    if len(existing) >= 10:
        existing[0].unlink()
    path = cache_dir / f"bg_{int(time.time())}.jpg"
    img.save(str(path), quality=90)


def _make_gradient_bg(category: str,
                      size: tuple = (VIDEO_W, VIDEO_H)) -> Image.Image:
    """Tạo gradient background đẹp theo màu ngành hàng."""
    scheme = COLOR_SCHEMES.get(category, COLOR_SCHEMES["fashion"])
    c1     = scheme["bg1"]
    c2     = scheme["bg2"]

    w, h = size
    img  = Image.new("RGB", size)
    draw = ImageDraw.Draw(img)

    # 3-tone gradient: top → mid → bottom
    c_mid = tuple((c1[i] + c2[i]) // 2 for i in range(3))

    for y in range(h):
        t = y / h
        if t < 0.5:
            t2  = t * 2
            col = tuple(int(c1[i] * (1-t2) + c_mid[i] * t2) for i in range(3))
        else:
            t2  = (t - 0.5) * 2
            col = tuple(int(c_mid[i] * (1-t2) + c2[i] * t2) for i in range(3))
        draw.line([(0, y), (w, y)], fill=col)

    # Thêm subtle texture noise
    arr   = np.array(img, dtype=np.float32)
    noise = np.random.normal(0, 4, arr.shape)
    arr   = np.clip(arr + noise, 0, 255).astype(np.uint8)
    img   = Image.fromarray(arr)

    # Thêm vài hình dạng trang trí
    _add_decorative_shapes(img, scheme["accent"], category)

    return img


def _add_decorative_shapes(img: Image.Image, accent: str, category: str):
    """Thêm hình dạng trang trí tinh tế vào background."""
    draw = ImageDraw.Draw(img, "RGBA")
    w, h = img.size
    r, g, b = _hex_to_rgb(accent)

    if category in ("fashion", "beauty"):
        # Circles mờ
        for _ in range(5):
            cx = random.randint(0, w)
            cy = random.randint(0, h)
            radius = random.randint(80, 250)
            draw.ellipse([cx-radius, cy-radius, cx+radius, cy+radius],
                         fill=(r, g, b, 18))
    elif category in ("health", "sports"):
        # Lines động
        for _ in range(8):
            x1 = random.randint(-w//2, w)
            y1 = random.randint(0, h)
            x2 = x1 + random.randint(200, 500)
            y2 = y1 + random.randint(-100, 100)
            draw.line([(x1, y1), (x2, y2)], fill=(r, g, b, 25), width=3)
    elif category in ("home", "food"):
        # Soft rectangles
        for _ in range(4):
            x1 = random.randint(-50, w//2)
            y1 = random.randint(-50, h//2)
            draw.rounded_rectangle(
                [x1, y1, x1+random.randint(200,500), y1+random.randint(200,500)],
                fill=(r, g, b, 15), radius=40)


def _enhance_bg(img: Image.Image) -> Image.Image:
    """Tăng cường màu sắc background."""
    img = ImageEnhance.Color(img).enhance(1.15)
    img = ImageEnhance.Contrast(img).enhance(1.08)
    img = ImageEnhance.Brightness(img).enhance(0.92)  # Hơi tối để nổi sản phẩm
    return img


def _crop_to_ratio(img: Image.Image, size: tuple) -> Image.Image:
    """Crop và resize ảnh về đúng tỉ lệ 9:16."""
    target_w, target_h = size
    target_ratio = target_w / target_h
    iw, ih       = img.size
    src_ratio    = iw / ih

    if src_ratio > target_ratio:
        new_w = int(ih * target_ratio)
        x     = (iw - new_w) // 2
        img   = img.crop((x, 0, x + new_w, ih))
    else:
        new_h = int(iw / target_ratio)
        y     = (ih - new_h) // 2
        img   = img.crop((0, y, iw, y + new_h))

    return img.resize(size, Image.LANCZOS)


def _get_prompts(category: str, gender: str) -> list:
    prompts = BG_PROMPTS.get(category, BG_PROMPTS["fashion"])
    if isinstance(prompts, dict):
        return prompts.get(gender, prompts.get("unisex", list(prompts.values())[0]))
    return prompts


def _hex_to_rgb(hex_color: str) -> tuple:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
