"""
pipeline/caption_gen.py — Tạo caption + hashtag tối ưu TikTok/Shopee.
"""
import random

TIKTOK_TMPL = {
    "dress evening gown": [
        "✨ Set váy {name} sang chảnh quá! Giá chỉ {price} 😍\n{tags}",
        "💃 Diện váy {name} đi đâu cũng được khen 🔥 {price}\n{tags}",
        "POV: Bạn mặc {name} và cả phố ngoái đầu 👗✨ {price}\n{tags}",
    ],
    "casual t-shirt": [
        "🔥 Basic nhưng không nhạt! {name} mix đồ siêu đỉnh 💪 {price}\n{tags}",
        "Outfit hôm nay 🌟 {name} | {price}\n{tags}",
        "{name} đang viral TikTok 🔥 Chỉ {price} mà đẹp thế!\n{tags}",
    ],
    "swimwear bikini": [
        "☀️ Set đi biển {name} cực xinh, giá {price} 🌊\n{tags}",
        "🏖️ Du lịch biển mặc {name} ai cũng ngoái nhìn 😍 {price}\n{tags}",
    ],
    "traditional ao dai": [
        "🌸 Áo dài {name} đẹp như tác phẩm nghệ thuật ✨ {price}\n{tags}",
        "🇻🇳 Tự hào diện áo dài Việt Nam 💕 {name} - {price}\n{tags}",
    ],
    "sportswear activewear": [
        "💪 Gym look chuẩn! {name} vừa đẹp vừa thoải mái - {price}\n{tags}",
        "🏃‍♀️ Workout outfit xịn sò {name} 🔥 Giá hời {price}\n{tags}",
    ],
    "hoodie streetwear": [
        "🔥 Chill ngày lạnh! {name} drip quá 😤 {price}\n{tags}",
        "Y2K vibes đang comeback 🤩 {name} - {price}\n{tags}",
    ],
    "default": [
        "🔥 {name} xinh xắn quá! Giá chỉ {price} 😍\n{tags}",
        "✨ {name} đang viral 🔥 {price}\n{tags}",
        "Set đồ {name} này hợp trend quá 💫 {price}\n{tags}",
    ],
}
SHOPEE_TMPL = [
    "👗 {name}\n✅ Giá: {price}\n✅ Freeship toàn quốc\n✅ Đổi trả 7 ngày\n{tags}",
    "🛒 Đặt ngay {name}!\nGiá ưu đãi: {price}\n💝 Freeship đơn từ 99k\n{tags}",
]

TT_TAGS  = ["#thoitrang","#ootd","#fashion","#outfit","#viral","#fyp",
            "#tiktokvietnam","#thoidai","#trending","#style","#fashionista"]
SP_TAGS  = ["#ShopeeFashion","#ShopeeVN","#MuaSắmOnline","#ThờiTrangNữ","#FreeShip"]
EX_TAGS  = {
    "dress":    ["#váy","#maxi","#dressoftheday"],
    "swimwear": ["#beachfashion","#đibiển"],
    "ao dai":   ["#áodài","#vietfashion"],
    "sport":    ["#gymwear","#activewear"],
    "hoodie":   ["#streetwear","#hoodieseason"],
}


def _tags(platform: str, garment: str) -> str:
    pool = set()
    if platform in ("tiktok","both"):
        pool.update(random.sample(TT_TAGS, min(7, len(TT_TAGS))))
    if platform in ("shopee","both"):
        pool.update(random.sample(SP_TAGS, min(5, len(SP_TAGS))))
    for k, v in EX_TAGS.items():
        if k in garment.lower():
            pool.update(v[:3]); break
    tags = list(pool)[:12]; random.shuffle(tags)
    return " ".join(tags)


def generate_caption(
    name: str = "", price: str = "",
    garment: str = "", platform: str = "tiktok",
) -> str:
    tags = _tags(platform, garment)
    n    = name  or "sản phẩm thời trang"
    p    = price or "Giá tốt nhất"

    if platform == "shopee":
        tmpl = random.choice(SHOPEE_TMPL)
    else:
        tmpl_list = None
        for key, lst in TIKTOK_TMPL.items():
            if any(w in garment.lower() for w in key.split()):
                tmpl_list = lst; break
        tmpl = random.choice(tmpl_list or TIKTOK_TMPL["default"])

    return tmpl.format(name=n, price=p, tags=tags)
