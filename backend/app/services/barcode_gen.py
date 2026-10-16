"""Barcode generation helpers (Code128) for printable product labels."""

import base64
from io import BytesIO

import barcode
from barcode.writer import SVGWriter

from app.core.exceptions import BusinessRuleError


def code128_svg_data_uri(value: str) -> str:
    """Render a Code128 barcode as an inline SVG data URI (no external deps at runtime)."""
    if not value:
        raise BusinessRuleError("Nilai barcode kosong.", code="BARCODE_EMPTY")
    if any(ord(ch) < 32 or ord(ch) > 127 for ch in value):
        raise BusinessRuleError(
            "Barcode hanya mendukung karakter ASCII standar (Code128B).",
            code="BARCODE_UNSUPPORTED",
        )
    code = barcode.get("code128", value, writer=SVGWriter())
    buffer = BytesIO()
    code.write(buffer)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"
