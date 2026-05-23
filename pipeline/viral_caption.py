"""
pipeline/viral_caption.py — Viral Caption Engine v7 (2026)
=============================================================================
Sinh caption + hashtag cho TẤT CẢ ngành hàng:
  fashion | beauty | health | home | food | tech | pet | sports | baby

Tích hợp 7-trigger emotional framework.
Dựa trên phân tích TikTok Vietnam Q1 2026 + Shopee Affiliate data.
=============================================================================
"""
import random
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from pipeline.emotional_engine import EmotionalPackage


@dataclass
class ViralCaption:
    tiktok: str
    shopee: str
    instagram: str           # Bonus: IG Reels format
    hashtags_tiktok: str
    hashtags_shopee: str
    comment_bait: str        # Câu kêu gọi comment để ×4 reach
    cta_bio: str             # CTA link in bio
    hook_ab_variants: list   # 3 hook variants để A/B test


# ══════════════════════════════════════════════════════════════════════════════
#  HASHTAG BANKS 2026
# ══════════════════════════════════════════════════════════════════════════════

_BASE_TT = "#fyp #viral #tiktokvietnam #trending2026 #tiktokshop #affiliate"
_BASE_SP = "#ShopeeFashion #ShopeeVN #FlashSale #FreeShip #ShopeeAffiliate #MuaSắmOnline #ShopeeLive"

_CAT_TAGS_TT = {
    "fashion":      "#thoitrang #ootd #ootdvietnam #fashionvn #outfitoftheday #styleinspo",
    "fashion_women":"#thoitrangnu #fashionwomen #outfitinspo #girldress #womensstyle",
    "fashion_men":  "#thoitrangnam #mensfashion #mensstyle #guystyle #outfitmen",
    "beauty":       "#skincare #lameskin #beautyviêtnam #skincareroutine #glowup #beautytips",
    "health":       "#suckhoe #healthy #wellness #supplement #vitamin #healthylifestyle",
    "home":         "#homedecor #homeinspo #interior #homevn #decorvietnam #tidyhome",
    "food":         "#food #foodvietnam #snack #foodies #ănngon #đồăn #foodtiktok",
    "tech":         "#tech #techvietnam #gadgets #phoneaccessories #setup #techreview",
    "pet":          "#boss #meovn #chovn #petlover #petvietnam #pets #thucung",
    "sports":       "#gym #fitness #workout #thethao #active #gymvietnam #yoga",
    "baby":         "#baby #bé #mevabe #motherhood #newborn #babytips #trẻem",
    "fashion_kids": "#bé #kids #kidsoutfit #trẻem #outfitbé #momlife #parentsvn",
}

_CAT_TAGS_SP = {
    "fashion":  "#ShopeeFashion #thoitrangonline #MuaSắmNhà",
    "beauty":   "#SkincareSale #BeautyShopee #ShopeeCosmetica",
    "health":   "#ShopeeHealth #SupplementSale #SuKhoeOnline",
    "home":     "#HomeDecorShopee #NhaDep #GiaDung",
    "food":     "#ShopeeFood #SnackSale #DoAnSale",
    "tech":     "#ShopeeThang #TechSale #GadgetShopee",
    "pet":      "#PetShopee #BossViet #ThuCungOnline",
    "sports":   "#SportsSale #GymEquipment #YogaShopee",
    "baby":     "#ShopeeMe #BabyShopee #MeBe",
    "fashion_kids": "#KidsShopee #TreEmOnline #BebeFashion",
}

_SEASONAL_BADGE = {
    1:"🧧 Tết Sale", 2:"💕 Valentine Sale", 3:"🌸 Mùa xuân Sale",
    4:"🌷 Tháng 4 Sale", 5:"☀️ Hè về Sale", 6:"🏖️ Beach Season",
    7:"🌊 Mid Summer", 8:"🎒 Back to School", 9:"🍂 Thu về Sale",
    10:"🍁 Fall Sale", 11:"🧥 Đông về Sale", 12:"🎄 Year-end Sale",
}

