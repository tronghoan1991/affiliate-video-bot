"""
pipeline/ai_analyzer.py — AI Garment & Face Recognition Engine
=============================================================================
Module trí tuệ nhân tạo trung tâm của bot:
  1. Nhận ảnh sản phẩm / ảnh người mặc → phân tích bằng CLIP
  2. Xác định: giới tính, nhóm tuổi, loại trang phục, phong cách, dịp dùng
  3. Đánh giá màu sắc, họa tiết, chất liệu (qua mô tả ảnh)
  4. Tự sinh kịch bản (VideoScript) phù hợp nhất
  5. Fallback text-only khi không có ảnh

AI Models được dùng:
  - openai/clip-vit-base-patch32 (zero-shot classification) — nhẹ, nhanh
  - Keyword matching fallback (không cần GPU, luôn hoạt động)
=============================================================================
"""
import logging
import re
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("AIAnalyzer")


# ══════════════════════════════════════════════════════════════════════════════
#  DATA STRUCTURES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class GarmentAnalysis:
    """Kết quả phân tích từ AI — đầu vào cho toàn bộ pipeline."""
    # Phân loại chính
    gender: str              # "women" | "men" | "children" | "unisex" | "baby"
    age_group: str           # "baby" | "toddler" | "kids" | "teen" | "adult" | "senior"
    garment_type: str        # "dress" | "shirt" | "pants" | ... (raw từ AI)
    garment_key: str         # key chuẩn hóa để tra template
    style_category: str      # "casual" | "formal" | "streetwear" | "sportswear" | "traditional" | "luxury"
    occasion: str            # "daily" | "office" | "party" | "beach" | "gym" | "wedding" | "school"

    # Chi tiết sản phẩm
    color_palette: list      # ["đỏ", "trắng", "navy"]
    pattern: str             # "trơn" | "kẻ sọc" | "hoa văn" | "chấm bi" | ...
    material_feel: str       # "nhẹ" | "ấm" | "mềm mại" | "cao cấp" | ...
    key_features: list       # ["tay ngắn", "cổ V", "cạp cao"]

    # Điểm bán hàng
    usp: str                 # Unique selling point nổi bật nhất
    target_customer: str     # "gen Z nữ 18-24" | "dad trung niên" | "bé gái 5-10 tuổi"
    confidence: float        # 0.0 - 1.0

    # Metadata
    analysis_method: str     # "clip_vision" | "text_keyword" | "hybrid"
    raw_description: str     # Mô tả gốc từ người dùng (nếu có)


@dataclass
class VideoScript:
    """Kịch bản video hoàn chỉnh do AI tự viết."""
    # Thông tin cơ bản
    title: str
    duration_seconds: float  # Tổng thời gian (mặc định 15s)
    platform: str

    # Các cảnh theo timeline
    hook_scene: "SceneBlock"         # 0–2.5s: dừng scroll
    reveal_scene: "SceneBlock"       # 2.5–6s: hiện sản phẩm + giá
    value_scene: "SceneBlock"        # 6–10s: value stack
    cta_scene: "SceneBlock"          # 10–13s: chốt đơn
    loop_scene: "SceneBlock"         # 13–15s: loop seamless

    # Nội dung đi kèm
    ai_prompt_main: str      # Prompt tạo video AI chính
    ai_prompt_hook: str      # Prompt frame hook (close-up)
    caption: str             # Caption đầy đủ
    hashtags: list
    music_mood: str
    color_scheme: dict       # Màu sắc overlay phù hợp style


@dataclass
class SceneBlock:
    """Một cảnh trong kịch bản video."""
    start_time: float
    end_time: float
    hook_text: str           # Text chính hiện trên màn hình
    subtext: str             # Text phụ (nhỏ hơn)
    visual_note: str         # Hướng dẫn quay/tạo AI video
    overlay_position: str    # "top" | "bottom" | "center" | "none"
    text_color: str
    bg_alpha: float          # Độ mờ overlay nền


# ══════════════════════════════════════════════════════════════════════════════
#  GARMENT TAXONOMY — Toàn bộ ngành thời trang (nam + nữ + trẻ em + unisex)
# ══════════════════════════════════════════════════════════════════════════════

