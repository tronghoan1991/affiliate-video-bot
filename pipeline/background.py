"""
pipeline/background.py — AI Prompt Builder v7 (10 ngành hàng)
Sinh prompt tối ưu cho Wan2.1, CogVideoX, AnimateDiff, FLUX.1
"""
import random

_STYLES = {
    "fashion":  "8K ultra-realistic fashion photography, Vietnamese model, cinematic shallow depth of field, magazine editorial quality",
    "beauty":   "8K beauty photography, Vietnamese woman, soft natural lighting, clean minimal background, professional skincare aesthetic",
    "health":   "8K wellness lifestyle photography, vibrant healthy energy, clean minimal, natural light, authentic Vietnamese",
    "home":     "8K interior photography, warm ambient lighting, cozy aesthetic, professional real estate quality",
    "food":     "8K food photography, vibrant colors, delicious close-up, steam rising, restaurant quality plating",
    "tech":     "8K product photography, sleek minimal white studio, dramatic product lighting, tech editorial quality",
    "pet":      "8K pet photography, warm natural light, cute authentic animal moment, joyful playful energy",
    "sports":   "8K athletic photography, dynamic motion, energy, sweat, determination, editorial sports magazine",
    "baby":     "8K soft baby photography, pastel tones, natural gentle light, innocent precious moment",
    "fashion_kids": "8K children's fashion photography, colorful playful, natural light, joyful authentic energy",
}

_MODELS = {
    "women":   "Beautiful confident Vietnamese woman 20s, warm genuine smile, natural beauty, relatable yet aspirational",
    "men":     "Handsome confident Vietnamese man late 20s, clean-cut, athletic, natural masculine charisma",
    "children":"Adorable Vietnamese child 5-10 years, bright happy eyes, natural playful energy",
    "baby":    "Adorable Vietnamese baby 0-2 years, chubby cheeks, big bright eyes, innocent expression",
    "unisex":  "Attractive Vietnamese couple mid-20s, natural chemistry, genuine smiles",
    "no_model":"",  # For product-only shots (tech, food, home objects)
}

_BACKGROUNDS = {
    "fashion_formal":       "sleek glass CBD office HCMC, marble lobby, morning light",
    "fashion_casual":       "vibrant Saigon street art district golden hour, colorful murals",
    "fashion_streetwear":   "underground urban skate park, authentic street culture backdrop",
    "fashion_sportswear":   "premium boutique gym HCMC, floor-to-ceiling mirrors, clean white",
    "fashion_traditional":  "Hoan Kiem Lake embankment golden hour, ancient temple, lotus blossoms",
    "fashion_luxury":       "luxury department store marble interior, high fashion atmosphere",
    "fashion_swimwear":     "pristine Phu Quoc white sand beach, crystal turquoise water",
    "beauty_skincare":      "minimalist white vanity, soft morning window light, clean aesthetic",
    "beauty_makeup":        "luxurious makeup studio, warm ring light, beauty blogger aesthetic",
    "health_supplement":    "bright modern kitchen, healthy food ingredients, clean minimal",
    "health_fitness":       "premium gym interior, motivational atmosphere, clean athletic",
    "home_decor":           "beautiful modern living room HCMC, warm ambient lighting, cozy",
    "home_kitchen":         "sleek modern kitchen, marble countertop, warm morning light",
    "food_snack":           "cozy aesthetic café table, soft natural light, artisan food styling",
    "food_drink":           "trendy bubble tea shop, pastel interior, Gen Z aesthetic",
    "tech_phone":           "ultra-clean white desk setup, minimal accessories, pro studio light",
    "tech_gaming":          "gaming setup RGB, dark room, dramatic lighting, pro gamer aesthetic",
    "pet_dog":              "bright sunny garden, green grass, happy playful dog moment",
    "pet_cat":              "cozy home interior, soft blanket, peaceful cat moment, warm light",
    "sports_gym":           "modern gym interior, weight equipment, motivational atmosphere",
    "sports_outdoor":       "beautiful outdoor park Ho Chi Minh City, morning run, fresh air",
    "baby_nursery":         "soft pastel nursery, fairy lights bokeh, plush toys, golden morning",
    "fashion_kids_play":    "colorful indoor playground, educational toys, warm family atmosphere",
}

_MOTIONS = {
    "fashion":  "natural confident model walk, fabric flowing in breeze, slight hair toss, authentic lifestyle movement",
    "beauty":   "gentle skincare application, close-up skin reveal, finger touches product, transformation moment",
    "health":   "energetic athletic movement, product reveal, person drinking/taking supplement, before-after reveal",
    "home":     "slow pan across beautiful room, product detail reveal, hand interacts with item, cozy atmosphere",
    "food":     "slow motion pour, steam rising, hand reaches for food, delicious close-up bite reveal",
    "tech":     "sleek product reveal, hand picks up device, screen lights up, feature demonstration",
    "pet":      "pet reacts to product, playful animal movement, owner interacts with pet, joyful moment",
    "sports":   "dynamic athletic motion, product in use during exercise, powerful confident movement",
    "baby":     "gentle baby movement, peaceful sleeping, parent holding baby, soft innocent gestures",
    "fashion_kids": "playful natural child movement, genuine laughter, joyful running, authentic kid energy",
}

_NEGATIVE = (
    "blurry, low quality, distorted face, bad anatomy, watermark, text overlay, "
    "logo, nsfw, explicit, bad lighting, overexposed, underexposed, "
    "cartoon, anime, artificial, plastic skin, bad proportions"
)

def _bg_key(category: str, subcategory: str = "") -> str:
    key = f"{category}_{subcategory}"
    if key in _BACKGROUNDS: return key
    return next((k for k in _BACKGROUNDS if k.startswith(f"{category}_")), list(_BACKGROUNDS.keys())[0])

def get_main_prompt(category: str, gender: str, product_name: str = "",
                    colors: list = None, material: str = "", subcategory: str = "") -> str:
    style   = _STYLES.get(category, _STYLES["fashion"])
    model   = _MODELS.get(gender, _MODELS["women"])
    bg_key  = _bg_key(category, subcategory)
    bg      = _BACKGROUNDS.get(bg_key, "beautiful Vietnamese urban setting")
    motion  = _MOTIONS.get(category, _MOTIONS["fashion"])

    color_str    = f", {', '.join(colors[:2])}" if colors else ""
    mat_str      = f", {material}" if material else ""
    product_str  = f"with {product_name}" if product_name else "with product"

    parts = [p for p in [model, f"{product_str}{color_str}{mat_str}"] if p]
    return f"{', '.join(parts)}. Background: {bg}. Movement: {motion}. {style}"

def get_hook_prompt(category: str, gender: str = "women") -> str:
    model = _MODELS.get(gender, _MODELS["women"])
    bg_key = _bg_key(category)
    bg = _BACKGROUNDS.get(bg_key, "beautiful Vietnamese setting")
    style = _STYLES.get(category, _STYLES["fashion"])
    return f"Close-up dramatic reveal: {model}, looking directly at camera with curiosity and warmth. Background: {bg}. Scroll-stopping first impression. {style}"

def get_negative_prompt() -> str:
    return _NEGATIVE
