import os
import sys
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import app.main as main_module  # noqa: E402
from app.main import app  # noqa: E402


def test_tna_upload_suggests_courses(monkeypatch):
    def fake_suggest(text: str):
        return [{"id": 1, "title": "Python Basics", "score": 0.9}]

    monkeypatch.setattr(main_module, "suggest_courses_from_text", fake_suggest)
    client = TestClient(app)
    client.post("/login", data={"username": "centre1", "password": "centrepass"})
    tna_text = "Need training in Python programming."
    resp = client.post("/tna", files={"file": ("tna.txt", tna_text.encode())})
    assert resp.status_code == 200
    assert "Python Basics" in resp.text
