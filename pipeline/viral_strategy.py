"""
pipeline/viral_strategy.py — Viral Content Strategy v6
=============================================================================
Tạo gói nội dung viral cho mọi loại sản phẩm thời trang.
Phủ sóng: Women × Men × Children × Baby × Unisex — 2026 format.
=============================================================================
"""
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ViralContent:
    hook_text: str
    hook_subtext: str
    value_stack: str
    comment_cta: str
    micro_story: str
    music_mood: str
    urgency_badge: str
    social_proof: str
    caption_tiktok: str
    caption_shopee: str
    hashtags_tiktok: str
    hashtags_shopee: str
    cta_tiktok: str
    cta_shopee: str


# ══════════════════════════════════════════════════════════════════════════════
#  HOOK LIBRARY
# ══════════════════════════════════════════════════════════════════════════════

_HOOKS = {
    "women_casual": [
        ("Tôi đã thử 15 bộ — đây là bộ duy nhất tôi giữ lại 😭", "Và đây là lý do"),
        ("Mặc cái này ra phố — được hỏi số 2 lần trong 1 tiếng 😂", "Không phải flex"),
        ("POV: Outfit chill nhưng ai cũng quay lại nhìn ✨", "Set này làm được"),
        ("Ai hỏi bạn mặc gì — hãy gửi video này 🔥", "Bí mật ở đây"),
    ],
    "women_formal": [
        ("Mặc cái này vào phòng họp — cả phòng IM lặng 💼", "Không phải vì kỹ năng"),
        ("Đồng nghiệp hỏi mua link 3 lần trong 1 ngày 😤", "Đây là set đó"),
        ("POV: Bạn bước vào văn phòng và sếp khen đầu tiên 👑", "Không phải vì báo cáo"),
        ("Set công sở giúp tôi nhận offer trong buổi phỏng vấn 🎯", "Outfit làm nên chuyện"),
    ],
    "women_streetwear": [
        ("Gen Z aesthetic 2026 — set này chuẩn vibe nhất 🔥", "Không cần giải thích"),
        ("Mặc cái này đến trường — được chụp ảnh không đếm được 📸", "Set này"),
        ("Streetwear nữ đang trending — đây là công thức 🌀", "Học ngay"),
        ("Hoodie này nhìn là biết có gu — giá rất đời 💯", "Xem ngay"),
    ],
    "women_sportswear": [
        ("Mặc set này vào gym — confidence level: max 💪", "Fabric magic"),
        ("Set tập vừa đẹp vừa không phải kéo chỉnh suốt buổi 🙌", "Bí quyết ở đây"),
        ("Gym-to-café 2026 — set này chuẩn nhất ☕", "Xem đây"),
        ("Vừa tập vừa được compliment — ai không thích? 😤", "Set này làm được"),
    ],
    "women_traditional": [
        ("Áo dài đẹp nhất tôi từng mặc — và tôi đã thử nhiều 🌸", "Đây là cái đó"),
        ("Mặc áo dài này ra ngoài — ai cũng dừng lại chụp hình 📸", "Thật sự"),
        ("Tự hào mặc áo dài Việt — đẹp không thua gì quốc tế 🇻🇳", "Xem ngay"),
        ("POV: Mặc áo dài này dự tiệc — không ai tin giá bao nhiêu 😍", "Xem đây"),
    ],
    "women_luxury": [
        ("Phụ kiện này nâng cả outfit từ 6 lên 10 điểm 💎", "Không thay đồ"),
        ("Luxury look không cần luxury budget — bằng chứng đây 🛍️", "Giá bất ngờ"),
        ("Cầm cái này ra phố — được hỏi mua link cả ngày ✨", "Link ở bio"),
        ("Không cần hàng hiệu để trông sang — xem đây 👑", "Bí mật ngay đây"),
    ],
    "women_swimwear": [
        ("Set biển hot nhất 2026 — ai mặc cũng được chụp hình 📸", "Còn hàng không?"),
        ("Đi biển năm này không lo chọn đồ nữa rồi 🏖️", "Đây rồi"),
        ("Bãi biển hè này: mặc set này — mọi ống kính hướng về 🌊", "Xem ngay"),
        ("Hội chị em order tập thể vì cái này 🔥", "Link bên dưới"),
    ],
    "men_formal": [
        ("Khoác bộ suit này — cả phòng họp im lặng khi bạn bước vào 🤫", "Power dressing"),
        ("CEO vibes không cần lương CEO 💼", "Giá bạn không đoán được"),
        ("Mặc suit này đi pitch — deal thành công không phải ngẫu nhiên 👊", "Xem đây"),
        ("Diện cái này đi phỏng vấn — nhận offer ngay hôm đó 🎯", "Bộ vest này"),
    ],
    "men_casual": [
        ("Áo này tôi mặc đi đâu cũng được compliment 💯", "Mà giá rẻ không tưởng"),
        ("Grab driver hỏi mua áo tôi đang mặc — thật không đùa 😂", "Link ở bio"),
        ("Set anh em đơn giản mà vẫn LOOK lắm 😎", "Công thức đây"),
        ("Casual nhưng nhìn là BIẾT có gu — ai cũng hỏi mua ở đâu 🔥", "Đây rồi"),
    ],
    "men_streetwear": [
        ("Streetwear nam 2026 đang đi hướng này — bạn biết chưa? 🛹", "Set đây"),
        ("Flex không cần giải thích — set này đủ nói thay 😤", "Drip check"),
        ("Hoodie này nhìn là biết có gu — giá lại rất đời 💯", "Xem ngay"),
        ("Gen Z anh em — set này chuẩn vibe nhất tháng này 🌀", "Link bio"),
    ],
    "men_sportswear": [
        ("Set gym anh em — mặc vào là muốn tập liền 💪", "Không cần motivation"),
        ("Gym-to-street 2026 — set nam này làm chuẩn nhất 🔥", "Xem đây"),
        ("Activewear nam đỉnh nhất tầm giá này — không bàn cãi 💯", "Order ngay"),
        ("Tập xong vẫn chill cafe được — không cần đổi đồ 🌿", "Set này"),
    ],
    "men_traditional": [
        ("Áo dài nam — phong thái quý ông Việt đúng nghĩa 🇻🇳", "Tự hào mặc"),
        ("Ba tôi xin link áo dài này — và ông không bao giờ xin link 😂", "Đẹp thật sự"),
        ("Mặc áo dài này đến sự kiện — không ai không ngoái nhìn 📸", "Xem đây"),
    ],
    "children_casual": [
        ("Bé mặc cái này — cưng đến mức ai cũng muốn bế 🥰", "Ba mẹ đừng bỏ lỡ"),
        ("Set bé cute nhất tháng — ba mẹ order ầm ầm 🔥", "Còn hàng không?"),
        ("Con mặc cái này đi chơi — được chụp hình liên tục 📸", "Ba mẹ đặt ngay"),
        ("Ba mẹ tìm đồ đẹp, an toàn, giá hợp lý? 🎯", "Đây rồi"),
    ],
    "children_formal": [
        ("Set bé đi sự kiện — cute như búp bê ra khỏi hộp 🎀", "Ba mẹ đặt ngay"),
        ("Bé mặc bộ này dự tiệc — ông bà bế không chịu thả 🥹", "Order ngay"),
        ("Set lễ phục cho bé đẹp nhất năm — thầy cô cũng khen 📚", "Còn kịp không?"),
    ],
    "children_traditional": [
        ("Bé mặc áo dài Tết — cute đến mức ông bà khóc vì yêu 🌸", "Ba mẹ đặt ngay"),
        ("Set áo dài bé đẹp nhất Tết — cả nhà phải chụp ảnh 📸", "Còn hàng nhé"),
        ("Áo dài bé xinh như trong tranh — Tết này phải có 🌺", "Ba mẹ xem ngay"),
    ],
    "baby_casual": [
        ("Bodysuit bé mềm như mây — ba mẹ sờ vào không muốn buông 🌙", "An toàn tuyệt đối"),
        ("Bé ngủ ngon hơn từ khi mặc set này — ba mẹ nói vậy 😇", "Chất liệu đặc biệt"),
        ("Ba mẹ tìm đồ cho bé sơ sinh an toàn, mềm mại? 👶", "Đây rồi"),
        ("Mua set này về mặc cho bé — cả nhà phát cuồng vì cute 🥹", "Link ở bio"),
    ],
    "unisex_casual": [
        ("Đồ đôi matching — cute nhưng không sến một chút nào 💕", "Cặp đôi xem ngay"),
        ("Set couple này viral vì quá cute mà không quá lố 🔥", "Mua cho người thương"),
        ("POV: Cặp đôi bạn mặc đồng phục ra phố 😍", "Ai cũng dừng lại nhìn"),
        ("Family matching 2026 — trend này gia đình nào cũng muốn 🌟", "Set này đây"),
    ],
}

