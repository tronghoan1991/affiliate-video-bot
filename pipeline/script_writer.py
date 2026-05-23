"""
pipeline/script_writer.py — AI Video Script Writer
=============================================================================
Dùng GarmentAnalysis để tự động viết kịch bản video hoàn chỉnh.

Kiến trúc:
  1. Chọn template phù hợp gender × style × occasion
  2. Tùy chỉnh theo màu sắc, họa tiết, tệp khách hàng
  3. Sinh VideoScript với timing chính xác
  4. Output sẵn sàng cho text_overlay + AI video generation

Phủ sóng: Women × Men × Children × Unisex — tất cả ngành thời trang
=============================================================================
"""
import random
from typing import Optional
from pipeline.ai_analyzer import GarmentAnalysis, VideoScript, SceneBlock


# ══════════════════════════════════════════════════════════════════════════════
#  HOOK LIBRARY — Theo Gender × Style (2026 authentic-first format)
# ══════════════════════════════════════════════════════════════════════════════

_HOOKS = {
    # ─── WOMEN ────────────────────────────────────────────────────────────────
    ("women", "formal"): [
        ("Mặc cái này vào phòng họp — cả phòng IM lặng 💼", "Không phải vì kỹ năng"),
        ("Set công sở này giúp tôi nhận offer trong buổi phỏng vấn 🎯", "Outfit làm nên chuyện"),
        ("Đồng nghiệp hỏi mua link 3 lần trong 1 ngày 😤", "Đây là set đó"),
        ("POV: Bạn bước vào văn phòng và sếp khen đầu tiên 👑", "Không phải vì báo cáo"),
    ],
    ("women", "casual"): [
        ("Tôi đã thử 15 bộ — đây là bộ duy nhất tôi giữ lại 😭", "Và đây là lý do"),
        ("Outfit chill nhất mùa này mà ai cũng hỏi mua ở đâu 🔥", "Bí mật ngay đây"),
        ("Mặc cái này ra phố — được hỏi số 2 lần trong 1 tiếng 😂", "Không phải flex"),
        ("POV: Bạn mặc đồ và cảm thấy tự tin 200% cả ngày ✨", "Set này làm được"),
    ],
    ("women", "streetwear"): [
        ("Gen Z aesthetic 2026 — set này chuẩn vibe nhất 🔥", "Không cần giải thích"),
        ("Outfit chill nhưng nhìn là biết có gu 😎", "Đây rồi"),
        ("Streetwear nữ đang trending — và đây là công thức 🌀", "Học ngay"),
        ("Mặc cái này đến trường — được chụp ảnh không nhớ bao nhiêu lần 📸", "Set này"),
    ],
    ("women", "sportswear"): [
        ("Mặc set này vào gym — không ai dám nhìn thẳng 💪", "Confidence level: max"),
        ("Set tập vừa đẹp vừa không phải kéo chỉnh suốt buổi 🙌", "Fabric magic"),
        ("Gym-to-café 2026: trend này — set này làm chuẩn nhất ☕", "Xem đây"),
        ("Vừa tập vừa được compliment — ai không thích? 😤", "Set này làm được"),
    ],
    ("women", "traditional"): [
        ("Áo dài đẹp nhất tôi từng mặc — và tôi đã thử nhiều 🌸", "Đây là cái đó"),
        ("Mặc áo dài này ra ngoài — ai cũng dừng lại chụp hình 📸", "Thật sự"),
        ("Tự hào mặc áo dài Việt — đẹp không thua gì quốc tế 🇻🇳", "Xem ngay"),
        ("POV: Bạn mặc áo dài này dự tiệc — không ai tin giá bao nhiêu 😍", "Xem đây"),
    ],
    ("women", "luxury"): [
        ("Phụ kiện này nâng cả outfit từ 6 lên 10 điểm 💎", "Không thay đồ"),
        ("Luxury look không cần luxury budget — bằng chứng đây 🛍️", "Giá bất ngờ"),
        ("Cầm cái này ra phố — được hỏi mua link cả ngày ✨", "Link ở bio"),
        ("Không cần hàng hiệu để trông sang — xem đây 👑", "Bí mật ngay đây"),
    ],

    # ─── MEN ──────────────────────────────────────────────────────────────────
    ("men", "formal"): [
        ("Khoác bộ suit này — cả phòng họp im lặng khi bạn bước vào 🤫", "Power dressing"),
        ("CEO vibes không cần lương CEO 💼", "Giá bạn không đoán được"),
        ("Mặc suit này đi pitch — nhà đầu tư gật đầu luôn 👊", "Không phải ngẫu nhiên"),
        ("Bộ vest đắt nhất không nhất thiết phải đắt tiền nhất ✨", "Xem đây"),
    ],
    ("men", "casual"): [
        ("Áo này tôi mặc đi đâu cũng được compliment 💯", "Mà giá rẻ không tưởng"),
        ("Outfit anh em đơn giản mà vẫn LOOK 😎", "Công thức đây"),
        ("Grab driver hỏi mua áo tôi đang mặc — thật không đùa 😂", "Link ở bio"),
        ("Set casual đỉnh nhất tôi tìm được tháng này 🔥", "Xứng đáng lắm"),
    ],
    ("men", "streetwear"): [
        ("Streetwear nam 2026 đang đi theo hướng này — bạn biết chưa? 🛹", "Set đây"),
        ("Flex không cần giải thích — set này đủ nói thay 😤", "Drip check"),
        ("Hoodie này nhìn là biết có gu — giá lại rất đời 💯", "Xem ngay"),
        ("Y2K x 2026 fusion — trend này đang đỉnh và đây là cách đúng 🌀", "Set này"),
    ],
    ("men", "sportswear"): [
        ("Set gym anh em mặc vào là muốn tập liền — không cần motivation 💪", "Bằng chứng đây"),
        ("Mặc set này vào gym — confident level khác hẳn 🏋️", "Thật sự"),
        ("Tập xong vẫn chill cafe được — không cần đổi đồ 🌿", "Set này"),
        ("Activewear nam đỉnh nhất tầm giá này 🔥", "Order ngay"),
    ],
    ("men", "traditional"): [
        ("Áo dài nam đẹp đến mức ba tôi cũng xin link 🌺", "Thật sự đẹp"),
        ("Quý ông diện áo dài Việt — phong thái khác hẳn 🇻🇳", "Tự hào mặc"),
        ("Mặc áo dài nam này dự sự kiện — không ai không ngoái nhìn 📸", "Xem đây"),
    ],
    ("men", "smart"): [
        ("Smart casual đỉnh nhất tháng này cho anh em 👔", "Set này đây"),
        ("Chinos + áo sơ mi = công thức không bao giờ sai 🎯", "Màu này mới nhất"),
        ("Đi làm hay đi chơi đều ổn — set đa năng nhất 2026 💯", "Link ở bio"),
    ],

    # ─── CHILDREN ─────────────────────────────────────────────────────────────
    ("children", "casual"): [
        ("Bé mặc cái này — cưng đến mức mọi người muốn bế 🥰", "Ba mẹ đừng bỏ lỡ"),
        ("Set bé cute nhất tháng này — ba mẹ order ầm ầm 🔥", "Còn hàng không?"),
        ("Con mặc cái này đi chơi — được chụp hình liên tục 📸", "Ba mẹ đặt ngay"),
        ("Ba mẹ tìm đồ cho bé đẹp, an toàn, giá hợp lý? 🎯", "Đây rồi"),
    ],
    ("children", "formal"): [
        ("Đồng phục bé đẹp nhất đầu năm học — ba mẹ xem ngay 📚", "Còn kịp mua không?"),
        ("Bé mặc đồng phục này đến trường — thầy cô cũng khen 👏", "Ba mẹ ơi"),
        ("Set bé đi dự sự kiện — cute như búp bê 🎀", "Order ngay trước hết"),
    ],
    ("children", "sportswear"): [
        ("Set đồ tập cho bé — năng động, thoải mái, dễ vận động 🏃", "Ba mẹ xem ngay"),
        ("Bé yêu thể thao cần set này — chất liệu an toàn tuyệt đối 💪", "Link ở bio"),
    ],
    ("children", "traditional"): [
        ("Bé mặc áo dài Tết cute đến mức ông bà khóc vì yêu 🌸", "Ba mẹ đặt ngay"),
        ("Set áo dài bé đẹp nhất Tết này — cả nhà phải chụp ảnh 📸", "Còn hàng nhé"),
    ],

    # ─── BABY ─────────────────────────────────────────────────────────────────
    ("baby", "casual"): [
        ("Bodysuit bé mềm như mây — ba mẹ sờ vào không muốn buông 🌙", "An toàn tuyệt đối"),
        ("Bé ngủ ngon hơn từ khi mặc set này — ba mẹ nói vậy 😇", "Chất liệu đặc biệt"),
        ("Ba mẹ tìm đồ cho bé sơ sinh an toàn, mềm mại? 👶", "Đây rồi"),
        ("Mua set này về mặc cho bé — cả nhà phát cuồng vì cute 🥹", "Link ở bio"),
    ],

    # ─── UNISEX ───────────────────────────────────────────────────────────────
    ("unisex", "casual"): [
        ("Đồ đôi matching — cute nhưng không kém phần slay 💕", "Cặp đôi xem ngay"),
        ("Set gia đình matching — khoảnh khắc này không thể thiếu 📸", "Ba mẹ đặt ngay"),
        ("Áo unisex này ai mặc cũng đẹp — thật không phải quảng cáo 💯", "Link ở bio"),
    ],
    ("unisex", "streetwear"): [
        ("Gender-free fashion 2026 — set này dẫn đầu trend 🌀", "Không giới hạn phong cách"),
        ("Hoodie này ai mặc cũng flex được — không kể giới tính 😤", "Đây rồi"),
        ("Unisex drip 2026 — freedom of style là đây 🔥", "Link bio"),
    ],
}

