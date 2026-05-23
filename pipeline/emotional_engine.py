"""
pipeline/emotional_engine.py — 7-Trigger Emotional Framework v7 (2026)
=============================================================================
Dựa trên neuromarketing research + phân tích 34,635 video TikTok viral
(OpusClip, Jan–Mar 2026) + tâm lý học hành vi người tiêu dùng Việt.

7 EMOTIONAL TRIGGERS đã được chứng minh tăng CTR:
  1. FOMO      — Sợ bỏ lỡ cơ hội / sản phẩm hot
  2. SOCIAL PROOF — Cộng đồng đã xác nhận / số lượng
  3. CURIOSITY — Tò mò, câu chuyện chưa kể xong
  4. TRANSFORMATION — Trước/sau, thay đổi rõ rệt
  5. AUTHENTICITY — Thật, không quảng cáo, người thật
  6. IDENTITY   — "Sản phẩm này là tôi" / giá trị cá nhân
  7. URGENCY    — Giới hạn thời gian / số lượng

Thứ tự áp dụng tối ưu (đã test):
  Hook (0-2s): CURIOSITY + FOMO
  Reveal (2-6s): SOCIAL PROOF + TRANSFORMATION
  Value (6-10s): AUTHENTICITY + IDENTITY
  CTA (10-13s): URGENCY + FOMO
  Loop (13-15s): CURIOSITY (dẫn vào loop tiếp)
=============================================================================
"""
import random
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class EmotionalPackage:
    """Gói nội dung cảm xúc cho 1 sản phẩm."""
    primary_trigger: str          # Trigger chính (mạnh nhất cho sản phẩm này)
    secondary_trigger: str        # Trigger phụ
    hook_curiosity: str           # Hook gây tò mò (0-1s)
    hook_fomo: str                # Hook FOMO (1-2s)
    social_proof_line: str        # Dòng social proof
    transformation_line: str      # Dòng transformation
    authenticity_story: str       # Micro-story thật
    identity_line: str            # Dòng identity
    urgency_line: str             # Dòng urgency
    loop_hook: str                # Hook loop cuối (kéo về đầu)
    emotional_music: str          # Mood nhạc phù hợp cảm xúc
    color_psychology: str         # Màu overlay (gợi cảm xúc đúng)
    ab_hooks: List[str]           # 3 variants hook để A/B test


# ══════════════════════════════════════════════════════════════════════════════
#  TRIGGER LIBRARIES — Phân theo ngành hàng 2026
# ══════════════════════════════════════════════════════════════════════════════

# ── FASHION (Thời trang) ──────────────────────────────────────────────────────
_FASHION_CURIOSITY = [
    "POV: Bạn mặc cái này ra đường lần đầu... 👀",
    "Tôi đã thử 20 bộ — đây là bộ duy nhất tôi không trả lại 😭",
    "Stylist của tôi thấy cái này liền nói... 😳",
    "Outfit này đã cứu tôi trong 3 tình huống khác nhau 🔥",
    "Cái này trông bình thường trên ảnh nhưng mặc vào thì... 👁️",
    "Người ta ngừng lại hỏi tôi về cái này 2 lần trong 1 tiếng ⏱️",
]
_FASHION_FOMO = [
    "Size của bạn đang còn — nhưng không biết đến khi nào 🕐",
    "Tuần trước sold out 2 lần — hàng vừa về 🔔",
    "Cả group đang order — bạn còn chờ gì? 💬",
    "Đợt này giá thấp nhất từ trước đến nay — không biết có còn không 📉",
    "3 người hỏi link cùng lúc tôi đang quay video này 😤",
]
_FASHION_SOCIAL_PROOF = [
    "8.4K đã order — review 4.9⭐ liên tục",
    "Sold out 5 lần — vừa restock hôm qua",
    "Top 1 best-seller ngành thời trang tuần này",
    "3,200 người đang xem sản phẩm này ngay lúc này",
    "500+ review 5 sao — không một review nào dưới 4 sao",
]
_FASHION_TRANSFORMATION = [
    "Trước: Không biết mặc gì. Sau: Được hỏi mua link mọi nơi 💫",
    "Từ ngày có cái này — tủ quần áo bớt hỗn loạn 60% 📦",
    "Mặc 1 lần → bạn bè hỏi đi đâu làm tóc mới à 😂",
    "Confidence level: 0 → 100 chỉ sau khi mặc vào",
]
_FASHION_AUTHENTICITY = [
    "Tôi không được sponsor — tôi tự bỏ tiền mua và đây là review thật",
    "Nói thật: Tôi đã hoài nghi khi order. Nhưng nhận hàng xong thì...",
    "Đây là lần đầu tiên tôi review 1 sản phẩm 2 lần vì quá thích",
    "Ba tôi thấy tôi mặc cái này và hỏi mua link — và ông ấy không bao giờ hỏi link",
]
_FASHION_IDENTITY = [
    "Sản phẩm này không phải cho người mặc đẹp — mà cho người muốn tự tin",
    "Bạn không cần phải có body hoàn hảo — bạn chỉ cần cái này 💪",
    "Mặc đẹp không phải xa xỉ — đây là cách tôi tôn trọng bản thân mỗi ngày",
    "Gen Z không mặc để được khen — mặc để cảm thấy mình ✨",
]