_DEFAULT_HOOKS = [
    ("Tìm mãi 2 tuần mới thấy sản phẩm đỉnh thế này 🔍", "Xứng đáng lắm"),
    ("Viral vì lý do bạn chưa biết — xem đến cuối 🎯", "Đáng xem"),
    ("Chất lượng này, giá này — không thể tin 🤯", "Thật 100%"),
    ("Order đi, 7 ngày không ưng hoàn tiền — còn ngại gì? 💪", "Link bio"),
]

# ══════════════════════════════════════════════════════════════════════════════
#  VALUE STACKS
# ══════════════════════════════════════════════════════════════════════════════

_VALUE_STACKS = {
    "women":    "✅ Freeship + đổi trả 7 ngày\n✅ Chất lượng chuẩn hình 100%\n✅ Ship 2-3 ngày toàn quốc",
    "men":      "✅ Freeship + đổi size miễn phí\n✅ Hàng chuẩn hình, đúng màu\n✅ Ship nhanh 1-3 ngày",
    "baby":     "✅ Chất liệu mềm, an toàn da bé\n✅ Không chất độc hại, đã kiểm định\n✅ Đổi trả 7 ngày + freeship",
    "children": "✅ Chất liệu an toàn cho trẻ em\n✅ Bền màu, không phai sau giặt\n✅ Freeship + đổi size miễn phí",
    "unisex":   "✅ Freeship toàn quốc\n✅ Đổi trả 7 ngày không cần lý do\n✅ Đóng gói cẩn thận, giao nhanh",
}

