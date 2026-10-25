"""
Core food-intelligence logic (framework independent).
Prompts, demo data, scoring rules, OpenCV heuristics and the TDEE meal planner.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import tempfile
from collections import defaultdict

import numpy as np
from PIL import Image

try:
    import cv2  # opencv-python-headless
except ImportError:  # video + pixel diagnostics are disabled without it
    cv2 = None


def num(x, default: float = 0.0) -> float:
    """Safely coerce a model-provided value to float."""
    try:
        if isinstance(x, str):
            m = re.search(r"-?\d+(\.\d+)?", x)
            return float(m.group()) if m else default
        return float(x)
    except (TypeError, ValueError):
        return default


def parse_json(text: str) -> dict:
    """Extract the first JSON object from an LLM response."""
    text = re.sub(r"```(?:json)?", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("Model did not return JSON.")
    return json.loads(text[start : end + 1])


def prep_image(file) -> Image.Image:
    img = Image.open(file)
    img = img.convert("RGB")
    img.thumbnail((1024, 1024))
    return img


def img_to_b64(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return base64.b64encode(buf.getvalue()).decode()


def img_hash(imgs) -> int:
    h = hashlib.md5()
    for im in imgs:
        h.update(im.tobytes()[:200000])
    return int(h.hexdigest(), 16)


def extract_frames(data: bytes, filename: str, n: int = 4) -> list:
    """Sample n evenly spaced frames from uploaded video bytes using OpenCV."""
    if cv2 is None:
        raise RuntimeError("OpenCV is not installed; video analysis unavailable.")
    suffix = os.path.splitext(filename or "")[1] or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(data)
        path = tmp.name
    frames = []
    try:
        cap = cv2.VideoCapture(path)
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total <= 0:
            raise ValueError("Could not read the video.")
        for idx in np.linspace(0, max(total - 1, 0), n, dtype=int):
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(idx))
            ok, frame = cap.read()
            if ok:
                im = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                im.thumbnail((896, 896))
                frames.append(im)
        cap.release()
    finally:
        os.unlink(path)
    if not frames:
        raise ValueError("No frames could be extracted.")
    return frames


# ============================ FOOD RECOGNITION ==============================
FOOD_PROMPT = (
    "You are an expert food scientist and registered dietitian. Analyze the meal photo. "
    "Identify the dish, cuisine, visible ingredients and estimated portion size, then estimate nutrition "
    "for the visible portion. Respond with ONLY valid JSON using this schema:\n"
    '{"dish_name":str,"cuisine":str,"ingredients":[str],"portion_size":str,"portion_grams":number,'
    '"calories":number,"protein_g":number,"carbs_g":number,"fat_g":number,"fiber_g":number,'
    '"sugar_g":number,"allergens":[str],"health_score":number(1-100),"health_rationale":str,'
    '"tips":[str],"confidence":number(0-1)}'
)

DEMO_DISHES = [
    {"dish_name": "Chicken Biryani", "cuisine": "Indian", "ingredients": ["Basmati rice", "Chicken", "Yogurt", "Onion", "Spices", "Ghee"],
     "portion_size": "1 plate (~350 g)", "portion_grams": 350, "calories": 640, "protein_g": 32, "carbs_g": 78, "fat_g": 21, "fiber_g": 3, "sugar_g": 4,
     "allergens": ["Dairy"], "health_score": 62, "health_rationale": "Good protein, but refined-carb heavy and rich in ghee.",
     "tips": ["Add a cucumber raita or salad for fiber.", "Use less ghee to cut ~80 kcal."], "confidence": 0.82},
    {"dish_name": "Greek Salad with Grilled Chicken", "cuisine": "Mediterranean", "ingredients": ["Cucumber", "Tomato", "Feta", "Olives", "Chicken breast", "Olive oil"],
     "portion_size": "1 large bowl (~380 g)", "portion_grams": 380, "calories": 420, "protein_g": 36, "carbs_g": 14, "fat_g": 25, "fiber_g": 5, "sugar_g": 8,
     "allergens": ["Dairy"], "health_score": 86, "health_rationale": "High protein, low refined carbs, healthy fats.",
     "tips": ["Excellent balanced meal.", "Watch the sodium from feta and olives."], "confidence": 0.86},
    {"dish_name": "Margherita Pizza (2 slices)", "cuisine": "Italian", "ingredients": ["Wheat dough", "Tomato sauce", "Mozzarella", "Basil"],
     "portion_size": "2 slices (~220 g)", "portion_grams": 220, "calories": 560, "protein_g": 24, "carbs_g": 68, "fat_g": 20, "fiber_g": 4, "sugar_g": 6,
     "allergens": ["Gluten", "Dairy"], "health_score": 55, "health_rationale": "Moderate protein; refined flour and saturated fat limit the score.",
     "tips": ["Pair with a green salad.", "Choose a whole-wheat crust when possible."], "confidence": 0.8},
    {"dish_name": "Vegetable Poha", "cuisine": "Indian", "ingredients": ["Flattened rice", "Peas", "Onion", "Peanuts", "Turmeric", "Curry leaves"],
     "portion_size": "1 bowl (~250 g)", "portion_grams": 250, "calories": 330, "protein_g": 8, "carbs_g": 55, "fat_g": 9, "fiber_g": 5, "sugar_g": 3,
     "allergens": ["Peanuts"], "health_score": 74, "health_rationale": "Light, fiber from vegetables; a little low in protein.",
     "tips": ["Add sprouts or paneer for protein.", "Squeeze lemon to boost iron absorption."], "confidence": 0.78},
]


def composite_health_score(n: dict) -> int:
    """Transparent rule-based score (1-100) from macros; blended with the model's own score."""
    kcal = max(num(n.get("calories")), 1)
    protein_pct = num(n.get("protein_g")) * 4 / kcal * 100
    fat_pct = num(n.get("fat_g")) * 9 / kcal * 100
    score = 50.0
    score += min(num(n.get("fiber_g")), 10) * 2.5
    if 15 <= protein_pct <= 35:
        score += 14
    elif protein_pct >= 10:
        score += 6
    if fat_pct > 45:
        score -= 10
    if num(n.get("sugar_g")) > 25:
        score -= 10
    if kcal > 900:
        score -= 10
    elif kcal < 120:
        score -= 5
    return int(max(1, min(100, score)))


