from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..core import RECIPE_PROMPT_T, demo_recipes
from ..database import get_db
from ..llm import LLMConfig, call_llm, get_config, run_with_fallback
from .common import save_record

router = APIRouter(prefix="/api/recipes", tags=["Recipe Assistant"])


class RecipeRequest(BaseModel):
    pantry: list[str] = Field(min_length=1, max_length=60)
    diet: str = "No restriction"
    max_time: int = Field(default=30, ge=5, le=240)
    servings: int = Field(default=2, ge=1, le=12)


@router.post("/generate")
def generate_recipes(req: RecipeRequest, cfg: LLMConfig = Depends(get_config), db: Session = Depends(get_db)):
    pantry = [p.strip()[:60] for p in req.pantry if p.strip()]
    if not pantry:
        raise HTTPException(400, "Please list at least one ingredient.")
    prompt = RECIPE_PROMPT_T.format(pantry=", ".join(pantry), diet=req.diet, time=req.max_time, servings=req.servings)
    res = run_with_fallback(cfg, lambda: call_llm(cfg, prompt), lambda: demo_recipes(pantry, req.diet, req.max_time))
    res.setdefault("recipes", [])
    return save_record(db, "recipes", "Recipes from: " + ", ".join(pantry[:4]), res)