GARMENT_TAXONOMY = {
    # ─── WOMEN ────────────────────────────────────────────────────────────────
    "dress_evening":    {"gender": "women", "age": "adult", "style": "formal",     "occasion": "party"},
    "dress_casual":     {"gender": "women", "age": "adult", "style": "casual",     "occasion": "daily"},
    "dress_midi":       {"gender": "women", "age": "adult", "style": "casual",     "occasion": "daily"},
    "dress_maxi":       {"gender": "women", "age": "adult", "style": "casual",     "occasion": "daily"},
    "dress_mini":       {"gender": "women", "age": "teen",  "style": "casual",     "occasion": "daily"},
    "blouse":           {"gender": "women", "age": "adult", "style": "casual",     "occasion": "daily"},
    "top_crop":         {"gender": "women", "age": "teen",  "style": "casual",     "occasion": "daily"},
    "skirt_mini":       {"gender": "women", "age": "teen",  "style": "casual",     "occasion": "daily"},
    "skirt_midi":       {"gender": "women", "age": "adult", "style": "casual",     "occasion": "daily"},
    "skirt_maxi":       {"gender": "women", "age": "adult", "style": "casual",     "occasion": "daily"},
    "ao_dai":           {"gender": "women", "age": "adult", "style": "traditional","occasion": "event"},
    "swimwear_women":   {"gender": "women", "age": "adult", "style": "casual",     "occasion": "beach"},
    "lingerie":         {"gender": "women", "age": "adult", "style": "intimate",   "occasion": "daily"},
    "pajamas_women":    {"gender": "women", "age": "adult", "style": "casual",     "occasion": "home"},
    "women_blazer":     {"gender": "women", "age": "adult", "style": "formal",     "occasion": "office"},
    "women_suit":       {"gender": "women", "age": "adult", "style": "formal",     "occasion": "office"},
    "women_coat":       {"gender": "women", "age": "adult", "style": "casual",     "occasion": "daily"},
    "women_jeans":      {"gender": "women", "age": "adult", "style": "casual",     "occasion": "daily"},
    "women_leggings":   {"gender": "women", "age": "adult", "style": "sportswear", "occasion": "gym"},
    "women_activewear": {"gender": "women", "age": "adult", "style": "sportswear", "occasion": "gym"},
    "women_hoodie":     {"gender": "women", "age": "teen",  "style": "streetwear", "occasion": "daily"},
    "handbag":          {"gender": "women", "age": "adult", "style": "luxury",     "occasion": "daily"},
    "shoes_women":      {"gender": "women", "age": "adult", "style": "casual",     "occasion": "daily"},
    "heels":            {"gender": "women", "age": "adult", "style": "formal",     "occasion": "party"},
    "jewelry":          {"gender": "women", "age": "adult", "style": "luxury",     "occasion": "daily"},

    # ─── MEN ──────────────────────────────────────────────────────────────────
    "men_tshirt":       {"gender": "men",   "age": "adult", "style": "casual",     "occasion": "daily"},
    "men_polo":         {"gender": "men",   "age": "adult", "style": "casual",     "occasion": "daily"},
    "men_shirt_casual": {"gender": "men",   "age": "adult", "style": "casual",     "occasion": "daily"},
    "men_shirt_formal": {"gender": "men",   "age": "adult", "style": "formal",     "occasion": "office"},
    "men_suit":         {"gender": "men",   "age": "adult", "style": "formal",     "occasion": "office"},
    "men_blazer":       {"gender": "men",   "age": "adult", "style": "formal",     "occasion": "office"},
    "men_jeans":        {"gender": "men",   "age": "adult", "style": "casual",     "occasion": "daily"},
    "men_shorts":       {"gender": "men",   "age": "adult", "style": "casual",     "occasion": "daily"},
    "men_chinos":       {"gender": "men",   "age": "adult", "style": "smart",      "occasion": "daily"},
    "men_hoodie":       {"gender": "men",   "age": "teen",  "style": "streetwear", "occasion": "daily"},
    "men_jacket":       {"gender": "men",   "age": "adult", "style": "casual",     "occasion": "daily"},
    "men_coat":         {"gender": "men",   "age": "adult", "style": "formal",     "occasion": "daily"},
    "men_sportswear":   {"gender": "men",   "age": "adult", "style": "sportswear", "occasion": "gym"},
    "men_swimwear":     {"gender": "men",   "age": "adult", "style": "casual",     "occasion": "beach"},
    "men_pajamas":      {"gender": "men",   "age": "adult", "style": "casual",     "occasion": "home"},
    "men_shoes":        {"gender": "men",   "age": "adult", "style": "casual",     "occasion": "daily"},
    "men_sneakers":     {"gender": "men",   "age": "teen",  "style": "streetwear", "occasion": "daily"},
    "men_accessories":  {"gender": "men",   "age": "adult", "style": "casual",     "occasion": "daily"},
    "men_streetwear":   {"gender": "men",   "age": "teen",  "style": "streetwear", "occasion": "daily"},
    "ao_dai_men":       {"gender": "men",   "age": "adult", "style": "traditional","occasion": "event"},

    # ─── CHILDREN ─────────────────────────────────────────────────────────────
    "baby_onesie":      {"gender": "unisex","age": "baby",  "style": "casual",     "occasion": "daily"},
    "baby_set":         {"gender": "unisex","age": "baby",  "style": "casual",     "occasion": "daily"},
    "baby_romper":      {"gender": "unisex","age": "toddler","style": "casual",    "occasion": "daily"},
    "kids_tshirt":      {"gender": "unisex","age": "kids",  "style": "casual",     "occasion": "daily"},
    "kids_dress":       {"gender": "children","age": "kids","style": "casual",     "occasion": "daily"},
    "kids_set":         {"gender": "unisex","age": "kids",  "style": "casual",     "occasion": "daily"},
    "kids_school":      {"gender": "unisex","age": "kids",  "style": "formal",     "occasion": "school"},
    "kids_sportswear":  {"gender": "unisex","age": "kids",  "style": "sportswear", "occasion": "play"},
    "kids_pajamas":     {"gender": "unisex","age": "kids",  "style": "casual",     "occasion": "home"},
    "kids_jacket":      {"gender": "unisex","age": "kids",  "style": "casual",     "occasion": "daily"},
    "kids_swimwear":    {"gender": "unisex","age": "kids",  "style": "casual",     "occasion": "beach"},
    "kids_shoes":       {"gender": "unisex","age": "kids",  "style": "casual",     "occasion": "daily"},
    "teen_casual":      {"gender": "unisex","age": "teen",  "style": "casual",     "occasion": "daily"},
    "teen_streetwear":  {"gender": "unisex","age": "teen",  "style": "streetwear", "occasion": "daily"},
    "kids_ao_dai":      {"gender": "unisex","age": "kids",  "style": "traditional","occasion": "event"},

    # ─── UNISEX ───────────────────────────────────────────────────────────────
    "unisex_hoodie":    {"gender": "unisex","age": "adult", "style": "streetwear", "occasion": "daily"},
    "unisex_tshirt":    {"gender": "unisex","age": "adult", "style": "casual",     "occasion": "daily"},
    "couple_set":       {"gender": "unisex","age": "adult", "style": "casual",     "occasion": "daily"},
    "family_matching":  {"gender": "unisex","age": "kids",  "style": "casual",     "occasion": "event"},
}

