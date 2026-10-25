from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from ..core import FRESH_PROMPT, demo_freshness, normalize_fresh, opencv_freshness_signals
from ..database import get_db
from ..llm import LLMConfig, call_llm, get_config, run_with_fallback
from .common import read_image, save_record

router = APIRouter(prefix="/api/freshness", tags=["Freshness"])


@router.post("/analyze")
def analyze_freshness(
    file: UploadFile = File(...),
    cfg: LLMConfig = Depends(get_config),
    db: Session = Depends(get_db),
):
    img = read_image(file)
    res = run_with_fallback(cfg, lambda: call_llm(cfg, FRESH_PROMPT, [img]), lambda: demo_freshness(img))
    res = normalize_fresh(res)
    res["signals"] = opencv_freshness_signals(img)
    return save_record(db, "freshness", f"{res.get('item', 'Item')} - {res['stage']}", res)
