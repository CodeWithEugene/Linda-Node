"""Vendored Husika Data Ingestor OpenAPI contract and local validation.

The app deliberately validates payloads but never posts them to Husika. The
snapshot metadata makes the exercise contract inspectable and refreshable.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .domain import sha256

CONTRACT_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "husika_openapi"
SPEC_PATH = CONTRACT_ROOT / "ingestor.openapi.json"
META_PATH = CONTRACT_ROOT / "ingestor.openapi.meta.json"


def _spec() -> dict[str, Any]:
    return json.loads(SPEC_PATH.read_text(encoding="utf-8"))


def metadata() -> dict[str, Any]:
    value = json.loads(META_PATH.read_text(encoding="utf-8"))
    value["sha256"] = sha256(SPEC_PATH.read_bytes())
    value["title"] = _spec()["info"]["title"]
    value["version"] = _spec()["info"]["version"]
    return value


def _inline_refs(value: Any, document: dict[str, Any]) -> Any:
    if isinstance(value, list):
        return [_inline_refs(item, document) for item in value]
    if not isinstance(value, dict):
        return value
    if "$ref" in value and value["$ref"].startswith("#/components/schemas/"):
        name = value["$ref"].rsplit("/", 1)[1]
        referenced = _inline_refs(copy.deepcopy(document["components"]["schemas"][name]), document)
        overrides = {key: item for key, item in value.items() if key != "$ref"}
        return _inline_refs({**referenced, **overrides}, document)
    return {key: _inline_refs(item, document) for key, item in value.items()}


def validate(payload: dict[str, Any]) -> None:
    """Validate the exact request bodies for the three Husika write endpoints."""
    document = _spec()
    validators = {
        "threat": Draft202012Validator(_inline_refs(document["components"]["schemas"]["ThreatCreate"], document)),
        "broadcast": Draft202012Validator(_inline_refs(document["components"]["schemas"]["BroadcastCreate"], document)),
        "message": Draft202012Validator(_inline_refs(document["components"]["schemas"]["BroadcastMessageBase"], document)),
        "location": Draft202012Validator(_inline_refs(document["components"]["schemas"]["ContentLocationCreate"], document)),
    }
    errors = []
    for name, validator in validators.items():
        resource = payload["requests"][name]
        errors.extend(f"{name}{error.json_path}: {error.message}" for error in validator.iter_errors(resource))
    if errors:
        raise ValueError("Husika OpenAPI validation failed: " + "; ".join(errors))