_COMMENT_BAITS = {
    "fashion":  ["Comment 'MUA' để nhận link ngay 👇", "Comment 'LINK' mình gửi liền 📩", "Comment 'MUỐN' nhận thêm ưu đãi 💌"],
    "beauty":   ["Comment 'DA' để nhận link serum 💆", "Comment 'SKINCARE' mình gửi link 📩", "Comment 'ĐẸPDA' nhận code giảm thêm ✨"],
    "health":   ["Comment 'KHỎE' để nhận link 💪", "Comment 'ORDER' mình gửi ngay 📦", "Comment 'SỨC KHỎE' nhận tư vấn miễn phí 🩺"],
    "home":     ["Comment 'NHÀ ĐẸP' để nhận link 🏠", "Comment 'MUA' gửi link liền 📩", "Comment 'DECOR' nhận combo deal 🛋️"],
    "food":     ["Comment 'ĂN' để nhận link mua 🍱", "Comment 'NGON' mình gửi link 😋", "Comment 'ORDER' nhận freeship đặc biệt 📦"],
    "tech":     ["Comment 'TECH' để nhận link 📱", "Comment 'MUA' mình gửi liền 💻", "Comment 'SETUP' nhận deal thêm ⚡"],
    "pet":      ["Comment 'BOSS' để nhận link 🐾", "Comment 'MÈO/CHÓ' mình gửi link 🐱", "Comment 'PET' nhận freeship đặc biệt 🐶"],
    "sports":   ["Comment 'GYM' để nhận link 💪", "Comment 'TẬPTHỂ' gửi link ngay 🏋️", "Comment 'ACTIVE' nhận deal thêm 🏃"],
    "baby":     ["Comment 'BÉ YÊU' để nhận link 👶", "Comment 'MẸ BÉ' mình gửi ngay 🍼", "Comment 'AN TOÀN' nhận tư vấn miễn phí 💕"],
    "fashion_kids": ["Comment 'BÉ CUTE' để nhận link 🎀", "Comment 'MUA CHO BÉ' gửi link 📩", "Comment 'BA MẸ' nhận thêm ưu đãi 👨‍👩‍👧"],
}

_BIO_CTAS = {
    "fashion":  ["💃 Link mua ở BIO 👆", "✨ Tap BIO — flash deal hôm nay!", "🛒 BIO có link — sale đang chạy!"],
    "beauty":   ["✨ Link skincare ở BIO 👆", "💆 Tap BIO — deal hôm nay!", "🌸 BIO ngay — hàng đang sale!"],
    "health":   ["💊 Link supplement ở BIO 👆", "💪 Tap BIO — combo deal!", "🏃 BIO có link — deal đặc biệt!"],
    "home":     ["🏠 Link decor ở BIO 👆", "🛋️ Tap BIO — sale đang chạy!", "✨ BIO ngay — combo home deal!"],
    "food":     ["🍱 Link đặt đồ ăn ở BIO 👆", "😋 Tap BIO — freeship hôm nay!", "🍜 BIO có link — deal snack!"],
    "tech":     ["📱 Link tech ở BIO 👆", "💻 Tap BIO — flash deal tech!", "⚡ BIO có link — giá launch!"],
    "pet":      ["🐾 Link cho boss ở BIO 👆", "🐱 Tap BIO — pet deal!", "🐶 BIO ngay — freeship boss!"],
    "sports":   ["💪 Link dụng cụ ở BIO 👆", "🏋️ Tap BIO — gym deal hôm nay!", "🏃 BIO có link — sale sports!"],
    "baby":     ["👶 Link cho bé ở BIO 👆", "🍼 Tap BIO — baby deal hôm nay!", "💕 BIO ngay — an toàn cho bé!"],
    "fashion_kids": ["🎀 Link đồ bé ở BIO 👆", "👗 Tap BIO — kids deal!", "🌈 BIO ngay — đồ bé đẹp!"],
}


def _hashtags_tt(category: str, gender: str = "") -> str:
    cat_tag = _CAT_TAGS_TT.get(f"{category}_{gender}" if f"{category}_{gender}" in _CAT_TAGS_TT else category, "")
    return f"{_BASE_TT} {cat_tag}".strip()


def _hashtags_sp(category: str) -> str:
    cat_tag = _CAT_TAGS_SP.get(category, "")
    return f"{_BASE_SP} {cat_tag}".strip()


