from __future__ import annotations

from datetime import datetime
from typing import Dict, Any


def create_verifiable_credential(provider: Dict[str, Any]) -> Dict[str, Any]:
    """Create a simple Verifiable Credential for an approved provider."""
    if provider.get("status") != "approved":
        raise ValueError("Provider must be approved to issue credential")

    subject_id = provider.get("verification_id") or provider.get("id")
    if subject_id and not str(subject_id).startswith("urn:uuid:"):
        subject_id = f"urn:uuid:{subject_id}"

    credential = {
        "@context": ["https://www.w3.org/2018/credentials/v1"],
        "type": ["VerifiableCredential", "EducationalProvider"],
        "issuer": "https://certify3.io/kyc",
        "issuanceDate": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "credentialSubject": {
            "id": subject_id,
            "name": provider.get("organisation_name"),
        },
    }

    credential["proof"] = {
        "type": "Ed25519Signature2018",
        "created": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "proofPurpose": "assertionMethod",
        "verificationMethod": "https://certify3.io/keys/1",
        "jws": (
            "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9."
            "eyJleGFtcGxlIjoidmFsaWRhdGlvbiJ9."
            "Q1IzZVdUajB1RUJ5eEdPZmxrWkNDS1lMNjBpaWxIY2VFbFFydkV2QldYQT0="
        ),
    }

    return credential


__all__ = ["create_verifiable_credential"]
