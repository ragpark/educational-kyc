import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from starlette.testclient import TestClient
from app.main import app


def test_centre_submission_prefills_fields():
    client = TestClient(app)
    resp = client.get("/centre-submission", params={"qualification_id": "123", "qualification_title": "History A Level"})
    assert resp.status_code == 200
    html = resp.text
    assert 'value="123"' in html
    assert 'value="History A Level"' in html
