"""Constrained NVIDIA NIM assists. They only return structured suggestions.

No endpoint in this module can mutate a case or alter policy eligibility.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from jsonschema import Draft202012Validator, ValidationError

from .config import settings
from .domain import BLOCKER_CODES
from .prompts import ASSIST_SPECS


class AssistUnavailable(Exception):
    pass


def _normalise_to_schema(value: Any, schema: dict[str, Any]) -> Any:
    """Discard model-only fields before validating the returned contract.

    NVIDIA NIM models sometimes add explanatory fields despite being asked for
    JSON only. The UI and audit log receive only the local, schema-defined
    shape; missing or invalid required values still fail validation.
    """
    if schema.get("type") == "object" and isinstance(value, dict):
        properties = schema.get("properties", {})
        return {
            key: _normalise_to_schema(value[key], child_schema)
            for key, child_schema in properties.items()
            if key in value and isinstance(child_schema, dict)
        }
    if schema.get("type") == "array" and isinstance(value, list) and isinstance(schema.get("items"), dict):
        return [_normalise_to_schema(item, schema["items"]) for item in value]
    return value


def assist_status() -> dict[str, Any]:
    return {"available": bool(settings.nvidia_api_key), "model": settings.nvidia_model if settings.nvidia_api_key else None}


async def _nvidia(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not settings.nvidia_api_key:
        raise AssistUnavailable("NVIDIA NIM is not configured")
    spec = ASSIST_SPECS[name]
    schema_instruction = json.dumps(spec["schema"], sort_keys=True)
    body = {
        "model": settings.nvidia_model,
        "messages": [
            {
                "role": "system",
                "content": (
                    spec["prompt"]
                    + "\nReturn one JSON object matching this JSON Schema and nothing else:\n"
                    + schema_instruction
                ),
            },
            {"role": "user", "content": json.dumps(payload, sort_keys=True)},
        ],
        "temperature": 0.2,
        "max_tokens": 1024,
        "stream": False,
    }
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"{settings.nvidia_base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.nvidia_api_key}"},
                    json=body,
                )
                response.raise_for_status()
            text = response.json()["choices"][0]["message"]["content"]
            if not isinstance(text, str):
                raise ValueError("NVIDIA NIM response content was not text")
            result = _normalise_to_schema(json.loads(text), spec["schema"])
            Draft202012Validator(spec["schema"]).validate(result)
            return result
        except (httpx.HTTPError, KeyError, IndexError, ValueError, json.JSONDecodeError, ValidationError) as exc:
            if attempt == 1:
                raise AssistUnavailable("NVIDIA NIM did not return valid structured output") from exc
            body["messages"].append({"role": "user", "content": "Return only one JSON object that matches the required schema."})
    raise AssistUnavailable("NVIDIA NIM did not return structured output")


async def run_matcher(case: dict[str, Any]) -> dict[str, Any]:
    eligible_ids = set(case["assessment"].get("eligible_action_cards", []))
    eligible = [card for card in case["action_cards"] if card["id"] in eligible_ids]
    result = await _nvidia("matcher", {"assessment": case["assessment"], "eligible_cards": [{"id": card["id"], "title": card["title"]} for card in eligible]})
    allowed = {card["id"] for card in eligible}
    candidates = result.get("candidates", [])
    if not isinstance(candidates, list) or any(item.get("card_id") not in allowed for item in candidates if isinstance(item, dict)):
        raise AssistUnavailable("Matcher output failed card-id validation")
    return {"candidates": candidates, "disclaimer": "AI ranking is descriptive only; deterministic eligibility remains authoritative."}


async def run_explainer(case: dict[str, Any]) -> dict[str, Any]:
    snapshot_ids = {item["id"] for item in case["evidence"]}
    result = await _nvidia("explainer", {"assessment": case["assessment"], "evidence": [{"id": item["id"], "label": item["label"], "hash": item["payload_sha256"]} for item in case["evidence"]]})
    if any(item not in snapshot_ids for item in result.get("cited_snapshot_ids", [])):
        raise AssistUnavailable("Evidence Explainer cited an unknown snapshot")
    return result


async def run_blocker(report: str) -> dict[str, Any]:
    result = await _nvidia("blockers", {"field_report": report, "taxonomy": sorted(BLOCKER_CODES)})
    if result.get("code") not in BLOCKER_CODES or result.get("severity") not in {"critical", "normal"}:
        raise AssistUnavailable("Blocker output failed taxonomy validation")
    required = {"code", "severity", "summary", "needs_human_review"}
    if not required.issubset(result):
        raise AssistUnavailable("Blocker output missed a required field")
    return result
