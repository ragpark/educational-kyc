import io

from fastapi.testclient import TestClient

from app.main import app, applications_db, lms_mis_assessment_runs, lms_mis_integrations


def test_lms_mis_page_requires_authentication():
    client = TestClient(app)
    response = client.get("/integrations/lms-mis", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/login"


def test_lms_mis_upload_assesses_learner_records_against_approved_qualifications():
    client = TestClient(app)

    login_response = client.post(
        "/login",
        data={"username": "centre1", "password": "centrepass"},
        follow_redirects=False,
    )
    assert login_response.status_code == 302

    applications_db.append(
        {
            "id": 9999,
            "awarding_organisation": "Example AO",
            "rn": "AO-1",
            "qualification_number": "QUAL-001",
            "qualification_title": "Level 3 Diploma in Teaching",
            "status": "Approved",
        }
    )

    try:
        csv_payload = (
            "learner_id,learner_name,qualification_id,qualification_title,registration_status\n"
            "L-001,Alice Smith,QUAL-001,Level 3 Diploma in Teaching,active\n"
            "L-002,Bob Jones,QUAL-404,Unknown Qualification,pending\n"
        )
        response = client.post(
            "/integrations/lms-mis/upload",
            files={"file": ("learners.csv", io.BytesIO(csv_payload.encode("utf-8")), "text/csv")},
        )

        assert response.status_code == 200
        assert "2 learner records processed" in response.text
        assert "1 matched approved qualifications" in response.text
        assert "1 flagged as not approved for this centre" in response.text
        assert "Eligible" in response.text
        assert "Not Approved" in response.text
    finally:
        applications_db.pop()
        lms_mis_integrations.clear()
        lms_mis_assessment_runs.clear()
