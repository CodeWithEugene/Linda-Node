"""Versioned, read-only demo policy and action-card library.

Policy content is code-reviewed YAML. This module exposes a parsed view to the
runtime and a raw view to the Policy Library screen.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .config import CONTENT_ROOT
from .domain import sha256


def _read_yaml(path: Path) -> tuple[str, dict[str, Any]]:
    raw = path.read_text(encoding="utf-8")
    return raw, yaml.safe_load(raw)


def policy() -> dict[str, Any]:
    raw, parsed = _read_yaml(CONTENT_ROOT / "policy.yaml")
    return {"id": sha256(raw), "raw": raw, "data": parsed, "name": "policy.yaml"}


def action_cards() -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    for path in sorted((CONTENT_ROOT / "actions").glob("*.yaml")):
        raw, data = _read_yaml(path)
        cards.append({**data, "version_hash": sha256(raw), "raw": raw})
    return cards


def card_by_id(card_id: str) -> dict[str, Any] | None:
    return next((card for card in action_cards() if card["id"] == card_id), None)
