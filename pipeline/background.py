"""
pipeline/background.py — AI Video Prompt Builder v6 (2026)
=============================================================================
Phủ sóng toàn bộ ngành thời trang: Women + Men + Children + Baby + Unisex
Prompt tối ưu cho:
  - Wan2.1-I2V-14B-480P (Alibaba — tốt nhất, miễn phí trên HuggingFace)
  - CogVideoX-5B (Tsinghua — nhanh, VRAM thấp hơn, miễn phí)
  - AnimateDiff XL (fallback nhẹ nhất, miễn phí)
  - Stable Video Diffusion (SVD) — ổn định
=============================================================================
"""

# ── Model Descriptions (người mẫu) ────────────────────────────────────────────

_MODELS = {
    "women":   "Beautiful confident Vietnamese woman in her mid-20s, natural beauty, warm genuine smile, slim build, expressive eyes, relatable yet aspirational presence",
    "men":     "Handsome confident Vietnamese man in his late 20s, clean-cut, strong jawline, athletic build, authentic masculine energy, natural charisma",
    "teen_f":  "Stylish Vietnamese teenage girl, bright eyes, youthful energy, natural smile, trendy Gen Z aesthetic",
    "teen_m":  "Stylish Vietnamese teenage boy, cool confident energy, street-smart look, natural charisma",
    "kids":    "Adorable Vietnamese child 5-10 years old, bright happy eyes, natural playful energy, cute innocent expression",
    "baby":    "Adorable Vietnamese baby 0-2 years old, chubby cheeks, big bright eyes, innocent happy expression, soft skin",
    "couple":  "Attractive Vietnamese couple in their mid-20s, natural chemistry, genuine smiles, complementary styles, couple goals",
    "family":  "Happy Vietnamese family, parents and children, genuine warmth and love, natural interactions",
}

# ── Background Scenes ─────────────────────────────────────────────────────────

_BG_MAP = {
    # ─── WOMEN ────────────────────────────────────────────────────────────────
    "dress_evening":    "luxury hotel rooftop terrace at dusk, panoramic HCMC skyline, bokeh city lights, blooming white orchids, warm amber uplighting, glamorous atmosphere",
    "dress_casual":     "vibrant Saigon street art district at golden hour, colorful murals, warm amber sunlight, trendy café backdrop",
    "ao_dai":           "Hoan Kiem Lake embankment at golden hour, ancient Ngoc Son Temple background, lotus blossoms, warm Vietnamese light, timeless cultural beauty",
    "swimwear_women":   "pristine Phu Quoc white sand beach, crystal-clear turquoise water, coconut palms, natural warm sunlight, paradise vacation atmosphere",
    "women_activewear": "premium boutique fitness studio in HCMC, floor-to-ceiling mirrors, soft professional lighting, clean white polished concrete",
    "women_coat":       "charming French colonial street in Hanoi Old Quarter at dusk, warm amber café lights, gentle mist, cozy romantic winter aesthetic",
    "women_suit":       "sleek modern co-working space HCMC, floor-to-ceiling glass windows, city skyline, warm morning light, professional atmosphere",
    "skirt_midi":       "elegant open-air mall promenade, blooming pink bougainvillea, warm afternoon light, premium lifestyle district",
    "top_trendy":       "rooftop pool bar HCMC, infinity pool, city skyline, golden hour light, aspirational urban lifestyle",
    "women_streetwear": "vibrant District 1 alley wall art, authentic street culture backdrop, graffiti murals, urban Gen Z energy",
    "women_luxury":     "luxury department store marble interior, designer boutique backdrop, high fashion atmosphere, aspirational shopping",

    # ─── MEN ──────────────────────────────────────────────────────────────────
    "men_suit":         "sleek glass-fronted CBD office building in HCMC, professional morning light, executive atmosphere, polished marble lobby",
    "men_tshirt":       "authentic Saigon street café, vintage scooters, warm afternoon light, local lifestyle authenticity",
    "men_hoodie":       "urban rooftop at sunset, city skyline, creative workspace vibes, modern urban atmosphere",
    "men_sportswear":   "modern gym interior, weight rack background, motivational atmosphere, clean athletic space",
    "men_traditional":  "Hanoi Old Quarter street at golden hour, ancient banyan tree, traditional Vietnamese architecture, cultural heritage",
    "men_streetwear":   "underground skate park, urban street scene, authentic street culture backdrop, Gen Z energy",

    # ─── CHILDREN ─────────────────────────────────────────────────────────────
    "kids_casual":      "bright colorful indoor playground, natural lighting, cheerful educational toys background, warm family atmosphere",
    "kids_dress":       "beautiful garden park, blooming flowers, warm natural sunlight, magical childhood atmosphere",
    "kids_traditional": "traditional Vietnamese house courtyard, Tet decorations, red lanterns, festive New Year atmosphere, kumquat trees",
    "kids_school":      "bright modern classroom, colorful educational posters, warm natural lighting, positive learning environment",

    # ─── BABY ─────────────────────────────────────────────────────────────────
    "baby_onesie":      "soft pastel nursery room, dreamy bokeh fairy lights, plush toys, warm golden morning light, safe cozy atmosphere",
    "baby_set":         "warm wooden bedroom interior, natural cotton sheets, soft morning light, safe natural baby environment",

    # ─── UNISEX / COUPLE / FAMILY ─────────────────────────────────────────────
    "couple_set":       "romantic rooftop café in Da Lat, fairy lights bokeh, misty mountain backdrop, couple goals atmosphere",
    "family_matching":  "beautiful city park in HCMC, lush green trees, warm afternoon light, happy family outing",
    "unisex_genz":      "vibrant youth street festival, colorful backdrop, Gen Z energy, urban art district",
}