_URGENCY_BADGES = [
    "🔥 HOT 2026", "⚡ FLASH SALE", "🔥 VIRAL NOW", "⏰ SẮP HẾT",
    "🏷️ GIÁ SỐC", "💥 BEST DEAL", "🔥 TOP SELLER", "⚡ LIMITED",
    "🌟 TRENDING", "🤖 AI PICKED",
]

_SEASONAL_BADGES = {
    1: "🧧 TẾT SALE", 2: "💕 V-DAY SALE", 3: "🌸 SPRING SALE",
    4: "🌷 MÙA XUÂN", 5: "☀️ HÈ VỀ RỒI", 6: "🏖️ BEACH SEASON",
    7: "🌊 MID SUMMER", 8: "🎒 BACK TO SCHOOL", 9: "🍂 THU VỀ",
    10: "🍁 FALL SALE", 11: "🧥 MÙA ĐÔNG", 12: "🎄 X-MAS SALE",
}

_SOCIAL_PROOF_POOL = [
    "4.7K+ ĐÃ ORDER", "SOLD OUT 6 LẦN", "8.2K YÊU THÍCH",
    "500+ REVIEW ⭐⭐⭐⭐⭐", "TOP 1 BÁN CHẠY", "3.5K HÀNG TUẦN",
    "VIRAL TIKTOK 2026", "2K+ REPEAT BUYER", "REVIEW 4.9/5 SAO",
    "#1 TRENDING NOW", "12K+ ĐÃ MUA", "SOLD OUT 2 LẦN TUẦN NÀY",
]

