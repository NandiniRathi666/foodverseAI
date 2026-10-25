import numpy as np
from PIL import Image

from app import core


def test_bmr_mifflin_male():
    # 10*70 + 6.25*170 - 5*28 + 5 = 1627.5
    assert round(core.bmr_mifflin(70, 170, 28, "Male"), 1) == 1627.5


def test_health_score_in_range():
    s = core.composite_health_score({"calories": 500, "protein_g": 30, "fiber_g": 8, "fat_g": 15, "sugar_g": 5})
    assert 1 <= s <= 100


def test_normalize_fresh_derives_advice():
    r = core.normalize_fresh({"stage": "spoiled-ish", "category": "Fruit"})
    assert r["stage"] == "Spoiled" and r["advice"] == "Discard immediately"


def test_hygiene_score_all_compliant_is_100():
    checks = {k: ("Compliant", "ok", "") for k, _, _ in core.INDICATORS}
    assert core.normalize_hygiene({"checks": checks})["score"] == 100


def test_hygiene_weighted_score():
    checks = {k: ("Compliant", "", "") for k, _, _ in core.INDICATORS}
    checks["sanitization"] = ("Violation", "dirty", "clean")  # weight 3 of total 13
    res = core.normalize_hygiene({"checks": checks})
    assert res["score"] == round(10 / 13 * 100, 1) and len(res["violations"]) == 1


def test_plan_hits_target_and_grocery():
    plan, grocery, _ = core.build_plan(2000, ["Vegan"])
    assert len(plan) == 7
    for day in plan:
        assert abs(sum(m["kcal"] for m in day) - 2000) <= 2
    assert grocery


def test_keto_macros_low_carb():
    m = core.macro_targets(2000, 70, "Fat Loss", ["Keto"])
    assert m["Carbs"] <= 30


def test_demo_recipes_vegan_only():
    out = core.demo_recipes(["lentils", "onion", "tomato"], "Vegan", 60)["recipes"]
    assert out and all("paneer" not in r["name"].lower() for r in out)


def test_opencv_signals_on_synthetic_image():
    img = Image.fromarray(np.full((64, 64, 3), (200, 40, 40), dtype=np.uint8))
    sig = core.opencv_freshness_signals(img)
    assert sig is None or 0 <= sig["spoilage_index"] <= 1


def test_parse_json_with_fences():
    assert core.parse_json('```json\n{"a": 1}\n```') == {"a": 1}