def generate_viral_caption(
    product_name: str,
    price: str,
    category: str,
    gender: str,
    emotional: EmotionalPackage,
    platform: str = "tiktok",
) -> ViralCaption:
    """Sinh caption đầy đủ cho mọi ngành hàng và platform."""
    month = datetime.now().month
    badge = _SEASONAL_BADGE.get(month, "🔥 HOT 2026")
    social = emotional.social_proof_line
    transform = emotional.transformation_line
    urgency = emotional.urgency_line
    comment_bait = random.choice(_COMMENT_BAITS.get(category, _COMMENT_BAITS["fashion"]))
    cta_bio = random.choice(_BIO_CTAS.get(category, _BIO_CTAS["fashion"]))
    ht_tt = _hashtags_tt(category, gender)
    ht_sp = _hashtags_sp(category)

    # Value stack theo category
    value_stacks = {
        "fashion":  "✅ Freeship toàn quốc\n✅ Đổi trả 7 ngày miễn phí\n✅ Giao 2-3 ngày",
        "beauty":   "✅ Dermatologist tested\n✅ Không chất độc hại\n✅ Đổi trả nếu không thấy kết quả",
        "health":   "✅ Chứng nhận Bộ Y tế\n✅ Nguyên liệu tự nhiên\n✅ Hoàn tiền 100% nếu không hài lòng",
        "home":     "✅ Freeship + đổi trả 7 ngày\n✅ Lắp đặt hướng dẫn chi tiết\n✅ Bảo hành 12 tháng",
        "food":     "✅ Hàng chính hãng có tem\n✅ Freeship đơn từ 99k\n✅ Đổi trả nếu hàng lỗi",
        "tech":     "✅ Bảo hành 12 tháng\n✅ Đổi trả 30 ngày\n✅ Freeship + giao nhanh",
        "pet":      "✅ Được khuyên bởi bác sĩ thú y\n✅ Không chất bảo quản độc hại\n✅ Freeship + đổi trả",
        "sports":   "✅ Chất liệu cao cấp\n✅ Bảo hành sản phẩm\n✅ Freeship toàn quốc",
        "baby":     "✅ An toàn tuyệt đối cho bé\n✅ Không BPA, không hóa chất độc\n✅ Đổi trả 7 ngày",
        "fashion_kids": "✅ Chất liệu an toàn cho bé\n✅ Freeship + đổi size\n✅ Giao 2-3 ngày",
    }
    value = value_stacks.get(category, value_stacks["fashion"])

    # TikTok caption (ngắn, punch, emoji)
    tiktok = (
        f"{emotional.hook_curiosity[:80]}\n\n"
        f"🏷️ {product_name}\n"
        f"💰 Chỉ {price} — {badge}\n"
        f"⭐ {social}\n\n"
        f"✨ {transform[:80]}\n\n"
        f"{value}\n\n"
        f"🎯 {emotional.authenticity_story[:70]}\n\n"
        f"{comment_bait}\n"
        f"{cta_bio}\n\n"
        f"{urgency}\n\n"
        f"{ht_tt}"
    )

    # Shopee caption (chi tiết, trust, conversion)
    shopee = (
        f"🛒 {product_name}\n"
        f"⭐ {social}\n"
        f"💰 Giá: {price} — {badge}\n\n"
        f"💡 TẠI SAO NÊN MUA:\n"
        f"• {transform}\n"
        f"• {emotional.identity_line[:80]}\n"
        f"• {emotional.authenticity_story[:80]}\n\n"
        f"{value}\n\n"
        f"📦 {urgency}\n"
        f"🛒 Nhấn GIỎ HÀNG ngay!\n\n"
        f"{ht_sp}"
    )

    # Instagram Reels format
    instagram = (
        f"✨ {emotional.hook_curiosity[:70]}\n\n"
        f"Sản phẩm: {product_name}\n"
        f"Giá: {price}\n\n"
        f"{value}\n\n"
        f"👆 Link in bio!\n\n"
        f"🏷️ {ht_tt.replace('#fyp #viral #tiktokvietnam', '#reels #instagram #instagramvietnam')}"
    )

    return ViralCaption(
        tiktok         = tiktok,
        shopee         = shopee,
        instagram      = instagram,
        hashtags_tiktok= ht_tt,
        hashtags_shopee= ht_sp,
        comment_bait   = comment_bait,
        cta_bio        = cta_bio,
        hook_ab_variants= emotional.ab_hooks,
    )