# ── BEAUTY / SKINCARE (Làm đẹp) ───────────────────────────────────────────────
_BEAUTY_CURIOSITY = [
    "Da tôi thay đổi sau 7 ngày dùng cái này — xem đến cuối 👁️",
    "Bác sĩ da liễu tôi không nói điều này — tôi tự tìm ra 🔬",
    "Sản phẩm này có gì mà 200 người tag nhau mua cùng lúc? 🤔",
    "Tôi đã thử 11 serum — đây là cái DUY NHẤT thấy kết quả sau 2 tuần",
    "POV: Skin bạn sau 30 ngày dùng đều đặn ✨",
    "Bạn gái hỏi tôi da tôi làm gì — câu trả lời là cái này 💆‍♀️",
]
_BEAUTY_FOMO = [
    "Flash sale kết thúc sau 2 tiếng — hàng đang hết dần 🔔",
    "Mẫu này sắp ngưng sản xuất — hàng còn rất ít 📦",
    "Promotion này chỉ áp dụng cho đơn hôm nay 💥",
    "1,200 người đang xem sản phẩm này ngay lúc này 👥",
]
_BEAUTY_SOCIAL_PROOF = [
    "12K review — 94% nói thấy kết quả sau 2 tuần",
    "Dermatologist tested — phù hợp da nhạy cảm, da dầu, da khô",
    "#1 serum bán chạy tháng này trên Shopee Beauty",
    "Viral suốt 3 tuần — mỗi ngày 500+ đơn mới",
]
_BEAUTY_TRANSFORMATION = [
    "Da mụn → da căng bóng sau 21 ngày. Review thật, không filter 📸",
    "Lỗ chân lông to → thu nhỏ rõ rệt — bạn bè tưởng tôi đi điều trị",
    "Thâm mụn bám 2 năm — mờ 60% sau 30 ngày dùng đều",
    "Trước: Đổ nền 3 lớp mới ra đường. Sau: Ra đường không cần nền 😮",
]
_BEAUTY_AUTHENTICITY = [
    "Tôi không bao giờ review nếu không thật sự thấy kết quả — đây là lần thứ 2",
    "Da tôi cực nhạy cảm, nổi mụn với 70% sản phẩm. Cái này không — đây là sự thật",
    "Mẹ tôi dùng xong hỏi mua thêm 3 hộp — mẹ không bao giờ khen skincare",
    "Đây là tuần thứ 4 — tôi quay lại vì thật sự có thay đổi",
]
_BEAUTY_IDENTITY = [
    "Skincare không phải xa xỉ — là đầu tư vào phiên bản tốt nhất của bạn",
    "Da đẹp = confidence. Không phải vì người khác — vì bạn xứng đáng",
    "Bạn không cần filter — bạn cần đúng sản phẩm",
    "Chăm sóc da là cách bạn nói yêu thương bản thân mỗi ngày 💕",
]

