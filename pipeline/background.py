"""
pipeline/background.py — AI Video Prompt Builder v5 (2026)
=============================================================================
Phủ sóng toàn bộ ngành thời trang: Women + Men + Children + Baby + Unisex
Prompt tối ưu cho Wan2.1 / CogVideoX / Kling v2 (2026 AI video engines)
=============================================================================
"""

# ── Model Descriptions ────────────────────────────────────────────────────────

_MODELS = {
    "women":   "Beautiful confident Vietnamese woman in her mid-20s, natural beauty, genuine warm smile, slim build, expressive eyes, relatable yet aspirational",
    "men":     "Handsome confident Vietnamese man in his late 20s, clean-cut appearance, strong jawline, athletic build, authentic masculine energy",
    "teen_f":  "Stylish Vietnamese teenage girl, bright eyes, youthful energy, natural smile, trendy aesthetic",
    "teen_m":  "Stylish Vietnamese teenage boy, cool confident energy, street-smart look, natural charisma",
    "kids":    "Adorable Vietnamese child 5-10 years old, bright happy eyes, natural playful energy, cute expression",
    "baby":    "Adorable Vietnamese baby 0-2 years old, chubby cheeks, big bright eyes, innocent happy expression",
    "couple":  "Attractive Vietnamese couple in their mid-20s, natural chemistry, genuine smiles, complementary styles",
    "family":  "Happy Vietnamese family of 3-4 people, parents and children, genuine warmth and love",
}

# ── Background Scenes ─────────────────────────────────────────────────────────

_BG_MAP = {
    # Women
    "dress_evening":    "luxury hotel rooftop terrace at dusk, panoramic HCMC skyline, soft bokeh city lights, blooming white orchids, warm amber uplighting, glamorous intimate atmosphere",
    "dress_casual":     "vibrant Saigon street art district at golden hour, colorful murals, warm amber sunlight, trendy café backdrop, authentic lifestyle energy",
    "ao_dai":           "Hoan Kiem Lake embankment at golden hour 6PM, ancient Ngoc Son Temple bridge background, lotus blossoms, warm Vietnamese golden light, timeless cultural beauty",
    "swimwear_women":   "pristine Phu Quoc white sand beach, crystal-clear turquoise water gradient, coconut palms, natural warm sunlight, paradise vacation atmosphere",
    "women_activewear": "premium boutique fitness studio in HCMC, floor-to-ceiling mirror wall, soft professional studio lighting, clean white polished concrete, aspirational wellness atmosphere",
    "women_coat":       "charming French colonial street in Hanoi Old Quarter at dusk, warm amber café lights reflecting on cobblestones, gentle mist, cozy romantic winter aesthetic",
    "women_suit":       "sleek modern co-working space, floor-to-ceiling glass windows, city skyline backdrop, warm morning light, professional yet aspirational atmosphere",
    "skirt_midi":       "elegant open-air mall promenade, row of blooming pink bougainvillea, warm afternoon light, premium lifestyle shopping district, feminine aspirational atmosphere",
    "handbag":          "minimalist high-end boutique interior, white Carrara marble surfaces, warm directional spotlights, oversized mirror wall, quiet luxury editorial aesthetic",
    "heels":            "luxury hotel lobby floor, marble with gold accents, crystal chandelier overhead, soft warm lighting, premium fashion commercial atmosphere",
    "women_hoodie":     "vibrant neon-lit street in D1 HCMC at night, colorful LED signs, street art mural wall, youth culture energy",

    # Men
    "men_suit":         "executive glass-tower boardroom on 30th floor, panoramic HCMC city view, polished dark oak table, soft professional directional lighting, power atmosphere",
    "men_shirt_formal": "sleek modern co-working space, floor-to-ceiling glass walls overlooking city, warm morning golden light, Scandinavian minimalist design, productivity atmosphere",
    "men_tshirt":       "vibrant Bui Vien street district at golden hour, colorful murals, authentic youth energy, outdoor café backdrop, cinematic warmth",
    "men_hoodie":       "urban night scene with neon signs, street art walls, skatepark in background, cool authentic street culture energy",
    "men_sportswear":   "premium boxing/fitness gym in HCMC, exposed brick walls, industrial lighting, heavy bags in background, authentic athletic energy",
    "men_jeans":        "industrial-chic rooftop in District 3, exposed red brick, string lights against deep blue twilight sky, raw urban creative atmosphere",
    "ao_dai_men":       "Temple of Literature Hanoi at golden hour, ancient architecture, koi pond, warm Vietnamese cultural atmosphere, timeless elegance",
    "men_jacket":       "modern café-bar rooftop at sunset, HCMC skyline panorama, casual but aspirational lifestyle setting",

    # Children
    "kids_dress":       "beautiful children's garden park with blooming flowers, soft morning sunlight, colorful butterflies, magical fairytale atmosphere, safe and joyful",
    "kids_set":         "bright modern playground, colorful equipment, natural afternoon light, safe and fun children's environment, happy energy",
    "kids_school":      "clean bright modern classroom or school corridor, natural light from large windows, organized educational environment, positive learning atmosphere",
    "kids_sportswear":  "safe outdoor sports area, green grass field, natural daylight, healthy active children's environment",
    "kids_ao_dai":      "beautiful traditional Vietnamese courtyard with lanterns, golden Tet atmosphere, cultural celebration setting, warm festival lighting",

    # Baby
    "baby_onesie":      "soft pastel nursery room, plush toys and mobiles, warm gentle lighting, cozy safe haven for baby, dreamy gentle atmosphere",
    "baby_set":         "bright clean modern baby room, white furniture, natural light from window, safe clean environment, gentle warm tones",
    "baby_romper":      "beautiful home interior with morning light, soft white bedding, natural wooden elements, clean aesthetic, peaceful baby atmosphere",

    # Unisex / Couple
    "couple_set":       "romantic afternoon walk in a blooming flower park, golden hour light, couple holding hands, natural genuine connection, beautiful lifestyle setting",
    "family_matching":  "beautiful family home garden or park, natural outdoor light, genuine family warmth, happy children playing, aspirational family lifestyle",
    "unisex_hoodie":    "cool urban street scene, street art backdrop, natural daylight, authentic youth lifestyle energy, free and confident",
}

