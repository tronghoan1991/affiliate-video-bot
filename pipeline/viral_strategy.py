"""
pipeline/viral_strategy.py — Viral Content Strategy Engine v5 (2026)
=============================================================================
Phủ sóng TOÀN BỘ ngành thời trang:
  ✅ Women: 20+ loại sản phẩm
  ✅ Men: 15+ loại sản phẩm
  ✅ Children: 12+ loại sản phẩm (baby, toddler, kids, teen)
  ✅ Unisex: couple set, family matching, gender-free
  ✅ 2026 trends: authentic hook, value stack, comment CTA, micro-story

Bot KHÔNG còn giới hạn chỉ nữ giới — toàn ngành thời trang.
=============================================================================
"""
import random
import datetime
from dataclasses import dataclass
from typing import Optional


@dataclass
class ViralContent:
    hook_text: str
    hook_subtext: str
    urgency_badge: str
    social_proof: str
    value_stack: str
    micro_story: str
    caption_tiktok: str
    caption_shopee: str
    hashtags_tiktok: list
    hashtags_shopee: list
    cta_tiktok: str
    cta_shopee: str
    music_mood: str
    comment_cta: str


# ══════════════════════════════════════════════════════════════════════════════
#  HOOKS — Women × Men × Children × Baby × Unisex
# ══════════════════════════════════════════════════════════════════════════════

