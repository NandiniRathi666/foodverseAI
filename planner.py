from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core import (
    ACTIVITY, DAYS, GOALS, bmr_mifflin, build_plan, categorize, fmt_qty, macro_targets,
)
from ..database import get_db
from ..llm import LLMConfig, call_llm, get_config
from .common import save_record

router = APIRouter(prefix="/api/planner", tags=["Meal Planner"])
ALLOWED_CONSTRAINTS = {"Vegan", "Keto", "Diabetic-Friendly"}


class Profile(BaseModel):
    age: int = Field(ge=14, le=90)
    gender: str = "Male"
    weight: float = Field(ge=35, le=250)
    height: float = Field(ge=120, le=230)
    activity: str
    goal: str
    constraints: list[str] = []


@router.get("/options")
def options():
    return {
        "activity": list(ACTIVITY),
        "goals": list(GOALS),
        "constraints": sorted(ALLOWED_CONSTRAINTS),
        "genders": ["Male", "Female", "Other"],
    }


@router.post("/generate")
def generate_plan(p: Profile, cfg: LLMConfig = Depends(get_config), db: Session = Depends(get_db)):
    if p.activity not in ACTIVITY:
        raise HTTPException(400, "Unknown activity level.")
    if p.goal not in GOALS:
        raise HTTPException(400, "Unknown goal.")
    if p.gender not in ("Male", "Female", "Other"):
        raise HTTPException(400, "Unknown gender.")
    constraints = [c for c in p.constraints if c in ALLOWED_CONSTRAINTS]

    bmr = bmr_mifflin(p.weight, p.height, p.age, p.gender)
    tdee = bmr * ACTIVITY[p.activity]
    floor = 1500 if p.gender == "Male" else 1200
    raw_target = tdee * (1 + GOALS[p.goal])
    target = max(raw_target, floor)
    plan, grocery, notes = build_plan(target, constraints)

    coach = None
    if cfg.live:
        try:
            prompt = (
                'Give 4 concise, practical, non-medical coaching tips as JSON {"tips":[str]} for a '
                f"{p.age}-year-old {p.gender.lower()}, {p.weight} kg, goal {p.goal}, "
                f"constraints {constraints or 'none'}, daily target {target:.0f} kcal."
            )
            coach = call_llm(cfg, prompt).get("tips")
        except Exception:  # noqa: BLE001
            coach = None

    days = [
        {"day": name, "total_kcal": sum(m["kcal"] for m in day), "meals": day}
        for name, day in zip(DAYS, plan)
    ]
    rows = sorted(
        ({"category": categorize(k), "item": k, "grams": round(v), "quantity": fmt_qty(v)} for k, v in grocery.items()),
        key=lambda r: (r["category"], r["item"]),
    )
    res = {
        "bmr": round(bmr),
        "tdee": round(tdee),
        "target": round(target),
        "floor_applied": raw_target < floor,
        "floor": floor,
        "macros": macro_targets(target, p.weight, p.goal, constraints),
        "days": days,
        "grocery": rows,
        "notes": notes,
        "coach": coach,
        "goal": p.goal,
        "constraints": constraints,
        "_source": "live" if coach else "local",
    }
    return save_record(db, "planner", f"{p.goal} plan - {round(target)} kcal", res)