# ── HEALTH / SUPPLEMENT ───────────────────────────────────────────────────────
_HEALTH_CURIOSITY = [
    "Tôi uống cái này 30 ngày — điều này xảy ra với cơ thể tôi 😮",
    "Bác sĩ khuyên — tôi thấy kết quả sau 2 tuần không ngờ 🩺",
    "Tại sao người Nhật trông trẻ hơn 15 tuổi? Bí mật là đây... 🇯🇵",
    "Sau 35 tuổi cơ thể thiếu thứ này — 90% không biết 🔬",
    "Mỡ bụng tôi đã đi đâu sau 21 ngày? 📉",
]
_HEALTH_FOMO = [
    "Combo giá tốt nhất hết 23/5 — còn vài chục hộp",
    "Mua 2 tặng 1 — hết hôm nay 🎁",
    "Lô này nhập từ Nhật — số lượng có hạn, không restock sớm 🇯🇵",
    "Flash deal 40% — chỉ hôm nay ⚡",
]
_HEALTH_SOCIAL_PROOF = [
    "Được dùng bởi 50,000+ người Việt — phản hồi tích cực 96%",
    "Chứng nhận Bộ Y tế — không chất bảo quản độc hại",
    "Review từ chuyên gia dinh dưỡng — khuyên dùng hàng ngày",
    "#1 bestseller ngành thực phẩm chức năng 3 tháng liên tiếp",
]
_HEALTH_TRANSFORMATION = [
    "Trước: Mệt mỏi, khó ngủ, da xỉn. Sau 30 ngày: Năng lượng +200% 🔋",
    "Cân nặng giảm 3kg không cần nhịn ăn — cách tôi làm là...",
    "Da từ xỉn màu → căng sáng không cần thêm gì. Collagen thật sự work",
    "Chạy bộ 5km không mệt — từ khi bổ sung thứ này",
]
_HEALTH_AUTHENTICITY = [
    "Tôi không phải KOL — chỉ là người bình thường muốn chia sẻ thật",
    "Review này không có thù lao — tôi mua tự bỏ tiền ra",
    "Chồng tôi uống đủ 30 ngày, anh ấy nói cảm thấy khác — anh không hay khen",
    "Tôi đã hoài nghi 100% — đây là trước và sau của TÔI, không phải người khác",
]
_HEALTH_IDENTITY = [
    "Sức khỏe không phải may mắn — là lựa chọn bạn làm mỗi ngày",
    "Người khỏe mạnh không tự nhiên sinh ra — họ đã đầu tư đúng chỗ",
    "Cơ thể bạn là tài sản quý nhất — đừng tiếc tiền đầu tư cho nó",
    "Tốt nhất cho sức khỏe của bạn = tốt nhất cho người bạn yêu thương",
]

