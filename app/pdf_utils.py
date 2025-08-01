from __future__ import annotations

import base64
import io
import json
from typing import Any, Dict

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas


def generate_credential_pdf(credential: Dict[str, Any], qr_b64: str) -> bytes:
    """Return PDF bytes containing credential details and a QR code."""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    subject = credential.get("credentialSubject", {})
    subject_name = subject.get("name", "")
    issuer = credential.get("issuer", "")
    issuance_date = credential.get("issuanceDate", "")

    c.setFont("Helvetica-Bold", 14)
    c.drawString(20 * mm, height - 30 * mm, f"Credential for: {subject_name}")
    c.setFont("Helvetica", 12)
    c.drawString(20 * mm, height - 40 * mm, f"Issuer: {issuer}")
    c.drawString(20 * mm, height - 50 * mm, f"Issued: {issuance_date}")

    # QR code
    try:
        qr_bytes = base64.b64decode(qr_b64)
        qr_img = ImageReader(io.BytesIO(qr_bytes))
        c.drawImage(qr_img, width - 60 * mm, height - 70 * mm, 40 * mm, 40 * mm)
    except Exception:
        pass

    c.setFont("Courier", 8)
    text_obj = c.beginText(20 * mm, height - 80 * mm)
    for line in json.dumps(credential, indent=2).splitlines():
        text_obj.textLine(line)
    c.drawText(text_obj)

    c.showPage()
    c.save()
    return buf.getvalue()


__all__ = ["generate_credential_pdf"]
