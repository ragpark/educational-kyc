from __future__ import annotations

import base64
import io
from typing import Any

import qrcode


def generate_qr_code(data: str) -> str:
    """Return base64-encoded PNG representing a QR code for the given data."""
    qr = qrcode.QRCode(box_size=4, border=1)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


__all__ = ["generate_qr_code"]