def normalize_food(res: dict) -> dict:
    for k in ["calories", "protein_g", "carbs_g", "fat_g", "fiber_g", "sugar_g", "portion_grams"]:
        res[k] = num(res.get(k))
    res["ingredients"] = list(res.get("ingredients") or [])
    res["allergens"] = list(res.get("allergens") or [])
    res["tips"] = list(res.get("tips") or [])
    rule = composite_health_score(res)
    model = num(res.get("health_score"), rule)
    res["rule_score"] = rule
    res["health_score"] = int(max(1, min(100, round((rule + model) / 2))))
    return res


# ============================ FRESHNESS =====================================
FRESH_PROMPT = (
    "You are a food safety microbiologist. Inspect the perishable item photo. Evaluate surface texture, "
    "discoloration, wrinkling/softening and visible mold or slime. Classify freshness stage as exactly one of "
    "'Fresh', 'Moderately Fresh', 'Spoiled'. Respond with ONLY valid JSON:\n"
    '{"item":str,"category":"Fruit|Vegetable|Meat|Seafood|Dairy|Other","stage":str,"confidence":number(0-1),'
    '"indicators":{"texture":str,"discoloration":str,"wrinkling":str,"mold":str},'
    '"shelf_life_estimate":str,"storage_tips":[str]}'
)

STAGES = ["Fresh", "Moderately Fresh", "Spoiled"]
ADVICE = {"Fresh": "Safe to consume", "Moderately Fresh": "Consume within 24h", "Spoiled": "Discard immediately"}
STAGE_COLOR = {"Fresh": "green", "Moderately Fresh": "amber", "Spoiled": "red"}
STORAGE_TIPS = {
    "Fruit": ["Store ripe fruit in the fridge crisper; keep ethylene producers (bananas, apples) apart.", "Wash only right before eating to prevent mold."],
    "Vegetable": ["Keep leafy greens in a breathable bag with a paper towel.", "Store root vegetables cool, dark and dry, away from onions/potatoes."],
    "Meat": ["Store at or below 4 °C on the lowest shelf in a sealed container.", "Freeze at -18 °C if not cooking within 1-2 days."],
    "Seafood": ["Keep on ice or at 0-2 °C and cook within 24 hours.", "Never refreeze thawed seafood."],
    "Dairy": ["Keep refrigerated at or below 4 °C and close tightly after use.", "Use clean utensils to avoid cross-contamination."],
    "Other": ["Keep refrigerated in an airtight container.", "Label with the date opened and follow the 2-hour rule at room temperature."],
}