_HOOKS = {
    # ─── WOMEN ────────────────────────────────────────────────────────────────
    "women_dress_evening":   [
        ("Tôi đã thử 12 cái váy — đây là cái duy nhất tôi giữ lại 😭", "Lý do ở video"),
        ("Sold out 6 lần vì ai mặc cũng không muốn cởi ra 🔥", "Lần này còn hàng"),
        ("POV: Mặc cái này đến tiệc và không ai rời mắt 👀", "Giá bạn không đoán được"),
        ("Bạn trai nhìn váy này và không nói được gì 😳", "Bí mật ngay đây"),
    ],
    "women_casual":          [
        ("Outfit chill nhất mùa này mà ai cũng hỏi mua ở đâu 🔥", "Bí mật đây"),
        ("Mặc cái này ra phố — được hỏi số 2 lần trong 1 tiếng 😂", "Không phải flex"),
        ("Tủ đồ của tôi có 30 cái — mà mặc cái này mỗi ngày 🤦", "Đây là lý do"),
        ("Set chill nhưng nhìn là BIẾT có gu 😎", "Giá rẻ không tưởng"),
    ],
    "women_formal":          [
        ("Mặc cái này vào phòng họp — cả phòng IM LẶNG 💼", "Không phải vì kỹ năng"),
        ("Đồng nghiệp hỏi mua link 3 lần trong 1 ngày 😤", "Đây là set đó"),
        ("POV: Bạn bước vào văn phòng và sếp khen đầu tiên 👑", "Set này làm được"),
        ("Set công sở giúp tôi nhận offer ngay buổi phỏng vấn 🎯", "Outfit làm nên chuyện"),
    ],
    "women_traditional":     [
        ("Áo dài đẹp nhất tôi từng mặc — và tôi đã thử nhiều 🌸", "Đây là cái đó"),
        ("Mặc áo dài này ra ngoài — ai cũng dừng lại chụp hình 📸", "Thật sự"),
        ("Tự hào mặc áo dài Việt — đẹp không thua gì quốc tế 🇻🇳", "Xem ngay"),
        ("3 thế hệ trong gia đình đều khen cái áo này 🌺", "Hãnh diện mặc"),
    ],
    "women_sportswear":      [
        ("Set gym này mặc vào muốn tập liền — không cần motivation 💪", "Bằng chứng đây"),
        ("Gym-to-café 2026 — trend này, set này chuẩn nhất ☕", "Xem đây"),
        ("Mặc set này đến gym — confident level khác hẳn bình thường 🏋️", "Thật luôn"),
        ("Vừa tập vừa được compliment — ai không thích? 😤", "Set này làm được"),
    ],
    "women_luxury":          [
        ("Phụ kiện này nâng cả outfit từ 6 lên 10 điểm 💎", "Không thay đồ"),
        ("Luxury look không cần luxury budget — bằng chứng đây 🛍️", "Giá bất ngờ"),
        ("Cầm cái này ra phố — được hỏi mua link cả ngày ✨", "Link ở bio"),
        ("Không cần hàng hiệu để trông sang — xem đây 👑", "Bí mật ngay đây"),
    ],
    "women_swimwear":        [
        ("Set biển hot nhất 2026 — ai mặc cũng được chụp hình 📸", "Còn hàng không?"),
        ("Đi biển năm này không lo chọn đồ nữa rồi 🏖️", "Đây rồi"),
        ("Bãi Phu Quoc hè này: ai mặc set này — mọi ống kính hướng về 🌊", "Xem ngay"),
        ("Hội chị em group chat order tập thể vì cái này 🔥", "Link bên dưới"),
    ],
    "women_streetwear":      [
        ("Gen Z aesthetic 2026 — set nữ này chuẩn vibe nhất 🔥", "Không cần giải thích"),
        ("Mặc cái này đến trường — được chụp ảnh cả buổi 📸", "Set này"),
        ("Streetwear nữ đang trending — và đây là công thức 🌀", "Học ngay"),
        ("Hoodie + quần này = outfit chill mà vẫn SLAY 😎", "Giá mà đời"),
    ],

    # ─── MEN ──────────────────────────────────────────────────────────────────
    "men_formal":            [
        ("Khoác bộ suit này — cả phòng họp im lặng khi bạn bước vào 🤫", "Power dressing"),
        ("CEO vibes không cần lương CEO 💼", "Giá bạn không đoán được"),
        ("Mặc suit này đi pitch — deal thành công không phải ngẫu nhiên 👊", "Xem đây"),
        ("Diện cái này đi phỏng vấn — nhận offer ngay hôm đó 🎯", "Bộ vest này"),
    ],
    "men_casual":            [
        ("Áo này tôi mặc đi đâu cũng được compliment 💯", "Mà giá rẻ không tưởng"),
        ("Grab driver hỏi mua áo tôi đang mặc — thật không đùa 😂", "Link ở bio"),
        ("Set anh em đơn giản mà vẫn LOOK lắm 😎", "Công thức đây"),
        ("Casual nhưng nhìn là BIẾT có gu — ai cũng hỏi mua ở đâu 🔥", "Đây rồi"),
    ],
    "men_streetwear":        [
        ("Streetwear nam 2026 đang đi hướng này — bạn biết chưa? 🛹", "Set đây"),
        ("Flex không cần giải thích — set này đủ nói thay 😤", "Drip check"),
        ("Hoodie này nhìn là biết có gu — giá lại rất đời 💯", "Xem ngay"),
        ("Gen Z anh em — set này chuẩn vibe nhất tháng này 🌀", "Link bio"),
    ],
    "men_sportswear":        [
        ("Set gym anh em — mặc vào là muốn tập liền 💪", "Không cần motivation"),
        ("Gym-to-street 2026 — set nam này làm chuẩn nhất 🔥", "Xem đây"),
        ("Activewear nam đỉnh nhất tầm giá này — không bàn cãi 💯", "Order ngay"),
        ("Tập xong vẫn chill cafe được — không cần đổi đồ 🌿", "Set này"),
    ],
    "men_traditional":       [
        ("Áo dài nam — phong thái quý ông Việt đúng nghĩa 🇻🇳", "Tự hào mặc"),
        ("Ba tôi xin link áo dài này — và ông không bao giờ xin link 😂", "Đẹp thật sự"),
        ("Mặc áo dài nam này đến sự kiện — không ai không ngoái nhìn 📸", "Xem đây"),
    ],
    "men_smartcasual":       [
        ("Smart casual anh em — công thức không bao giờ sai 🎯", "Màu này mới nhất"),
        ("Đi làm hay đi chơi đều ổn — set đa năng nhất 2026 💯", "Link ở bio"),
        ("Chinos + áo sơ mi = mặc đi đâu cũng ổn 😎", "Set này đây"),
    ],

    # ─── CHILDREN ─────────────────────────────────────────────────────────────
    "kids_casual":           [
        ("Bé mặc cái này — cưng đến mức ai cũng muốn bế 🥰", "Ba mẹ đừng bỏ lỡ"),
        ("Set bé cute nhất tháng này — ba mẹ order ầm ầm 🔥", "Còn hàng không?"),
        ("Con mặc cái này đi chơi — được chụp hình liên tục 📸", "Ba mẹ đặt ngay"),
        ("Ba mẹ tìm đồ cho bé đẹp, an toàn, giá hợp lý? 🎯", "Đây rồi"),
    ],
    "kids_formal":           [
        ("Set bé đi sự kiện — cute như búp bê ra khỏi hộp 🎀", "Ba mẹ đặt ngay"),
        ("Đồng phục bé đẹp nhất năm học này — thầy cô cũng khen 📚", "Còn kịp không?"),
        ("Bé mặc bộ này dự tiệc — ông bà bế không chịu thả 🥹", "Order ngay"),
    ],
    "kids_traditional":      [
        ("Bé mặc áo dài Tết — cute đến mức ông bà khóc vì yêu 🌸", "Ba mẹ đặt ngay"),
        ("Set áo dài bé đẹp nhất Tết này — cả nhà phải chụp ảnh 📸", "Còn hàng nhé"),
        ("Áo dài bé xinh như trong tranh — Tết này phải có 🌺", "Ba mẹ xem ngay"),
    ],
    "kids_sportswear":       [
        ("Set đồ tập cho bé — năng động, thoải mái, dễ vận động 🏃", "Ba mẹ xem ngay"),
        ("Bé yêu thể thao cần set này — chất liệu an toàn 100% 💪", "Link ở bio"),
    ],

    # ─── BABY ─────────────────────────────────────────────────────────────────
    "baby_onesie":           [
        ("Bodysuit bé mềm như mây — ba mẹ sờ vào không muốn buông 🌙", "An toàn tuyệt đối"),
        ("Bé ngủ ngon hơn từ khi mặc set này — ba mẹ nói vậy 😇", "Chất liệu đặc biệt"),
        ("Ba mẹ tìm đồ cho bé sơ sinh an toàn, mềm mại? 👶", "Đây rồi"),
        ("Mua set này về mặc cho bé — cả nhà phát cuồng vì cute 🥹", "Link ở bio"),
    ],
    "baby_set":              [
        ("Set bé sơ sinh đầy đủ nhất tôi tìm được 👶", "Ba mẹ xem ngay"),
        ("Gift set cho bé mới sinh — ba mẹ bỉm sữa đang tìm phải không? 🍼", "Đây rồi"),
        ("Chất liệu bamboo mềm nhẹ — an toàn tuyệt đối cho da bé 🌿", "Ba mẹ xem đây"),
    ],

    # ─── UNISEX ───────────────────────────────────────────────────────────────
    "unisex_couple":         [
        ("Đồ đôi matching — cute nhưng không sến một chút nào 💕", "Cặp đôi xem ngay"),
        ("Set couple này viral vì quá cute mà không quá lố 🔥", "Mua cho anh/chị/bạn"),
        ("POV: Cặp đôi bạn mặc đồng phục ra phố 😍", "Ai cũng dừng lại nhìn"),
    ],
    "unisex_family":         [
        ("Set gia đình matching — khoảnh khắc này không thể thiếu 📸", "Ba mẹ đặt ngay"),
        ("Family matching 2026 — trend này gia đình nào cũng muốn làm 🌟", "Set này đây"),
        ("Cả nhà mặc giống nhau đi chơi — ai cũng quay lại nhìn 🥰", "Đặt ngay"),
    ],
    "unisex_genz":           [
        ("Gender-free fashion 2026 — set này dẫn đầu trend 🌀", "Không giới hạn phong cách"),
        ("Hoodie ai mặc cũng flex được — không kể giới tính 😤", "Đây rồi"),
        ("Unisex drip 2026 — freedom of style là đây 🔥", "Link bio"),
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
    "baby":     "✅ Chất liệu mềm an toàn da bé\n✅ Không chất độc hại, kiểm định\n✅ Đổi trả 7 ngày + freeship",
    "children": "✅ Chất liệu an toàn cho trẻ em\n✅ Bền màu, không phai sau giặt\n✅ Freeship + đổi size miễn phí",
    "unisex":   "✅ Freeship toàn quốc\n✅ Đổi trả 7 ngày không cần lý do\n✅ Đóng gói cẩn thận, giao nhanh",
}


# ══════════════════════════════════════════════════════════════════════════════
#  URGENCY BADGES & SOCIAL PROOF
# ══════════════════════════════════════════════════════════════════════════════

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
    "#1 TRENDING NOW",
]
_COMMENT_CTAS = {
    "women":    ["Comment 'MUA' để nhận link ngay 👇", "Comment 'LINK' — mình gửi liền 📩"],
    "men":      ["Comment 'BRO LINK' để nhận ngay 👇", "Comment 'MUA' — mình gửi liền 💪"],
    "children": ["Ba mẹ comment 'BÉ' để nhận link 👇", "Comment 'MUA CHO BÉ' — gửi ngay 🍼"],
    "baby":     ["Ba mẹ comment 'BÉ YÊU' để nhận link 👶", "Comment 'AN TOÀN' — gửi link ngay"],
    "unisex":   ["Comment 'MATCH' để nhận link 💕", "Comment 'ĐÔI' — mình gửi link liền"],
}

