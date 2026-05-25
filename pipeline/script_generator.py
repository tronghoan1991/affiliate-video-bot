"""
pipeline/script_generator.py — AI Script Generator
====================================================
Tạo script reviewer thực thụ — đủ nội dung, cảm xúc, chuyên nghiệp.
Cấu trúc: Hook → Unbox → Chi tiết → Try-on/Demo → Cảm nhận → So sánh → CTA

Không cần AI API — dùng template system thông minh + emotional engine.
"""
import random
from dataclasses import dataclass, field
from typing import List

from pipeline.emotional_engine import EmotionalPackage


@dataclass
class VideoScript:
    """Script hoàn chỉnh cho video affiliate."""
    title:        str
    total_scenes: int
    scenes:       List[dict]   # [{scene_type, text, duration_hint, shot_type}]
    full_text:    str           # Toàn bộ script để TTS
    duration_est: float         # Ước tính thời gian (giây)
    caption:      str           # Caption cho TikTok/Shopee


# ══════════════════════════════════════════════════════════════════════════════
# SCENE TEMPLATES — Theo ngành hàng
# ══════════════════════════════════════════════════════════════════════════════

def _scene(scene_type: str, shot: str, text: str, duration: float = 3.0) -> dict:
    return {"scene_type": scene_type, "shot_type": shot,
            "text": text, "duration_hint": duration}


