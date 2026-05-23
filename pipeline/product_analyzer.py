"""
pipeline/product_analyzer.py — Multi-Category Product Analyzer v7 (2026)
=============================================================================
Phân tích sản phẩm thuộc BẤT KỲ ngành hàng nào (không chỉ thời trang):

  NGÀNH HÀNG 2026 (theo thị phần affiliate Vietnam):
    1. fashion      — Thời trang (commission 7-12%)
    2. beauty       — Làm đẹp / Skincare (commission 10-15%)
    3. health       — Sức khỏe / Supplement (commission 12-20%)
    4. home         — Gia dụng / Nội thất (commission 8-12%)
    5. food         — Đồ ăn / Snack (commission 5-10%)
    6. tech         — Phụ kiện công nghệ (commission 5-8%)
    7. pet          — Thú cưng (commission 8-15%)
    8. sports       — Thể thao / Outdoor (commission 7-10%)
    9. baby         — Mẹ & Bé (commission 8-15%)
   10. fashion_kids — Thời trang trẻ em (commission 7-12%)

Tự động detect category từ tên/mô tả sản phẩm.
=============================================================================
"""
import logging
import random
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger("ProductAnalyzer")


@dataclass
class ProductAnalysis:
    """Kết quả phân tích sản phẩm toàn diện."""
    name: str
    category: str           # fashion | beauty | health | home | food | tech | pet | sports | baby
    subcategory: str        # Phân loại chi tiết hơn
    gender: str             # women | men | unisex | children | baby
    target_demo: str        # Mô tả đối tượng mục tiêu cụ thể
    price_tier: str         # budget | mid | premium | luxury
    key_benefit: str        # Lợi ích chính của sản phẩm
    pain_point: str         # Vấn đề sản phẩm giải quyết
    ai_prompt_style: str    # Style prompt cho AI video
    background_mood: str    # Môi trường quay phù hợp
    confidence: float       # 0.0 – 1.0


# ══════════════════════════════════════════════════════════════════════════════
#  KEYWORD DETECTION MAPS
# ══════════════════════════════════════════════════════════════════════════════

