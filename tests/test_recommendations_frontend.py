from fastapi.testclient import TestClient
from app.main import app


def test_recommendations_page_served():
    client = TestClient(app)
    resp = client.get("/recommendations/index.htm?centre_id=1")
    assert resp.status_code == 200
    assert "Course Recommendations" in resp.text


def test_dashboard_js_served():
    client = TestClient(app)
    resp = client.get("/recommendations/Dashboard.js")
    assert resp.status_code == 200
    assert "getInitialCentreId" in resp.text
