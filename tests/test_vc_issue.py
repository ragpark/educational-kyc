import os, sys; sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.vc_issue import create_verifiable_credential


def test_vc_contains_proof():
    provider = {
        "id": "prov-123",
        "organisation_name": "Test Provider",
        "status": "approved",
    }

    vc = create_verifiable_credential(provider)
    assert "proof" in vc
