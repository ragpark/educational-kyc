import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.vc_issue import create_verifiable_credential
from app.vc_verify import verify_credential


def test_verify_valid_credential():
    provider = {
        "id": 1,
        "verification_id": "11111111-1111-1111-1111-111111111111",
        "organisation_name": "Test Provider",
        "status": "approved",
    }

    vc = create_verifiable_credential(provider)
    result = verify_credential(vc, expected_subject=vc["credentialSubject"]["id"])
    assert result["is_valid"]


def test_verify_revoked_credential_fails():
    provider = {
        "id": 1,
        "verification_id": "11111111-1111-1111-1111-111111111111",
        "organisation_name": "Test Provider",
        "status": "approved",
        "revoked": True,
        "revocation_reason": "Poor Credit",
    }

    vc = create_verifiable_credential(provider)
    result = verify_credential(vc, expected_subject=vc["credentialSubject"]["id"])
    assert not result["is_valid"]
    assert not result["not_revoked"]