SCRIPT_TEMPLATES = {

# ─────────────────────────────────────────────────────────────────────────────
"fashion": {
    "hooks": [
        "Tôi đã thử {count} bộ quần áo tuần này — và chỉ có MỘT cái khiến tôi không thể bỏ xuống.",
        "Bạn có bao giờ mặc một thứ gì đó lần đầu mà cảm thấy ngay đây là của mình không?",
        "Cái này tôi order vì thấy rẻ — nhận hàng xong tôi quên luôn giá tiền.",
        "POV: Bạn tìm được sản phẩm mà ai nhìn cũng hỏi mua ở đâu.",
        "Tôi không định quay video này — nhưng sau khi mặc thì tôi PHẢI chia sẻ.",
    ],
    "unbox": [
        "Đây rồi! Package về đến tay rồi. Nhìn cái đóng gói thôi đã thấy chỉn chu — bọc kỹ, thơm nữa.",
        "Hàng về nhé! Mở ra xem — vải cầm trên tay thôi đã thấy khác, không phải loại rẻ tiền.",
        "Okay package mở ra rồi — màu thực ngoài đời đẹp hơn ảnh nhiều, mình bị bất ngờ thật sự.",
    ],
    "detail_shots": [
        "Nhìn kỹ vào đây — đường may thẳng tắp, không có chỉ thừa, không có lỗi vải. Chất lượng ổn áp.",
        "Cận cảnh vải nhé — {material_feel}. Sờ vào thấy ngay loại vải này xịn hơn nhiều so với mức giá.",
        "Chi tiết quan trọng mà ảnh không thấy được — {unique_detail}. Đây là cái làm mình thích nhất.",
        "Xem đường viền này — hoàn thiện rất kỹ. Rõ ràng là có đầu tư vào khâu sản xuất.",
    ],
    "wearing": [
        "Mặc thử vào xem nhé. Ôi — {fit_feeling}. Tôn dáng mà vẫn thoải mái.",
        "Bước ra khỏi phòng với cái này — cảm giác {confidence_feeling}. Không cần giải thích thêm.",
        "Thử mặc theo nhiều cách — {style_versatility}. Một cái mà phối được nhiều kiểu.",
    ],
    "honest_review": [
        "Nói thật nhé — điểm tôi thích nhất là {best_point}. Điểm cần cải thiện là {weak_point} — nhưng so với giá thì không đáng kể.",
        "Tôi đã dùng {comparison} trước đây, và cái này {honest_comparison}. Không phải khen cho có.",
        "Sau {usage_time} dùng — {result}. Đây là kết quả thật, không filter, không chỉnh sửa.",
    ],
    "cta": [
        "Link mình để trong bio — giá {price}, freeship, đổi trả 7 ngày. Đặt ngay kẻo hết size!",
        "Nếu bạn đang tìm {product_benefit} — đây là cái mình recommend 100%. Link dưới nhé!",
        "Comment '{trigger_word}' mình sẽ gửi link thẳng vào DM. Giá đang flash sale hôm nay thôi!",
    ],
},

# ─────────────────────────────────────────────────────────────────────────────
"beauty": {
    "hooks": [
        "Tôi đã dùng {product_name} được {days} ngày — và đây là da tôi bây giờ.",
        "Bác sĩ da liễu của tôi hỏi tôi đang dùng gì — câu trả lời là {product_name}.",
        "Có {count} người tag tôi hỏi da tôi làm gì. Bí quyết chỉ là cái này thôi.",
        "Tôi không tin serum giá rẻ cho đến khi thử cái này.",
        "7 ngày dùng thử — xem kết quả thật không chỉnh sửa nhé.",
    ],
    "unbox": [
        "Sản phẩm về rồi nhé! Texture nhìn đã thấy sang — không quá đặc, không quá lỏng.",
        "Mở ra xem — mùi {scent_desc}, dễ chịu không hắc. Texture như {texture_desc}.",
        "Packaging đẹp, không rẻ tiền chút nào. Nhìn là biết có đầu tư vào sản phẩm.",
    ],
    "detail_shots": [
        "Nhỏ 1-2 giọt lên tay — nhìn texture này, thấm nhanh, không nhờn, không sticky.",
        "Cận cảnh thành phần — {key_ingredient}. Đây là thứ làm nên sự khác biệt của sản phẩm này.",
        "Apply lên da — serum thấm trong {absorb_time}. Không phải chờ lâu mới bôi tiếp được.",
        "Nhìn da ngay sau khi apply — {immediate_effect}. Kết quả thấy liền, không cần chờ tuần.",
    ],
    "wearing": [
        "Skincare routine của mình — bước này apply sau toner, trước kem dưỡng. Thứ tự quan trọng lắm.",
        "Da mình sau {days} ngày dùng đều đặn — {skin_result}. Không filter, ánh sáng tự nhiên.",
        "Before và after đây nhé — {before_state} vs bây giờ. Cùng góc chụp, cùng ánh sáng.",
    ],
    "honest_review": [
        "Ưu điểm: {pros}. Nhược điểm: {cons}. Overall thì mình rate {rating}/10.",
        "Mình đã thử {comparison_product} — {honest_comparison_beauty}. Cái này win ở điểm {win_point}.",
        "Dùng {usage_time_beauty} — {skin_change}. Đây là kết quả thật của mình.",
    ],
    "cta": [
        "Link trong bio — {price}, có kèm quà tặng hôm nay. Mua 2 được giảm thêm nhé!",
        "Ai đang khổ sở với {skin_problem} — thử cái này đi, mình dám đảm bảo.",
        "Đặt hôm nay freeship toàn quốc. Comment '{trigger_word_beauty}' để mình tag link!",
    ],
},

# ─────────────────────────────────────────────────────────────────────────────
"health": {
    "hooks": [
        "Tôi uống {product_name} được {days} ngày — đây là thay đổi tôi nhận ra.",
        "Bạn có đang bỏ qua thứ cơ thể cần nhất không? Tôi đã bỏ qua trong {years} năm.",
        "Sau {age_trigger} — cơ thể tôi bắt đầu ra tín hiệu. Và đây là cách tôi lắng nghe nó.",
        "Tôi hoài nghi về supplement cho đến khi thử cái này {months} tháng liên tục.",
    ],
    "unbox": [
        "Sản phẩm về rồi — mở hộp ra xem. Đóng gói kỹ, seal an toàn, có date rõ ràng.",
        "Mùi {health_scent} — {taste_desc}. Không có mùi khó chịu như nhiều loại khác.",
        "Thành phần in rõ trên hộp — {ingredients}. Mình luôn check kỹ trước khi uống.",
    ],
    "detail_shots": [
        "Cận cảnh viên thuốc — {form_desc}. Kích thước vừa, dễ nuốt, không cần chia.",
        "Thành phần chính: {key_health_ingredient}. Hàm lượng đủ để có tác dụng thật sự.",
        "QR code truy xuất nguồn gốc — quét ra được thông tin đầy đủ. Minh bạch.",
        "Certificate trên hộp — {cert_info}. Sản phẩm đã qua kiểm định.",
    ],
    "wearing": [
        "Routine của mình — uống {dose} vào {timing}. Uống với nước ấm để hấp thụ tốt hơn.",
        "Sau {result_timeframe} uống đều — {health_result}. Không phải placebo — tôi đã kiểm tra.",
        "So sánh trước và sau {health_timeframe} — {health_before} vs {health_after}.",
    ],
    "honest_review": [
        "Điểm tôi thích: {health_pros}. Lưu ý: {health_note}. Không phải thuốc — là thực phẩm bổ sung.",
        "Tôi đã thử {health_comparison} — {health_honest_compare}. Cái này phù hợp hơn vì {health_reason}.",
        "Hiệu quả thật sự sau {test_period}: {real_result}. Không phóng đại.",
    ],
    "cta": [
        "Giá {price} cho {duration_supply} — chia ra mỗi ngày chỉ {daily_cost}. Đáng đầu tư cho sức khỏe.",
        "Link bio — order hôm nay tặng thêm {gift}. Freeship đơn từ {min_order}.",
        "Comment '{trigger_health}' để mình gửi thêm thông tin chi tiết cho bạn!",
    ],
},

# ─────────────────────────────────────────────────────────────────────────────
"home": {
    "hooks": [
        "Căn phòng tôi thay đổi hoàn toàn sau khi có cái này — không tốn nhiều tiền.",
        "Bạn đang tìm cách làm nhà đẹp hơn với ngân sách ít? Xem hết video này.",
        "Cái này tôi order vì tiện — nhưng hóa ra nó thay đổi cả thói quen sống của tôi.",
    ],
    "unbox": [
        "Hàng về rồi — đóng gói chắc chắn, không bị vỡ hay trầy xước gì.",
        "Mở ra xem — chất liệu {home_material}, cầm trên tay thấy {home_quality_feel}.",
        "Kích thước thực tế — đúng như mô tả, không bị nhỏ hơn ảnh như nhiều shop khác.",
    ],
    "detail_shots": [
        "Chi tiết sản phẩm — {home_detail}. Hoàn thiện tốt, không có góc cạnh sắc.",
        "Cận cảnh chất liệu — {home_material_close}. Bền, dễ lau chùi, không bám bụi.",
        "Xem {home_unique_feature} — đây là điểm khác biệt so với các sản phẩm tương tự.",
    ],
    "wearing": [
        "Lắp đặt rất nhanh — chỉ mất {setup_time}. Không cần công cụ đặc biệt.",
        "Đặt vào góc {location} — nhìn ngay thấy {home_effect}. Không gian thay đổi hẳn.",
        "Thử nghiệm thực tế — {home_test}. Hoạt động đúng như quảng cáo.",
    ],
    "honest_review": [
        "Dùng {home_usage_time} — {home_result}. Chất lượng vẫn như ngày đầu.",
        "So với {home_comparison} — {home_honest}. Giá tốt hơn, chất lượng tương đương.",
        "Nếu nhà bạn cần {home_need} — đây là lựa chọn đáng tiền nhất mình từng thấy.",
    ],
    "cta": [
        "Giá {price}, freeship. Đặt hôm nay nhận trong {delivery_time}.",
        "Link trong bio. Mua 2 tặng thêm {home_gift}. Số lượng có hạn!",
        "Comment '{trigger_home}' để mình tư vấn thêm kích thước phù hợp với nhà bạn!",
    ],
},

# ─────────────────────────────────────────────────────────────────────────────
"food": {
    "hooks": [
        "Tôi đã ăn thử {product_name} — và tôi hiểu tại sao nó viral.",
        "Đồ ăn vặt này tôi mua vì tò mò — hóa ra không thể dừng lại được.",
        "Bạn đang tìm snack ngon mà không tội lỗi? Xem hết này đi.",
    ],
    "unbox": [
        "Package về rồi — đóng gói kỹ, seal vẫn nguyên, tươi mới.",
        "Mở ra — mùi {food_scent} bay ra ngay. {first_smell_reaction}.",
        "Nhìn sản phẩm thật — màu sắc {food_color}, {food_visual_appeal}.",
    ],
    "detail_shots": [
        "Cận cảnh texture — {food_texture}. Nhìn là thấy ngon rồi.",
        "Thành phần trên bao bì — {food_ingredient}. Không có chất bảo quản lạ.",
        "Kích thước portion — {food_portion}. Vừa đủ cho {food_serve_for}.",
    ],
    "wearing": [
        "Thử ngay đây — {taste_reaction}. {flavor_detail}.",
        "Texture khi ăn — {food_eat_texture}. {mouthfeel_desc}.",
        "Ăn hết 1 cái rồi lấy cái thứ 2 — {addictive_comment}.",
    ],
    "honest_review": [
        "Ngon thật sự — điểm {food_rating}/10. {food_honest_opinion}.",
        "So với {food_comparison} — {food_compare_result}. Cái này thắng ở {food_win}.",
        "Phù hợp cho {food_occasion}. Không phù hợp nếu bạn {food_not_for}.",
    ],
    "cta": [
        "Giá {price} được {quantity} — {food_value_calc}. Quá hời!",
        "Link bio — freeship, giao nhanh {food_delivery}. Order ngay kẻo hết!",
        "Comment '{trigger_food}' để mình gửi combo ưu đãi cho bạn!",
    ],
},

# ─────────────────────────────────────────────────────────────────────────────
"baby": {
    "hooks": [
        "Mẹ ơi! Cái này tôi đã không mua sớm hơn — sai lầm lớn nhất của tôi.",
        "Bé nhà tôi từ khi có {product_name} — thay đổi hoàn toàn.",
        "Review honest cho các mẹ — không phải sponsor, tự bỏ tiền mua.",
    ],
    "unbox": [
        "Hàng về rồi mẹ ơi — mở ra xem. An toàn không có cạnh sắc, nhựa không mùi.",
        "Chất liệu {baby_material} — mềm mại, không kích ứng da bé.",
        "Size thực tế — đúng như mô tả, phù hợp cho bé {baby_age}.",
    ],
    "detail_shots": [
        "Kiểm tra độ an toàn — {baby_safety_check}. Quan trọng nhất với đồ em bé.",
        "Cận cảnh chất liệu — {baby_material_detail}. Đạt tiêu chuẩn {baby_cert}.",
        "Chi tiết thiết kế — {baby_design_feature}. Dành riêng cho bé, không phải thu nhỏ đồ người lớn.",
    ],
    "wearing": [
        "Thử cho bé — {baby_reaction}. Bé không khó chịu là tín hiệu tốt nhất rồi.",
        "Dùng thực tế — {baby_practical_use}. {baby_ease_of_use}.",
        "Sau {baby_usage_time} dùng — {baby_result}. Đáng tiền lắm mẹ ơi.",
    ],
    "honest_review": [
        "Mình rate {baby_rating}/10. Thích vì {baby_pros}. Lưu ý {baby_note}.",
        "So với {baby_comparison} — {baby_honest_compare}. Cái này {baby_advantage}.",
        "Recommend cho bé từ {baby_age_range}. Không phù hợp nếu {baby_not_suitable}.",
    ],
    "cta": [
        "Giá {price} — đầu tư nhỏ cho bé yêu. Link bio, freeship toàn quốc!",
        "Order hôm nay tặng thêm {baby_gift}. Số lượng giới hạn mẹ ơi!",
        "Comment '{trigger_baby}' để mình tư vấn size và màu phù hợp cho bé nhé!",
    ],
},

# ─────────────────────────────────────────────────────────────────────────────
"sports": {
    "hooks": [
        "Set gym này đã thay đổi cách tôi tập — không phải vì đẹp mà vì {sport_function}.",
        "Tôi đã thử {count_sports} bộ đồ thể thao — đây là cái cuối cùng tôi cần.",
        "Review thật sau {training_sessions} buổi tập với {product_name}.",
    ],
    "unbox": [
        "Hàng về — chất vải cầm trên tay thấy {sport_fabric_feel}. Không phải loại nhanh xả.",
        "Màu thực đẹp hơn ảnh — {sport_color_comment}. Co giãn 4 chiều tốt.",
        "Kiểm tra đường may — {sport_stitching}. Quan trọng khi vận động mạnh.",
    ],
    "detail_shots": [
        "Công nghệ vải — {sport_tech}. Thấm mồ hôi nhanh, không dính da.",
        "Cận cảnh waistband/cổ áo — {sport_detail}. Thoải mái khi tập cường độ cao.",
        "Túi và chi tiết — {sport_feature}. Tiện dụng hơn nhiều loại khác.",
    ],
    "wearing": [
        "Mặc vào tập thử — {sport_wearing_feel}. {sport_movement_comment}.",
        "Sau {sport_session_length} tập — {sweat_performance}. Vải vẫn {fabric_state}.",
        "Thử các động tác — {sport_flexibility}. Không bị kéo căng hay tuột.",
    ],
    "honest_review": [
        "Sau {sport_weeks} tuần tập đều — {sport_durability}. Chất lượng giữ tốt.",
        "So với {sport_comparison} giá tương đương — {sport_honest}. Cái này {sport_win_point}.",
        "Rating {sport_rating}/10. Recommend cho {sport_target}.",
    ],
    "cta": [
        "Giá {price} — {sport_value}. Link bio, freeship, đủ size S đến XL!",
        "Flash sale hôm nay thôi — giảm thêm {sport_discount}. Order ngay!",
        "Comment '{trigger_sport}' mình gửi link size chart chi tiết!",
    ],
},

}  # End SCRIPT_TEMPLATES