def opencv_freshness_signals(img: Image.Image) -> dict | None:
    """Cheap pixel heuristics (dark spots, browning, texture irregularity). Informational only."""
    if cv2 is None:
        return None
    small = cv2.resize(np.array(img), (256, 256))
    hsv = cv2.cvtColor(small, cv2.COLOR_RGB2HSV)
    h, s, v = hsv[..., 0], hsv[..., 1], hsv[..., 2]
    background = (s < 25) & (v > 200)  # white plates / counters
    mask = ~background
    total = max(int(mask.sum()), 1)
    dark = float(((v < 55) & mask).sum()) / total
    brown = float(((h >= 8) & (h <= 25) & (s > 80) & (v >= 40) & (v < 170) & mask).sum()) / total
    gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
    lap = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    index = min(1.0, dark * 2.0 + brown * 0.8 + max(0.0, lap - 400) / 6000)
    stage = "Fresh" if index < 0.18 else "Moderately Fresh" if index < 0.42 else "Spoiled"
    return {"dark_pct": dark * 100, "brown_pct": brown * 100, "texture_var": lap, "spoilage_index": index, "stage": stage}


def demo_freshness(img: Image.Image) -> dict:
    sig = opencv_freshness_signals(img)
    if sig:
        stage = sig["stage"]
    else:
        stage = STAGES[img_hash([img]) % 3]
    texts = {
        "Fresh": ("Firm, smooth surface", "Uniform natural color", "No wrinkling", "No mold visible", "Several days under proper storage"),
        "Moderately Fresh": ("Slightly soft in places", "Some dulling / minor spots", "Early wrinkling", "No mold visible", "About 1 day"),
        "Spoiled": ("Mushy or slimy patches", "Dark or off-color areas", "Heavy wrinkling / collapse", "Possible mold or decay", "Past safe shelf life"),
    }[stage]
    return {"item": "Perishable item (demo estimate)", "category": "Other", "stage": stage,
            "confidence": 0.6, "indicators": dict(zip(["texture", "discoloration", "wrinkling", "mold"], texts[:4])),
            "shelf_life_estimate": texts[4], "storage_tips": STORAGE_TIPS["Other"]}


def normalize_fresh(res: dict) -> dict:
    stage = str(res.get("stage", "")).strip().lower()
    res["stage"] = next((s for s in STAGES if s.lower() == stage), None) or (
        "Spoiled" if "spoil" in stage or "rot" in stage else "Moderately Fresh" if "moder" in stage else "Fresh")
    res["advice"] = ADVICE[res["stage"]]
    cat = res.get("category") if res.get("category") in STORAGE_TIPS else "Other"
    res["category"] = cat
    if not res.get("storage_tips"):
        res["storage_tips"] = STORAGE_TIPS[cat]
    res["indicators"] = res.get("indicators") or {}
    return res


# ============================ HYGIENE =======================================
# (key, label, weight) - weights reflect food-safety risk
INDICATORS = [
    ("head_covering", "Chef hat / hairnet", 2),
    ("gloves", "Glove usage", 2),
    ("sanitization", "Sanitization state (stations, tools)", 3),
    ("cross_contamination", "Cross-contamination control", 3),
    ("uniform", "Clean uniform / apron", 1),
    ("surfaces", "Surfaces, floors & equipment cleanliness", 2),
]
SEVERITY = {k: ("Critical" if w == 3 else "Major" if w == 2 else "Minor") for k, _, w in INDICATORS}

HYGIENE_PROMPT = (
    "You are a certified HACCP food safety auditor. Examine these kitchen image(s)/video frames. For EACH of "
    "these indicator keys give status 'Compliant', 'Violation' or 'Not visible': head_covering (chef hat/hairnet), "
    "gloves (glove use by food handlers), sanitization (clean, sanitized stations and tools), cross_contamination "
    "(e.g. raw poultry/meat near vegetables or ready-to-eat food, shared boards), uniform (clean uniform/apron), "
    "surfaces (surfaces/floors/equipment clean). Only judge what is visible. Respond with ONLY valid JSON:\n"
    '{"summary":str,"checks":[{"key":str,"status":str,"detail":str,"action":str}]}'
)

