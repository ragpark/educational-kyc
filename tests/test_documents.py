import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi.testclient import TestClient
from app.main import app, documents_storage

client = TestClient(app)

def test_documents_upload_requires_auth():
    documents_storage.clear()
    resp = client.post("/documents/upload", files={"files": ("test.txt", b"hi")})
    assert resp.status_code == 401


def test_documents_upload_success():
    documents_storage.clear()
    client.post("/login", data={"username": "centre1", "password": "centrepass"})
    resp = client.post("/documents/upload", files={"files": ("test.txt", b"hi")})
    assert resp.status_code == 200
    assert resp.json().get("success")


def test_safeguarding_policy_assessment():
    documents_storage.clear()
    client.post("/login", data={"username": "centre1", "password": "centrepass"})
    content = b"Safeguarding Policy for 2024 ensures child safety."
    resp = client.post(
        "/documents/upload",
        files={"files": ("safeguarding_policy.txt", content)},
    )
    assert resp.status_code == 200
    docs = documents_storage["Example Learning Centre"]
    assert docs[-1]["assessment"] == "green"
    assert docs[-1]["assessment_rationale"]
