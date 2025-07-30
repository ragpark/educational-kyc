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


    try:
        # Pillow's Image.save requires the format when saving to a buffer.
        # If Pillow isn't installed, qrcode falls back to a PyPNG implementation
        # whose save() method does not accept the format argument.
        img.save(buf, format="PNG")
    except TypeError:
        img.save(buf)

    img.save(buf, format="PNG")


    return base64.b64encode(buf.getvalue()).decode()


__all__ = ["generate_qr_code"]