DEMO_HYGIENE = [
    {"summary": "Busy prep line with mixed compliance.",
     "checks": {"head_covering": ("Compliant", "All visible staff wear hats or hairnets.", ""),
                "gloves": ("Violation", "One handler preparing salad without gloves.", "Require gloves or tongs for ready-to-eat food."),
                "sanitization": ("Compliant", "Stations appear wiped and sanitizer bucket present.", ""),
                "cross_contamination": ("Violation", "Raw poultry tray sits beside fresh vegetables.", "Separate raw meat from produce; use color-coded boards."),
                "uniform": ("Compliant", "Aprons look clean.", ""),
                "surfaces": ("Not visible", "Floor not in frame.", "")}},
    {"summary": "Well-organized kitchen with good practices.",
     "checks": {"head_covering": ("Compliant", "Hairnets and caps worn.", ""),
                "gloves": ("Compliant", "Gloves worn during handling.", ""),
                "sanitization": ("Compliant", "Clean, organized stations.", ""),
                "cross_contamination": ("Compliant", "Raw and cooked items appear separated.", ""),
                "uniform": ("Compliant", "Clean uniforms.", ""),
                "surfaces": ("Violation", "Minor spills near the fryer.", "Clean spills immediately to prevent slips and pests.")}},
    {"summary": "Several serious hygiene concerns observed.",
     "checks": {"head_covering": ("Violation", "Staff member without head covering.", "Enforce hair restraint policy."),
                "gloves": ("Violation", "Bare hands handling cooked food.", "Provide gloves/tongs and retrain staff."),
                "sanitization": ("Violation", "Cluttered counter with food debris.", "Clean and sanitize before and after each task."),
                "cross_contamination": ("Violation", "Cutting board shared for raw chicken and vegetables.", "Use dedicated boards; sanitize between uses."),
                "uniform": ("Compliant", "Uniform appears acceptable.", ""),
                "surfaces": ("Violation", "Dirty surfaces and visible grease.", "Schedule deep cleaning and a daily checklist.")}},
]


def normalize_hygiene(raw: dict) -> dict:
    """Accepts demo (dict) or live (list) check format; computes weighted compliance %."""
    by_key = {}
    checks = raw.get("checks", [])
    if isinstance(checks, dict):
        for k, (st_, d, a) in checks.items():
            by_key[k] = {"status": st_, "detail": d, "action": a}
    else:
        for c in checks:
            if isinstance(c, dict) and c.get("key"):
                by_key[c["key"]] = c
    rows, earned, total = [], 0, 0
    for key, label, w in INDICATORS:
        c = by_key.get(key, {})
        s = str(c.get("status", "Not visible")).lower()
        status = "Compliant" if s.startswith("compl") else "Violation" if s.startswith("viol") else "Not visible"
        if status == "Compliant":
            earned += w
            total += w
        elif status == "Violation":
            total += w
        rows.append({"Indicator": label, "Status": status, "Severity": SEVERITY[key] if status == "Violation" else "-",
                     "Observation": c.get("detail", ""), "Corrective action": c.get("action", "") if status == "Violation" else ""})
    raw["rows"] = rows
    raw["score"] = round(earned / total * 100, 1) if total else None
    raw["violations"] = [r for r in rows if r["Status"] == "Violation"]
    return raw


# ============================ RECIPES =======================================
RECIPE_PROMPT_T = (
    "You are a creative chef and nutritionist. The user's pantry: {pantry}. Diet: {diet}. Max cooking time: "
    "{time} minutes. Servings: {servings}. Suggest 3 creative, nutritious recipes that mostly use the pantry "
    "(basic salt/oil/water are assumed). Respond with ONLY valid JSON:\n"
    '{{"recipes":[{{"name":str,"cook_time_min":number,"difficulty":"Easy|Medium|Hard","servings":number,'
    '"calories_per_serving":number,"ingredients_used":[str],"missing_ingredients":[str],"steps":[str],'
    '"substitutions":[{{"ingredient":str,"substitute":str}}],"nutrition_note":str}}]}}'
)