_DEFAULT_BG = "clean editorial fashion studio, gradient ivory-to-white background, professional three-point studio lighting, premium commercial photography setup"

# ── Motion Prompts ────────────────────────────────────────────────────────────

_MOTION_MAP = {
    # Women
    "dress_evening":    "model slowly turns 360° showing gown from all angles, silk fabric billowing and catching light beautifully, then walks gracefully toward camera with confident smile",
    "ao_dai":           "model walks with serene grace across bridge, ao dai silk flowing poetically in gentle breeze like living art, slow turn revealing back embroidery",
    "swimwear_women":   "model walks confidently toward camera from shoreline, sea breeze gently lifting hair, pauses to show full outfit, confident radiant smile",
    "women_activewear": "model does dynamic graceful warm-up stretches showcasing full range of motion, fabric stretching and recovering perfectly, ends in confident power pose",
    "women_coat":       "model walks in cinematic slow motion, coat billowing open with each step, pauses to adjust lapel, turns showing coat from profile angle",
    "women_suit":       "model walks purposefully into frame, pauses to subtly adjust blazer, slight turn showing clean profile, professional yet warm expression",
    "skirt_midi":       "model spins elegantly showing skirt blooming outward in slow motion, fabric flowing and swirling, then poses confidently facing camera",
    "handbag":          "model brings bag close for intimate detail shot showing craftsmanship, slow rotation revealing all angles, then styled with full outfit",

    # Men
    "men_suit":         "model enters frame with powerful confident stride, pauses to adjust jacket lapel showing perfect tailoring, slow turn showing suit from both sides, commanding presence",
    "men_shirt_formal": "model walks purposefully into frame, rolls sleeve slightly showing detail, slight turn for side profile, professional yet approachable expression",
    "men_tshirt":       "model does relaxed casual movement showing shirt from all angles, arms out showing fit, ends with casual hands-in-pockets confident pose",
    "men_hoodie":       "model does casual head-nod and body sway, pulls hood up dramatically then pushes back confidently, streetwear fully displayed, authentic street energy",
    "men_sportswear":   "model does dynamic athletic movements showing fabric performance, shadowboxing or stretching, ends with confident power pose facing camera",
    "men_jeans":        "model walks toward camera showing full jeans silhouette, natural gait showing movement, turns to show back pockets and perfect fit",

    # Children
    "kids_dress":       "child twirls happily showing dress, fabric spinning and catching light, natural joyful expression, runs toward camera with big smile",
    "kids_set":         "child plays naturally in outfit showing full clothing in motion, runs and jumps, genuine happy child energy, product always clearly visible",
    "baby_onesie":      "baby sits and plays naturally showing onesie clearly, cute hand gestures, big bright happy eyes, gentle loving close-up shots",

    # Couple / Family
    "couple_set":       "couple walks together holding hands showing matching outfits, turns to look at each other and smile, both turn toward camera showing full outfits",
    "family_matching":  "family poses together in matching outfits, parents and children, genuine laughter and connection, group turns to show full matching looks",
}

