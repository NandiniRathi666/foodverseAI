"""API tests (demo mode, temporary SQLite DB). Run: pytest"""
import io
import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ.pop("GEMINI_API_KEY", None)

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.main import app  # noqa: E402


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (80, 80), (180, 90, 40)).save(buf, "PNG")
    return buf.getvalue()


def test_all_endpoints_and_history():
    with TestClient(app) as c:
        h = c.get("/api/health").json()
        assert h["database"] and h["ai_mode"] == "demo"

        files = {"file": ("m.png", _png(), "image/png")}
        r = c.post("/api/food/analyze", files=files)
        assert r.status_code == 200 and r.json()["_source"] == "demo" and r.json()["saved"]

        assert c.post("/api/freshness/analyze", files={"file": ("f.png", _png(), "image/png")}).status_code == 200
        assert c.post("/api/hygiene/analyze", files={"file": ("k.png", _png(), "image/png")}).status_code == 200

        r = c.post("/api/recipes/generate", json={"pantry": ["rice", "egg"], "diet": "No restriction", "max_time": 30, "servings": 2})
        assert r.status_code == 200 and r.json()["recipes"]

        opts = c.get("/api/planner/options").json()
        r = c.post("/api/planner/generate", json={"age": 28, "gender": "Male", "weight": 70, "height": 170,
                                                  "activity": opts["activity"][2], "goal": "Fat Loss", "constraints": ["Keto"]})
        assert r.status_code == 200 and len(r.json()["days"]) == 7

        hist = c.get("/api/history").json()
        assert len(hist) >= 5
        rid = hist[0]["id"]
        assert c.get(f"/api/history/{rid}").json()["result"]
        assert c.delete(f"/api/history/{rid}").status_code == 200
        assert c.get(f"/api/history/{rid}").status_code == 404


def test_bad_upload_rejected():
    with TestClient(app) as c:
        r = c.post("/api/food/analyze", files={"file": ("x.png", b"not an image", "image/png")})
        assert r.status_code == 400
