import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.vc_issue import create_verifiable_credential


def test_vc_contains_proof_and_issuer():
    provider = {
        "id": 1,
        "verification_id": "11111111-1111-1111-1111-111111111111",
        "organisation_name": "Test Provider",
        "status": "approved",
    }

    vc = create_verifiable_credential(provider)

    assert vc["issuer"] == "https://certify3.io/kyc"
    assert vc["credentialSubject"]["id"].startswith("urn:uuid:")
    assert "proof" in vc and "jws" in vc["proof"]