# ══════════════════════════════════════════════════════════════════════════════
#  KEYWORD MATCHING — Text-based classifier (fallback, luôn hoạt động)
# ══════════════════════════════════════════════════════════════════════════════

_KEYWORD_MAP = {
    # Women
    "váy dạ hội|đầm dạ hội|evening gown|gown": "dress_evening",
    "váy|đầm|dress": "dress_casual",
    "áo dài nữ|áo dài phụ nữ": "ao_dai",
    "bikini|đồ bơi nữ|swimwear nữ": "swimwear_women",
    "bộ đồ tập nữ|quần legging|legging|yoga pants": "women_leggings",
    "áo thun nữ|top nữ": "blouse",
    "chân váy": "skirt_midi",
    "áo khoác nữ|coat nữ": "women_coat",
    "áo vest nữ|blazer nữ|suit nữ|bộ vest nữ": "women_suit",
    "jeans nữ|quần jeans nữ": "women_jeans",
    "hoodie nữ|áo hoodie nữ": "women_hoodie",
    "túi xách|handbag|bag nữ": "handbag",
    "giày cao gót|heels": "heels",
    "trang sức|jewelry|necklace|vòng cổ": "jewelry",
    "đồ ngủ nữ|pyjama nữ": "pajamas_women",
    "đồ tập gym nữ|activewear nữ": "women_activewear",

    # Men
    "áo thun nam|áo phông nam|t-shirt nam": "men_tshirt",
    "áo polo nam": "men_polo",
    "áo sơ mi nam|dress shirt nam": "men_shirt_formal",
    "áo sơ mi casual nam|casual shirt nam": "men_shirt_casual",
    "vest nam|suit nam|bộ vest nam|bộ suit nam": "men_suit",
    "blazer nam|áo vest đơn nam": "men_blazer",
    "jeans nam|quần jeans nam|denim nam": "men_jeans",
    "quần short nam|shorts nam": "men_shorts",
    "quần tây nam|chinos nam|quần kaki nam": "men_chinos",
    "hoodie nam|áo hoodie nam": "men_hoodie",
    "áo khoác nam|jacket nam|coat nam": "men_jacket",
    "đồ tập gym nam|activewear nam|sportswear nam": "men_sportswear",
    "đồ bơi nam|swim trunk": "men_swimwear",
    "giày nam|shoes nam|sneaker nam": "men_sneakers",
    "streetwear nam|outfit nam": "men_streetwear",
    "áo dài nam": "ao_dai_men",
    "phụ kiện nam|accessories nam": "men_accessories",
    "đồ ngủ nam|pyjama nam": "men_pajamas",

    # Children
    "bodysuit bé|áo liền bé|onesie": "baby_onesie",
    "set bé sơ sinh|đồ sơ sinh": "baby_set",
    "romper bé|áo liền quần bé": "baby_romper",
    "áo thun bé|áo phông trẻ em": "kids_tshirt",
    "váy bé gái|đầm bé gái|dress bé": "kids_dress",
    "bộ đồ trẻ em|set trẻ em|set bé": "kids_set",
    "đồng phục học sinh|school uniform": "kids_school",
    "đồ tập trẻ em|sportwear trẻ em": "kids_sportswear",
    "đồ ngủ bé|pyjama trẻ em": "kids_pajamas",
    "áo khoác trẻ em|jacket bé": "kids_jacket",
    "đồ bơi trẻ em|swim bé": "kids_swimwear",
    "giày trẻ em|shoes bé": "kids_shoes",
    "áo dài bé|áo dài trẻ em": "kids_ao_dai",
    "teen|tuổi teen|học sinh": "teen_casual",
    "streetwear teen|outfit teen": "teen_streetwear",

    # Unisex
    "hoodie unisex|áo hoodie đôi": "unisex_hoodie",
    "áo thun unisex|áo đôi": "unisex_tshirt",
    "đồ đôi|couple": "couple_set",
    "đồ gia đình|family matching|set gia đình": "family_matching",
}