_CATEGORY_KW = {
    "beauty": [
        "serum", "kem", "cream", "toner", "essence", "dưỡng", "mặt nạ", "mask",
        "son", "lipstick", "lipgloss", "phấn", "foundation", "kem nền", "mascara",
        "nước tẩy trang", "tẩy tế bào", "retinol", "vitamin c", "niacinamide",
        "hyaluronic", "collagen da", "whitening", "trắng da", "mụn", "lỗ chân lông",
        "skincare", "dưỡng ẩm", "chống nắng", "spf", "sunscreen", "eye cream",
        "xịt khoáng", "essence", "ampoule", "sheet mask", "peel", "tẩy da chết",
        "dầu dừa", "makeup", "trang điểm", "phấn mắt", "eyeliner", "kẻ mắt",
    ],
    "health": [
        "vitamin", "collagen", "supplement", "thực phẩm chức năng", "uống",
        "bổ sung", "canxi", "omega", "probiotics", "men vi sinh", "enzyme",
        "giảm cân", "giảm mỡ", "detox", "trà thảo mộc", "thảo dược",
        "đông trùng", "nhân sâm", "spirulina", "whey protein", "protein",
        "creatine", "bcaa", "pre-workout", "post-workout", "recover",
        "melatonin", "ngủ ngon", "trí nhớ", "focus", "tập trung",
        "immunity", "miễn dịch", "kháng khuẩn", "kháng virus",
    ],
    "home": [
        "đèn", "nến thơm", "diffuser", "gối", "chăn", "ga", "thảm",
        "decor", "trang trí", "hộp đựng", "kệ", "giá", "móc", "dán",
        "bình hoa", "cắm hoa", "chậu", "cây cảnh", "đồ dùng bếp",
        "nồi", "chảo", "máy xay", "blender", "air fryer", "lò nướng",
        "bộ dao", "cutting board", "thớt", "hộp bảo quản", "túi zip",
        "máy hút bụi", "lau sàn", "dọn nhà", "tổ chức", "organize",
        "closet organizer", "drawer", "storage", "giỏ đựng",
    ],
    "food": [
        "snack", "đồ ăn vặt", "bánh", "kẹo", "chocolate", "socola",
        "chips", "popcorn", "crackers", "cookie", "mứt", "jam", "honey", "mật",
        "trà", "tea", "cà phê", "coffee", "ca cao", "cocoa", "matcha",
        "nước ép", "smoothie", "protein shake", "meal replacement",
        "mì", "phở", "bún", "instant", "ăn liền", "kimchi",
        "tương", "sốt", "sauce", "dressing", "gia vị", "spice",
        "dried fruit", "hạt", "nuts", "granola", "oat", "yến mạch",
    ],
    "tech": [
        "ốp lưng", "case", "dán màn", "kính cường lực", "tempered glass",
        "tai nghe", "earbuds", "earphone", "headphone", "bluetooth",
        "sạc", "charger", "cáp", "cable", "type-c", "lightning",
        "pin dự phòng", "powerbank", "power bank", "sạc nhanh",
        "hub", "usb", "adapter", "bàn phím", "keyboard", "chuột", "mouse",
        "webcam", "tripod", "giá đỡ", "ring light", "đèn studio",
        "smartwatch", "đồng hồ thông minh", "fitness tracker",
        "airpods", "tws", "noise cancelling",
    ],
    "pet": [
        "chó", "mèo", "dog", "cat", "pet", "thú cưng", "boss",
        "thức ăn chó", "thức ăn mèo", "cat food", "dog food",
        "đồ chơi chó", "đồ chơi mèo", "toy", "chuồng", "vòng cổ",
        "xích", "leash", "grooming", "tắm thú cưng", "lược",
        "cát vệ sinh", "sand", "litter", "snack thú cưng", "treat",
        "vitamin chó", "vitamin mèo", "supplement pet",
    ],
    "sports": [
        "yoga", "gym", "tập gym", "boxing", "chạy bộ", "running",
        "đạp xe", "cycling", "bơi lội", "swimming", "leo núi", "hiking",
        "tennis", "cầu lông", "badminton", "bóng đá", "bóng rổ",
        "resistance band", "dây kháng lực", "tạ", "kettlebell", "dumbbell",
        "thảm yoga", "yoga mat", "foam roller", "jump rope", "nhảy dây",
        "túi gym", "gym bag", "nước tập", "bình nước", "shaker",
    ],
    "baby": [
        "sơ sinh", "newborn", "baby", "em bé", "nhũ nhi", "0-12",
        "bình sữa", "bottle", "ti giả", "núm ti", "pacifier",
        "bỉm", "tã", "diaper", "khăn ướt", "baby wipes",
        "xe đẩy", "stroller", "nôi", "crib", "ghế ăn", "high chair",
        "đồ chơi sơ sinh", "đồ chơi em bé", "baby toy",
        "sữa bột", "formula", "ăn dặm", "baby food",
        "bodysuit", "onesie", "đồ ngủ bé", "romper",
    ],
    "fashion_kids": [
        "trẻ em", "kids", "bé", "child", "học sinh", "đồng phục",
        "set bé", "quần bé", "áo bé", "váy bé",
        "3 tuổi", "4 tuổi", "5 tuổi", "6 tuổi", "7 tuổi",
        "8 tuổi", "9 tuổi", "10 tuổi", "11 tuổi", "12 tuổi",
        "3-8", "4-12", "3-12", "kids fashion", "trang phục trẻ em",
    ],
}

# Fashion là default — chỉ detect nếu không match category nào khác
_FASHION_KW = [
    "áo", "quần", "váy", "đầm", "đồ", "set", "vest", "blazer", "hoodie",
    "jacket", "coat", "shirt", "tshirt", "jeans", "legging", "dress",
    "skirt", "suit", "casual", "formal", "streetwear", "outfit",
    "thời trang", "fashion", "ootd", "mặc", "style",
]

_GENDER_KW = {
    "men":  ["nam", "men", "anh", "chú", "bố", "ông", "trai", "boy", "he", "him"],
    "children": ["bé", "trẻ em", "kids", "child", "con", "học sinh"],
    "baby": ["sơ sinh", "baby", "nhũ nhi", "tã", "bỉm", "0-12", "newborn"],
    "unisex": ["đôi", "couple", "gia đình", "family", "unisex", "matching"],
}

