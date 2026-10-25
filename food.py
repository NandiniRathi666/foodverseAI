from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from ..core import DEMO_DISHES, FOOD_PROMPT, img_hash, normalize_food
from ..database import get_db
from ..llm import LLMConfig, call_llm, get_config, run_with_fallback
from .common import read_image, save_record

router = APIRouter(prefix="/api/food", tags=["Food Recognition"])


@router.post("/analyze")
def analyze_food(
    file: UploadFile = File(...),
    cfg: LLMConfig = Depends(get_config),
    db: Session = Depends(get_db),
):
    img = read_image(file)
    res = run_with_fallback(
        cfg,
        lambda: call_llm(cfg, FOOD_PROMPT, [img]),
        lambda: dict(DEMO_DISHES[img_hash([img]) % len(DEMO_DISHES)]),
    )
    res = normalize_food(res)
    return save_record(db, "food", res.get("dish_name", "Meal"), res)