# ══════════════════════════════════════════════════════════════════════════════
#  CAPTIONS
# ══════════════════════════════════════════════════════════════════════════════

_CAPTIONS_TIKTOK = {
    "women": (
        "✨ {name} — outfit này tôi mặc đi đâu cũng được khen 🔥\n"
        "Giá chỉ {price} mà nhìn premium vậy đó!\n\n{value}\n\n{comment_cta} hoặc link ở bio 👆\n{tags}"
    ),
    "men": (
        "💪 {name} — anh em hỏi mua link liên tục 😎\n"
        "Giá: {price} — nhìn như đồ cao cấp!\n\n{value}\n\n{comment_cta}\n{tags}"
    ),
    "children": (
        "🥰 {name} — set cho bé cute không chịu được!\n"
        "Ba mẹ ơi, giá chỉ {price} mà bé mặc đẹp thế này!\n\n{value}\n\n{comment_cta}\n{tags}"
    ),
    "baby": (
        "👶 {name} — chất liệu an toàn tuyệt đối cho bé yêu!\n"
        "Giá: {price} — ba mẹ yên tâm 100%\n\n{value}\n\n{comment_cta}\n{tags}"
    ),
    "unisex": (
        "💕 {name} — ai mặc cũng đẹp, không kể giới tính!\n"
        "Giá: {price}\n\n{value}\n\n{comment_cta}\n{tags}"
    ),
}