def _keyword_classify(text: str) -> str:
    """Phân loại sản phẩm bằng keyword matching."""
    t = text.lower().strip()
    for pattern, key in _KEYWORD_MAP.items():
        for kw in pattern.split("|"):
            if kw.strip() in t:
                return key
    # Detect gender từ text nếu không match garment cụ thể
    if any(w in t for w in ["nam", "men", "boy", "con trai"]):
        return "men_tshirt"
    if any(w in t for w in ["bé", "trẻ em", "baby", "kids", "con", "nhi đồng"]):
        return "kids_set"
    return "dress_casual"  # default: women's casual


# ══════════════════════════════════════════════════════════════════════════════
#  CLIP-BASED VISION CLASSIFIER
# ══════════════════════════════════════════════════════════════════════════════

# Zero-shot labels cho CLIP
_CLIP_LABELS_GENDER = [
    "women's clothing", "men's clothing", "children's clothing",
    "baby clothes", "unisex clothing"
]

_CLIP_LABELS_GARMENT = [
    "evening dress gown", "casual dress", "blouse top", "skirt",
    "t-shirt shirt", "suit jacket blazer", "coat jacket", "hoodie sweatshirt",
    "jeans pants trousers", "sportswear activewear", "swimwear bikini",
    "traditional vietnamese ao dai", "baby romper onesie", "kids clothing",
    "accessories handbag shoes jewelry"
]

_CLIP_LABELS_STYLE = [
    "casual everyday style", "formal business professional style",
    "streetwear urban style", "sportswear athletic style",
    "traditional cultural style", "luxury premium style", "cute kawaii style"
]

