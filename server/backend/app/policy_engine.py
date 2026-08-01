"""Pure, transparent assessment of a decision case against policy.yaml.

No IO, no LLM, no randomness. Every number in the returned trace carries the
label of where it came from: `official_source` (an upstream snapshot),
`policy_assumption` (policy.yaml), or `user_entered`.

The engine never invents a stage. When no stage condition is met the stage is
``None`` and the assessment says so explicitly (build.md 6.17: "Never
fabricate: live case shows 'no activation recommended'").
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .library import action_cards, policy

STAGE_ORDER = {"ready": 1, "set": 2, "go": 3}
DEFAULT_FRESHNESS_MAX_DAYS = 45


def _is_synthetic(snapshot: dict[str, Any]) -> bool:
    meta = snapshot.get("meta") or {}
    return bool(meta.get("synthetic") or (meta.get("provenance") or {}).get("synthetic"))


def _records(snapshots: list[dict[str, Any]], *keys: str) -> list[dict[str, Any]]:
    """Flatten payload records, tagging each with where it came from."""
    found: list[dict[str, Any]] = []
    for snapshot in snapshots:
        payload = snapshot.get("payload") or {}
        origin = {
            "_adapter": snapshot.get("adapter"),
            "_freshness": snapshot.get("freshness"),
            "_synthetic": _is_synthetic(snapshot),
        }
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                found.extend({**item, **origin} for item in value if isinstance(item, dict))
    return found


def _age_days(timestamp: str) -> int:
    try:
        return max(0, (datetime.now(UTC) - datetime.fromisoformat(timestamp.replace("Z", "+00:00"))).days)
    except (AttributeError, ValueError):
        return 9999


def observed_signal(snapshots: list[dict[str, Any]], area_id: str | None, indicator: str | None = None) -> dict[str, Any]:
    """Strongest reading for this area. Never falls back to another area.

    Recorded upstream evidence always outranks a synthetic fixture, and the
    chosen observation carries its own origin so a synthetic demo reading can
    never be presented as an official one.
    """
    candidates = [
        record for record in _records(snapshots, "forecasts", "files")
        if (area_id is None or record.get("area_id") == area_id)
        and (indicator is None or record.get("indicator") == indicator)
    ]
    if not candidates:
        return {"probability": None, "quantile": None, "lead_months": None, "source": None, "synthetic": False}
    best = max(candidates, key=lambda item: (not item.get("_synthetic"), float(item.get("probability") or 0)))
    synthetic = bool(best.get("_synthetic"))
    citation = best.get("probability_source") or best.get("source_file") or "upstream snapshot"
    return {
        "probability": float(best.get("probability") or 0),
        "quantile": float(best["quantile"]) if best.get("quantile") is not None else None,
        "lead_months": int(best.get("lead_months") or 0),
        "indicator": best.get("indicator"),
        "valid_date": best.get("valid_date"),
        "adapter": best.get("_adapter"),
        "freshness": best.get("_freshness"),
        "synthetic": synthetic,
        "source": f"SYNTHETIC demo fixture — {citation}" if synthetic else citation,
    }


def detect_compound_signals(snapshots: list[dict[str, Any]], area_id: str | None, hazard: str, stage: str | None) -> list[str]:
    """Deterministic overlap check, NOT a scientific index (build.md 6.9).

    Requires: the same admin area, at least two *different* hazard categories,
    and an active drought signal that has already reached the ready stage.
    """
    if not stage or not area_id:
        return []
    active = {hazard}
    for record in _records(snapshots, "events"):
        if record.get("area_id") != area_id:
            continue
        if str(record.get("status", "active")).lower() not in {"active", "ongoing", ""}:
            continue
        other = record.get("hazard")
        if other:
            active.add(other)
    return sorted(active) if len(active) > 1 else []


def evaluate_stop_trigger(policy_document: dict[str, Any], observed_probability: float | None) -> dict[str, Any]:
    condition = policy_document["stop_trigger"]["condition"]
    threshold = float(condition["probability_lt"])
    fired = observed_probability is not None and observed_probability < threshold
    return {
        "armed": True,
        "condition": f"P < {threshold}",
        "indicator": condition["on_indicator"],
        "observed": observed_probability,
        "fired": bool(fired),
        "last_checked": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
    }


def evaluate(snapshots: list[dict[str, Any]], hazard: str, area_id: str | None = None) -> dict[str, Any]:
    document = policy()["data"]["policy"]
    signal = observed_signal(snapshots, area_id)
    probability = signal["probability"]
    quantile = signal["quantile"]
    lead_months = signal["lead_months"] or 0

    stage: str | None = None
    trace = []
    for name, definition in document["stages"].items():
        condition = definition["condition"]
        if probability is None or quantile is None:
            passed = False
            detail = "no observed probability for this area in the attached evidence"
        else:
            passed = (
                probability >= condition["probability_gte"]
                and quantile <= condition["quantile"]
                and lead_months >= condition.get("min_lead_months", 0)
            )
            detail = f"observed P={probability:.3f} @q{quantile} with {lead_months} months lead"
        trace.append({
            "stage": name,
            "condition": f"P ≥ {condition['probability_gte']} @q≤{condition['quantile']}"
                         + (f", lead ≥ {condition['min_lead_months']}m" if condition.get("min_lead_months") else ""),
            "observed": probability,
            "detail": detail,
            "passed": passed,
        })
        if passed:
            stage = name

    cards = [card for card in action_cards() if card["hazard"] == hazard]
    eligible: list[dict[str, Any]] = []
    ineligible: list[dict[str, Any]] = []
    available_days = lead_months * 30
    for card in cards:
        if stage is None:
            ineligible.append({"card": card["id"], "reason": "no stage reached — no activation recommended"})
        elif STAGE_ORDER[card["stage_required"]] > STAGE_ORDER[stage]:
            ineligible.append({
                "card": card["id"],
                "reason": f"stage gate failed (card needs {card['stage_required'].upper()}, assessment is {stage.upper()})",
            })
        elif card["lead_time_days"] > available_days:
            ineligible.append({
                "card": card["id"],
                "reason": f"lead-time gate failed (needs {card['lead_time_days']}d; have {available_days}d)",
            })
        else:
            eligible.append(card)

    cost = document["cost_loss"]
    exposure = cost["exposed_households"]
    effectiveness = max((float(card.get("effectiveness", 0)) for card in eligible), default=0.0)
    expected_loss = (probability or 0) * exposure["value"] * cost["loss_per_household_usd"] * effectiveness
    action_cost = sum(card["budget"]["readiness_tranche"]["amount"] for card in eligible)
    net_benefit = expected_loss - action_cost

    schema_ok = all(snapshot.get("schema_ok") for snapshot in snapshots)
    schema_failures = [snapshot.get("adapter") for snapshot in snapshots if not snapshot.get("schema_ok")]
    freshest_age = min((_age_days(snapshot.get("retrieved_at", "")) for snapshot in snapshots), default=9999)
    max_age = int(document.get("source_freshness_max_days", DEFAULT_FRESHNESS_MAX_DAYS))
    has_exposure = all(card.get("effectiveness") and card.get("budget") for card in eligible)

    gates = [
        {
            "id": "signal_present",
            "passed": stage is not None,
            "detail": (f"Assessment reached {stage.upper()}" if stage
                       else "No stage condition met — no activation recommended for this area"),
        },
        {
            "id": "source_freshness",
            "passed": freshest_age <= max_age,
            "detail": f"Newest grounding snapshot is {freshest_age}d old (limit {max_age}d)",
        },
        {
            "id": "schema_valid",
            "passed": bool(schema_ok),
            "detail": "All grounding snapshots passed their source schema"
                      if schema_ok else f"Schema validation failed for: {', '.join(filter(None, schema_failures))}",
        },
        {
            "id": "data_completeness",
            "passed": bool(eligible) and has_exposure,
            "detail": "Exposure, cost, and effectiveness present on every eligible card"
                      if eligible and has_exposure else "No eligible card carries complete cost/effectiveness data",
        },
        {
            "id": "lead_time",
            "passed": bool(eligible),
            "detail": f"{len(eligible)} action card(s) fit the {available_days}d available lead time"
                      if eligible else f"No action card fits the {available_days}d available lead time",
        },
        {
            "id": "net_benefit",
            "passed": net_benefit > cost["margin_usd"],
            "detail": f"Expected net benefit ${net_benefit:,.0f} vs required margin ${cost['margin_usd']:,.0f}",
        },
    ]

    return {
        "policy_version_id": policy()["id"],
        "stage": stage,
        "ndma_phase": document["ndma_phase_mapping"][stage] if stage else None,
        "recommendation": "no activation recommended" if stage is None else f"activation readiness at {stage.upper()}",
        "synthetic_observation": bool(signal.get("synthetic")),
        "gates": gates,
        "stage_trace": trace,
        "observed_signal": signal,
        "cost_loss": {
            "formula": "P × exposed households × loss/household × effectiveness − readiness tranche cost",
            "probability": probability,
            "exposed_households": exposure["value"],
            "loss_per_household_usd": cost["loss_per_household_usd"],
            "effectiveness": effectiveness,
            "expected_avoidable_loss_usd": round(expected_loss, 2),
            "action_cost_usd": action_cost,
            "net_expected_benefit_usd": round(net_benefit, 2),
            "margin_usd": cost["margin_usd"],
            "exceeds_margin": net_benefit > cost["margin_usd"],
            "sources": [
                {
                    "field": "probability",
                    "source": "policy_assumption" if signal.get("synthetic") else "official_source",
                    "citation": signal["source"] or "no observation",
                },
                {"field": "exposed_households", "source": "policy_assumption", "citation": exposure["citation"]},
                {"field": "loss_per_household_usd", "source": "policy_assumption", "citation": "policy.yaml cost_loss"},
                {"field": "effectiveness", "source": "policy_assumption", "citation": "action card effectiveness"},
            ],
        },
        "eligible_action_cards": [card["id"] for card in eligible],
        "ineligible": ineligible,
        "compound_signals": detect_compound_signals(snapshots, area_id, hazard, stage),
        "stop_trigger": evaluate_stop_trigger(document, probability),
    }