# ── HOME & LIVING ─────────────────────────────────────────────────────────────
_HOME_CURIOSITY = [
    "Phòng tôi thay đổi hoàn toàn với item 200k này — ai cũng hỏi 😮",
    "IKEA hack 2026 người Việt đang làm — bạn biết chưa? 🏠",
    "Item này làm nhà tôi sạch 3× nhanh hơn — mà không dùng hóa chất ✨",
    "Mọi người đến chơi đều hỏi mua cái này ở đâu 🛋️",
    "Bạn đang làm sai cách tổ chức tủ — đây là cách đúng 📦",
]
_HOME_FOMO = [
    "Sale cuối mùa — hàng này không về nữa 🏷️",
    "Set này giá tốt nhất tháng — hết là hết 📦",
    "Flash deal 50% — chỉ còn 11 tiếng ⚡",
    "Order trước Tết để kịp trang trí nhà 🧧",
]
_HOME_SOCIAL_PROOF = [
    "15K đơn mỗi tháng — item bán chạy số 1 home decor",
    "4.9 sao / 6,000 review — không có review dưới 4 sao",
    "Trending suốt 3 tháng — vừa được featured trên báo",
    "Được recommend bởi 200+ home blogger Việt Nam",
]
_HOME_TRANSFORMATION = [
    "Trước: Phòng bừa bộn, bí bách. Sau: Căn phòng trong mơ 😍",
    "Dọn nhà từ 3 tiếng → 45 phút nhờ cái này 🕐",
    "Từ chung cư bình thường → căn hộ ai vào cũng chụp ảnh 📸",
    "Bụi bặm không còn là vấn đề sau khi có cái này trong nhà",
]
_HOME_AUTHENTICITY = [
    "Không phải nhà thiết kế — chỉ là người yêu nhà và hay thử đồ mới",
    "Mua về tưởng trả lại — nhưng giờ không thể thiếu trong bếp",
    "Mẹ tôi không chịu mua gì online — nhưng cái này bà đặt 2 cái cho hàng xóm",
    "Tôi đã mua 4 sản phẩm tương tự — cái này duy nhất xứng đáng giữ lại",
]
_HOME_IDENTITY = [
    "Ngôi nhà phản ánh bạn là ai — đầu tư vào nó là đầu tư vào chính mình",
    "Không gian sống đẹp → tâm trạng tốt hơn → năng suất cao hơn 🌟",
    "Bạn dành 8-10 tiếng mỗi ngày ở nhà — xứng đáng được đẹp hơn",
    "Nhà không cần đắt tiền để ấm cúng — chỉ cần đúng sản phẩm",
]

# ── FOOD / SNACK ─────────────────────────────────────────────────────────────
_FOOD_CURIOSITY = [
    "Snack này người Việt đang ăn nhiều nhất 2026 — bạn thử chưa? 🤤",
    "Tôi đã ăn sạch 3 hộp trong 1 tuần — đây là lý do 😭",
    "Vị này không giải thích được — phải tự thử mới biết 👅",
    "Tại sao đồ ăn Đài Loan / Nhật / Hàn lại nghiện đến vậy? Thử đây biết 🍜",
    "Bạn bè đến chơi ăn hết mà không hỏi — đặt thêm vì hết mất rồi 😂",
]
_FOOD_FOMO = [
    "Flash sale flash deal — chỉ còn ít hộp cuối 🍱",
    "Lô nhập này gần hết — không biết khi nào có đợt mới 📦",
    "Sale cuối tháng — giá rẻ nhất từ trước đến nay 💸",
    "Mua 3 freeship — chỉ hôm nay ⚡",
]
_FOOD_SOCIAL_PROOF = [
    "20K+ đơn mỗi tháng — snack bán chạy số 1 Shopee Food",
    "Rating 4.9⭐ / 8,000 review — 95% người mua mua lại",
    "Viral 3 tuần liên tiếp — ai ăn cũng tag người thân",
    "Được featured trên Shopee Mall — đảm bảo hàng chính hãng",
]
_FOOD_TRANSFORMATION = [
    "Từ ngày có hộp này — không còn ăn vặt ngoài đường nữa 💪",
    "Bữa ăn vặt 3 giờ sáng: Trước: mì gói. Sau: cái này 😌",
    "Mood bình thường → mood tốt sau khi ăn — không đùa",
    "Cả văn phòng ăn sạch trong 1 buổi — đặt thêm liền",
]
_FOOD_AUTHENTICITY = [
    "Ăn xong hết 1 hộp rồi mới quay review — vì ngon thật sự",
    "Không sponsored — tôi thích thật sự và muốn chia sẻ",
    "Con tôi 8 tuổi ăn xong hỏi mua thêm — đây là tiêu chuẩn của tôi",
    "Tôi hay review food nhưng đây là cái đầu tiên tôi review 2 lần",
]
_FOOD_IDENTITY = [
    "Ăn ngon là quyền — không cần đắt mới ngon 🍽️",
    "Snack tốt = mood tốt = ngày tốt hơn 😊",
    "Bạn xứng đáng với những thứ ngon nhất trong tầm ngân sách của bạn",
    "Chia sẻ đồ ăn ngon = cách yêu thương đơn giản nhất ❤️",
]

