"""Pure, transparent assessment of a decision case against policy.yaml."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .library import action_cards, policy

STAGE_ORDER = {"ready": 1, "set": 2, "go": 3}


def _forecast_values(snapshots: list[dict[str, Any]]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for snapshot in snapshots:
        records.extend(snapshot["payload"].get("forecasts", []))
    return max(records, key=lambda item: item.get("probability", 0), default={})


def _age_days(timestamp: str) -> int:
    try:
        return max(0, (datetime.now(UTC) - datetime.fromisoformat(timestamp.replace("Z", "+00:00"))).days)
    except ValueError:
        return 9999


def evaluate(snapshots: list[dict[str, Any]], hazard: str) -> dict[str, Any]:
    document = policy()["data"]["policy"]
    forecast = _forecast_values(snapshots)
    probability = float(forecast.get("probability", 0))
    quantile = float(forecast.get("quantile", 1))
    lead_months = int(forecast.get("lead_months", 0))
    trace = []
    stage = "ready"
    for name, definition in document["stages"].items():
        condition = definition["condition"]
        passed = probability >= condition["probability_gte"] and quantile <= condition["quantile"] and lead_months >= condition.get("min_lead_months", 0)
        trace.append({"stage": name, "condition": f"P ≥ {condition['probability_gte']} @q{condition['quantile']}", "observed": probability, "passed": passed})
        if passed:
            stage = name
    schema_ok = all(snapshot["schema_ok"] for snapshot in snapshots)
    freshest_age = min((_age_days(snapshot["retrieved_at"]) for snapshot in snapshots), default=9999)
    cards = [card for card in action_cards() if card["hazard"] == hazard]
    eligible = [card for card in cards if STAGE_ORDER.get(card["stage_required"], 99) <= STAGE_ORDER.get(stage, 0) and card["lead_time_days"] <= lead_months * 30]
    ineligible = [{"card": card["id"], "reason": "stage gate failed" if STAGE_ORDER.get(card["stage_required"], 99) > STAGE_ORDER.get(stage, 0) else f"lead-time gate failed (needs {card['lead_time_days']}d; have {lead_months * 30}d)"} for card in cards if card not in eligible]
    policy_cost = document["cost_loss"]
    exposure = policy_cost["exposed_households"]
    effectiveness = max((float(card.get("effectiveness", 0)) for card in eligible), default=0)
    expected_loss = probability * exposure["value"] * policy_cost["loss_per_household_usd"] * effectiveness
    action_cost = sum(card["budget"]["readiness_tranche"]["amount"] for card in eligible)
    triggers = [item for snapshot in snapshots for item in snapshot["payload"].get("events", [])]
    hazards = sorted({hazard, *(item.get("hazard") for item in triggers if item.get("hazard") and item.get("hazard") != hazard)})
    gates = [
        {"id": "source_freshness", "passed": freshest_age <= 45, "detail": f"Newest grounding snapshot is {freshest_age}d old"},
        {"id": "schema_valid", "passed": schema_ok, "detail": "All grounding snapshots passed validation" if schema_ok else "One or more source snapshots failed validation"},
        {"id": "lead_time", "passed": bool(eligible), "detail": "At least one action card fits the available lead time" if eligible else "No action card fits the available lead time"},
        {"id": "net_benefit", "passed": expected_loss - action_cost > policy_cost["margin_usd"], "detail": f"Expected net benefit is ${expected_loss - action_cost:,.0f}"},
    ]
    return {
        "policy_version_id": policy()["id"], "stage": stage, "ndma_phase": document["ndma_phase_mapping"][stage],
        "gates": gates, "stage_trace": trace,
        "cost_loss": {"probability": probability, "exposed_households": exposure["value"], "loss_per_household_usd": policy_cost["loss_per_household_usd"], "expected_avoidable_loss_usd": round(expected_loss, 2), "action_cost_usd": action_cost, "net_expected_benefit_usd": round(expected_loss - action_cost, 2), "margin_usd": policy_cost["margin_usd"], "sources": [{"field": "exposed_households", **exposure}, {"field": "probability", "source": "official_source"}]},
        "eligible_action_cards": [card["id"] for card in eligible], "ineligible": ineligible,
        "compound_signals": hazards if len(hazards) > 1 else [],
        "stop_trigger": {"armed": True, "condition": "P < 0.30", "last_checked": datetime.now(UTC).isoformat()},
    }
