import types
import sys
import importlib

from fastapi import FastAPI
from fastapi.testclient import TestClient


# Provide a lightweight recommendation module so the main app can import it
dummy_module = types.ModuleType("backend.recommend")
dummy_module.app = FastAPI()


@dummy_module.app.get("/recommend/{centre_id}")
def _unused_route(centre_id: int, top_n: int = 10):
    """Placeholder route not used in tests but required for FastAPI mount."""
    return {"centre": {"id": centre_id}, "recommendations": []}


def recommend(centre_id: int, top_n: int = 10):
    return {
        "centre": {"id": centre_id},
        "recommendations": [{"id": 1, "title": "Dummy", "score": 0.5}],
    }


dummy_module.recommend = recommend
sys.modules["backend.recommend"] = dummy_module


from app.main import app  # noqa: E402  # import after dummy module injection
import app.main as main_module  # noqa: E402


def test_build_recommendations(monkeypatch):
    """Ensure the build-recommendations endpoint returns recommendation data."""

    # Avoid running the actual ETL and reloading during tests
    monkeypatch.setattr(main_module, "run_etl", lambda: None)
    monkeypatch.setattr(importlib, "reload", lambda module: module)

    client = TestClient(app)
    resp = client.post("/build-recommendations", json={"centre_id": 1, "top_n": 1})
    assert resp.status_code == 200
    data = resp.json()
    assert data["centre"]["id"] == 1
    assert len(data["recommendations"]) == 1