_DEFAULT_BG = "beautiful Vietnamese urban lifestyle setting, warm natural lighting, authentic modern atmosphere"

# ── Motion Descriptions ────────────────────────────────────────────────────────

_MOTION_MAP = {
    "dress_evening":    "elegant slow spin 360°, fabric flowing gracefully in gentle breeze, confident runway walk toward camera",
    "dress_casual":     "natural confident walk, gentle hair toss, authentic lifestyle movement, slight dress sway",
    "ao_dai":           "graceful slow turn showing full ao dai, gentle breeze creating fabric flow, traditional elegant movement",
    "swimwear_women":   "confident beach walk, gentle waves backdrop, natural sun-kissed movement, carefree vacation energy",
    "women_activewear": "dynamic stretch and flex movements, athletic confident pose, high-energy workout energy",
    "women_suit":       "confident power walk toward camera, professional authority presence, strong purposeful movement",
    "men_suit":         "confident power walk through office lobby, jacket adjustment, authoritative executive presence",
    "men_tshirt":       "casual relaxed movement, natural lifestyle gesture, authentic street photography feel",
    "men_sportswear":   "dynamic athletic movement, workout energy, confident gym presence",
    "kids_casual":      "playful natural movement, genuine childhood energy, joyful authentic expression",
    "baby_onesie":      "gentle peaceful baby movement, soft natural gestures, innocent playful energy",
    "couple_set":       "natural couple interaction, genuine chemistry, walking together, sharing authentic moment",
    "family_matching":  "happy family interaction, natural warmth, authentic family moments, genuine joy",
}

_DEFAULT_MOTION = "natural confident movement, authentic lifestyle presence, smooth camera reveal"

# ── Negative Prompt ────────────────────────────────────────────────────────────

_NEGATIVE_PROMPT = (
    "blurry, low quality, distorted face, ugly, bad anatomy, deformed body, "
    "extra limbs, missing limbs, watermark, text overlay, logo, brand name, "
    "nsfw, explicit, nude, violent, gore, bad lighting, overexposed, underexposed, "
    "cartoon, anime, illustration, painting, sketch, drawing, artificial looking, "
    "plastic skin, unnatural colors, bad proportions, duplicate, clone"
)

# ── Full Prompt Builder ────────────────────────────────────────────────────────

_QUALITY_SUFFIX = (
    "8K ultra-realistic, cinematic quality, professional fashion photography, "
    "shallow depth of field, perfect lighting, magazine editorial quality, "
    "authentic Vietnamese model, natural skin texture"
)


def _garment_key_from_analysis(garment_key: str) -> str:
    mapping = {
        "women_formal":     "women_suit",
        "women_casual":     "dress_casual",
        "women_streetwear": "women_streetwear",
        "women_sportswear": "women_activewear",
        "women_traditional":"ao_dai",
        "women_luxury":     "women_luxury",
        "women_swimwear":   "swimwear_women",
        "men_formal":       "men_suit",
        "men_casual":       "men_tshirt",
        "men_streetwear":   "men_streetwear",
        "men_sportswear":   "men_sportswear",
        "men_traditional":  "men_traditional",
        "children_casual":  "kids_casual",
        "children_formal":  "kids_dress",
        "children_traditional": "kids_traditional",
        "baby_casual":      "baby_onesie",
        "unisex_casual":    "couple_set",
    }
    return mapping.get(garment_key, garment_key)


def get_background_prompt(garment_key: str) -> str:
    bg_key = _garment_key_from_analysis(garment_key)
    return _BG_MAP.get(bg_key, _DEFAULT_BG)


def get_motion_prompt(garment_key: str) -> str:
    bg_key = _garment_key_from_analysis(garment_key)
    return _MOTION_MAP.get(bg_key, _DEFAULT_MOTION)


def get_model_description(gender: str, sub: str = "") -> str:
    key = sub if sub in _MODELS else gender
    return _MODELS.get(key, _MODELS["women"])


def get_negative_prompt() -> str:
    return _NEGATIVE_PROMPT


def get_full_prompt(garment_key: str, gender: str, product_name: str = "", colors: list = None, material: str = "") -> str:
    """Tổng hợp full prompt tối ưu cho AI video generation."""
    model_desc = get_model_description(gender)
    bg         = get_background_prompt(garment_key)
    motion     = get_motion_prompt(garment_key)

    color_str    = f", {', '.join(colors[:2])}" if colors else ""
    material_str = f", {material}" if material else ""
    product_str  = f"wearing {product_name}" if product_name else "wearing stylish outfit"

    return (
        f"{model_desc}, {product_str}{color_str}{material_str}. "
        f"Background: {bg}. "
        f"Movement: {motion}. "
        f"{_QUALITY_SUFFIX}"
    )


def get_hook_frame_prompt(garment_key: str, gender: str = "women") -> str:
    """Prompt cho frame đầu tiên (hook frame) — cần thu hút nhất."""
    model_desc = get_model_description(gender)
    bg_key     = _garment_key_from_analysis(garment_key)
    bg         = _BG_MAP.get(bg_key, _DEFAULT_BG)
    return (
        f"Close-up dramatic reveal shot: {model_desc}, "
        f"looking directly at camera with confidence and warmth, "
        f"Background: {bg}, "
        f"dramatic lighting, scroll-stopping first impression, "
        f"{_QUALITY_SUFFIX}"
    )


def get_loop_prompt(garment_key: str, gender: str = "women") -> str:
    """Prompt cho frame loop cuối — cần khớp với frame đầu để tạo loop liền mạch."""
    return get_full_prompt(garment_key, gender) + ", seamless loop end frame, matching opening composition"