_PRICE_TIERS = {
    "budget":  (0, 100),
    "mid":     (100, 500),
    "premium": (500, 2000),
    "luxury":  (2000, 999999),
}

_TARGET_DEMOS = {
    ("fashion", "women"):  "Phụ nữ Việt 18–35, yêu thời trang, xem TikTok ≥3h/ngày",
    ("fashion", "men"):    "Nam giới Việt 20–35, quan tâm style, mua sắm online",
    ("beauty", "women"):   "Phụ nữ Việt 18–40, đam mê skincare, xem review beauty",
    ("health", "women"):   "Phụ nữ Việt 25–45, quan tâm sức khỏe, lối sống lành mạnh",
    ("health", "men"):     "Nam giới Việt 22–40, tập gym, chú trọng sức khỏe",
    ("home", "women"):     "Phụ nữ Việt 22–40, yêu nhà đẹp, hay mua đồ decor online",
    ("food", "unisex"):    "Người Việt 16–35, thích ăn vặt, hay mua Shopee Food",
    ("tech", "men"):       "Nam giới Việt 18–35, dân công nghệ, hay theo dõi tech review",
    ("pet", "unisex"):     "Pet owner Việt 20–40, yêu thú cưng, chi nhiều cho boss",
    ("baby", "women"):     "Mẹ trẻ Việt 22–38, tìm sản phẩm an toàn cho bé",
    ("fashion_kids", "unisex"): "Ba mẹ Việt 25–40, tìm đồ đẹp an toàn cho con",
    ("sports", "unisex"):  "Người Việt 20–40, lối sống active, hay tập gym/yoga/chạy bộ",
}

_KEY_BENEFITS = {
    "fashion":      "Tự tin, phong cách, được compliment",
    "beauty":       "Da đẹp, tự tin không cần filter",
    "health":       "Sức khỏe tốt, năng lượng dồi dào",
    "home":         "Nhà đẹp, ngăn nắp, không gian sống tốt hơn",
    "food":         "Ăn ngon, tiện lợi, thỏa mãn",
    "tech":         "Năng suất cao hơn, cuộc sống tiện hơn",
    "pet":          "Boss khỏe, vui, hạnh phúc",
    "sports":       "Tập hiệu quả hơn, cơ thể đẹp hơn",
    "baby":         "Bé an toàn, thoải mái, phát triển tốt",
    "fashion_kids": "Con đẹp, thoải mái, ba mẹ tự hào",
}

_PAIN_POINTS = {
    "fashion":      "Không biết mặc gì, tủ đầy mà không có gì mặc",
    "beauty":       "Da mụn, thâm, không đều màu, tốn tiền mãi không hết",
    "health":       "Mệt mỏi, thiếu năng lượng, không kiểm soát được cân nặng",
    "home":         "Nhà bừa bộn, tốn thời gian dọn, không gian chật chội",
    "food":         "Đói giữa buổi, đồ ăn vặt không ngon hoặc không lành mạnh",
    "tech":         "Thiết bị hay hỏng, năng suất thấp, setup không chuyên nghiệp",
    "pet":          "Boss ít vận động, biếng ăn, lông xỉn, khó chăm sóc",
    "sports":       "Tập không hiệu quả, thiếu dụng cụ, không có motivation",
    "baby":         "Lo lắng an toàn cho bé, không biết chọn đồ phù hợp",
    "fashion_kids": "Khó tìm đồ đẹp, an toàn, giá hợp lý cho con",
}

_AI_STYLES = {
    "fashion":      "high-fashion lifestyle photography, editorial quality",
    "beauty":       "clean beauty aesthetic, soft lighting, before-after reveal",
    "health":       "wellness lifestyle, active healthy person, clean minimal",
    "home":         "interior photography, cozy home, warm ambient lighting",
    "food":         "food photography, vibrant colors, delicious close-up",
    "tech":         "tech product photography, sleek minimal, studio lighting",
    "pet":          "cute pet photography, warm natural light, joyful energy",
    "sports":       "dynamic athletic photography, motion blur, energy",
    "baby":         "soft pastel nursery, gentle natural light, innocent cute",
    "fashion_kids": "colorful playful photography, natural light, joyful child",
}

