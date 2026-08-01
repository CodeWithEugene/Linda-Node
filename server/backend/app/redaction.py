"""Mask personal email addresses on every surface that leaves the database.

Raw upstream payloads are retained verbatim so provenance hashes stay
reproducible against the real endpoint, but ICPAC trigger rules carry the
notification addresses of named individuals. build.md 6.2 requires those to be
masked in every API response, UI render, packet, and export.
"""

from __future__ import annotations

import re
from typing import Any

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")


def mask_email(address: str) -> str:
    """`crimson.sikolia@igad.int` becomes `c***@igad.int`."""
    local, _, domain = address.partition("@")
    if not domain:
        return address
    return f"{local[:1]}***@{domain}"


def mask_text(value: str) -> str:
    return EMAIL_PATTERN.sub(lambda match: mask_email(match.group(0)), value)


def redact(value: Any) -> Any:
    """Recursively mask addresses in any JSON-shaped structure."""
    if isinstance(value, str):
        return mask_text(value)
    if isinstance(value, list):
        return [redact(item) for item in value]
    if isinstance(value, dict):
        return {key: redact(item) for key, item in value.items()}
    return value