_CLIP_LABELS_OCCASION = [
    "office work daily", "party evening out", "beach vacation",
    "gym workout", "school education", "wedding special event",
    "home leisure relaxation", "street outdoor"
]


def _try_clip_classify(image_path: str) -> Optional[dict]:
    """
    Phân loại bằng CLIP vision model.
    Returns None nếu không có GPU/model.
    """
    try:
        from PIL import Image
        from transformers import CLIPProcessor, CLIPModel
        import torch

        logger.info("Loading CLIP model...")
        model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
        processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
        model.eval()

        image = Image.open(image_path).convert("RGB")

        results = {}
        for label_set_name, labels in [
            ("gender", _CLIP_LABELS_GENDER),
            ("garment", _CLIP_LABELS_GARMENT),
            ("style", _CLIP_LABELS_STYLE),
            ("occasion", _CLIP_LABELS_OCCASION),
        ]:
            inputs = processor(
                text=labels,
                images=image,
                return_tensors="pt",
                padding=True,
            )
            with torch.no_grad():
                outputs = model(**inputs)
            probs = outputs.logits_per_image.softmax(dim=1)[0]
            best_idx = probs.argmax().item()
            results[label_set_name] = {
                "label": labels[best_idx],
                "confidence": float(probs[best_idx]),
            }

        logger.info(f"CLIP results: {results}")
        return results

    except ImportError:
        logger.info("CLIP not available (transformers not installed)")
        return None
    except Exception as e:
        logger.warning(f"CLIP classification failed: {e}")
        return None


def _parse_clip_results(clip: dict) -> tuple:
    """Chuyển CLIP output → garment_key + metadata."""
    gender_label = clip["gender"]["label"]
    garment_label = clip["garment"]["label"].lower()
    style_label = clip["style"]["label"].lower()
    occasion_label = clip["occasion"]["label"].lower()

    # Map gender
    if "men" in gender_label and "women" not in gender_label:
        gender = "men"
    elif "children" in gender_label or "baby" in gender_label:
        gender = "children"
    elif "unisex" in gender_label:
        gender = "unisex"
    else:
        gender = "women"

    # Map garment_key từ CLIP label + gender
    key = "dress_casual"  # default
    if "evening" in garment_label or "gown" in garment_label:
        key = "dress_evening" if gender == "women" else "men_suit"
    elif "suit" in garment_label or "blazer" in garment_label:
        key = "women_suit" if gender == "women" else "men_suit"
    elif "hoodie" in garment_label or "sweatshirt" in garment_label:
        key = "women_hoodie" if gender == "women" else ("men_hoodie" if gender == "men" else "unisex_hoodie")
    elif "skirt" in garment_label:
        key = "skirt_midi"
    elif "swimwear" in garment_label or "bikini" in garment_label:
        key = "swimwear_women" if gender == "women" else ("men_swimwear" if gender == "men" else "kids_swimwear")
    elif "activewear" in garment_label or "sportswear" in garment_label:
        key = "women_activewear" if gender == "women" else ("men_sportswear" if gender == "men" else "kids_sportswear")
    elif "coat" in garment_label or "jacket" in garment_label:
        key = "women_coat" if gender == "women" else "men_jacket"
    elif "t-shirt" in garment_label or "shirt" in garment_label:
        key = "blouse" if gender == "women" else ("men_shirt_casual" if gender == "men" else "kids_tshirt")
    elif "jeans" in garment_label or "pants" in garment_label:
        key = "women_jeans" if gender == "women" else "men_jeans"
    elif "ao dai" in garment_label:
        key = "ao_dai" if gender == "women" else "ao_dai_men"
    elif "baby" in garment_label or "romper" in garment_label:
        key = "baby_romper"
    elif "kids" in garment_label or "children" in garment_label:
        key = "kids_set"
    elif "accessories" in garment_label:
        key = "jewelry" if gender == "women" else "men_accessories"

    return key, gender, style_label, occasion_label


# ══════════════════════════════════════════════════════════════════════════════
#  COLOR & PATTERN DETECTION
# ══════════════════════════════════════════════════════════════════════════════

