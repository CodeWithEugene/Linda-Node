"""Versioned, schema-validated, read-only policy and action-card library.

Policy content is code-reviewed YAML. Both documents are validated against
JSON Schemas at load; the app refuses to serve an invalid policy (build.md 6.4)
rather than silently assessing against a malformed rulebook.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from .config import CONTENT_ROOT
from .domain import sha256

SCHEMA_ROOT = Path(CONTENT_ROOT) / "schemas"


class PolicyInvalid(RuntimeError):
    """Raised at startup when policy.yaml or an action card fails its schema."""


def _validator(name: str) -> Draft202012Validator:
    return Draft202012Validator(json.loads((SCHEMA_ROOT / f"{name}.schema.json").read_text(encoding="utf-8")))


def _read_yaml(path: Path) -> tuple[str, dict[str, Any]]:
    raw = path.read_text(encoding="utf-8")
    return raw, yaml.safe_load(raw)


def _check(validator: Draft202012Validator, document: Any, label: str) -> None:
    errors = [f"{error.json_path}: {error.message}" for error in validator.iter_errors(document)]
    if errors:
        raise PolicyInvalid(f"{label} failed schema validation — {'; '.join(errors[:5])}")


@lru_cache(maxsize=1)
def _policy_document() -> dict[str, Any]:
    raw, parsed = _read_yaml(Path(CONTENT_ROOT) / "policy.yaml")
    _check(_validator("policy"), parsed, "policy.yaml")
    return {"id": sha256(raw), "raw": raw, "data": parsed, "name": "policy.yaml", "schema_valid": True}


@lru_cache(maxsize=1)
def _action_card_documents() -> tuple[dict[str, Any], ...]:
    validator = _validator("action_card")
    cards: list[dict[str, Any]] = []
    for path in sorted((Path(CONTENT_ROOT) / "actions").glob("*.yaml")):
        raw, data = _read_yaml(path)
        _check(validator, data, path.name)
        cards.append({**data, "version_hash": sha256(raw), "raw": raw, "source_file": path.name})
    if not cards:
        raise PolicyInvalid("No action cards found in content/actions/")
    identifiers = [card["id"] for card in cards]
    duplicates = sorted({item for item in identifiers if identifiers.count(item) > 1})
    if duplicates:
        raise PolicyInvalid(f"Duplicate action card ids: {', '.join(duplicates)}")
    return tuple(cards)


def policy() -> dict[str, Any]:
    return dict(_policy_document())


def action_cards() -> list[dict[str, Any]]:
    return [dict(card) for card in _action_card_documents()]


def card_by_id(card_id: str) -> dict[str, Any] | None:
    return next((card for card in action_cards() if card["id"] == card_id), None)


def validate_library() -> dict[str, Any]:
    """Called at application startup so a bad rulebook fails loudly and early."""
    document = policy()
    return {"policy_version_id": document["id"], "action_cards": len(action_cards()), "schema_valid": True}