_CAPTIONS_SHOPEE = (
    "🛒 {name}\n⭐ 4.9/5 sao\n💰 {price}\n\n{value}\n\n"
    "📦 Ship 2-4 ngày | Đổi trả 7 ngày\n{tags}"
)

# ══════════════════════════════════════════════════════════════════════════════
#  HASHTAGS
# ══════════════════════════════════════════════════════════════════════════════

_BASE_TIKTOK = "#fyp #foryoupage #viral #tiktokvietnam #thoitrang #ootd #tiktokshop #trending2026 #affiliate"
_GENDER_HASHTAGS = {
    "women":    "#thoitrangnu #fashionwomen #outfitoftheday",
    "men":      "#thoitrangnam #mensfashion #mensstyle",
    "children": "#thoitrangtrerem #kidsoutfit #kidsclothes",
    "baby":     "#babyoutfit #babyclothes #sơsinh #babyfashion",
    "unisex":   "#unisex #couplelook #familymatching",
}
_BASE_SHOPEE = "#ShopeeFashion #ShopeeVN #FreeShip #FlashSale #ShopeeLive #ShopeeAffiliate"

# ══════════════════════════════════════════════════════════════════════════════
#  MUSIC MOOD
# ══════════════════════════════════════════════════════════════════════════════

_MUSIC_MOOD = {
    "women_formal":      "powerful_cinematic",
    "women_casual":      "trendy_pop",
    "women_streetwear":  "phonk_street",
    "women_sportswear":  "energetic_edm",
    "women_traditional": "vietnamese_modern",
    "women_luxury":      "luxury_elegant",
    "women_swimwear":    "summer_tropical",
    "men_formal":        "powerful_cinematic",
    "men_casual":        "casual_hype",
    "men_streetwear":    "phonk_street",
    "men_sportswear":    "energetic_edm",
    "men_traditional":   "vietnamese_modern",
    "men_smartcasual":   "corporate_smooth",
    "kids_casual":       "feminine_pop",
    "kids_traditional":  "vietnamese_modern",
    "baby_onesie":       "cozy_aesthetic",
    "baby_set":          "cozy_aesthetic",
    "unisex_couple":     "trendy_pop",
    "unisex_family":     "trendy_pop",
    "unisex_genz":       "phonk_street",
}

