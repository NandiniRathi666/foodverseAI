import io
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..core import DEMO_HYGIENE, HYGIENE_PROMPT, extract_frames, img_hash, normalize_hygiene, prep_image
from ..database import get_db
from ..llm import LLMConfig, call_llm, get_config, run_with_fallback
from .common import read_upload, save_record

router = APIRouter(prefix="/api/hygiene", tags=["Kitchen Hygiene"])
VIDEO_EXT = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


@router.post("/analyze")
def analyze_hygiene(
    file: UploadFile = File(...),
    cfg: LLMConfig = Depends(get_config),
    db: Session = Depends(get_db),
):
    data = read_upload(file)
    is_video = (file.content_type or "").startswith("video/") or os.path.splitext(file.filename or "")[1].lower() in VIDEO_EXT
    try:
        frames = extract_frames(data, file.filename or "clip.mp4", 4) if is_video else [prep_image(io.BytesIO(data))]
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"Could not read the {'video' if is_video else 'image'}: {e}")

    raw = run_with_fallback(
        cfg,
        lambda: call_llm(cfg, HYGIENE_PROMPT, frames),
        lambda: dict(DEMO_HYGIENE[img_hash(frames) % len(DEMO_HYGIENE)]),
    )
    res = normalize_hygiene(raw)
    res.pop("checks", None)  # raw form is replaced by normalized `rows`
    res["frames_analyzed"] = len(frames)
    res["input_type"] = "video" if is_video else "image"
    score = res["score"]
    return save_record(db, "hygiene", f"Hygiene audit - {score if score is not None else 'n/a'}%", res)