_COMMENT_CTAS = {
    "women":    ["Comment 'MUA' để nhận link ngay 👇", "Comment 'LINK' — mình gửi liền 📩",
                 "Comment 'MUỐN' để nhận ưu đãi thêm 💌"],
    "men":      ["Comment 'BRO LINK' để nhận ngay 👇", "Comment 'MUA' — mình gửi liền 💪",
                 "Comment 'SIZE' để được tư vấn miễn phí"],
    "children": ["Ba mẹ comment 'BÉ' để nhận link 👇", "Comment 'MUA CHO BÉ' — gửi ngay 🍼",
                 "Comment 'SIZE' để tư vấn kích thước phù hợp"],
    "baby":     ["Ba mẹ comment 'BÉ YÊU' để nhận link 👶", "Comment 'AN TOÀN' — gửi link ngay",
                 "Comment 'MUỐN' để nhận tư vấn miễn phí"],
    "unisex":   ["Comment 'MATCH' để nhận link 💕", "Comment 'ĐÔI' — mình gửi link liền",
                 "Comment 'GIA ĐÌNH' để nhận deal đặc biệt 👨‍👩‍👧‍👦"],
}

_MICRO_STORIES = {
    "women":    [
        "Hôm qua mặc set này đi café — barista hỏi mua link 😭",
        "Đặt về định trả lại — mặc thử rồi không trả được nữa 💀",
        "Mua cho bạn, mình giữ luôn một cái vì quá đẹp 😅",
    ],
    "men":      [
        "Bro cùng phòng hỏi mình mua ở đâu ngay ngày đầu mặc",
        "Sếp khen outfit hôm đó — không phải vì báo cáo đâu nhé 😂",
        "Mặc đi gym, xong ghé cafe luôn — không ai biết vừa tập xong",
    ],
    "children": [
        "Bé mặc đi chơi — cô giáo hỏi ba mẹ mua ở đâu 🥰",
        "Ông bà thấy bé mặc set này — khen cả buổi không ngừng",
        "Con nhất quyết không cởi ra dù về nhà rồi 😂",
    ],
    "baby":     [
        "Bé ngủ ngon hơn từ khi mặc bodysuit này — ba mẹ không tin thật 😌",
        "Da bé mềm, không bị hăm từ khi dùng chất liệu này",
        "Khách nhìn bé ở cafe cứ hỏi bé mặc gì cute vậy 🥹",
    ],
    "unisex":   [
        "Cả nhà mặc matching đi chơi — được chụp ảnh bởi người lạ 😂",
        "Bạn bè thấy ảnh cặp đôi — hỏi mua link ầm ầm",
        "Mặc set này đi Đà Lạt — ảnh nào cũng đẹp như ảnh studio",
    ],
}

_MUSIC_MOOD = {
    "women_formal":     "powerful_cinematic",
    "women_casual":     "trendy_pop",
    "women_streetwear": "phonk_street",
    "women_sportswear": "energetic_edm",
    "women_traditional":"vietnamese_modern",
    "women_luxury":     "luxury_elegant",
    "women_swimwear":   "summer_tropical",
    "men_formal":       "powerful_cinematic",
    "men_casual":       "casual_hype",
    "men_streetwear":   "phonk_street",
    "men_sportswear":   "energetic_edm",
    "men_traditional":  "vietnamese_modern",
    "children_casual":  "cute_pop",
    "children_formal":  "cute_pop",
    "children_traditional": "vietnamese_modern",
    "baby_casual":      "cozy_lullaby",
    "unisex_casual":    "trendy_pop",
}

_HASHTAGS_TIKTOK_BASE = "#fyp #foryoupage #viral #tiktokvietnam #thoitrang #ootd #tiktokshop #trending2026 #affiliate #thoitrangnuoctoan"
_HASHTAGS_GENDER = {
    "women":    "#thoitrangnu #fashionwomen #outfitoftheday #ootdvietnam",
    "men":      "#thoitrangnam #mensfashion #mensstyle #outfitmen",
    "children": "#thoitrangtrerem #kidsoutfit #kidsclothes #babyshop",
    "baby":     "#babyoutfit #babyclothes #sosinh #babyfashionvn",
    "unisex":   "#unisex #couplelook #familymatching #đôiđẹp",
}
_HASHTAGS_SHOPEE_BASE = "#ShopeeFashion #ShopeeVN #FreeShip #FlashSale #ShopeeLive #ShopeeAffiliate #MuaSắmOnline"