# ══════════════════════════════════════════════════════════════════════════════
#  CTA
# ══════════════════════════════════════════════════════════════════════════════

_CTA_TIKTOK = {
    "women":    ["💃 Link mua ở BIO 👆", "✨ Tap bio — sale hôm nay!"],
    "men":      ["👔 Link mua ở BIO 👆", "💪 Tap bio — flash deal!"],
    "children": ["🎀 Link mua cho bé ở BIO 👆", "🏫 Ba mẹ tap bio!"],
    "baby":     ["👶 Link mua cho bé ở BIO 👆", "🍼 Ba mẹ tap bio nhé!"],
    "unisex":   ["💕 Link mua ở BIO 👆", "🔥 Tap bio — hết hàng đừng tiếc!"],
}
_CTA_SHOPEE = {
    "women":    "🛒 Nhấn GIỎ HÀNG ngay — freeship!",
    "men":      "🛒 Đặt hàng ngay anh em — freeship!",
    "children": "🛒 Mua cho bé ngay — hàng an toàn!",
    "baby":     "🛒 Đặt cho bé ngay — freeship!",
    "unisex":   "🛒 Order ngay — đổi trả 7 ngày!",
}


# ══════════════════════════════════════════════════════════════════════════════
#  HELPER: Detect gender từ garment string
# ══════════════════════════════════════════════════════════════════════════════

def _detect_gender(garment: str) -> str:
    g = garment.lower()
    if any(w in g for w in ["nam", "men", "boy", "anh", "chú", "bố"]):
        return "men"
    if any(w in g for w in ["bé", "baby", "trẻ em", "kids", "nhi", "con"]):
        if any(w in g for w in ["sơ sinh", "baby", "0-", "1-", "2-"]):
            return "baby"
        return "children"
    if any(w in g for w in ["đôi", "couple", "gia đình", "family", "unisex"]):
        return "unisex"
    return "women"  # default


def _detect_style(garment: str) -> str:
    g = garment.lower()
    if any(w in g for w in ["vest", "suit", "blazer", "công sở", "formal", "sơ mi"]):
        return "formal"
    if any(w in g for w in ["áo dài", "ao dai", "truyền thống"]):
        return "traditional"
    if any(w in g for w in ["gym", "tập", "sport", "active", "yoga", "legging"]):
        return "sportswear"
    if any(w in g for w in ["hoodie", "street", "drip", "phonk", "skate", "urban"]):
        return "streetwear"
    if any(w in g for w in ["túi", "bag", "trang sức", "jewelry", "phụ kiện", "đồng hồ"]):
        return "luxury"
    if any(w in g for w in ["bikini", "bơi", "swim", "beach"]):
        return "swimwear"
    return "casual"


