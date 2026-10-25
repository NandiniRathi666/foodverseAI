import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Record

router = APIRouter(prefix="/api/history", tags=["History"])


def _row(r: Record) -> dict:
    return {"id": r.id, "kind": r.kind, "title": r.title, "created_at": r.created_at.isoformat()}


@router.get("")
def list_history(kind: str | None = None, limit: int = Query(50, ge=1, le=200), db: Session = Depends(get_db)):
    q = select(Record).order_by(Record.created_at.desc(), Record.id.desc()).limit(limit)
    if kind:
        q = q.where(Record.kind == kind)
    return [_row(r) for r in db.scalars(q)]


@router.get("/{record_id}")
def get_record(record_id: int, db: Session = Depends(get_db)):
    r = db.get(Record, record_id)
    if not r:
        raise HTTPException(404, "Record not found.")
    return {**_row(r), "result": json.loads(r.payload)}


@router.delete("/{record_id}")
def delete_record(record_id: int, db: Session = Depends(get_db)):
    r = db.get(Record, record_id)
    if not r:
        raise HTTPException(404, "Record not found.")
    db.delete(r)
    db.commit()
    return {"deleted": record_id}