_DEFAULT_HOOK = [
    ("Tìm mãi 2 tuần mới thấy sản phẩm đỉnh thế này 🔍", "Xứng đáng lắm"),
    ("Viral vì lý do bạn chưa biết — xem đến cuối 🎯", "Đáng xem lắm"),
    ("Đây là thứ bạn đang cần mà chưa biết 🎯", "Xem ngay"),
    ("Chất lượng này, giá này — thật không thể tin 🤯", "Thật 100%"),
]

# ══════════════════════════════════════════════════════════════════════════════
#  VALUE STACK — Theo gender × age_group
# ══════════════════════════════════════════════════════════════════════════════

_VALUE_STACKS = {
    "women": "✅ Freeship + đổi trả 7 ngày\n✅ Chất lượng chuẩn hình 100%\n✅ Ship 2-3 ngày toàn quốc",
    "men":   "✅ Freeship + đổi size miễn phí\n✅ Hàng chuẩn hình, đúng màu\n✅ Ship nhanh 1-3 ngày",
    "baby":  "✅ Chất liệu mềm an toàn cho da bé\n✅ Không chất độc hại, kiểm định\n✅ Đổi trả 7 ngày + freeship",
    "children": "✅ Chất liệu an toàn cho trẻ em\n✅ Bền màu, không phai sau giặt\n✅ Freeship + đổi size miễn phí",
    "unisex": "✅ Freeship toàn quốc\n✅ Đổi trả 7 ngày không cần lý do\n✅ Đóng gói cẩn thận, giao nhanh",
}

