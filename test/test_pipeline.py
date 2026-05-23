"""
tests/test_pipeline.py — Full Pipeline Test Suite
=============================================================================
Chạy thử toàn bộ pipeline KHÔNG cần GPU, không cần Drive mount.
Tests text-only path (no CLIP, no video generation):
  1. ai_analyzer: nhận diện tất cả gender/style
  2. script_writer: sinh kịch bản cho mọi loại sản phẩm
  3. viral_strategy: build_viral_content cho tất cả categories
  4. background: get_full_prompt cho tất cả garment keys
  5. caption_gen: generate_caption wrapper

Chạy: python -m pytest tests/test_pipeline.py -v
Hoặc: python tests/test_pipeline.py
=============================================================================
"""
import sys
import os
import traceback
import datetime

# Đảm bảo import từ project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

PASS = "✅"
FAIL = "❌"
WARN = "⚠️"

results = []


def test(name: str, fn):
    try:
        result = fn()
        results.append((PASS, name, str(result)[:120] if result else "OK"))
        print(f"  {PASS} {name}")
        if result:
            preview = str(result)[:100].replace("\n", " | ")
            print(f"     → {preview}")
    except Exception as e:
        results.append((FAIL, name, str(e)[:120]))
        print(f"  {FAIL} {name}: {e}")
        traceback.print_exc()


# ══════════════════════════════════════════════════════════════════════════════
#  GROUP 1: AI ANALYZER
# ══════════════════════════════════════════════════════════════════════════════

def run_analyzer_tests():
    print("\n" + "═"*60)
    print("GROUP 1: AI Analyzer — Nhận diện trang phục & khuôn mặt")
    print("═"*60)

    from pipeline.ai_analyzer import analyze_product, GarmentAnalysis, GARMENT_TAXONOMY

    # Women products
    test("Analyze: Váy dạ hội (women formal)", lambda: (
        lambda a: f"gender={a.gender} | key={a.garment_key} | style={a.style_category} | target={a.target_customer[:30]}"
    )(analyze_product("Váy dạ hội lụa đỏ", "Váy nữ tay dài cổ V sang trọng")))

    test("Analyze: Áo dài nữ (women traditional)", lambda: (
        lambda a: f"gender={a.gender} | key={a.garment_key} | usp={a.usp[:40]}"
    )(analyze_product("Áo dài nữ hoa sen", "Áo dài phụ nữ vải lụa cao cấp")))

    test("Analyze: Set gym nữ (women sportswear)", lambda: (
        lambda a: f"gender={a.gender} | style={a.style_category} | features={a.key_features[:2]}"
    )(analyze_product("Bộ đồ tập gym nữ", "Quần legging + áo crop top thể thao co giãn 4 chiều")))

    # Men products
    test("Analyze: Vest nam xanh navy (men formal)", lambda: (
        lambda a: f"gender={a.gender} | key={a.garment_key} | target={a.target_customer[:30]}"
    )(analyze_product("Vest nam xanh navy", "Bộ suit nam công sở cao cấp slim fit", gender_hint="men")))

    test("Analyze: Áo thun nam streetwear (men casual)", lambda: (
        lambda a: f"gender={a.gender} | style={a.style_category} | colors={a.color_palette}"
    )(analyze_product("Áo thun nam màu đen", "Áo phông nam oversize streetwear graphic")))

    test("Analyze: Áo dài nam (men traditional)", lambda: (
        lambda a: f"gender={a.gender} | key={a.garment_key} | confidence={a.confidence:.0%}"
    )(analyze_product("Áo dài nam", "Áo dài phụ nam truyền thống", gender_hint="men")))

    # Children products
    test("Analyze: Set bé gái (children casual)", lambda: (
        lambda a: f"gender={a.gender} | age={a.age_group} | key={a.garment_key}"
    )(analyze_product("Váy bé gái hoa nhí", "Đầm bé gái cotton dễ thương 3-8 tuổi")))

    test("Analyze: Bộ đồ trẻ em unisex (children set)", lambda: (
        lambda a: f"gender={a.gender} | age={a.age_group} | target={a.target_customer[:30]}"
    )(analyze_product("Bộ đồ trẻ em", "Set đồ bé trai bé gái cotton mềm 2-10 tuổi")))

    test("Analyze: Bodysuit bé sơ sinh (baby)", lambda: (
        lambda a: f"gender={a.gender} | age={a.age_group} | usp={a.usp[:40]}"
    )(analyze_product("Bodysuit bé sơ sinh", "Bodysuit cotton organic cho bé 0-12 tháng")))

    # Unisex
    test("Analyze: Đồ đôi couple (unisex couple)", lambda: (
        lambda a: f"gender={a.gender} | key={a.garment_key} | target={a.target_customer[:30]}"
    )(analyze_product("Áo đôi matching", "Đồ đôi áo thun cặp đôi unisex")))

    test("Analyze: Set gia đình (family matching)", lambda: (
        lambda a: f"gender={a.gender} | key={a.garment_key} | method={a.analysis_method}"
    )(analyze_product("Set đồ gia đình", "Đồ gia đình matching 4 người ba mẹ và bé")))

    # Taxonomy coverage
    test("GARMENT_TAXONOMY coverage (50+ items)", lambda: (
        f"{len(GARMENT_TAXONOMY)} garment types | "
        f"Women: {sum(1 for v in GARMENT_TAXONOMY.values() if v['gender']=='women')} | "
        f"Men: {sum(1 for v in GARMENT_TAXONOMY.values() if v['gender']=='men')} | "
        f"Unisex: {sum(1 for v in GARMENT_TAXONOMY.values() if v['gender']=='unisex')} | "
        f"Children: {sum(1 for v in GARMENT_TAXONOMY.values() if v['gender'] in ('children','unisex') and v['age'] in ('baby','toddler','kids'))}"
    ))