# ══════════════════════════════════════════════════════════════════════════════
# FILLER DATA — Điền vào template
# ══════════════════════════════════════════════════════════════════════════════

_FILLERS = {
    # Fashion
    "count": ["5", "7", "10", "12"],
    "material_feel": ["mềm mượt như lụa", "cotton dày dặn", "vải linen thoáng mát", "nỉ dày, ấm"],
    "unique_detail": ["nút bấm đặc biệt", "đường viền phối màu", "khóa kéo ẩn", "tay áo có chi tiết riêng"],
    "fit_feeling": ["vừa vặn như may đo", "thoải mái không bó", "tôn dáng rõ rệt"],
    "confidence_feeling": ["tự tin hơn 200%", "như một người khác hoàn toàn", "sẵn sàng ra đường ngay"],
    "style_versatility": ["đi cafe, đi làm, đi chơi đều được", "phối với jeans, chân váy hay quần âu"],
    "best_point": ["chất vải", "form dáng", "đường may tinh tế", "màu đẹp hơn ảnh"],
    "weak_point": ["túi hơi nhỏ", "cần ủi kỹ hơn", "màu đậm hơn ảnh chút xíu"],
    "comparison": ["hàng cùng tầm giá", "hàng Taobao trước đây", "thương hiệu nội địa khác"],
    "honest_comparison": ["chất lượng vượt trội hơn hẳn", "ngang ngửa nhưng giá rẻ hơn 40%"],
    "usage_time": ["2 tuần", "1 tháng", "3 tuần"],
    "result": ["vải không phai màu, không xù lông", "đường may vẫn chắc, dáng giữ nguyên"],
    "trigger_word": ["muốn", "link", "mua", "info"],

    # Beauty
    "days": ["7", "14", "21", "30"],
    "scent_desc": ["nhẹ nhàng, không gắt", "hoa tươi tinh tế", "thanh mát dễ chịu"],
    "texture_desc": ["nước nhẹ", "gel mỏng", "serum lỏng", "emulsion mịn"],
    "key_ingredient": ["Vitamin C 15%", "Niacinamide 10%", "Retinol 0.3%", "Hyaluronic Acid"],
    "absorb_time": ["10-15 giây", "dưới 20 giây", "30 giây"],
    "immediate_effect": ["da căng hơn ngay", "ẩm mượt rõ rệt", "tone đều hơn trông thấy"],
    "skin_result": ["da sáng hơn 2 tông", "mụn giảm rõ rệt", "lỗ chân lông nhỏ lại"],
    "rating": ["8.5", "9", "8", "9.5"],
    "skin_problem": ["da khô", "mụn", "thâm nám", "da nhờn", "lỗ chân lông to"],
    "trigger_word_beauty": ["da đẹp", "muốn", "review", "link"],

    # Health
    "years": ["2", "3", "5"],
    "months": ["3", "6", "2"],
    "health_scent": ["thảo mộc nhẹ", "trái cây tự nhiên", "không mùi"],
    "taste_desc": ["không đắng", "vị hơi ngọt nhẹ", "trung tính, dễ uống"],
    "ingredients": ["không chất bảo quản", "nguồn gốc tự nhiên", "không gluten"],
    "key_health_ingredient": ["Collagen Peptide 5000mg", "Vitamin D3 2000IU", "Omega-3 EPA/DHA"],
    "form_desc": ["viên nang nhỏ vừa", "dạng bột dễ pha", "viên sủi tan nhanh"],
    "cert_info": ["FDA approved", "GMP certified", "ISO 22000"],
    "health_result": ["ngủ ngon hơn rõ rệt", "khớp bớt đau", "da căng hơn", "năng lượng tốt hơn"],
    "result_timeframe": ["2 tuần", "1 tháng", "3 tuần"],
    "daily_cost": ["5k", "7k", "10k"],
    "min_order": ["200k", "299k", "300k"],
    "gift": ["quà tặng kèm", "thêm 1 hộp sample", "voucher giảm tiếp"],
    "trigger_health": ["khỏe", "tư vấn", "mua"],

    # Home
    "home_material": ["inox 304", "gỗ tự nhiên", "nhựa ABS cao cấp", "vải canvas dày"],
    "home_quality_feel": ["chắc tay", "nhẹ mà bền", "cao cấp hơn dự tính"],
    "home_detail": ["góc bo tròn an toàn", "bề mặt chống trầy", "thiết kế tối giản"],
    "home_material_close": ["không gỉ, không mốc", "dễ vệ sinh", "kháng khuẩn tự nhiên"],
    "home_unique_feature": ["khả năng chịu tải cao", "thiết kế modular", "công nghệ khóa đặc biệt"],
    "setup_time": ["5 phút", "10 phút", "3 phút"],
    "location": ["góc phòng khách", "bàn làm việc", "phòng tắm", "nhà bếp"],
    "home_effect": ["gọn gàng, ngăn nắp hơn hẳn", "thẩm mỹ lên rõ rệt", "tiết kiệm diện tích"],
    "home_usage_time": ["1 tháng", "2 tháng", "3 tuần"],
    "home_result": ["vẫn như mới", "không cong vênh, không xỉn màu"],
    "home_comparison": ["hàng cùng loại trên thị trường", "hàng nội địa Trung"],
    "home_honest": ["chất lượng ngang nhưng giá tốt hơn nhiều"],
    "home_need": ["tổ chức không gian", "decor phòng", "giải pháp lưu trữ"],
    "delivery_time": ["2-3 ngày", "ngày hôm sau", "1-2 ngày"],
    "home_gift": ["1 set phụ kiện", "voucher giảm tiếp"],
    "trigger_home": ["tư vấn", "muốn", "link", "kích thước"],

    # Food
    "food_scent": ["thơm nức", "hương trái cây", "béo ngậy"],
    "first_smell_reaction": ["Trời ơi ngửi thôi đã thấy ngon", "Mùi này quen lắm", "Thơm hơn mình nghĩ"],
    "food_color": ["đẹp như ảnh", "vàng óng tự nhiên", "tươi sáng"],
    "food_visual_appeal": ["nhìn là thấy thèm rồi", "trình bày đẹp", "kích thước vừa phải"],
    "food_texture": ["giòn tan", "mềm mại", "dai vừa phải", "xốp nhẹ"],
    "food_ingredient": ["không MSG", "không chất bảo quản", "từ nguyên liệu tự nhiên"],
    "food_portion": ["vừa cho 1 người", "đủ ăn cả ngày", "share được cho 2-3 người"],
    "food_serve_for": ["1 người ăn vặt", "cả gia đình", "2-3 bạn"],
    "taste_reaction": ["Ôi ngon thật!", "Vị này quen mà vẫn bất ngờ", "Đúng như kỳ vọng"],
    "flavor_detail": ["Vị ngọt vừa, không ngấy", "Vị mặn nhẹ, ăn hoài không chán", "Cân bằng giữa mặn và ngọt"],
    "food_eat_texture": ["giòn đều từ đầu đến cuối", "tan trong miệng", "nhai thú vị"],
    "mouthfeel_desc": ["Không bị ngấy dù ăn nhiều", "Sạch miệng sau khi ăn"],
    "addictive_comment": ["Lấy thêm cái nữa không cưỡng được", "Mở ra là ăn hết luôn"],
    "food_rating": ["9", "8.5", "9.5"],
    "food_honest_opinion": ["Ngon hơn mình nghĩ nhiều", "Xứng đáng với giá tiền"],
    "food_comparison": ["snack cùng loại ở siêu thị", "hàng ngoại cùng tầm giá"],
    "food_compare_result": ["ngon không thua, giá rẻ hơn"],
    "food_win": ["hương vị tự nhiên hơn", "không bị ngọt gắt", "portion hợp lý"],
    "food_occasion": ["xem phim", "làm việc", "picnic", "đãi khách"],
    "food_not_for": ["kiêng đường", "dị ứng gluten"],
    "quantity": ["5 gói", "10 cái", "1 hộp 12 viên"],
    "food_value_calc": ["mỗi ngày chỉ tốn 5-10k", "rẻ hơn ra ngoài mua"],
    "food_delivery": ["hỏa tốc 2h", "2-3 ngày"],
    "trigger_food": ["muốn thử", "order", "link"],

    # Baby
    "baby_material": ["cotton organic", "silicone food-grade", "vải bamboo"],
    "baby_age": ["0-6 tháng", "6-12 tháng", "1-3 tuổi"],
    "baby_safety_check": ["không BPA, không phthalate", "đạt tiêu chuẩn EN71", "kiểm định OEKO-TEX"],
    "baby_cert": ["OEKO-TEX", "EN71", "ASTM F963"],
    "baby_material_detail": ["siêu mềm, không gây kích ứng", "kháng khuẩn tự nhiên"],
    "baby_design_feature": ["thiết kế ergonomic cho tay bé", "màu sắc kích thích thị giác"],
    "baby_reaction": ["bé thích ngay, không quấy", "bé cầm không chịu bỏ"],
    "baby_practical_use": ["dễ vệ sinh, bỏ máy rửa bát được", "nhỏ gọn mang theo tiện"],
    "baby_ease_of_use": ["Mẹ một tay bế bé, một tay dùng được"],
    "baby_usage_time": ["2 tuần", "1 tháng"],
    "baby_result": ["bé ăn ngon hơn", "bé ngủ ngon hơn", "bé vui và an toàn"],
    "baby_rating": ["9.5", "9", "10"],
    "baby_pros": ["an toàn tuyệt đối", "chất lượng tốt", "tiện lợi cho mẹ"],
    "baby_note": ["vệ sinh thường xuyên", "kiểm tra thường xuyên theo độ tuổi"],
    "baby_comparison": ["hàng ngoại cùng loại", "sản phẩm khác cùng tầm giá"],
    "baby_honest_compare": ["chất lượng ngang, giá rẻ hơn 30-40%"],
    "baby_advantage": ["an toàn hơn, thiết kế phù hợp bé Việt hơn"],
    "baby_age_range": ["0 đến 24 tháng", "3 đến 36 tháng"],
    "baby_not_suitable": ["bé đã quá tuổi khuyến cáo"],
    "baby_gift": ["túi đựng đồ em bé", "set phụ kiện kèm"],
    "trigger_baby": ["bé yêu", "mua", "tư vấn size", "link"],

    # Sports
    "count_sports": ["8", "10", "6"],
    "training_sessions": ["10", "15", "20"],
    "sport_fabric_feel": ["mềm mượt, co giãn tốt", "nhẹ như không mặc", "thoáng khí rõ rệt"],
    "sport_color_comment": ["không bị nhợt hay lố như ảnh", "màu thật rất ổn"],
    "sport_stitching": ["may flatlock không tạo vết hằn", "đường may chắc chắn"],
    "sport_tech": ["Dri-Fit thoát ẩm", "4-way stretch", "Quick-dry"],
    "sport_detail": ["không bị cào da", "elastic vừa đủ không siết"],
    "sport_feature": ["túi điện thoại vừa iPhone 15", "phản quang an toàn"],
    "sport_wearing_feel": ["thoải mái như mặc pyjama", "không bị bó hay kéo"],
    "sport_movement_comment": ["squat sâu không bị tuột", "chạy không bị phồng"],
    "sport_session_length": ["1 tiếng tập", "buổi tập 90 phút"],
    "sweat_performance": ["thấm mồ hôi nhanh, khô lại cũng nhanh"],
    "fabric_state": ["khô thoáng, không dính da", "nhẹ, không nặng dù đổ nhiều mồ hôi"],
    "sport_flexibility": ["squat, deadlift, burpees đều ổn hết"],
    "sport_weeks": ["4", "6", "8"],
    "sport_durability": ["vải không phai, không xù", "co giãn vẫn tốt như mới"],
    "sport_comparison": ["hàng cùng phân khúc giá", "thương hiệu nội địa khác"],
    "sport_honest": ["chất lượng không thua kém gì"],
    "sport_win_point": ["độ thoáng khí", "form giữ tốt hơn", "giá tốt hơn nhiều"],
    "sport_rating": ["8.5", "9", "9.5"],
    "sport_target": ["người tập gym", "runner", "yoga", "người tập thể thao nhà"],
    "sport_discount": ["10%", "15%", "20%"],
    "trigger_sport": ["gym", "link", "size chart", "muốn"],
}