# ══════════════════════════════════════════════════════════════════════════════
#  CTA — Theo gender × platform
# ══════════════════════════════════════════════════════════════════════════════

_CTA_MAP = {
    ("women", "tiktok"):    ["💃 Link mua ở BIO 👆", "✨ Tap bio — sale hôm nay!"],
    ("men",   "tiktok"):    ["👔 Link mua ở BIO 👆", "💪 Tap bio — flash deal!"],
    ("baby",  "tiktok"):    ["👶 Link mua cho bé ở BIO 👆", "🍼 Ba mẹ tap bio nhé!"],
    ("children","tiktok"):  ["🎀 Link mua cho bé ở BIO 👆", "🏫 Ba mẹ tap bio!"],
    ("unisex","tiktok"):    ["💕 Link mua ở BIO 👆", "🔥 Tap bio — hết hàng đừng tiếc!"],
    ("women", "shopee"):    ["🛒 Nhấn GIỎ HÀNG ngay!", "📦 Đặt hàng — freeship hôm nay!"],
    ("men",   "shopee"):    ["🛒 Đặt hàng ngay anh em!", "📦 Order — freeship + đổi size!"],
    ("baby",  "shopee"):    ["🛒 Đặt cho bé ngay!", "📦 Freeship + đổi trả 7 ngày!"],
    ("children","shopee"):  ["🛒 Mua cho bé ngay!", "📦 Hàng an toàn — freeship!"],
    ("unisex","shopee"):    ["🛒 Order ngay!", "📦 Đặt hàng — hết hàng đừng tiếc!"],
}