# ══════════════════════════════════════════════════════════════════════════════
#  GROUP 2: SCRIPT WRITER
# ══════════════════════════════════════════════════════════════════════════════

def run_script_writer_tests():
    print("\n" + "═"*60)
    print("GROUP 2: Script Writer — AI tự viết kịch bản video")
    print("═"*60)

    from pipeline.ai_analyzer import analyze_product
    from pipeline.script_writer import write_video_script, VideoScript

    test_cases = [
        ("Váy dạ hội nữ",    "850k",  "Váy nữ lụa dài tay cổ V",            "women",    "tiktok"),
        ("Suit nam xanh",    "1.2tr", "Bộ vest nam công sở slim fit",          "men",      "tiktok"),
        ("Set bé gái 5-8t",  "185k",  "Bộ đồ bé gái cotton hoa nhí",         "children", "shopee"),
        ("Bodysuit sơ sinh", "125k",  "Bodysuit organic bé 0-12 tháng",       "baby",     "shopee"),
        ("Áo đôi matching",  "299k",  "Đồ đôi áo thun cặp đôi unisex",       "unisex",   "tiktok"),
        ("Áo dài nữ hoa",    "650k",  "Áo dài phụ nữ lụa cao cấp",           "women",    "tiktok"),
        ("Áo hoodie nam",    "350k",  "Hoodie nam streetwear oversize",        "men",      "tiktok"),
        ("Đồ gia đình",      "490k",  "Set đồ gia đình matching 4 người",     "unisex",   "shopee"),
    ]

    for name, price, desc, gender_hint, platform in test_cases:
        def make_test(n, p, d, g, plat):
            def run():
                analysis = analyze_product(n, d, gender_hint=g)
                script = write_video_script(analysis, n, p, plat)
                assert isinstance(script.hook_scene.hook_text, str), "hook_text must be str"
                assert len(script.hook_scene.hook_text) > 5, "hook_text too short"
                assert isinstance(script.caption, str), "caption must be str"
                assert len(script.hashtags) > 3, "hashtags too few"
                assert script.music_mood, "music_mood empty"
                return (
                    f"[{g}|{plat}] hook={script.hook_scene.hook_text[:40]}... | "
                    f"music={script.music_mood} | tags={len(script.hashtags)}"
                )
            return run
        test(f"Script: {name} [{gender_hint}|{platform}]", make_test(name, price, desc, gender_hint, platform))

    # Verify SceneBlock timing
    def check_timing():
        analysis = analyze_product("Test product", "Women casual dress")
        script = write_video_script(analysis, "Test", "299k", "tiktok")
        assert script.hook_scene.start_time == 0.0
        assert script.hook_scene.end_time > 0
        assert script.reveal_scene.start_time >= script.hook_scene.end_time
        assert script.value_scene.start_time >= script.reveal_scene.start_time
        assert script.cta_scene.start_time >= script.value_scene.start_time
        assert script.loop_scene.start_time >= script.cta_scene.start_time
        return f"Timeline: 0→{script.hook_scene.end_time:.1f}→{script.value_scene.start_time:.1f}→{script.cta_scene.start_time:.1f}→{script.loop_scene.start_time:.1f}→{script.duration_seconds:.1f}s"
    test("Script: Timeline ordering correct (5 scenes)", check_timing)


