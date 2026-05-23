"""
pipeline/ai_analyzer.py — AI Garment Analyzer v6
=============================================================================
Phân tích sản phẩm thời trang:
  1. Nhận text mô tả → phân loại bằng keyword matching (chạy mọi nơi, không cần GPU)
  2. Nhận ảnh → CLIP zero-shot classification (cần GPU / Colab)
  3. Output: GarmentAnalysis → dùng cho toàn bộ pipeline sinh video

AI Models (miễn phí, chạy trên Colab GPU):
  - openai/clip-vit-large-patch14 — nhận diện ảnh tốt hơn base patch32
  - Fallback: keyword matching — không cần GPU, luôn hoạt động
=============================================================================
"""
import logging
import random
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger("AIAnalyzer")


# ══════════════════════════════════════════════════════════════════════════════
#  DATA STRUCTURES
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class GarmentAnalysis:
    gender: str           # women | men | children | baby | unisex
    age_group: str        # baby | toddler | kids | teen | adult | senior
    garment_type: str     # Tên loại trang phục (raw)
    garment_key: str      # Key chuẩn hóa
    style_category: str   # casual | formal | streetwear | sportswear | traditional | luxury | swimwear
    occasion: str         # daily | office | party | beach | gym | wedding | school | tet

    color_palette: list   # ["đỏ", "trắng"]
    pattern: str          # trơn | kẻ sọc | hoa văn | chấm bi | v.v.
    material_feel: str    # nhẹ | ấm | mềm mại | cao cấp
    key_features: list    # ["tay ngắn", "cổ V"]

    usp: str              # Unique selling point
    target_customer: str  # "gen Z nữ 18-24"
    confidence: float     # 0.0 - 1.0

    analysis_method: str  # clip_vision | text_keyword | hybrid
    raw_description: str  # Mô tả gốc từ người dùng


@dataclass
class SceneBlock:
    hook_text: str        # Câu chính hiển thị trên màn hình
    subtext: str          # Câu phụ / CTA nhỏ
    duration: float       # Giây
    transition: str       # fade | slide | zoom | none
    overlay_style: str    # hook_top | product_mid | value_bottom | cta_full


@dataclass
class VideoScript:
    title: str
    duration_seconds: float
    platform: str

    hook_scene: SceneBlock
    reveal_scene: SceneBlock
    value_scene: SceneBlock
    cta_scene: SceneBlock
    loop_scene: SceneBlock

    ai_prompt_main: str
    ai_prompt_hook: str
    caption: str
    music_mood: str
    hashtags: str


# ══════════════════════════════════════════════════════════════════════════════
#  KEYWORD MAPS
# ══════════════════════════════════════════════════════════════════════════════

_GENDER_KW = {
    "men":      ["nam", "men", "anh", "chú", "bố", "ông", "trai", "boy", "he", "him", "vest", "suit nam", "áo sơ mi nam"],
    "children": ["bé", "trẻ em", "kids", "child", "nhi", "con", "học sinh", "3-", "4-", "5-", "6-", "7-", "8-", "9-", "10-"],
    "baby":     ["sơ sinh", "baby", "0-", "1-", "2-", "nhũ nhi", "tã", "bib", "onesie", "bodysuit bé"],
    "unisex":   ["đôi", "couple", "gia đình", "family", "unisex", "gender-free", "matching"],
}
_STYLE_KW = {
    "formal":       ["vest", "suit", "blazer", "công sở", "formal", "sơ mi", "tuxedo", "đồng phục"],
    "traditional":  ["áo dài", "ao dai", "truyền thống", "tết", "lễ hội"],
    "sportswear":   ["gym", "tập", "sport", "active", "yoga", "legging", "chạy bộ", "thể thao"],
    "streetwear":   ["hoodie", "street", "drip", "phonk", "skate", "urban", "oversized", "cap", "sneaker"],
    "luxury":       ["túi", "bag", "trang sức", "jewelry", "phụ kiện", "đồng hồ", "watch", "luxury", "sang"],
    "swimwear":     ["bikini", "bơi", "swim", "beach", "biển", "đi biển"],
}
_OCCASION_KW = {
    "office":   ["văn phòng", "công sở", "office", "họp", "phỏng vấn"],
    "party":    ["dạ hội", "tiệc", "party", "event", "sự kiện"],
    "beach":    ["biển", "beach", "hồ bơi", "pool"],
    "gym":      ["gym", "tập", "workout", "yoga"],
    "wedding":  ["cưới", "wedding", "đám cưới"],
    "school":   ["học", "school", "trường", "lớp"],
    "tet":      ["tết", "tet", "mùng", "xuân"],
}
_COLOR_KW = {
    "đỏ": ["đỏ", "red", "crimson", "scarlet"],
    "trắng": ["trắng", "white", "ivory"],
    "đen": ["đen", "black"],
    "xanh navy": ["navy", "xanh navy", "xanh đậm"],
    "xanh dương": ["xanh dương", "blue", "sky blue"],
    "xanh lá": ["xanh lá", "green", "mint"],
    "hồng": ["hồng", "pink", "rose", "baby pink"],
    "vàng": ["vàng", "yellow", "gold", "mustard"],
    "be/kem": ["be", "kem", "cream", "nude", "beige"],
    "tím": ["tím", "purple", "lavender", "violet"],
    "cam": ["cam", "orange", "coral"],
    "xám": ["xám", "grey", "gray"],
    "nâu": ["nâu", "brown", "chocolate", "caramel"],
}
_PATTERN_KW = {
    "hoa văn": ["hoa", "floral", "flower"],
    "kẻ sọc": ["sọc", "stripe", "kẻ"],
    "chấm bi": ["chấm", "dot", "polka"],
    "caro": ["caro", "plaid", "check", "tartan"],
    "da báo": ["leopard", "da báo", "animal print"],
    "trơn": [],  # default
}
_MATERIAL_KW = {
    "lụa cao cấp": ["lụa", "silk", "satin"],
    "cotton mềm": ["cotton", "cotton mềm", "vải bông"],
    "thun thoáng": ["thun", "jersey", "knit"],
    "denim": ["denim", "jeans", "jean"],
    "kaki": ["kaki", "khaki", "canvas"],
    "len ấm": ["len", "wool", "cashmere", "flannel"],
}


