import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from starlette.testclient import TestClient
from app.main import app, applications_db


def test_centre_submission_populates_applications_table():
    client = TestClient(app)
    applications_db.clear()
    data = {
        "verification_id": "verif123",
        "qualification_id": "QUAL123",
        "ao_id": "AO999",
        "ao_name": "Test Awarding Org",
        "title": "Test Qualification",
        "start_date": "2025-09-01",
        "cohort_size": "30",
        "staff_id": "S1",
        "staff_role": "Manager",
        "staff_name": "Alice",
        "staff_email": "alice@example.com",
        "ofqual_ack": "on",
        "gdpr_consent": "on",
        "share_aos": "on",
        # Additional fields required by handler
        "group_ukprn": "G123",
        "legal_name": "My Org",
        "organisation_type": "College",
        "address_line1": "1 Street",
        "postcode": "AB1 2CD",
        "site_id": "SITE1",
        "site_ukprn": "10000001",
        "site_name": "Main Site",
    }
    resp = client.post("/centre-submission", data=data)
    assert resp.status_code == 200
    assert len(applications_db) == 1
    app_entry = applications_db[0]
    assert app_entry["awarding_organisation"] == "Test Awarding Org"
    assert app_entry["rn"] == "AO999"
    assert app_entry["qualification_number"] == "QUAL123"
    assert app_entry["qualification_title"] == "Test Qualification"