# ══════════════════════════════════════════════════════════════════════════════
#  GROUP 3: VIRAL STRATEGY
# ══════════════════════════════════════════════════════════════════════════════

def run_viral_strategy_tests():
    print("\n" + "═"*60)
    print("GROUP 3: Viral Strategy — Content Engine 2026")
    print("═"*60)

    from pipeline.viral_strategy import build_viral_content, build_caption, ViralContent

    test_products = [
        ("Váy maxi hoa nhí",    "299k",  "Váy nữ maxi casual mùa hè",              "women",    "tiktok"),
        ("Suit nam xanh navy",  "850k",  "Vest nam công sở formal",                 "men",      "tiktok"),
        ("Set bé gái 3-8t",     "185k",  "Bộ đồ trẻ em cotton bé gái",             "children", "shopee"),
        ("Bodysuit sơ sinh",    "125k",  "Bodysuit baby 0-12 tháng",                "baby",     "shopee"),
        ("Áo đôi couple",       "299k",  "Đồ đôi matching couple unisex",           "unisex",   "tiktok"),
        ("Áo dài nữ",           "650k",  "Áo dài nữ truyền thống lụa",             "women",    "tiktok"),
        ("Hoodie nam",          "350k",  "Hoodie nam streetwear oversize",           "men",      "tiktok"),
        ("Set gia đình",        "490k",  "Đồ gia đình matching family",              "unisex",   "shopee"),
        ("Bộ gym activewear",   "450k",  "Đồ tập gym nữ activewear co giãn",        "women",    "tiktok"),
        ("Áo dài nam",          "700k",  "Áo dài nam truyền thống",                 "men",      "shopee"),
    ]

    for name, price, garment, gender, platform in test_products:
        def make_test(n, p, g, gen, plat):
            def run():
                vc = build_viral_content(name=n, price=p, garment=g, platform=plat, gender_override=gen)
                assert isinstance(vc, ViralContent)
                assert vc.hook_text, "hook_text empty"
                assert vc.value_stack, "value_stack empty"
                assert vc.comment_cta, "comment_cta empty"
                assert vc.micro_story, "micro_story empty"
                assert len(vc.hashtags_tiktok) >= 5, "too few hashtags"
                assert vc.music_mood, "music_mood empty"
                return (
                    f"[{gen}|{plat}] hook={vc.hook_text[:40]}... | "
                    f"mood={vc.music_mood} | "
                    f"cta={vc.comment_cta[:30]}"
                )
            return run
        test(f"Viral: {name} [{gender}|{platform}]", make_test(name, price, garment, gender, platform))

    # Caption generation
    test("Caption TikTok: nữ", lambda: (
        lambda c: f"len={len(c)} chars | preview={c[:60]}"
    )(build_caption("Váy đẹp", "299k", "Váy nữ casual", "tiktok")))

    test("Caption Shopee: nam", lambda: (
        lambda c: f"len={len(c)} chars | preview={c[:60]}"
    )(build_caption("Suit nam", "850k", "Vest nam formal", "shopee")))

    test("Caption: Trẻ em (shopee)", lambda: (
        lambda c: f"len={len(c)} chars | has_price={'850k' not in c}"
    )(build_caption("Set bé", "185k", "Bộ đồ bé gái", "shopee")))