_BG_MOODS = {
    "fashion":      "Saigon street golden hour / Premium mall interior",
    "beauty":       "Minimalist white vanity / Natural window light bathroom",
    "health":       "Modern gym / Bright kitchen with healthy food",
    "home":         "Cozy living room / Modern kitchen interior",
    "food":         "Aesthetic café / Cozy home dining area",
    "tech":         "Clean desk setup / Modern home office",
    "pet":          "Cozy living room / Sunny garden with pets",
    "sports":       "Modern gym / Outdoor park morning",
    "baby":         "Soft pastel nursery / Cozy bedroom",
    "fashion_kids": "Colorful playground / Bright indoor play area",
}


def _detect_category(text: str) -> str:
    t = text.lower()
    scores = {}
    for cat, kws in _CATEGORY_KW.items():
        scores[cat] = sum(1 for kw in kws if kw in t)
    best = max(scores, key=scores.get)
    if scores[best] > 0:
        return best
    # Fashion check
    fashion_score = sum(1 for kw in _FASHION_KW if kw in t)
    return "fashion" if fashion_score > 0 else "fashion"


def _detect_gender(text: str, category: str) -> str:
    t = text.lower()
    if category in ("baby",):
        return "baby"
    if category == "fashion_kids":
        return "children"
    if category in ("home", "food", "pet", "sports"):
        for g, kws in _GENDER_KW.items():
            if any(k in t for k in kws):
                return g
        return "unisex"
    for g, kws in _GENDER_KW.items():
        if any(k in t for k in kws):
            return g
    if category == "beauty":
        return "women"
    if category == "tech":
        return "men"
    return "women"


def _detect_price_tier(price_str: str) -> str:
    import re
    nums = re.findall(r"\d+", price_str.replace(".", "").replace(",", ""))
    if not nums:
        return "mid"
    val = int(nums[0])
    if val > 100 and val < 10000:   # Giá đơn vị nghìn đồng (99k = 99)
        val *= 1000
    for tier, (lo, hi) in _PRICE_TIERS.items():
        if lo * 1000 <= val < hi * 1000:
            return tier
    return "mid"


def analyze_product(
    product_name: str,
    description: str = "",
    price: str = "",
    image_path: str = None,
    category_hint: str = "",
    gender_hint: str = "",
) -> ProductAnalysis:
    """
    Phân tích sản phẩm toàn diện.
    Tự động detect category, gender, price_tier từ tên + mô tả.
    """
    combined = f"{product_name} {description}".lower()

    category = category_hint if category_hint else _detect_category(combined)
    gender   = gender_hint if gender_hint else _detect_gender(combined, category)
    price_tier = _detect_price_tier(price) if price else "mid"

    # Subcategory
    subcategory = f"{gender}_{category}"

    # Target demo
    demo_key = (category, gender)
    target_demo = _TARGET_DEMOS.get(demo_key, f"Người dùng Việt quan tâm {category}")

    # CLIP analysis (nếu có ảnh và GPU)
    confidence = 0.88
    if image_path:
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
                "fashion clothing", "skincare beauty product", "health supplement",
                "home decor", "food snack", "tech accessory", "pet product",
                "sports equipment", "baby product",
            ]
            texts = tokenizer(candidates).to(device)
            import torch.nn.functional as F
            with torch.no_grad():
                if = model.encode_image(img)
                tf = model.encode_text(texts)
                if_ = if / if.norm(dim=-1, keepdim=True)
                tf_ = tf / tf.norm(dim=-1, keepdim=True)
                sims = (if_ @ tf_.T).squeeze(0)
            top_idx = sims.argmax().item()
            confidence = float(sims[top_idx])
            logger.info(f"CLIP: {candidates[top_idx]} ({confidence:.0%})")
        except Exception as e:
            logger.debug(f"CLIP skipped: {e}")

    return ProductAnalysis(
        name           = product_name,
        category       = category,
        subcategory    = subcategory,
        gender         = gender,
        target_demo    = target_demo,
        price_tier     = price_tier,
        key_benefit    = _KEY_BENEFITS.get(category, "Chất lượng tốt, giá hợp lý"),
        pain_point     = _PAIN_POINTS.get(category, "Tìm hoài mà không có sản phẩm ưng ý"),
        ai_prompt_style= _AI_STYLES.get(category, _AI_STYLES["fashion"]),
        background_mood= _BG_MOODS.get(category, _BG_MOODS["fashion"]),
        confidence     = confidence,
    )
