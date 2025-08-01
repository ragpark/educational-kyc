import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app, providers_db

client = TestClient(app)


def test_credential_pdf_download():
    provider = {
        "id": 99,
        "verification_id": "test-pdf",
        "organisation_name": "PDF Provider",
        "status": "approved",
    }
    providers_db.append(provider)
    resp = client.get("/credential/test-pdf/download")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("application/pdf")
    assert "attachment" in resp.headers.get("content-disposition", "")
    providers_db.remove(provider)