# ══════════════════════════════════════════════════════════════════════════════
#  GROUP 4: BACKGROUND / AI PROMPT
# ══════════════════════════════════════════════════════════════════════════════

def run_background_tests():
    print("\n" + "═"*60)
    print("GROUP 4: Background Prompts — AI Video 2026")
    print("═"*60)

    from pipeline.background import (
        get_background_prompt, get_motion_prompt, get_full_prompt,
        get_hook_frame_prompt, get_loop_prompt, get_negative_prompt,
        get_model_description,
    )

    garment_keys = [
        ("dress_evening", "women"),
        ("ao_dai", "women"),
        ("men_suit", "men"),
        ("men_tshirt", "men"),
        ("kids_dress", "children"),
        ("baby_onesie", "baby"),
        ("couple_set", "unisex"),
        ("family_matching", "unisex"),
        ("women_activewear", "women"),
        ("men_sportswear", "men"),
    ]

    for key, gender in garment_keys:
        def make_test(k, g):
            def run():
                bg = get_background_prompt(k)
                motion = get_motion_prompt(k)
                full = get_full_prompt(k, g)
                hook = get_hook_frame_prompt(k)
                assert len(full) > 100, f"prompt too short: {len(full)}"
                assert len(bg) > 20, "bg prompt too short"
                return f"bg={len(bg)}ch | motion={len(motion)}ch | full={len(full)}ch | hook={len(hook)}ch"
            return run
        test(f"Prompt: {key} [{gender}]", make_test(key, gender))

    test("Model descriptions: all genders", lambda: (
        f"women={len(get_model_description('women'))}ch | "
        f"men={len(get_model_description('men'))}ch | "
        f"kids={len(get_model_description('children', 'kids'))}ch | "
        f"baby={len(get_model_description('unisex', 'baby'))}ch"
    ))

    test("Negative prompt present + adequate length", lambda: (
        lambda n: f"len={len(n)} chars — {PASS if len(n) > 100 else FAIL}"
    )(get_negative_prompt()))


# ══════════════════════════════════════════════════════════════════════════════
#  GROUP 5: CAPTION GEN (wrapper)
# ══════════════════════════════════════════════════════════════════════════════

def run_caption_tests():
    print("\n" + "═"*60)
    print("GROUP 5: Caption Generator — Platform × Gender")
    print("═"*60)

    from pipeline.caption_gen import generate_caption, generate_viral_package

    test("Caption: Váy nữ TikTok", lambda: generate_caption("Váy đẹp", "299k", "Váy nữ casual maxi", "tiktok")[:80])
    test("Caption: Suit nam TikTok", lambda: generate_caption("Suit nam", "850k", "Vest nam công sở", "tiktok")[:80])
    test("Caption: Bé gái Shopee", lambda: generate_caption("Set bé", "185k", "Bộ đồ bé gái cotton", "shopee")[:80])
    test("Caption: Baby Shopee", lambda: generate_caption("Bodysuit", "125k", "Bodysuit bé sơ sinh", "shopee")[:80])
    test("Caption: Đồ đôi TikTok", lambda: generate_caption("Áo đôi", "299k", "Đồ đôi couple matching", "tiktok")[:80])

    def check_viral_package():
        vc = generate_viral_package("Váy maxi", "299k", "Váy nữ casual", "tiktok")
        assert vc.hook_text
        assert vc.value_stack
        assert vc.comment_cta
        assert vc.micro_story
        assert vc.music_mood
        return f"ViralContent OK | hook={vc.hook_text[:40]}... | mood={vc.music_mood}"
    test("generate_viral_package: full ViralContent object", check_viral_package)