_CTA_TIKTOK = {
    "women":    ["💃 Link mua ở BIO 👆", "✨ Tap bio — sale hôm nay!", "🛒 Click bio — flash deal!"],
    "men":      ["👔 Link mua ở BIO 👆", "💪 Tap bio — flash deal!", "🛒 Bio ngay anh em!"],
    "children": ["🎀 Link cho bé ở BIO 👆", "🏫 Ba mẹ tap bio!", "👶 Bio có link đặt ngay!"],
    "baby":     ["👶 Link cho bé ở BIO 👆", "🍼 Ba mẹ tap bio nhé!", "💝 Bio — deal cho bé!"],
    "unisex":   ["💕 Link mua ở BIO 👆", "🔥 Tap bio — hết hàng đừng tiếc!", "💑 Bio — deal đôi!"],
}
_CTA_SHOPEE = {
    "women":    "🛒 Nhấn GIỎ HÀNG ngay — freeship!",
    "men":      "🛒 Đặt hàng ngay anh em — freeship!",
    "children": "🛒 Mua cho bé ngay — hàng an toàn!",
    "baby":     "🛒 Đặt cho bé ngay — freeship!",
    "unisex":   "🛒 Order ngay — đổi trả 7 ngày!",
}


def _hook_key(gender: str, style: str) -> str:
    key = f"{gender}_{style}"
    return key if key in _HOOKS else f"{gender}_casual"


def build_viral_content(
    name: str = "",
    price: str = "",
    garment: str = "",
    platform: str = "tiktok",
    gender_override: str = "",
) -> ViralContent:
    """Tạo gói nội dung viral đầy đủ cho mọi sản phẩm thời trang."""
    from pipeline.ai_analyzer import analyze_product
    analysis = analyze_product(name, garment, gender_hint=gender_override)
    gender = analysis.gender
    style  = analysis.style_category
    hkey   = _hook_key(gender, style)
    mkey   = f"{gender}_{style}"

    hook_text, hook_sub = random.choice(_HOOKS.get(hkey, _DEFAULT_HOOKS))
    value        = _VALUE_STACKS.get(gender, _VALUE_STACKS["unisex"])
    comment_cta  = random.choice(_COMMENT_CTAS.get(gender, ["Comment 'MUA' để nhận link 👇"]))
    micro_story  = random.choice(_MICRO_STORIES.get(gender, _MICRO_STORIES["women"]))
    music_mood   = _MUSIC_MOOD.get(mkey, "trendy_pop")

    month = datetime.now().month
    badge = _SEASONAL_BADGES.get(month, random.choice(_URGENCY_BADGES))
    proof = random.choice(_SOCIAL_PROOF_POOL)

    gender_tags = _HASHTAGS_GENDER.get(gender, "")
    hashtags_tt = f"{_HASHTAGS_TIKTOK_BASE} {gender_tags}".strip()
    hashtags_sp = _HASHTAGS_SHOPEE_BASE

    cta_tt = random.choice(_CTA_TIKTOK.get(gender, _CTA_TIKTOK["women"]))
    cta_sp = _CTA_SHOPEE.get(gender, _CTA_SHOPEE["women"])

    caption_tt = (
        f"✨ {name} — {hook_text[:50]}\n"
        f"💰 Giá chỉ {price} — {proof}\n\n"
        f"{value}\n\n"
        f"{comment_cta}\n"
        f"{cta_tt}\n\n"
        f"{hashtags_tt}"
    )
    caption_sp = (
        f"🛒 {name}\n"
        f"⭐ 4.9/5 sao — {proof}\n"
        f"💰 {price}\n\n"
        f"{value}\n\n"
        f"📦 Ship 2-4 ngày | Đổi trả 7 ngày\n"
        f"{cta_sp}\n\n"
        f"{hashtags_sp}"
    )

    return ViralContent(
        hook_text      = hook_text,
        hook_subtext   = hook_sub,
        value_stack    = value,
        comment_cta    = comment_cta,
        micro_story    = micro_story,
        music_mood     = music_mood,
        urgency_badge  = badge,
        social_proof   = proof,
        caption_tiktok = caption_tt,
        caption_shopee = caption_sp,
        hashtags_tiktok= hashtags_tt,
        hashtags_shopee= hashtags_sp,
        cta_tiktok     = cta_tt,
        cta_shopee     = cta_sp,
    )