_COMMENT_CTA_MAP = {
    "women":    ["Comment 'MUA' để nhận link ngay 👇", "Comment 'LINK' — mình gửi liền 📩"],
    "men":      ["Comment 'BRO LINK' để nhận ngay 👇", "Comment 'MUA' — mình gửi liền 💪"],
    "children": ["Ba mẹ comment 'BÉ' để nhận link 👇", "Comment 'MUA CHO BÉ' — gửi ngay 🍼"],
    "baby":     ["Ba mẹ comment 'BÉ YÊU' để nhận link 👶", "Comment 'AN TOÀN' — gửi link ngay"],
    "unisex":   ["Comment 'MATCH' để nhận link 💕", "Comment 'ĐÔI' — mình gửi link liền"],
}

# ══════════════════════════════════════════════════════════════════════════════
#  COLOR SCHEME — Overlay color theo gender + style
# ══════════════════════════════════════════════════════════════════════════════

_COLOR_SCHEMES = {
    ("women", "formal"):      {"hook": "#FFFFFF", "name": "#FFD700", "price": "#FF3C3C", "cta": "#FFDC3C", "badge_bg": "#DC2626"},
    ("women", "casual"):      {"hook": "#FFFFFF", "name": "#FFD700", "price": "#FF3C3C", "cta": "#FFDC3C", "badge_bg": "#DC2626"},
    ("women", "luxury"):      {"hook": "#FFFFFF", "name": "#D4AF37", "price": "#FF3C3C", "cta": "#D4AF37", "badge_bg": "#7C3AED"},
    ("women", "traditional"): {"hook": "#FFFFFF", "name": "#FFD700", "price": "#FF3C3C", "cta": "#FFA500", "badge_bg": "#B91C1C"},
    ("men", "formal"):        {"hook": "#FFFFFF", "name": "#60A5FA", "price": "#FF3C3C", "cta": "#60A5FA", "badge_bg": "#1D4ED8"},
    ("men", "casual"):        {"hook": "#FFFFFF", "name": "#60A5FA", "price": "#FF3C3C", "cta": "#FFDC3C", "badge_bg": "#2563EB"},
    ("men", "streetwear"):    {"hook": "#FFFFFF", "name": "#A78BFA", "price": "#FF3C3C", "cta": "#A78BFA", "badge_bg": "#7C3AED"},
    ("men", "sportswear"):    {"hook": "#FFFFFF", "name": "#34D399", "price": "#FF3C3C", "cta": "#34D399", "badge_bg": "#059669"},
    ("children", "casual"):   {"hook": "#FFFFFF", "name": "#FB923C", "price": "#FF3C3C", "cta": "#FB923C", "badge_bg": "#EA580C"},
    ("children", "formal"):   {"hook": "#FFFFFF", "name": "#60A5FA", "price": "#FF3C3C", "cta": "#60A5FA", "badge_bg": "#2563EB"},
    ("baby", "casual"):       {"hook": "#FFFFFF", "name": "#F9A8D4", "price": "#FF3C3C", "cta": "#F9A8D4", "badge_bg": "#DB2777"},
    ("unisex", "casual"):     {"hook": "#FFFFFF", "name": "#FFD700", "price": "#FF3C3C", "cta": "#FFDC3C", "badge_bg": "#DC2626"},
    ("unisex", "streetwear"): {"hook": "#FFFFFF", "name": "#A78BFA", "price": "#FF3C3C", "cta": "#A78BFA", "badge_bg": "#7C3AED"},
}
_DEFAULT_COLOR = {"hook": "#FFFFFF", "name": "#FFD700", "price": "#FF3C3C", "cta": "#FFDC3C", "badge_bg": "#DC2626"}

