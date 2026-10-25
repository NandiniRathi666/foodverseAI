"""Food Verse AI - FastAPI backend entrypoint.  Run: uvicorn app.main:app --reload"""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import models  # noqa: F401  (registers tables)
from .config import cors_origins
from .core import cv2
from .database import Base, engine, get_db
from .llm import LLMConfig, get_config
from .routers import food, freshness, history, hygiene, planner, recipes


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)  # creates tables on first start
    yield


app = FastAPI(title="Food Verse AI API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (food, freshness, hygiene, recipes, planner, history):
    app.include_router(r.router)


@app.get("/api/health", tags=["System"])
def health(cfg: LLMConfig = Depends(get_config), db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:  # noqa: BLE001
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "database": db_ok,
        "database_type": engine.dialect.name,
        "ai_mode": "live" if cfg.live else "demo",
        "provider": cfg.provider,
        "opencv": cv2 is not None,
    }
