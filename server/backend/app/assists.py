"""Constrained Gemini assists. They only return structured suggestions.

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


def assist_status() -> dict[str, Any]:
    return {"available": bool(settings.gemini_api_key), "model": settings.gemini_model if settings.gemini_api_key else None}


async def _gemini(name: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not settings.gemini_api_key:
        raise AssistUnavailable("Gemini is not configured")
    spec = ASSIST_SPECS[name]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{settings.gemini_model}:generateContent"
    body = {
        "systemInstruction": {"parts": [{"text": spec["prompt"]}]},
        "contents": [{"role": "user", "parts": [{"text": json.dumps(payload, sort_keys=True)}]}],
        "generationConfig": {
            "temperature": 0.2,
            "responseMimeType": "application/json",
            "responseJsonSchema": spec["schema"],
        },
    }
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(url, params={"key": settings.gemini_api_key}, json=body)
                response.raise_for_status()
            text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
            result = json.loads(text)
            Draft202012Validator(spec["schema"]).validate(result)
            return result
        except (httpx.HTTPError, KeyError, IndexError, json.JSONDecodeError, ValidationError) as exc:
            if attempt == 1:
                raise AssistUnavailable("Gemini did not return valid structured output") from exc
            body["contents"][0]["parts"].append({"text": f"Previous output failed validation: {exc}. Return JSON matching the supplied schema."})
    raise AssistUnavailable("Gemini did not return structured output")


async def run_matcher(case: dict[str, Any]) -> dict[str, Any]:
    eligible_ids = set(case["assessment"].get("eligible_action_cards", []))
    eligible = [card for card in case["action_cards"] if card["id"] in eligible_ids]
    result = await _gemini("matcher", {"assessment": case["assessment"], "eligible_cards": [{"id": card["id"], "title": card["title"]} for card in eligible]})
    allowed = {card["id"] for card in eligible}
    candidates = result.get("candidates", [])
    if not isinstance(candidates, list) or any(item.get("card_id") not in allowed for item in candidates if isinstance(item, dict)):
        raise AssistUnavailable("Matcher output failed card-id validation")
    return {"candidates": candidates, "disclaimer": "AI ranking is descriptive only; deterministic eligibility remains authoritative."}


async def run_explainer(case: dict[str, Any]) -> dict[str, Any]:
    snapshot_ids = {item["id"] for item in case["evidence"]}
    result = await _gemini("explainer", {"assessment": case["assessment"], "evidence": [{"id": item["id"], "label": item["label"], "hash": item["payload_sha256"]} for item in case["evidence"]]})
    if any(item not in snapshot_ids for item in result.get("cited_snapshot_ids", [])):
        raise AssistUnavailable("Evidence Explainer cited an unknown snapshot")
    return result


async def run_blocker(report: str) -> dict[str, Any]:
    result = await _gemini("blockers", {"field_report": report, "taxonomy": sorted(BLOCKER_CODES)})
    if result.get("code") not in BLOCKER_CODES or result.get("severity") not in {"critical", "normal"}:
        raise AssistUnavailable("Blocker output failed taxonomy validation")
    required = {"code", "severity", "summary", "needs_human_review"}
    if not required.issubset(result):
        raise AssistUnavailable("Blocker output missed a required field")
    return result
