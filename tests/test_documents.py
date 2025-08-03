import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from fastapi.testclient import TestClient
from app.main import app, documents_storage
from datetime import datetime

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
    data = resp.json()
    assert data.get("success")

    # Check response contains expected assessments
    assert "assessments" in data
    assert data["assessments"][0]["assessment"] in {"green", "amber", "red"}

    # Also validate internal storage, if needed
    docs = documents_storage["Example Learning Centre"]
    assert docs[-1]["assessment"] == "green"
    assert docs[-1]["assessment_rationale"]


def test_image_upload_classification_default_red():
    documents_storage.clear()
    client.post("/login", data={"username": "centre1", "password": "centrepass"})
    # 1x1 PNG pixel
    img = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\xdac\xf8\x0f\x00\x01\x01\x01\x00\x18\xdd\x8d\xc5\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    resp = client.post(
        "/documents/upload", files={"files": ("class.png", img, "image/png")}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["assessments"][0]["image_relevance"] == "red"
    docs = documents_storage["Example Learning Centre"]
    assert docs[-1]["image_relevance"] == "red"


def test_override_image_classification():
    documents_storage.clear()
    client.post("/login", data={"username": "centre1", "password": "centrepass"})
    img = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
        b"\x00\x00\x00\nIDATx\xdac\xf8\x0f\x00\x01\x01\x01\x00\x18\xdd\x8d\xc5\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    client.post(
        "/documents/upload", files={"files": ("class.png", img, "image/png")}
    )
    resp = client.post(
        "/documents/0/classify", data={"classification": "green"}, allow_redirects=False
    )
    assert resp.status_code == 303
    assert documents_storage["Example Learning Centre"][0]["image_relevance"] == "green"


def test_documents_page_shows_assessment_and_rationale():
    documents_storage.clear()
    client.post("/login", data={"username": "centre1", "password": "centrepass"})
    year = datetime.utcnow().year
    content = f"Safeguarding Policy for {year} ensures child safety.".encode()
    client.post(
        "/documents/upload",
        files={"files": ("safeguarding_policy.txt", content)},
    )
    resp = client.get("/documents")
    assert resp.status_code == 200
    assert "Green" in resp.text
    assert "It appears relevant and up to date." in resp.text
