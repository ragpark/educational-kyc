from __future__ import annotations

from datetime import datetime
from typing import Dict, Any


def create_verifiable_credential(provider: Dict[str, Any]) -> Dict[str, Any]:
    """Create a simple Verifiable Credential for an approved provider."""
    if provider.get("status") != "approved":
        raise ValueError("Provider must be approved to issue credential")

    credential = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential", "EducationalProvider"],
        "issuer": "https://example.com/kyc",
        "issuanceDate": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "credentialSubject": {
            "id": provider.get("id"),
            "name": provider.get("organisation_name"),
        },
    }

    credential["proof"] = {
        "type": "Ed25519Signature2018",
        "created": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "proofPurpose": "assertionMethod",
        "verificationMethod": "https://example.com/keys/1",
        "jws": "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9...",
    }

    return credential


__all__ = ["create_verifiable_credential"]