RECIPE_LIB = [
    {"name": "Veggie Egg Fried Rice", "needs": {"rice", "egg", "onion", "carrot", "peas", "soy sauce", "garlic"}, "veg": False, "vegan": False,
     "cook_time_min": 20, "difficulty": "Easy", "calories_per_serving": 420,
     "steps": ["Cook rice and let it cool (day-old rice works best).", "Sauté garlic and onion in oil for 2 min.", "Add diced carrot and peas; cook 3 min.",
               "Push veggies aside, scramble the eggs, then mix everything.", "Add rice and soy sauce; stir-fry on high heat for 3-4 min."],
     "substitutions": [{"ingredient": "egg", "substitute": "crumbled tofu"}, {"ingredient": "soy sauce", "substitute": "tamari or coconut aminos"}],
     "nutrition_note": "Balanced carbs and protein; add extra veggies for fiber."},
    {"name": "Masoor Dal (Red Lentil Soup)", "needs": {"lentils", "onion", "tomato", "garlic", "turmeric", "cumin", "ginger"}, "veg": True, "vegan": True,
     "cook_time_min": 30, "difficulty": "Easy", "calories_per_serving": 310,
     "steps": ["Rinse 1 cup red lentils; boil with turmeric in 3 cups water for 15 min.", "Temper cumin, garlic, ginger and onion in oil until golden.",
               "Add chopped tomato and cook until soft.", "Stir the masala into the dal; simmer 5 min and season.", "Finish with lemon juice and coriander."],
     "substitutions": [{"ingredient": "lentils", "substitute": "split moong dal"}, {"ingredient": "tomato", "substitute": "a splash of lemon/tamarind"}],
     "nutrition_note": "High in plant protein and fiber; very low cost."},
    {"name": "Chickpea Veggie Salad Bowl", "needs": {"chickpeas", "cucumber", "tomato", "onion", "lemon", "olive oil"}, "veg": True, "vegan": True,
     "cook_time_min": 10, "difficulty": "Easy", "calories_per_serving": 350,
     "steps": ["Drain and rinse chickpeas.", "Dice cucumber, tomato and red onion.", "Whisk lemon juice, olive oil, salt and pepper.", "Toss everything and rest 5 min before serving."],
     "substitutions": [{"ingredient": "chickpeas", "substitute": "white beans or boiled kidney beans"}, {"ingredient": "lemon", "substitute": "vinegar"}],
     "nutrition_note": "Fiber-rich, great cold lunch; add feta or tofu for extra protein."},
    {"name": "Garlic Veggie Pasta", "needs": {"pasta", "garlic", "olive oil", "tomato", "spinach", "cheese"}, "veg": True, "vegan": False,
     "cook_time_min": 20, "difficulty": "Easy", "calories_per_serving": 480,
     "steps": ["Boil pasta in salted water until al dente; save a cup of pasta water.", "Sauté sliced garlic in olive oil until fragrant.", "Add tomato and spinach; cook 3-4 min.",
               "Toss pasta with sauce, a splash of pasta water and cheese."],
     "substitutions": [{"ingredient": "pasta", "substitute": "whole-wheat pasta or zucchini noodles"}, {"ingredient": "cheese", "substitute": "nutritional yeast"}],
     "nutrition_note": "Use whole-wheat pasta to raise fiber."},
    {"name": "Paneer / Tofu Stir-Fry", "needs": {"paneer", "tofu", "bell pepper", "onion", "garlic", "soy sauce", "broccoli"}, "veg": True, "vegan": False,
     "cook_time_min": 18, "difficulty": "Medium", "calories_per_serving": 390,
     "steps": ["Cube paneer or tofu and pan-sear until golden; set aside.", "Stir-fry onion, garlic, pepper and broccoli on high heat for 4 min.",
               "Return protein to the pan, add soy sauce and a pinch of pepper.", "Serve over rice or quinoa."],
     "substitutions": [{"ingredient": "paneer", "substitute": "tofu (vegan)"}, {"ingredient": "broccoli", "substitute": "cabbage or green beans"}],
     "nutrition_note": "High protein; low in carbs if served without rice."},
]


def demo_recipes(pantry: list, diet: str, time_limit: int) -> dict:
    items = {p.lower().strip() for p in pantry if p.strip()}

    def overlap(r):
        return sum(1 for n in r["needs"] if any(n in i or i in n for i in items))

    pool = [r for r in RECIPE_LIB if r["cook_time_min"] <= max(time_limit, 10)]
    if diet == "Vegan":
        pool = [r for r in pool if r["vegan"]]
    elif diet == "Vegetarian":
        pool = [r for r in pool if r["veg"]]
    pool = pool or RECIPE_LIB
    ranked = sorted(pool, key=overlap, reverse=True)[:3]
    out = []
    for r in ranked:
        used = [n for n in r["needs"] if any(n in i or i in n for i in items)]
        missing = [n for n in r["needs"] if n not in used]
        out.append({**{k: v for k, v in r.items() if k not in ("needs", "veg", "vegan")},
                    "servings": 2, "ingredients_used": sorted(used), "missing_ingredients": sorted(missing)})
    return {"recipes": out}