def _extract_colors_patterns(description: str) -> tuple:
    """Trích xuất màu sắc và họa tiết từ mô tả text."""
    desc = description.lower()

    color_keywords = {
        "đỏ": "đỏ", "red": "đỏ", "hồng": "hồng", "pink": "hồng",
        "xanh navy": "navy", "navy": "navy", "xanh lam": "xanh lam",
        "blue": "xanh lam", "xanh lá": "xanh lá", "green": "xanh lá",
        "vàng": "vàng", "yellow": "vàng", "cam": "cam", "orange": "cam",
        "trắng": "trắng", "white": "trắng", "đen": "đen", "black": "đen",
        "xám": "xám", "grey": "xám", "gray": "xám", "be": "be",
        "beige": "be", "tím": "tím", "purple": "tím", "nâu": "nâu",
        "brown": "nâu", "kem": "kem", "cream": "kem",
    }
    colors = list({color_keywords[k] for k in color_keywords if k in desc})[:3]
    if not colors:
        colors = ["đa màu"]

    pattern_keywords = {
        "trơn": "trơn", "solid": "trơn", "kẻ sọc": "kẻ sọc",
        "stripe": "kẻ sọc", "hoa": "hoa văn", "floral": "hoa văn",
        "chấm": "chấm bi", "polka": "chấm bi", "caro": "caro",
        "plaid": "caro", "họa tiết": "họa tiết", "print": "họa tiết",
        "thêu": "thêu", "embroidery": "thêu", "graphic": "graphic print",
    }
    pattern = "trơn"  # default
    for k, v in pattern_keywords.items():
        if k in desc:
            pattern = v
            break

    return colors, pattern


def _infer_target_customer(gender: str, age_group: str, style: str) -> str:
    """Xác định khách hàng mục tiêu cụ thể."""
    mapping = {
        ("women", "adult", "formal"):     "Chị em công sở 25-40 tuổi",
        ("women", "adult", "casual"):     "Nữ gen Y-Z thích thời trang 18-35 tuổi",
        ("women", "teen", "streetwear"):  "Nữ gen Z năng động 15-24 tuổi",
        ("women", "adult", "traditional"):"Phụ nữ Việt trân trọng văn hóa",
        ("women", "adult", "luxury"):     "Phụ nữ thành đạt thích luxury look",
        ("women", "adult", "sportswear"): "Chị em yêu gym và lối sống active",
        ("men", "adult", "formal"):       "Anh em công sở/doanh nhân 25-45 tuổi",
        ("men", "adult", "casual"):       "Nam gen Y thích style thoải mái 22-35 tuổi",
        ("men", "teen", "streetwear"):    "Bạn nam gen Z thích street style 15-25 tuổi",
        ("men", "adult", "sportswear"):   "Anh em gym yêu thể thao",
        ("men", "adult", "traditional"):  "Quý ông trân trọng văn hóa Việt",
        ("children", "baby", "casual"):   "Ba mẹ có con 0-2 tuổi",
        ("children", "toddler", "casual"):"Ba mẹ có con 2-4 tuổi",
        ("children", "kids", "casual"):   "Ba mẹ có con 5-12 tuổi",
        ("unisex", "kids", "casual"):     "Ba mẹ tìm đồ cho bé không phân biệt giới",
        ("unisex", "teen", "streetwear"): "Giới trẻ gen Z không giới hạn phong cách",
        ("unisex", "adult", "casual"):    "Cặp đôi hoặc bạn bè thích tự do phong cách",
    }
    return mapping.get((gender, age_group, style),
                       f"Khách hàng thời trang {gender} {age_group}")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN ANALYZER
# ══════════════════════════════════════════════════════════════════════════════