def _match(text: str, keywords: list) -> bool:
    t = text.lower()
    return any(k in t for k in keywords)


def _detect_colors(text: str) -> list:
    found = [color for color, kws in _COLOR_KW.items() if _match(text, kws)]
    return found[:3] if found else ["không rõ"]


def _detect_pattern(text: str) -> str:
    for ptn, kws in _PATTERN_KW.items():
        if kws and _match(text, kws):
            return ptn
    return "trơn"


def _detect_material(text: str) -> str:
    for mat, kws in _MATERIAL_KW.items():
        if _match(text, kws):
            return mat
    return "vải thoáng mát"


def _usp_for(gender: str, style: str, material: str) -> str:
    usps = {
        ("women", "formal"):      "Tự tin, chuyên nghiệp — mặc vào là lên level ngay",
        ("women", "casual"):      "Thoải mái cả ngày mà vẫn đẹp không cần cố",
        ("women", "traditional"): "Áo dài Việt tinh tế — tự hào khi mặc",
        ("women", "sportswear"):  "Thoáng khí, co giãn 4 chiều — tập không bó bất cứ động tác nào",
        ("women", "streetwear"):  "Streetwear 2026 chuẩn trend — flex không cần giải thích",
        ("women", "luxury"):      "Sang trọng dễ phối — nâng tầm bất kỳ outfit nào",
        ("women", "swimwear"):    "Tôn dáng, không sợ lệch — tự tin ở bất kỳ góc nào",
        ("men", "formal"):        "Suit chuẩn form — gặp ai cũng ấn tượng ngay",
        ("men", "casual"):        "Đơn giản mà có gu — mặc đi đâu cũng hợp",
        ("men", "streetwear"):    "Drip 2026 — chuẩn vibe không cần nỗ lực",
        ("men", "sportswear"):    "Năng động, thoáng khí — từ gym đến café không cần đổi đồ",
        ("men", "traditional"):   "Áo dài nam — phong thái quý ông Việt đúng nghĩa",
        ("children", "casual"):   "Cute, an toàn, thoải mái — bé thích mặc cả ngày",
        ("baby", "casual"):       "Chất liệu mềm mại, an toàn tuyệt đối cho làn da bé",
        ("unisex", "casual"):     "Matching đẹp mà không sến — ai mặc cũng phù hợp",
    }
    return usps.get((gender, style), f"{material} — chất lượng vượt giá tiền")


def _target_for(gender: str, style: str) -> str:
    targets = {
        ("women", "formal"):      "Phụ nữ văn phòng 23-35 tuổi muốn ăn mặc chuyên nghiệp",
        ("women", "casual"):      "Cô gái trẻ 18-28 tuổi yêu thích phong cách thoải mái",
        ("women", "traditional"): "Phụ nữ Việt yêu văn hóa truyền thống, dịp lễ Tết",
        ("women", "streetwear"):  "Gen Z nữ 16-25 tuổi theo trend đường phố 2026",
        ("women", "sportswear"):  "Chị em năng động 20-35 tuổi tập gym, yoga, chạy bộ",
        ("men", "formal"):        "Nam giới công sở 25-40 tuổi cần suit chất lượng",
        ("men", "casual"):        "Anh chàng trẻ 20-35 tuổi thích mặc đơn giản có gu",
        ("men", "streetwear"):    "Gen Z nam 16-28 tuổi đam mê streetwear 2026",
        ("men", "sportswear"):    "Anh chàng năng động 20-35 tuổi tập gym, chạy bộ",
        ("children", "casual"):   "Ba mẹ có con 3-12 tuổi tìm đồ đẹp, an toàn, giá hợp lý",
        ("baby", "casual"):       "Ba mẹ có bé sơ sinh - 24 tháng, ưu tiên an toàn tuyệt đối",
        ("unisex", "casual"):     "Cặp đôi, gia đình muốn mặc đồng phục matching cute",
    }
    return targets.get((gender, style), "Người tiêu dùng Việt yêu thích thời trang")


