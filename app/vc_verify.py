from __future__ import annotations

from datetime import datetime
from typing import Dict, Any, Optional

# Simple trusted issuer and revocation data for demo purposes
TRUSTED_ISSUERS = {"https://certify3.io/kyc"}
AUTHORIZED_KEYS = {"https://certify3.io/kyc": {"https://certify3.io/keys/1"}}
TRUST_REGISTRY = {"https://certify3.io/kyc": {"EducationalProvider"}}
REVOKED_IDS = set()


def verify_credential(credential: Dict[str, Any], expected_subject: Optional[str] = None) -> Dict[str, Any]:
    """Validate a Verifiable Credential issued by this service."""
    issuer = credential.get("issuer")
    issuer_trusted = issuer in TRUSTED_ISSUERS

    proof = credential.get("proof", {})
    key_valid = issuer_trusted and proof.get("verificationMethod") in AUTHORIZED_KEYS.get(issuer, set())

    types = set(credential.get("type", []))
    trust_registry_ok = issuer_trusted and "EducationalProvider" in types and "EducationalProvider" in TRUST_REGISTRY.get(issuer, set())

    expiration = credential.get("expirationDate")
    not_expired = True
    if expiration:
        try:
            not_expired = datetime.fromisoformat(expiration.rstrip("Z")) > datetime.utcnow()
        except Exception:
            not_expired = False

    cred_id = credential.get("id") or credential.get("credentialSubject", {}).get("id")
    not_revoked = cred_id not in REVOKED_IDS

    subject_match = True
    if expected_subject:
        subject_match = credential.get("credentialSubject", {}).get("id") == expected_subject

    is_valid = all([issuer_trusted, key_valid, trust_registry_ok, not_expired, not_revoked, subject_match])

    return {
        "issuer_trusted": issuer_trusted,
        "key_valid": key_valid,
        "trust_registry_ok": trust_registry_ok,
        "not_expired": not_expired,
        "not_revoked": not_revoked,
        "subject_match": subject_match,
        "is_valid": is_valid,
    }


__all__ = ["verify_credential"]