# ============================ MEAL PLANNER ==================================
ACTIVITY = {
    "Sedentary (little/no exercise)": 1.2,
    "Lightly active (1-3 days/week)": 1.375,
    "Moderately active (3-5 days/week)": 1.55,
    "Very active (6-7 days/week)": 1.725,
    "Athlete (2x/day training)": 1.9,
}
GOALS = {"Fat Loss": -0.20, "Maintenance": 0.0, "Muscle Gain": 0.10, "Body Recomposition": -0.05}
PROTEIN_PER_KG = {"Fat Loss": 2.0, "Maintenance": 1.4, "Muscle Gain": 1.8, "Body Recomposition": 2.0}
SLOT_SHARE = {"Breakfast": 0.25, "Lunch": 0.30, "Dinner": 0.30, "Snack": 0.15}
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# (name, base kcal, tags: V=vegan K=keto D=diabetic-friendly, {ingredient: grams})
MEALS = {
    "Breakfast": [
        ("Oats with banana & peanut butter", 400, "V", {"Rolled oats": 60, "Banana": 100, "Peanut butter": 20, "Soy milk": 200}),
        ("Veggie omelette with whole-grain toast", 380, "D", {"Eggs": 150, "Spinach": 50, "Tomato": 60, "Whole-grain bread": 50, "Olive oil": 5}),
        ("Greek yogurt berry parfait", 350, "D", {"Greek yogurt": 200, "Mixed berries": 100, "Almonds": 20, "Chia seeds": 10}),
        ("Tofu scramble with veggies", 340, "VDK", {"Tofu": 200, "Spinach": 60, "Bell pepper": 60, "Olive oil": 10, "Turmeric": 2}),
        ("Avocado & egg bowl", 450, "DK", {"Eggs": 120, "Avocado": 100, "Spinach": 40, "Olive oil": 10}),
        ("Chia pudding with coconut milk", 330, "VDK", {"Chia seeds": 40, "Coconut milk": 150, "Almonds": 15}),
    ],
    "Lunch": [
        ("Grilled chicken quinoa bowl", 520, "D", {"Chicken breast": 150, "Quinoa": 80, "Broccoli": 100, "Olive oil": 10, "Lemon": 20}),
        ("Chickpea veggie curry with brown rice", 560, "VD", {"Chickpeas": 150, "Brown rice": 70, "Tomato": 100, "Onion": 50, "Coconut milk": 50, "Spinach": 50}),
        ("Lentil soup with whole-grain bread", 480, "VD", {"Red lentils": 80, "Carrot": 60, "Onion": 50, "Whole-grain bread": 50, "Olive oil": 10}),
        ("Chicken salad (no croutons)", 480, "DK", {"Chicken breast": 150, "Romaine lettuce": 100, "Parmesan": 25, "Olive oil": 15}),
        ("Tofu & veggie stir-fry bowl", 450, "VDK", {"Tofu": 200, "Broccoli": 100, "Bell pepper": 80, "Sesame oil": 10, "Soy sauce": 15}),
    ],
    "Dinner": [
        ("Baked salmon, sweet potato & greens", 560, "D", {"Salmon": 150, "Sweet potato": 150, "Green beans": 100, "Olive oil": 10}),
        ("Turkey meatballs with zucchini noodles", 500, "DK", {"Ground turkey": 160, "Zucchini": 200, "Tomato sauce": 80, "Olive oil": 10, "Parmesan": 15}),
        ("Black bean tacos with avocado", 540, "V", {"Black beans": 120, "Corn tortillas": 80, "Avocado": 60, "Tomato": 80, "Romaine lettuce": 40}),
        ("Tofu & cauliflower coconut curry", 500, "VDK", {"Tofu": 180, "Cauliflower": 150, "Coconut milk": 120, "Spinach": 50, "Curry paste": 15}),
        ("Grilled steak with asparagus & mushrooms", 580, "DK", {"Beef sirloin": 150, "Asparagus": 120, "Mushrooms": 100, "Olive oil": 10}),
        ("Shrimp stir-fry with brown rice", 520, "D", {"Shrimp": 150, "Brown rice": 70, "Broccoli": 100, "Bell pepper": 60, "Sesame oil": 10}),
    ],
    "Snack": [
        ("Apple with almond butter", 200, "V", {"Apple": 150, "Almond butter": 20}),
        ("Handful of mixed nuts", 200, "VDK", {"Mixed nuts": 30}),
        ("Hummus with carrot & cucumber sticks", 180, "VD", {"Hummus": 60, "Carrot": 80, "Cucumber": 80}),
        ("Cottage cheese with cucumber", 160, "DK", {"Cottage cheese": 150, "Cucumber": 80}),
        ("Boiled eggs", 160, "DK", {"Eggs": 100}),
    ],
}