# ── TECH ACCESSORIES ─────────────────────────────────────────────────────────
_TECH_CURIOSITY = [
    "Phụ kiện này thay đổi cách tôi dùng điện thoại hoàn toàn 📱",
    "Tại sao người dùng iPhone/Samsung đều đang mua cái này? 🤔",
    "Tôi đã mua 5 cái rẻ tiền — cái này giải quyết vấn đề mà 5 cái kia không làm được",
    "Tech hack 2026 — tiết kiệm 2 tiếng mỗi ngày với cái này ⏱️",
    "Đổ pin điện thoại lúc 9 giờ sáng — 11 giờ đêm vẫn còn 40% 🔋",
]
_TECH_FOMO = [
    "Flash deal — giá gốc 500k, hôm nay còn 199k ⚡",
    "Nhập hàng đợt đầu — bán hết là hết đợt này 📦",
    "Giá launch đặc biệt — hết ngày mai về giá gốc 💸",
    "Chỉ còn 50 sản phẩm trong kho 🔔",
]
_TECH_SOCIAL_PROOF = [
    "Được review bởi 5 tech reviewer lớn — đánh giá 9/10",
    "10K+ đơn trong tháng đầu launch — kỷ lục brand",
    "4.8⭐ / 3,500 review — top 1 bán chạy tech accessories",
    "Được recommend bởi dân công nghệ — không phải người thường",
]
_TECH_TRANSFORMATION = [
    "Trước: Cáp hỏng mỗi 2 tháng. Sau: 1 năm vẫn mới 💪",
    "Không còn lo hết pin khi ra ngoài — game changer thật sự",
    "Setup desk tôi trông professional hơn 300% nhờ cái này 🖥️",
    "Từ ngày có cái này — không bao giờ dùng bao bì cũ nữa",
]
_TECH_AUTHENTICITY = [
    "Tôi hay mua đồ tech — đây là cái đáng mua nhất 6 tháng qua",
    "Không sponsored — tôi tự bỏ tiền mua để test trước khi chia sẻ",
    "Thật ra tôi hoài nghi — nhưng sau 3 tháng dùng tôi đã thay đổi ý kiến",
    "Dev team của tôi mua hết 10 cái sau khi thấy tôi dùng",
]
_TECH_IDENTITY = [
    "Người dùng tech thông minh biết: rẻ hơn không phải lúc nào cũng tốt hơn",
    "Setup đẹp = mindset làm việc tốt hơn = kết quả tốt hơn 🚀",
    "Bạn dùng thiết bị công nghệ 10h/ngày — xứng đáng dùng đồ tốt",
    "Đầu tư vào công cụ làm việc = đầu tư vào năng suất của chính bạn",
]

