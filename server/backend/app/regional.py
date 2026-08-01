"""Region-wide readiness view across every GHA admin-1 unit.

The same deterministic policy that governs a single decision case is applied to
all 214 admin-1 units ICPAC publishes statistics for, so the landing screen is a
live readiness ranking rather than one prepared example. Units that reach no
stage are reported as such — most of the region usually does, and that is the
honest result.
"""

from __future__ import annotations

import sqlite3
from typing import Any

from .library import policy
from .policy_engine import STAGE_ORDER, evaluate_stop_trigger
from .sources import COUNTRY_NAMES, refresh_adapter, source_mode, tile_source

HAZARD_BY_SEVERITY_BASIS = ("heat", "flood")


def _drought_stage(document: dict[str, Any], probability: float, quantile: float, lead_months: int) -> str | None:
    stage: str | None = None
    for name, definition in document["stages"].items():
        condition = definition["condition"]
        if (
            probability >= condition["probability_gte"]
            and quantile <= condition["quantile"]
            and lead_months >= condition.get("min_lead_months", 0)
        ):
            stage = name
    return stage


def _severity_stage(document: dict[str, Any], severity: str | None) -> str | None:
    if not severity:
        return None
    stage: str | None = None
    for name, definition in document["stages"].items():
        allowed = [str(item).lower() for item in definition["condition"]["upstream_severity_in"]]
        if str(severity).lower() in allowed:
            stage = name
    return stage


def regional_overview(conn: sqlite3.Connection) -> dict[str, Any]:
    forecasts_snapshot = refresh_adapter(conn, "forecasts")
    triggers_snapshot = refresh_adapter(conn, "triggers")
    areas_snapshot = refresh_adapter(conn, "areas")

    drought = policy("drought")
    drought_document = drought["data"]["policy"]
    area_names = {item["id"]: item for item in areas_snapshot["payload"].get("areas", [])}

    # Active upstream trigger events, keyed by area so a unit can carry both a
    # seasonal drought probability and a monitored heat/flood event.
    events_by_area: dict[str, list[dict[str, Any]]] = {}
    for event in triggers_snapshot["payload"].get("events", []):
        if str(event.get("status", "active")).lower() in {"active", "ongoing", ""}:
            events_by_area.setdefault(event.get("area_id", ""), []).append(event)

    units: list[dict[str, Any]] = []
    for record in forecasts_snapshot["payload"].get("forecasts", []):
        area_id = record.get("area_id") or ""
        country = record.get("country") or area_id.split(".")[0]
        probability = float(record.get("probability") or 0)
        stage = _drought_stage(drought_document, probability, float(record.get("quantile") or 1), int(record.get("lead_months") or 0))

        hazards: list[dict[str, Any]] = [{
            "hazard": "drought",
            "stage": stage,
            "basis": "probability",
            "observed": probability,
            "indicator": record.get("indicator"),
            "policy_version_id": drought["id"],
        }]
        for event in events_by_area.get(area_id, []):
            hazard = event.get("hazard")
            if hazard in HAZARD_BY_SEVERITY_BASIS:
                document = policy(hazard)
                hazards.append({
                    "hazard": hazard,
                    "stage": _severity_stage(document["data"]["policy"], event.get("severity")),
                    "basis": "upstream_severity",
                    "observed": event.get("severity"),
                    "value": event.get("value"),
                    "threshold_value": event.get("threshold_value"),
                    "indicator": event.get("indicator"),
                    "policy_version_id": document["id"],
                })

        staged = [item for item in hazards if item["stage"]]
        top = max(staged, key=lambda item: STAGE_ORDER[item["stage"]], default=None)
        units.append({
            "area_id": area_id,
            "area_name": record.get("area_name") or area_names.get(area_id, {}).get("name") or area_id,
            "country": country,
            "country_name": COUNTRY_NAMES.get(country, record.get("country_name") or country),
            "probability": probability,
            "return_periods": record.get("return_periods", {}),
            "valid_date": record.get("valid_date"),
            "lead_months": record.get("lead_months"),
            "indicator": record.get("indicator"),
            "hazards": hazards,
            "stage": top["stage"] if top else None,
            "stage_hazard": top["hazard"] if top else None,
            "ndma_phase": policy(top["hazard"])["data"]["policy"]["ndma_phase_mapping"][top["stage"]] if top else None,
            "compound": len({item["hazard"] for item in staged}) > 1,
            "snapshot_id": forecasts_snapshot["id"],
        })

    units.sort(key=lambda item: (STAGE_ORDER.get(item["stage"] or "", 0), item["probability"]), reverse=True)

    by_country: dict[str, dict[str, Any]] = {}
    for unit in units:
        entry = by_country.setdefault(unit["country"], {
            "country": unit["country"], "country_name": unit["country_name"],
            "units": 0, "activating": 0, "max_probability": 0.0, "stages": {"ready": 0, "set": 0, "go": 0},
        })
        entry["units"] += 1
        entry["max_probability"] = max(entry["max_probability"], unit["probability"])
        if unit["stage"]:
            entry["activating"] += 1
            entry["stages"][unit["stage"]] += 1

    issue = forecasts_snapshot["payload"].get("issue", {})
    activating = [unit for unit in units if unit["stage"]]
    return {
        "mode": source_mode(conn),
        "generated_at": forecasts_snapshot["retrieved_at"],
        "issue": {
            "id": issue.get("id"),
            "season": issue.get("target_season"),
            "year": issue.get("target_year"),
            "valid_date": issue.get("valid_date"),
            "lead_months": issue.get("lead_months"),
            "indicator": issue.get("indicator"),
            "data_source": issue.get("data_source"),
        },
        "available_issues": forecasts_snapshot["payload"].get("issues", []),
        "evidence": {
            "forecasts": {"snapshot_id": forecasts_snapshot["id"], "sha256": forecasts_snapshot["payload_sha256"],
                          "endpoint_url": forecasts_snapshot["endpoint_url"], "freshness": forecasts_snapshot["freshness"],
                          "retrieved_at": forecasts_snapshot["retrieved_at"]},
            "triggers": {"snapshot_id": triggers_snapshot["id"], "sha256": triggers_snapshot["payload_sha256"],
                         "endpoint_url": triggers_snapshot["endpoint_url"], "freshness": triggers_snapshot["freshness"],
                         "retrieved_at": triggers_snapshot["retrieved_at"]},
            "areas": {"snapshot_id": areas_snapshot["id"], "sha256": areas_snapshot["payload_sha256"],
                      "endpoint_url": areas_snapshot["endpoint_url"], "freshness": areas_snapshot["freshness"],
                      "retrieved_at": areas_snapshot["retrieved_at"]},
        },
        "policies": {hazard: policy(hazard)["id"] for hazard in ("drought", "heat", "flood")},
        "totals": {
            "units": len(units),
            "countries": len(by_country),
            "activating": len(activating),
            "ready": sum(1 for unit in activating if unit["stage"] == "ready"),
            "set": sum(1 for unit in activating if unit["stage"] == "set"),
            "go": sum(1 for unit in activating if unit["stage"] == "go"),
            "compound": sum(1 for unit in units if unit["compound"]),
            "max_probability": max((unit["probability"] for unit in units), default=0.0),
        },
        "countries": sorted(by_country.values(), key=lambda item: (-item["activating"], -item["max_probability"])),
        "units": units,
        "tiles": tile_source(),
        "stop_trigger": evaluate_stop_trigger(drought_document, None),
    }