GROCERY_CATEGORIES = {
    "🥬 Produce": ["spinach", "tomato", "broccoli", "bell pepper", "onion", "carrot", "banana", "berries", "lemon", "avocado", "romaine", "cucumber",
                   "zucchini", "green beans", "cauliflower", "asparagus", "mushroom", "apple", "sweet potato"],
    "🥩 Protein & Dairy": ["egg", "chicken", "salmon", "turkey", "beef", "shrimp", "tofu", "yogurt", "cottage", "parmesan"],
    "🌾 Grains & Legumes": ["oats", "bread", "quinoa", "rice", "lentil", "chickpea", "black beans", "tortilla"],
    "🥜 Nuts, Seeds & Pantry": ["almond", "peanut", "chia", "nuts", "hummus", "coconut", "soy", "olive oil", "sesame", "curry", "turmeric", "sauce"],
}


def categorize(item: str) -> str:
    low = item.lower()
    for cat, keys in GROCERY_CATEGORIES.items():
        if any(k in low for k in keys):
            return cat
    return "🧂 Other"


def bmr_mifflin(weight: float, height: float, age: int, gender: str) -> float:
    base = 10 * weight + 6.25 * height - 5 * age
    return base + {"Male": 5, "Female": -161}.get(gender, -78)


def macro_targets(kcal: float, weight: float, goal: str, constraints: list) -> dict:
    protein = PROTEIN_PER_KG[goal] * weight
    protein = min(protein, kcal * 0.4 / 4)  # never exceed 40% of calories
    if "Keto" in constraints:
        carbs = min(30.0, kcal * 0.05 / 4 * 4)
        fat = max((kcal - protein * 4 - carbs * 4) / 9, 0)
    elif "Diabetic-Friendly" in constraints:
        carbs = kcal * 0.40 / 4
        fat = max((kcal - protein * 4 - carbs * 4) / 9, 0)
    else:
        fat = kcal * 0.28 / 9
        carbs = max((kcal - protein * 4 - fat * 9) / 4, 0)
    return {"Protein": round(protein), "Carbs": round(carbs), "Fats": round(fat)}


def build_plan(target_kcal: float, constraints: list):
    need = ""
    if "Vegan" in constraints:
        need += "V"
    if "Keto" in constraints:
        need += "K"
    if "Diabetic-Friendly" in constraints:
        need += "D"
    notes = []
    pools = {}
    for slot, meals in MEALS.items():
        pool = [m for m in meals if set(need) <= set(m[2])]
        if not pool:  # relax: drop diabetic, then keto
            for drop in ("D", "K"):
                relaxed = need.replace(drop, "")
                pool = [m for m in meals if set(relaxed) <= set(m[2])]
                if pool:
                    notes.append(f"No {slot.lower()} matched every constraint; relaxed '{drop}' tag.")
                    break
        pools[slot] = pool or meals
    plan, grocery = [], defaultdict(float)
    for d in range(7):
        day = []
        for si, (slot, share) in enumerate(SLOT_SHARE.items()):
            pool = pools[slot]
            name, base_kcal, _tags, ing = pool[(d + si) % len(pool)]
            target = target_kcal * share
            scale = max(0.5, min(2.5, target / base_kcal))
            scaled = {k: round(v * scale) for k, v in ing.items()}
            for k, v in scaled.items():
                grocery[k] += v
            day.append({"slot": slot, "meal": name, "kcal": round(target), "ingredients": scaled})
        plan.append(day)
    return plan, dict(grocery), sorted(set(notes))


def fmt_qty(g: float) -> str:
    return f"{g / 1000:.2f} kg" if g >= 1000 else f"{g:.0f} g"