# ── PET PRODUCTS ─────────────────────────────────────────────────────────────
_PET_CURIOSITY = [
    "Con chó của tôi đã thay đổi sau khi dùng cái này 🐕 — xem phản ứng",
    "Thú cưng của bạn có xứng đáng với điều này không? 🐱",
    "Tại sao boss nhà tôi lại thích cái này hơn đồ chơi đắt tiền? 🤔",
    "Bí quyết để thú cưng ngoan hơn, vui hơn — đây 🐾",
]
_PET_FOMO = [
    "Set quà Tết cho boss — hàng sắp hết 🐾",
    "Flash deal pet supplies — kết thúc 23:59 đêm nay ⏰",
    "Hàng nhập từ Hàn — batch này hết không restock sớm 🇰🇷",
]
_PET_SOCIAL_PROOF = [
    "Được khuyên bởi 200+ bác sĩ thú y Việt Nam",
    "5,000+ boss đang dùng — rating 4.9⭐",
    "Viral trong cộng đồng pet Việt — #1 bestseller tháng này",
]
_PET_TRANSFORMATION = [
    "Boss từ lười biếng → chạy nhảy đùa giỡn sau 2 tuần dùng",
    "Lông boss từ xỉn, rụng → bóng mượt trong 1 tháng 🌟",
    "Boss từ hay bỏ ăn → ăn hết sạch mỗi bữa — mình cũng ngạc nhiên",
]
_PET_AUTHENTICITY = [
    "Boss nhà tôi khó tính lắm — nhưng cái này được chấp thuận ngay lần đầu",
    "Tôi mua vì yêu boss — không phải vì được trả tiền",
    "3 boss ở nhà — cả 3 đều chấp nhận cái này. Hiếm lắm",
]
_PET_IDENTITY = [
    "Thú cưng của bạn tin tưởng bạn hoàn toàn — đừng phụ lòng họ 🐾",
    "Boss nhà bạn xứng đáng với điều tốt nhất trong tầm giá",
    "Yêu boss = chăm sóc đúng cách, đúng sản phẩm 💕",
]

# ── MUSIC MOODS BY CATEGORY ────────────────────────────────────────────────────
_CATEGORY_MUSIC = {
    "fashion":     "trendy_pop",
    "beauty":      "luxury_elegant",
    "health":      "corporate_smooth",
    "home":        "lofi_chill",
    "food":        "cute_pop",
    "tech":        "phonk_street",
    "pet":         "cute_pop",
    "default":     "trendy_pop",
}

# ── COLOR PSYCHOLOGY ──────────────────────────────────────────────────────────
_CATEGORY_COLORS = {
    "fashion_women": "gradient_pink_red",
    "fashion_men":   "gradient_navy_blue",
    "beauty":        "gradient_rose_gold",
    "health":        "gradient_green_teal",
    "home":          "gradient_warm_amber",
    "food":          "gradient_orange_red",
    "tech":          "gradient_dark_blue",
    "pet":           "gradient_purple_lavender",
    "children":      "gradient_yellow_orange",
    "baby":          "gradient_soft_blue",
    "default":       "gradient_pink_red",
}


# ══════════════════════════════════════════════════════════════════════════════
#  URGENCY + LOOP
# ══════════════════════════════════════════════════════════════════════════════

_URGENCY_LINES = [
    "⏰ Giá này chỉ hôm nay — đặt ngay trước khi hết",
    "🔥 Đang flash sale — {n} người đang xem sản phẩm này",
    "⚡ Kho còn ít — ai đặt trước người đó có",
    "💥 Giảm thêm {pct}% khi dùng code: VIRAL2026",
    "🚨 {n} người vừa đặt trong 1 giờ qua — không đùa",
    "⌛ Sale kết thúc lúc 23:59 đêm nay — tranh thủ",
]

_LOOP_HOOKS = [
    "Và đây là lý do không ai bỏ qua được cái này... 👀",
    "Xem lại từ đầu — bạn sẽ thấy điều tôi đã miss 🔄",
    "Còn 1 điều tôi chưa nói về sản phẩm này... 💬",
    "Phần hay nhất ở ngay đầu video — xem lại nhé 🔁",
    "Bạn có để ý điều này ở giây đầu tiên không? 👁️",
]


# ══════════════════════════════════════════════════════════════════════════════
#  PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