_DEFAULT_MOTION = "model poses elegantly, slowly turns 360° showing outfit completely, fabric flowing naturally, confident graceful movement toward camera"

# ── Camera & Quality ──────────────────────────────────────────────────────────

_CAMERA_STYLE = (
    "9:16 vertical TikTok-native framing, cinematic slow push-in from product detail close-up, "
    "smoothly pulls back to full body reveal, shallow depth of field keeping outfit sharp, "
    "handheld with subtle organic stabilization, professional fashion × authentic TikTok hybrid"
)

_QUALITY = (
    "8K ultra-detailed hyperrealistic, professional fashion commercial quality, "
    "natural fabric texture clearly visible, vibrant true-to-life colors matching actual product, "
    "ultra-smooth realistic human motion, product always sharply in focus, "
    "cinematic color grading warm golden tones, high-end production value"
)

_NEGATIVE = (
    "ugly, deformed, disfigured, blurry product, low quality, watermark, text in scene, "
    "extra limbs, bad anatomy, distorted face, cartoon, anime, nsfw, "
    "unrealistic robot movement, product hidden or cut off, oversaturated, grainy, "
    "temporal inconsistency, flickering textures, AI artifact, unnatural skin"
)

# ── Public API ────────────────────────────────────────────────────────────────

def get_background_prompt(garment_key: str) -> str:
    return _BG_MAP.get(garment_key, _DEFAULT_BG)


def get_motion_prompt(garment_key: str) -> str:
    return _MOTION_MAP.get(garment_key, _DEFAULT_MOTION)


def get_model_description(gender: str, age_group: str = "adult") -> str:
    if age_group in ("baby", "toddler"):
        return _MODELS["baby"]
    if age_group == "kids":
        return _MODELS["kids"]
    if gender == "men":
        return _MODELS["men"]
    if gender == "unisex":
        return _MODELS["couple"]
    return _MODELS["women"]


def get_full_prompt(garment_key: str, gender: str = "women", age_group: str = "adult", extra_desc: str = "") -> str:
    model = get_model_description(gender, age_group)
    motion = get_motion_prompt(garment_key)
    bg = get_background_prompt(garment_key)
    product_desc = extra_desc or garment_key.replace("_", " ")

    return (
        f"{model} wearing {product_desc}, "
        f"outfit perfectly fitted, product clearly visible throughout. "
        f"{motion}. "
        f"Setting: {bg}. "
        f"{_CAMERA_STYLE}. "
        f"{_QUALITY}."
    )


def get_hook_frame_prompt(garment_key: str) -> str:
    hook_details = {
        "dress_evening":    "extreme macro close-up of evening gown fabric — silk threads visible, embroidery detail stunning",
        "ao_dai":           "extreme close-up of ao dai silk embroidery — individual threads visible, stunning traditional craftsmanship",
        "men_suit":         "razor-sharp close-up of suit lapel buttonhole and perfectly folded pocket square, premium fabric detail",
        "women_activewear": "macro close-up of activewear technical fabric — compression mesh pattern detail, premium quality",
        "kids_dress":       "close-up of kids dress fabric — soft colorful detail, safe quality visible, charming pattern",
        "baby_onesie":      "extreme close-up of baby onesie fabric — ultra-soft texture, gentle organic material feel",
        "handbag":          "macro shot of handbag hardware and leather stitching detail, premium craftsmanship evident",
        "couple_set":       "close-up detail of matching couple outfit fabric and design element",
    }
    detail = hook_details.get(garment_key, f"dramatic macro close-up of {garment_key.replace('_',' ')} texture and craftsmanship")
    return f"{detail}, then smooth pull-back reveal to full outfit, cinematic fashion reveal moment"


def get_loop_prompt(garment_key: str, gender: str = "women") -> str:
    bg = get_background_prompt(garment_key)
    model = get_model_description(gender)
    return (
        f"Continuation: {model} wearing {garment_key.replace('_',' ')} in {bg}, "
        f"product still clearly visible, different angle revealing more detail, "
        f"authentic smile, subtle movement keeping viewer engaged, seamless loop-friendly ending"
    )


def get_negative_prompt() -> str:
    return _NEGATIVE