# ══════════════════════════════════════════════════════════════════════════════
#  CAPTION TEMPLATES — Theo gender + style (micro-story format 2026)
# ══════════════════════════════════════════════════════════════════════════════

_CAPTION_TEMPLATES = {
    ("women", "formal"): (
        "Set công sở {name} này thay đổi cách mọi người nhìn bạn 💼\n"
        "Trước: Lo lắng không biết mặc gì đi làm\n"
        "Sau: Sếp khen, đồng nghiệp hỏi mua link 😎\n"
        "Giá: {price}\n{value}\n{comment_cta}\n{tags}"
    ),
    ("women", "casual"): (
        "Outfit {name} này tôi mặc đi đâu cũng được khen 🌸\n"
        "Giá chỉ {price} mà nhìn premium vậy đó!\n{value}\n"
        "{comment_cta} hoặc link ở bio 👆\n{tags}"
    ),
    ("women", "traditional"): (
        "Áo dài {name} đẹp đến nức lòng 🌺\n"
        "Tự hào mặc, tự hào show — giá chỉ {price}\n{value}\n"
        "{comment_cta}\n{tags}"
    ),
    ("men", "formal"): (
        "Set suit {name} — boss energy không cần giải thích 💼👑\n"
        "POV: Bạn bước vào phòng họp và cả phòng chú ý\n"
        "Giá: {price} — xứng đáng từng đồng\n{value}\n"
        "{comment_cta}\n{tags}"
    ),
    ("men", "casual"): (
        "Anh em ơi, set {name} này tôi mặc đi đâu cũng được hỏi 💯\n"
        "Giá {price} mà nhìn như đồ cao cấp 😤\n{value}\n"
        "{comment_cta}\n{tags}"
    ),
    ("men", "streetwear"): (
        "Streetwear drip 2026 — {name} 🔥😤\n"
        "Mặc ra đường là tự khắc nổi bật, không cần cố\n"
        "Giá: {price}\n{value}\n{comment_cta}\n{tags}"
    ),
    ("children", "casual"): (
        "Ba mẹ ơi — set {name} cho bé cute không chịu được 🥰\n"
        "Bé mặc vào là ai cũng muốn bế!\n"
        "Giá: {price}\n{value}\n{comment_cta}\n{tags}"
    ),
    ("children", "formal"): (
        "Set {name} cho bé đi học/sự kiện xinh như búp bê 🎀\n"
        "Giá: {price} — ba mẹ đặt ngay trước khi hết!\n{value}\n"
        "{comment_cta}\n{tags}"
    ),
    ("baby", "casual"): (
        "Ba mẹ tìm đồ cho bé sơ sinh an toàn, mềm mại? 👶\n"
        "{name} — chất liệu đặc biệt, không gây kích ứng da bé\n"
        "Giá: {price}\n{value}\n{comment_cta}\n{tags}"
    ),
    ("unisex", "casual"): (
        "Set đôi {name} — matching cute mà không sến 💕\n"
        "Ai mặc cũng đẹp — không kể giới tính!\n"
        "Giá: {price}\n{value}\n{comment_cta}\n{tags}"
    ),
}
_DEFAULT_CAPTION = (
    "{name} — viral vì lý do này 🔥\nGiá: {price}\n{value}\n{comment_cta}\n{tags}"
)