_CATEGORY_MAP = {
    "fashion": {
        "curiosity": _FASHION_CURIOSITY, "fomo": _FASHION_FOMO,
        "social": _FASHION_SOCIAL_PROOF, "transform": _FASHION_TRANSFORMATION,
        "auth": _FASHION_AUTHENTICITY, "identity": _FASHION_IDENTITY,
    },
    "beauty": {
        "curiosity": _BEAUTY_CURIOSITY, "fomo": _BEAUTY_FOMO,
        "social": _BEAUTY_SOCIAL_PROOF, "transform": _BEAUTY_TRANSFORMATION,
        "auth": _BEAUTY_AUTHENTICITY, "identity": _BEAUTY_IDENTITY,
    },
    "health": {
        "curiosity": _HEALTH_CURIOSITY, "fomo": _HEALTH_FOMO,
        "social": _HEALTH_SOCIAL_PROOF, "transform": _HEALTH_TRANSFORMATION,
        "auth": _HEALTH_AUTHENTICITY, "identity": _HEALTH_IDENTITY,
    },
    "home": {
        "curiosity": _HOME_CURIOSITY, "fomo": _HOME_FOMO,
        "social": _HOME_SOCIAL_PROOF, "transform": _HOME_TRANSFORMATION,
        "auth": _HOME_AUTHENTICITY, "identity": _HOME_IDENTITY,
    },
    "food": {
        "curiosity": _FOOD_CURIOSITY, "fomo": _FOOD_FOMO,
        "social": _FOOD_SOCIAL_PROOF, "transform": _FOOD_TRANSFORMATION,
        "auth": _FOOD_AUTHENTICITY, "identity": _FOOD_IDENTITY,
    },
    "tech": {
        "curiosity": _TECH_CURIOSITY, "fomo": _TECH_FOMO,
        "social": _TECH_SOCIAL_PROOF, "transform": _TECH_TRANSFORMATION,
        "auth": _TECH_AUTHENTICITY, "identity": _TECH_IDENTITY,
    },
    "pet": {
        "curiosity": _PET_CURIOSITY, "fomo": _PET_FOMO,
        "social": _PET_SOCIAL_PROOF, "transform": _PET_TRANSFORMATION,
        "auth": _PET_AUTHENTICITY, "identity": _PET_IDENTITY,
    },
}


def _lib(category: str) -> dict:
    return _CATEGORY_MAP.get(category, _CATEGORY_MAP["fashion"])


def build_emotional_package(
    product_name: str,
    category: str = "fashion",
    gender: str = "women",
    price: str = "",
) -> EmotionalPackage:
    """
    Tạo gói cảm xúc đầy đủ cho 1 sản phẩm.
    category: fashion | beauty | health | home | food | tech | pet
    """
    lib = _lib(category)

    # Primary / secondary trigger theo category
    trigger_map = {
        "fashion": ("fomo", "identity"),
        "beauty":  ("transformation", "social"),
        "health":  ("transformation", "authenticity"),
        "home":    ("curiosity", "social"),
        "food":    ("curiosity", "authenticity"),
        "tech":    ("social", "fomo"),
        "pet":     ("authenticity", "identity"),
    }
    primary, secondary = trigger_map.get(category, ("fomo", "social"))

    # Urgency với số ngẫu nhiên thật
    urgency = random.choice(_URGENCY_LINES).format(
        n=random.randint(120, 1800),
        pct=random.choice([10, 15, 20, 25, 30]),
    )

    # Color key
    color_key = f"fashion_{gender}" if category == "fashion" else category
    color = _CATEGORY_COLORS.get(color_key, _CATEGORY_COLORS["default"])

    # 3 hook variants để A/B test
    pool = lib["curiosity"] + lib["fomo"]
    random.shuffle(pool)
    ab_hooks = pool[:3]

    return EmotionalPackage(
        primary_trigger    = primary,
        secondary_trigger  = secondary,
        hook_curiosity     = random.choice(lib["curiosity"]),
        hook_fomo          = random.choice(lib["fomo"]),
        social_proof_line  = random.choice(lib["social"]),
        transformation_line= random.choice(lib["transform"]),
        authenticity_story = random.choice(lib["auth"]),
        identity_line      = random.choice(lib["identity"]),
        urgency_line       = urgency,
        loop_hook          = random.choice(_LOOP_HOOKS),
        emotional_music    = _CATEGORY_MUSIC.get(category, "trendy_pop"),
        color_psychology   = color,
        ab_hooks           = ab_hooks,
    )
