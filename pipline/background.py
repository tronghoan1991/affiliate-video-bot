"""
pipeline/background.py — Background prompt mapping & full prompt builder.
"""

_BG_MAP = {
    "formal office shirt":    "modern glass-wall corporate office, soft professional lighting, marble floors",
    "business suit":          "luxury conference room, city skyline window, elegant interior, powerful atmosphere",
    "casual t-shirt":         "vibrant urban street, colorful murals, trendy fashion district, golden hour",
    "dress evening gown":     "beautiful garden terrace, soft bokeh, romantic warm lighting, flowers",
    "swimwear bikini":        "tropical white sand beach, crystal turquoise water, palm trees, sunny day",
    "sportswear activewear":  "modern bright gym, motivational atmosphere, clean equipment background",
    "winter coat jacket":     "snowy European street, cozy cafe exterior, soft winter light, leafless trees",
    "traditional ao dai":     "Hoan Kiem Lake Hanoi, lotus pond, ancient Vietnamese architecture, golden light",
    "jeans pants":            "industrial chic loft, brick walls, trendy coffee shop, lifestyle setting",
    "skirt mini maxi":        "bright airy shopping mall, clean white marble, premium retail environment",
    "hoodie streetwear":      "urban night street, neon lights, skatepark, street art wall, cool atmosphere",
    "luxury accessories":     "luxury boutique interior, soft studio lighting, premium product photography",
}
_DEFAULT_BG = "clean fashion studio, soft gradient background, professional lighting"

_MOTION_MAP = {
    "dress":      "model gracefully turns 360 degrees, dress flows beautifully in gentle breeze",
    "skirt":      "model walks forward confidently, skirt sways with each elegant step",
    "swimwear":   "model poses on beach, gentle ocean breeze moves hair naturally, confident smile",
    "ao dai":     "model walks gracefully on wooden bridge, ao dai flows poetically in wind",
    "coat":       "model walks in cinematic slow motion, coat billows subtly, hands in pockets",
    "sport":      "model does light dynamic stretch, energetic natural movement",
    "suit":       "model stands with powerful presence, slight confident head turn",
    "hoodie":     "model does casual urban pose, subtle body sway, relaxed street vibe",
    "swimwear bikini": "model poses confidently on tropical beach",
}
_DEFAULT_MOTION = "model poses elegantly, subtle natural movement, hair gently flows"


def get_background_prompt(garment: str) -> str:
    lower = garment.lower()
    for key, prompt in _BG_MAP.items():
        if key in lower:
            return prompt
    return _DEFAULT_BG


def get_motion_prompt(garment: str) -> str:
    lower = garment.lower()
    for key, mot in _MOTION_MAP.items():
        if key in lower:
            return mot
    return _DEFAULT_MOTION


def get_full_prompt(garment: str, bg_prompt: str = "") -> str:
    motion = get_motion_prompt(garment)
    bg     = bg_prompt or get_background_prompt(garment)
    return (
        f"Beautiful Vietnamese fashion model wearing {garment}, {motion}. "
        f"{bg}. Cinematic slow push-in shot, shallow depth of field, "
        f"soft golden bokeh, professional fashion commercial quality, "
        f"8K ultra detailed, natural fabric texture, elegant pose, "
        f"smooth realistic motion, vibrant colors."
    )


def get_negative_prompt() -> str:
    return (
        "ugly, deformed, disfigured, blurry, low quality, watermark, logo, text overlay, "
        "extra limbs, bad anatomy, distorted face, cartoon, anime, static, frozen, "
        "flickering, nsfw, nude, unrealistic motion, robot movement"
    )