# ══════════════════════════════════════════════════════════════════════════════
#  HASHTAG LIBRARY — Theo gender + style
# ══════════════════════════════════════════════════════════════════════════════

_BASE_TAGS = "#fyp #foryoupage #viral #tiktokvietnam #thoitrang #ootd #tiktokshop #trending2026"
_GENDER_TAGS = {
    "women":    "#thoitrangnu #fashionwomen #outfitoftheday #fashionista",
    "men":      "#thoitrangnam #mensfashion #mensstyle #outfitmen",
    "children": "#thoitrangtrerem #kidsoutfit #babyoutfit #kidsclothes",
    "baby":     "#babyoutfit #babyclothes #sơsinh #dotre #babyfashion",
    "unisex":   "#unisex #couplelook #familymatching #ootd",
}
_STYLE_TAGS = {
    "formal":      "#congso #officewear #businessstyle #powerdressing",
    "casual":      "#casualstyle #everyday #ootd #streetstyle",
    "streetwear":  "#streetwear #hiphop #urbanfashion #genz #drip",
    "sportswear":  "#gymwear #activewear #sportstyle #gymoutfit #gymtok",
    "traditional": "#aodai #vietfashion #áodài #vietculture #trangphucviet",
    "luxury":      "#luxury #luxurylook #premiumfashion #accessorylook",
    "intimate":    "#homefashion #sleepwear #cozy",
    "smart":       "#smartcasual #mensstyle #officecasual",
}


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN SCRIPT WRITER
# ══════════════════════════════════════════════════════════════════════════════