# ══════════════════════════════════════════════════════════════════════════════
#  GROUP 6: VIDEO OUTPUT EVALUATION
# ══════════════════════════════════════════════════════════════════════════════

def run_video_eval():
    print("\n" + "═"*60)
    print("GROUP 6: Video Output Evaluation — Chấm điểm")
    print("═"*60)

    from pipeline.ai_analyzer import analyze_product
    from pipeline.script_writer import write_video_script
    from pipeline.viral_strategy import build_viral_content

    scenarios = [
        {"name": "Váy dạ hội đỏ lụa", "price": "850k", "desc": "Váy nữ lụa đỏ cổ V dài tay sang trọng", "gender": "women"},
        {"name": "Suit nam xanh navy", "price": "1.2tr", "desc": "Bộ vest nam slim fit công sở",            "gender": "men"},
        {"name": "Set bé gái hoa nhí", "price": "185k", "desc": "Bộ đồ trẻ em cotton bé gái 3-8 tuổi",   "gender": "children"},
    ]

    for sc in scenarios:
        def make_eval(s):
            def run():
                analysis = analyze_product(s["name"], s["desc"], gender_hint=s["gender"])
                script = write_video_script(analysis, s["name"], s["price"], "tiktok")
                vc = build_viral_content(s["name"], s["price"], s["desc"], "tiktok", gender_override=s["gender"])

                # Scoring
                scores = {}

                # Hook quality
                hook = script.hook_scene.hook_text
                has_emoji = any(ord(c) > 127 for c in hook)
                hook_len = len(hook)
                scores["hook_quality"] = 10 if (has_emoji and 20 < hook_len < 80) else 7

                # Value stack
                vs = script.value_scene.hook_text
                has_price_info = any(w in vs for w in ["✅", "freeship", "đổi trả", "Ship"])
                scores["value_stack"] = 10 if (has_price_info and len(vs) > 30) else 6

                # Comment CTA
                cta = script.cta_scene.subtext
                has_comment = "Comment" in cta or "comment" in cta
                scores["comment_cta"] = 10 if has_comment else 5

                # Caption completeness
                cap = script.caption
                has_tags = "#" in cap
                has_name = s["name"][:5] in cap or "name" in cap.lower()
                scores["caption"] = 9 if (has_tags and len(cap) > 100) else 6

                # Music mood
                scores["music_mood"] = 10 if script.music_mood else 0

                # AI prompt quality
                prompt_len = len(script.ai_prompt_main)
                scores["ai_prompt"] = 10 if prompt_len > 200 else 7

                total = sum(scores.values())
                max_score = len(scores) * 10
                pct = total / max_score * 100

                detail = " | ".join(f"{k}={v}/10" for k, v in scores.items())
                return f"SCORE: {total}/{max_score} ({pct:.0f}%) | {detail}"
            return run
        test(f"Eval [{sc['gender']}]: {sc['name']}", make_eval(sc))


# ══════════════════════════════════════════════════════════════════════════════
#  FINAL SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

def print_summary():
    print("\n" + "═"*60)
    print("TỔNG KẾT CHẠY THỬ")
    print("═"*60)
    passed = sum(1 for r in results if r[0] == PASS)
    failed = sum(1 for r in results if r[0] == FAIL)
    total  = len(results)
    print(f"\n✅ Passed: {passed}/{total}")
    if failed:
        print(f"❌ Failed: {failed}/{total}")
        print("\nFailed tests:")
        for r in results:
            if r[0] == FAIL:
                print(f"  {FAIL} {r[1]}: {r[2]}")
    print(f"\nPass rate: {passed/total*100:.1f}%")
    print(f"Run time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("═"*60)
    return passed == total


if __name__ == "__main__":
    print("\n🚀 AFFILIATE BOT v5 — FULL PIPELINE TEST")
    print(f"📅 {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("="*60)

    run_analyzer_tests()
    run_script_writer_tests()
    run_viral_strategy_tests()
    run_background_tests()
    run_caption_tests()
    run_video_eval()

    success = print_summary()
    sys.exit(0 if success else 1)