# ══════════════════════════════════════════════════════════════════════════════
#  CLIP-BASED ANALYSIS (chỉ chạy khi có GPU)
# ══════════════════════════════════════════════════════════════════════════════

def _analyze_with_clip(image_path: str, description: str = "") -> Optional[dict]:
    """Dùng CLIP để phân tích ảnh sản phẩm — chỉ chạy trên Colab GPU."""
    try:
        import torch
        import open_clip
        from PIL import Image as PILImage

        device = "cuda" if torch.cuda.is_available() else "cpu"
        model, _, preprocess = open_clip.create_model_and_transforms(
            "ViT-L-14", pretrained="laion2b_s32b_b82k", device=device
        )
        tokenizer = open_clip.get_tokenizer("ViT-L-14")

        img = preprocess(PILImage.open(image_path).convert("RGB")).unsqueeze(0).to(device)

        candidates = [
            "women's dress", "women's casual outfit", "women's formal suit",
            "men's suit", "men's casual shirt", "men's streetwear",
            "children's clothing", "baby clothing", "couple matching outfit",
            "women's sportswear", "men's sportswear", "traditional Vietnamese ao dai",
            "women's swimwear", "luxury fashion accessories",
        ]
        texts = tokenizer(candidates).to(device)

        with torch.no_grad():
            img_feat  = model.encode_image(img)
            txt_feat  = model.encode_text(texts)
            img_feat /= img_feat.norm(dim=-1, keepdim=True)
            txt_feat /= txt_feat.norm(dim=-1, keepdim=True)
            sims = (img_feat @ txt_feat.T).squeeze(0)

        top_idx = sims.argmax().item()
        confidence = float(sims[top_idx])
        return {"label": candidates[top_idx], "confidence": confidence}

    except Exception as e:
        logger.warning(f"CLIP analysis thất bại: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def analyze_product(
    product_name: str,
    product_description: str = "",
    image_path: Optional[str] = None,
    gender_hint: str = "",
) -> GarmentAnalysis:
    """
    Phân tích sản phẩm thời trang → trả về GarmentAnalysis.
    Tự động chọn phương pháp: CLIP (có ảnh + GPU) hoặc keyword (không có ảnh).
    """
    combined = f"{product_name} {product_description}".lower()

    # ── Phát hiện giới tính ───────────────────────────────────────────────────
    gender = gender_hint
    if not gender:
        for g, kws in _GENDER_KW.items():
            if _match(combined, kws):
                gender = g
                break
        if not gender:
            gender = "women"  # default

    # ── Phát hiện phong cách ──────────────────────────────────────────────────
    style = "casual"
    for s, kws in _STYLE_KW.items():
        if _match(combined, kws):
            style = s
            break

    # ── Phát hiện dịp dùng ────────────────────────────────────────────────────
    occasion = "daily"
    for occ, kws in _OCCASION_KW.items():
        if _match(combined, kws):
            occasion = occ
            break

    # ── Nhóm tuổi ─────────────────────────────────────────────────────────────
    age_map = {"baby": "baby", "children": "kids", "men": "adult", "women": "adult", "unisex": "adult"}
    age_group = age_map.get(gender, "adult")

    # ── Màu + họa tiết + chất liệu ────────────────────────────────────────────
    colors   = _detect_colors(combined)
    pattern  = _detect_pattern(combined)
    material = _detect_material(combined)

    # ── Garment key ───────────────────────────────────────────────────────────
    garment_key = f"{gender}_{style}"

    # ── CLIP (nếu có ảnh) ─────────────────────────────────────────────────────
    method     = "text_keyword"
    confidence = 0.82
    if image_path:
        clip_result = _analyze_with_clip(image_path, combined)
        if clip_result and clip_result["confidence"] > 0.4:
            method     = "clip_vision"
            confidence = clip_result["confidence"]

    return GarmentAnalysis(
        gender         = gender,
        age_group      = age_group,
        garment_type   = product_name,
        garment_key    = garment_key,
        style_category = style,
        occasion       = occasion,
        color_palette  = colors,
        pattern        = pattern,
        material_feel  = material,
        key_features   = [c for c in colors[:2]] + [pattern],
        usp            = _usp_for(gender, style, material),
        target_customer= _target_for(gender, style),
        confidence     = confidence,
        analysis_method= method,
        raw_description= product_description,
    )