def analyze_product(
    product_name: str = "",
    product_description: str = "",
    image_path: Optional[str] = None,
    gender_hint: str = "",      # "women" | "men" | "children" | "" (auto-detect)
) -> GarmentAnalysis:
    """
    Phân tích sản phẩm thời trang → GarmentAnalysis.

    Quy trình:
    1. CLIP vision (nếu có ảnh + model)
    2. Keyword text matching (luôn chạy)
    3. Combine results với confidence scoring
    """
    combined_text = f"{product_name} {product_description}".strip()

    # Override gender nếu user đã chỉ định
    if gender_hint and gender_hint in ("women", "men", "children", "unisex", "baby"):
        gender_override = gender_hint
    else:
        gender_override = None

    clip_results = None
    method = "text_keyword"

    # Try CLIP if image provided
    if image_path:
        clip_results = _try_clip_classify(image_path)
        if clip_results:
            method = "clip_vision"

    # Determine garment_key
    if clip_results:
        garment_key, gender_clip, style_clip, occasion_clip = _parse_clip_results(clip_results)
        confidence = clip_results["garment"]["confidence"]
        # Nếu confidence thấp, blend với keyword result
        if confidence < 0.5:
            kw_key = _keyword_classify(combined_text)
            garment_key = kw_key if kw_key != "dress_casual" else garment_key
            method = "hybrid"
    else:
        garment_key = _keyword_classify(combined_text)
        confidence = 0.85  # keyword matching thường khá chính xác

    # Get taxonomy info
    taxonomy = GARMENT_TAXONOMY.get(garment_key, GARMENT_TAXONOMY["dress_casual"])
    gender = gender_override or taxonomy["gender"]
    age_group = taxonomy["age"]
    style = taxonomy.get("style", "casual")
    occasion = taxonomy.get("occasion", "daily")

    # Extract colors & patterns
    colors, pattern = _extract_colors_patterns(combined_text)

    # Infer material feel from keywords
    material_feel = "mềm mại"
    for kw, feel in [
        ("lụa|silk|satin", "lụa mềm mại"),
        ("cotton|vải bông", "thoáng mát"),
        ("wool|len|dạ", "ấm áp"),
        ("denim|jean", "bền chắc"),
        ("ren|lace", "tinh tế"),
        ("caosu|spandex|lycra|stretch", "co giãn tốt"),
        ("polyester", "nhẹ, dễ chăm sóc"),
        ("vải thô|linen", "tự nhiên, thoáng"),
    ]:
        if any(k in combined_text.lower() for k in kw.split("|")):
            material_feel = feel
            break

    # Extract key features
    features = []
    feature_kw = {
        "cổ V|v-neck": "cổ V thanh lịch",
        "cổ tròn|round neck": "cổ tròn dễ phối",
        "tay ngắn|short sleeve": "tay ngắn thoải mái",
        "tay dài|long sleeve": "tay dài sang trọng",
        "không tay|sleeveless": "không tay mát mẻ",
        "cạp cao|high waist": "cạp cao tôn dáng",
        "form rộng|oversized": "form rộng thời thượng",
        "form ôm|slim fit": "form ôm tôn dáng",
        "có túi|with pocket": "tiện dụng có túi",
        "freeship|miễn phí": "freeship toàn quốc",
    }
    for kw, label in feature_kw.items():
        if any(k in combined_text.lower() for k in kw.split("|")):
            features.append(label)
    if not features:
        features = ["chất liệu tốt", "may đẹp tỉ mỉ"]

    # USP
    usp_map = {
        "dress_evening": "Váy dạ hội đẳng cấp với mức giá không tưởng",
        "ao_dai": "Áo dài Việt đẹp — tự hào văn hóa dân tộc",
        "men_suit": "Suit cao cấp — boss energy không cần giải thích",
        "women_activewear": "Đồ tập co giãn 4 chiều, không hề khó chịu",
        "kids_set": "An toàn tuyệt đối cho bé, ba mẹ yên tâm",
        "baby_onesie": "Chất liệu mềm nhẹ, an toàn 100% cho da bé",
        "couple_set": "Đồ đôi matching — kỷ niệm tình yêu đẹp nhất",
        "family_matching": "Set gia đình matching — khoảnh khắc đáng nhớ",
        "handbag": "Luxury look không cần luxury budget",
        "men_streetwear": "Street style đỉnh — flex không cần giải thích",
    }
    usp = usp_map.get(garment_key, "Chất lượng vượt trội với mức giá tốt nhất")

    target = _infer_target_customer(gender, age_group, style)

    return GarmentAnalysis(
        gender=gender,
        age_group=age_group,
        garment_type=product_name or garment_key.replace("_", " "),
        garment_key=garment_key,
        style_category=style,
        occasion=occasion,
        color_palette=colors,
        pattern=pattern,
        material_feel=material_feel,
        key_features=features,
        usp=usp,
        target_customer=target,
        confidence=confidence,
        analysis_method=method,
        raw_description=combined_text,
    )
