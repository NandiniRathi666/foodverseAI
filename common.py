import io
import json

from fastapi import HTTPException, UploadFile
from PIL import Image
from sqlalchemy.orm import Session

from ..config import MAX_UPLOAD_BYTES
from ..core import prep_image
from ..models import Record


def read_upload(upload: UploadFile) -> bytes:
    data = upload.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"File too large (limit {MAX_UPLOAD_BYTES // 1024 // 1024} MB).")
    if not data:
        raise HTTPException(400, "Empty file.")
    return data


def read_image(upload: UploadFile) -> Image.Image:
    data = read_upload(upload)
    try:
        return prep_image(io.BytesIO(data))
    except Exception:  # noqa: BLE001
        raise HTTPException(400, "Could not read the uploaded file as an image.")


def save_record(db: Session, kind: str, title: str, result: dict) -> dict:
    """Persist the result; a database problem never breaks the analysis itself."""
    try:
        rec = Record(kind=kind, title=(title or kind)[:200], payload=json.dumps(result, default=str))
        db.add(rec)
        db.commit()
        db.refresh(rec)
        result["id"] = rec.id
        result["created_at"] = rec.created_at.isoformat()
        result["saved"] = True
    except Exception:  # noqa: BLE001
        db.rollback()
        result["saved"] = False
    return result