def write_video_script(
    analysis: GarmentAnalysis,
    product_name: str,
    product_price: str,
    platform: str = "tiktok",
    duration: float = 15.0,
) -> VideoScript:
    """
    AI tự viết kịch bản video hoàn chỉnh từ GarmentAnalysis.
    Returns VideoScript sẵn sàng cho overlay + AI video generation.
    """
    gender = analysis.gender
    age = analysis.age_group
    style = analysis.style_category
    occasion = analysis.occasion

    # Normalize age_group → gender key for lookup
    lookup_gender = gender
    if age in ("baby", "toddler"):
        lookup_gender = "baby"
    elif age in ("kids",) and gender in ("unisex", "children"):
        lookup_gender = "children"

    # ── Hook ──────────────────────────────────────────────────────
    hook_pool = (_HOOKS.get((lookup_gender, style)) or
                 _HOOKS.get((gender, style)) or
                 _HOOKS.get((gender, "casual")) or
                 _DEFAULT_HOOK)
    hook_text, hook_subtext = random.choice(hook_pool)

    # ── Value stack ───────────────────────────────────────────────
    value = _VALUE_STACKS.get(lookup_gender, _VALUE_STACKS.get(gender, _VALUE_STACKS["unisex"]))

    # ── CTA ───────────────────────────────────────────────────────
    cta_pool = (_CTA_MAP.get((lookup_gender, platform)) or
                _CTA_MAP.get((gender, platform)) or
                ["🛍️ Link mua ở bio 👆"])
    cta = random.choice(cta_pool)

    comment_pool = _COMMENT_CTA_MAP.get(lookup_gender, _COMMENT_CTA_MAP.get(gender, ["Comment 'MUA' để nhận link 👇"]))
    comment_cta = random.choice(comment_pool)

    # ── Color scheme ──────────────────────────────────────────────
    colors = (_COLOR_SCHEMES.get((lookup_gender, style)) or
              _COLOR_SCHEMES.get((gender, style)) or
              _DEFAULT_COLOR)

    # ── Hashtags ──────────────────────────────────────────────────
    tags = f"{_BASE_TAGS} {_GENDER_TAGS.get(lookup_gender, _GENDER_TAGS.get(gender, ''))} {_STYLE_TAGS.get(style, '')}"

    # ── Caption ───────────────────────────────────────────────────
    caption_tmpl = (_CAPTION_TEMPLATES.get((lookup_gender, style)) or
                    _CAPTION_TEMPLATES.get((gender, style)) or
                    _CAPTION_TEMPLATES.get((gender, "casual")) or
                    _DEFAULT_CAPTION)
    caption = caption_tmpl.format(
        name=product_name, price=product_price,
        value=value, comment_cta=comment_cta, tags=tags,
    )

    # ── AI Video Prompts ──────────────────────────────────────────
    from pipeline.background import get_full_prompt, get_hook_frame_prompt
    from pipeline.ai_analyzer import GARMENT_TAXONOMY

    # Map garment_key → background prompt
    bg_key = analysis.garment_key.replace("women_", "").replace("men_", "").replace("kids_", "").replace("baby_", "")
    gender_label = (
        "Vietnamese woman in her mid-20s" if gender == "women"
        else "Vietnamese man in his late 20s" if gender == "men"
        else "Vietnamese baby/child" if age in ("baby", "toddler", "kids")
        else "Vietnamese teenager"
    )
    ai_prompt = (
        f"Beautiful confident {gender_label} wearing {product_name}, "
        f"outfit perfectly fitted, product clearly visible. "
        f"{get_full_prompt(bg_key)}"
    )
    ai_hook_prompt = get_hook_frame_prompt(bg_key)

    # ── Music mood ────────────────────────────────────────────────
    music_map = {
        "formal":      "powerful_cinematic",
        "casual":      "trendy_pop",
        "streetwear":  "phonk_street",
        "sportswear":  "energetic_edm",
        "traditional": "vietnamese_modern",
        "luxury":      "luxury_elegant",
        "intimate":    "cozy_aesthetic",
        "smart":       "corporate_smooth",
    }
    music_mood = music_map.get(style, "trendy_pop")
    if age in ("baby", "toddler", "kids"):
        music_mood = "cozy_aesthetic"  # Nhạc nhẹ nhàng cho sản phẩm trẻ em

    # ── Timing ───────────────────────────────────────────────────
    hook_end   = min(2.5, duration * 0.17)
    value_start = min(6.0, duration * 0.4)
    cta_start   = min(10.0, duration * 0.67)
    loop_start  = min(13.0, duration * 0.87)

    return VideoScript(
        title=f"[{gender.upper()}] {product_name} — {style}",
        duration_seconds=duration,
        platform=platform,
        hook_scene=SceneBlock(
            start_time=0.0, end_time=hook_end,
            hook_text=hook_text, subtext=hook_subtext,
            visual_note="Extreme close-up product detail → pull back reveal",
            overlay_position="top", text_color=colors["hook"], bg_alpha=0.65,
        ),
        reveal_scene=SceneBlock(
            start_time=hook_end, end_time=value_start,
            hook_text=product_name, subtext=f"💰 {product_price}",
            visual_note="Full outfit reveal, model turns 360°, product clearly visible",
            overlay_position="bottom", text_color=colors["name"], bg_alpha=0.6,
        ),
        value_scene=SceneBlock(
            start_time=value_start, end_time=cta_start,
            hook_text=value, subtext="",
            visual_note="Model walking, styling, showing different angles",
            overlay_position="center-left", text_color="#FFFFFF", bg_alpha=0.55,
        ),
        cta_scene=SceneBlock(
            start_time=cta_start, end_time=loop_start,
            hook_text=cta, subtext=comment_cta,
            visual_note="Final confident pose, direct camera engagement",
            overlay_position="bottom", text_color=colors["cta"], bg_alpha=0.7,
        ),
        loop_scene=SceneBlock(
            start_time=loop_start, end_time=duration,
            hook_text="", subtext="",
            visual_note="Seamless loop frame — same as opening frame",
            overlay_position="none", text_color="#FFFFFF", bg_alpha=0.0,
        ),
        ai_prompt_main=ai_prompt,
        ai_prompt_hook=ai_hook_prompt,
        caption=caption,
        hashtags=tags.split(),
        music_mood=music_mood,
        color_scheme=colors,
    )