def _fill(template: str, info: dict, fillers: dict) -> str:
    """Điền dữ liệu vào template."""
    result = template
    # Điền từ product_info trước
    for k, v in info.items():
        result = result.replace(f"{{{k}}}", str(v))
        result = result.replace(f"{{product_{k}}}", str(v))

    # Điền filler ngẫu nhiên
    import re
    placeholders = re.findall(r"\{(\w+)\}", result)
    for ph in placeholders:
        if ph in fillers:
            result = result.replace(f"{{{ph}}}", random.choice(fillers[ph]))

    # Xóa placeholder còn sót
    result = re.sub(r"\{[^}]+\}", "", result)
    return result.strip()


def generate_full_script(
    product_info: dict,
    analysis,           # ProductAnalysis
    emotional: EmotionalPackage,
    platform: str = "tiktok",
) -> VideoScript:
    """
    Tạo script hoàn chỉnh: Hook → Unbox → Chi tiết → Demo → Review → CTA
    Thời lượng: tự động theo nội dung (~60-120 giây)
    """
    category = analysis.category if hasattr(analysis, "category") else "fashion"
    gender   = analysis.gender   if hasattr(analysis, "gender")   else "female"
    name     = product_info.get("name", "Sản phẩm")
    price    = product_info.get("price", "")

    tmpl = SCRIPT_TEMPLATES.get(category, SCRIPT_TEMPLATES["fashion"])
    info = {**product_info, "product_name": name, "price": price,
            "days": random.choice(_FILLERS["days"])}

    def pick(key): return _fill(random.choice(tmpl[key]), info, _FILLERS)
    def pick_detail(): return _fill(random.choice(tmpl["detail_shots"]), info, _FILLERS)

    scenes = []

    # ① HOOK (0-3s) — Curiosity + FOMO
    hook_text = emotional.hook_curiosity or pick("hooks")
    scenes.append(_scene("hook", "close_face", hook_text, 3.0))

    # ② SOCIAL PROOF (3-5s)
    scenes.append(_scene("social_proof", "text_overlay",
                          emotional.social_proof_line, 2.5))

    # ③ UNBOX (5-12s) — Reveal sản phẩm
    scenes.append(_scene("unbox", "wide_shot", pick("unbox"), 6.0))

    # ④ DETAIL x2 (12-22s) — Cận cảnh chuyên nghiệp
    scenes.append(_scene("detail", "macro_close", pick_detail(), 4.5))
    scenes.append(_scene("detail", "macro_close", pick_detail(), 4.5))

    # ⑤ TRANSFORMATION (22-27s)
    scenes.append(_scene("transformation", "split_screen",
                          emotional.transformation_line, 5.0))

    # ⑥ WEARING/DEMO (27-40s) — Người mặc/dùng sản phẩm
    scenes.append(_scene("wearing", "medium_shot", pick("wearing"), 7.0))
    scenes.append(_scene("wearing", "medium_shot", pick("wearing"), 6.0))

    # ⑦ HONEST REVIEW (40-55s) — Authenticity
    scenes.append(_scene("review", "talking_head", emotional.authenticity_story, 5.0))
    scenes.append(_scene("review", "talking_head", pick("honest_review"), 8.0))

    # ⑧ IDENTITY (55-60s)
    scenes.append(_scene("identity", "close_face", emotional.identity_line, 4.0))

    # ⑨ URGENCY (60-65s)
    scenes.append(_scene("urgency", "text_overlay", emotional.urgency_line, 4.0))

    # ⑩ CTA (65-75s)
    cta_text = pick("cta")
    scenes.append(_scene("cta", "wide_product", cta_text, 7.0))

    # ⑪ LOOP HOOK (75s) — Kéo xem lại
    scenes.append(_scene("loop", "close_face", emotional.loop_hook, 3.0))

    # Build full TTS script (chỉ các scene có text thật)
    tts_parts = [s["text"] for s in scenes
                 if s["scene_type"] not in ("social_proof", "urgency", "loop")]
    full_text = " ".join(tts_parts)

    duration_est = sum(s["duration_hint"] for s in scenes)

    # Caption
    if hasattr(emotional, "ab_hooks"):
        caption_hook = random.choice(emotional.ab_hooks)
    else:
        caption_hook = hook_text[:80]

    caption = (
        f"{caption_hook}\n\n"
        f"✅ {emotional.social_proof_line}\n"
        f"🔥 {emotional.urgency_line}\n\n"
        f"💰 Giá: {price}\n"
        f"🛒 Link trong bio / comment 'link'\n\n"
        f"#affiliate #review #viral"
    )

    return VideoScript(
        title=f"Review {name}",
        total_scenes=len(scenes),
        scenes=scenes,
        full_text=full_text,
        duration_est=duration_est,
        caption=caption,
    )