def _hook_key(gender: str, style: str) -> str:
    mapping = {
        ("women", "casual"):      "women_casual",
        ("women", "formal"):      "women_formal",
        ("women", "streetwear"):  "women_streetwear",
        ("women", "sportswear"):  "women_sportswear",
        ("women", "traditional"): "women_traditional",
        ("women", "luxury"):      "women_luxury",
        ("women", "swimwear"):    "women_swimwear",
        ("men", "formal"):        "men_formal",
        ("men", "casual"):        "men_casual",
        ("men", "streetwear"):    "men_streetwear",
        ("men", "sportswear"):    "men_sportswear",
        ("men", "traditional"):   "men_traditional",
        ("men", "smart"):         "men_smartcasual",
        ("children", "casual"):   "kids_casual",
        ("children", "formal"):   "kids_formal",
        ("children", "traditional"):"kids_traditional",
        ("children", "sportswear"):"kids_sportswear",
        ("baby", "casual"):       "baby_onesie",
        ("unisex", "casual"):     "unisex_couple",
        ("unisex", "streetwear"): "unisex_genz",
    }
    return mapping.get((gender, style), "women_casual")


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def build_viral_content(
    name: str = "",
    price: str = "",
    garment: str = "",
    platform: str = "tiktok",
    gender_override: str = "",
) -> ViralContent:
    """
    Tạo gói nội dung viral cho BẤT KỲ sản phẩm thời trang nào.
    Tự động nhận diện: nam/nữ/trẻ em/unisex + phong cách + dịp dùng.
    """
    gender = gender_override or _detect_gender(garment)
    style = _detect_style(garment)
    hkey = _hook_key(gender, style)
    mkey = f"{gender}_{style}"

    # Hook
    hook_pool = _HOOKS.get(hkey, _DEFAULT_HOOKS)
    hook_text, hook_subtext = random.choice(hook_pool)

    # Value & CTA
    value = _VALUE_STACKS.get(gender, _VALUE_STACKS["unisex"])
    comment_cta = random.choice(_COMMENT_CTAS.get(gender, ["Comment 'MUA' để nhận link 👇"]))

    # Music
    music_mood = _MUSIC_MOOD.get(mkey, "trendy_pop")

    # Hashtags
    htags_tiktok = (_BASE_TIKTOK + " " + _GENDER_HASHTAGS.get(gender, "")).split()
    htags_shopee = _BASE_SHOPEE.split()

    # Caption
    cap_tpl = _CAPTIONS_TIKTOK.get(gender, _CAPTIONS_TIKTOK["women"])
    tags_str = " ".join(htags_tiktok[:12])
    caption_tiktok = cap_tpl.format(name=name, price=price, value=value, comment_cta=comment_cta, tags=tags_str)
    caption_shopee = _CAPTIONS_SHOPEE.format(name=name, price=price, value=value, tags=" ".join(htags_shopee[:8]))

    # CTA
    cta_tiktok = random.choice(_CTA_TIKTOK.get(gender, _CTA_TIKTOK["women"]))
    cta_shopee = _CTA_SHOPEE.get(gender, _CTA_SHOPEE["women"])

    # Badge
    month = datetime.datetime.now().month
    urgency_badge = _SEASONAL_BADGES.get(month) if random.random() < 0.3 else random.choice(_URGENCY_BADGES)

    # Micro story
    stories = {
        "women": f"Trước: Không biết mặc gì 😩\nSau khi order {name}: Được khen cả ngày 💃\nKết quả: Order thêm 2 màu 🛒",
        "men":   f"Trước: Set đồ bình thường, không nổi bật\nSau khi mặc {name}: Anh em hỏi mua link liên tục 💪\nKết quả: Tự tin +100% 🔥",
        "children": f"Trước: Loay hoay tìm đồ cho bé an toàn mà đẹp\nSau khi mua {name}: Bé mặc vào ai cũng khen 🥰\nKết quả: Ba mẹ order thêm!",
        "baby":  f"Trước: Tìm mãi đồ sơ sinh mềm mại an toàn\nSau khi mua {name}: Bé ngủ ngon, da không kích ứng 👶\nKết quả: Đặt thêm set dự phòng!",
        "unisex": f"Trước: Không tìm được đồ cả hai đều thích\nSau khi order {name}: Cả hai mặc ra phố đều được khen 💕\nKết quả: Order set thứ 2 rồi!",
    }

    return ViralContent(
        hook_text=hook_text,
        hook_subtext=hook_subtext,
        urgency_badge=urgency_badge,
        social_proof=random.choice(_SOCIAL_PROOF_POOL),
        value_stack=value,
        micro_story=stories.get(gender, stories["women"]),
        caption_tiktok=caption_tiktok,
        caption_shopee=caption_shopee,
        hashtags_tiktok=htags_tiktok,
        hashtags_shopee=htags_shopee,
        cta_tiktok=cta_tiktok,
        cta_shopee=cta_shopee,
        music_mood=music_mood,
        comment_cta=comment_cta,
    )


def build_caption(name: str = "", price: str = "", garment: str = "", platform: str = "tiktok") -> str:
    vc = build_viral_content(name=name, price=price, garment=garment, platform=platform)
    return vc.caption_tiktok if platform != "shopee" else vc.caption_shopee
