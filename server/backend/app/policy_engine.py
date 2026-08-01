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
ACTIVE_EVENT_STATES = {"active", "ongoing", ""}


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


def observed_event(snapshots: list[dict[str, Any]], area_id: str | None, hazard: str) -> dict[str, Any]:
    """The most severe *active* upstream trigger event for this area and hazard.

    Heat and rainfall are monitoring-only indicators upstream, so readiness for
    those hazards follows ICPAC's own detected events. Linda maps their severity
    to a stage; it never classifies severity itself.
    """
    candidates = [
        record for record in _records(snapshots, "events")
        if record.get("hazard") == hazard
        and (area_id is None or record.get("area_id") == area_id)
        and str(record.get("status", "active")).lower() in ACTIVE_EVENT_STATES
    ]
    if not candidates:
        return {"severity": None, "value": None, "threshold_value": None, "source": None, "synthetic": False, "active": False}
    best = max(candidates, key=lambda item: (not item.get("_synthetic"), _severity_rank(item.get("severity"))))
    synthetic = bool(best.get("_synthetic"))
    citation = f"ICPAC trigger event {best.get('id')} severity_level={best.get('severity')}"
    return {
        "severity": best.get("severity"),
        "value": best.get("value"),
        "threshold_value": best.get("threshold_value"),
        "indicator": best.get("indicator"),
        "detected_at": best.get("detected_at"),
        "active": True,
        "adapter": best.get("_adapter"),
        "freshness": best.get("_freshness"),
        "synthetic": synthetic,
        "source": f"SYNTHETIC demo fixture — {citation}" if synthetic else citation,
    }


_SEVERITY_ORDER = ("low", "minor", "moderate", "high", "major", "severe", "extreme", "critical")


def _severity_rank(value: str | None) -> int:
    try:
        return _SEVERITY_ORDER.index(str(value or "").lower())
    except ValueError:
        return -1


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


def evaluate_stop_trigger(
    policy_document: dict[str, Any],
    observed_probability: float | None,
    *,
    upstream_active: bool | None = None,
) -> dict[str, Any]:
    """Both stop-trigger shapes: a collapsing probability, or a resolved event."""
    condition = policy_document["stop_trigger"]["condition"]
    checked = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if condition.get("resolved_upstream"):
        fired = upstream_active is False
        return {
            "armed": True,
            "condition": "upstream trigger event no longer active",
            "indicator": condition["on_indicator"],
            "observed": upstream_active,
            "fired": bool(fired),
            "last_checked": checked,
        }
    threshold = float(condition["probability_lt"])
    fired = observed_probability is not None and observed_probability < threshold
    return {
        "armed": True,
        "condition": f"P < {threshold}",
        "indicator": condition["on_indicator"],
        "observed": observed_probability,
        "fired": bool(fired),
        "last_checked": checked,
    }


def evaluate(snapshots: list[dict[str, Any]], hazard: str, area_id: str | None = None) -> dict[str, Any]:
    document_wrapper = policy(hazard)
    document = document_wrapper["data"]["policy"]
    basis = document_wrapper["signal_basis"]

    if basis == "upstream_severity":
        signal = observed_event(snapshots, area_id, hazard)
        probability, quantile, lead_months = None, None, 0
    else:
        signal = observed_signal(snapshots, area_id)
        probability = signal["probability"]
        quantile = signal["quantile"]
        lead_months = signal["lead_months"] or 0

    stage: str | None = None
    trace = []
    for name, definition in document["stages"].items():
        condition = definition["condition"]
        if basis == "upstream_severity":
            allowed = [str(item).lower() for item in condition["upstream_severity_in"]]
            observed_value = signal.get("severity")
            passed = bool(signal.get("active")) and str(observed_value or "").lower() in allowed
            readable = f"ICPAC severity_level ∈ {{{', '.join(allowed)}}}"
            detail = (
                f"upstream event severity_level={observed_value}"
                if signal.get("active") else "no active upstream trigger event for this area"
            )
        else:
            observed_value = probability
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
            readable = f"P ≥ {condition['probability_gte']} @q≤{condition['quantile']}" + (
                f", lead ≥ {condition['min_lead_months']}m" if condition.get("min_lead_months") else ""
            )
        trace.append({
            "stage": name,
            "condition": readable,
            "observed": observed_value,
            "detail": detail,
            "passed": passed,
        })
        if passed:
            stage = name

    cards = [card for card in action_cards() if card["hazard"] == hazard]
    eligible: list[dict[str, Any]] = []
    ineligible: list[dict[str, Any]] = []
    # Monitoring-driven hazards act on an observed onset; the seasonal lead does not apply.
    available_days = lead_months * 30 if basis == "probability" else max(card["lead_time_days"] for card in action_cards())
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
        "policy_version_id": document_wrapper["id"],
        "policy_name": document["name"],
        "signal_basis": basis,
        "hazard": hazard,
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
                {
                    "field": "exposed_households",
                    "source": "official_source" if exposure.get("source") == "official_source" else "policy_assumption",
                    "citation": exposure["citation"],
                },
                {"field": "loss_per_household_usd", "source": "policy_assumption", "citation": "policy.yaml cost_loss"},
                {"field": "effectiveness", "source": "policy_assumption", "citation": "action card effectiveness"},
            ],
        },
        "eligible_action_cards": [card["id"] for card in eligible],
        "ineligible": ineligible,
        "compound_signals": detect_compound_signals(snapshots, area_id, hazard, stage),
        "stop_trigger": evaluate_stop_trigger(document, probability, upstream_active=signal.get("active")),
    }
