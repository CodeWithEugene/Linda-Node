"""Idempotent demo scenario (build.md 8).

Three cases are seeded so a judge landing cold sees the whole arc without
driving it: the blocked case they can advance themselves, a completed handed-off
case with all four exports already generated, and a revoked case showing the
stop-trigger path. Every snapshot here is produced by the *same* normalisers and
schemas the live adapters use, so seeded evidence is not a special case.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .domain import canonical_json, now, sha256
from .library import action_cards, policy
from .policy_engine import evaluate
from .redaction import redact
from .sources import (
    normalise_areas,
    normalise_forecasts,
    normalise_triggers,
    parse_pipeline_csv,
    validate_source,
)

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "replay"

# The seeded scenario runs on a real admin-1 unit whose *recorded* ICPAC
# statistic already crosses a policy stage — Ruvuma, Tanzania at 51.8% rp3
# exceedance for OND 2026. Nothing in the default seed is synthetic.
DEMO_AREA = ("TZA.22_1", "Ruvuma", "Tanzania")


def _fixture(name: str) -> tuple[str, dict[str, Any]]:
    text = (FIXTURE_ROOT / name).read_text(encoding="utf-8")
    return text, json.loads(text)


def _insert_snapshot(conn: Any, snapshot_id: str, adapter: str, location: str, payload: dict[str, Any], raw_text: str, meta: dict[str, Any], created_at: str) -> dict[str, Any]:
    raw_document = canonical_json({location: raw_text})
    errors = validate_source(adapter, payload)
    digest = sha256(raw_document)
    conn.execute(
        """INSERT INTO source_snapshots
           (id,adapter,endpoint_url,retrieved_at,payload_json,payload_raw,payload_sha256,schema_ok,freshness,logical_key,meta_json)
           VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
        (snapshot_id, adapter, location, created_at, canonical_json(payload), raw_document, digest,
         0 if errors else 1, "replay", adapter,
         canonical_json({**meta, "schema_errors": errors, "seeded": True,
                         "parts": [{"url": location, "sha256": sha256(raw_text), "bytes": len(raw_text.encode())}]})),
    )
    return {
        "id": snapshot_id, "adapter": adapter, "endpoint_url": location, "retrieved_at": created_at,
        "payload": redact(payload), "payload_sha256": digest, "schema_ok": not errors,
        "freshness": "replay", "meta": {**meta, "schema_errors": errors},
    }


def _seed_snapshots(conn: Any, created_at: str) -> dict[str, dict[str, Any]]:
    triggers_text, triggers_raw = _fixture("triggers.json")
    forecasts_text, forecasts_raw = _fixture("forecasts.json")
    areas_text, areas_raw = _fixture("areas.json")
    pipeline_text = (FIXTURE_ROOT / "pipeline_ond2026.csv").read_text(encoding="utf-8")
    return {
        "triggers": _insert_snapshot(
            conn, "snap_0000seed_triggers", "triggers", "fixtures/replay/triggers.json",
            normalise_triggers(triggers_raw.get("rules"), triggers_raw.get("events"), triggers_raw.get("actions"), triggers_raw.get("check_logs")),
            triggers_text, {"mode": "replay_only", "provenance": triggers_raw.get("_provenance", {})}, created_at),
        "forecasts": _insert_snapshot(
            conn, "snap_0000seed_forecasts", "forecasts", "fixtures/replay/forecasts.json",
            normalise_forecasts(forecasts_raw.get("available"), forecasts_raw.get("stats")),
            forecasts_text, {"mode": "replay_only", "synthetic": False, "escalation_step": 0,
                             "coverage": "all GHA countries",
                             "provenance": forecasts_raw.get("_provenance", {})}, created_at),
        "areas": _insert_snapshot(
            conn, "snap_0000seed_areas", "areas", "fixtures/replay/areas.json",
            normalise_areas(areas_raw), areas_text,
            {"mode": "replay_only", "provenance": areas_raw.get("_provenance", {})}, created_at),
        "pipeline": _insert_snapshot(
            conn, "snap_0000seed_pipeline", "pipeline", "fixtures/replay/pipeline_ond2026.csv",
            parse_pipeline_csv(pipeline_text, source_file="03_prob_csv_q.py compatible output"),
            pipeline_text, {"mode": "replay_only", "synthetic": False, "fixture": True,
                            "format": "exceedance_probability_csv",
                            "note": "Recorded ICPAC rp3 statistics rendered in the 03_prob_csv_q.py column layout."}, created_at),
    }


def _evidence_from(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    kinds = {"forecasts": "forecast", "triggers": "trigger_event", "areas": "area", "pipeline": "pipeline_csv"}
    labels = {
        "forecasts": "OND 2026 return-period exceedance for all 214 GHA admin-1 units",
        "triggers": "ICPAC trigger rules, events and actions (incl. Bungoma Triggers)",
        "areas": "GADM admin-1 index for the 11 GHA countries",
        "pipeline": "ibf-thresholds-triggers exceedance CSV",
    }
    return [{
        "id": item["id"], "kind": kinds.get(item["adapter"], "manual_note"),
        "label": labels.get(item["adapter"], item["adapter"]), "adapter": item["adapter"],
        "endpoint_url": item["endpoint_url"], "retrieved_at": item["retrieved_at"],
        "payload_sha256": item["payload_sha256"], "freshness": item["freshness"],
        "schema_ok": bool(item["schema_ok"]), "schema_errors": item["meta"].get("schema_errors", []),
    } for item in snapshots]


def _insert_case(conn: Any, case_id: str, title: str, state: str, assessment: dict[str, Any], evidence: list[dict[str, Any]], created_at: str, version: int = 1) -> None:
    conn.execute(
        """INSERT INTO decision_cases (id,area_id,area_name,hazard,title,state,policy_version_id,assessment_json,evidence_json,action_card_ids_json,stage,version,created_by,created_at,updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (case_id, DEMO_AREA[0], DEMO_AREA[1], "drought", title, state, assessment["policy_version_id"],
         canonical_json(assessment), canonical_json(evidence),
         canonical_json([card["id"] for card in action_cards() if card["hazard"] == "drought"]),
         assessment["stage"], version, "usr_david", created_at, created_at),
    )


def _insert_tasks(conn: Any, case_id: str, assessment: dict[str, Any], created_at: str, *, blocked: bool) -> None:
    cards = {card["id"]: card for card in action_cards()}
    index = 0
    for card_id in assessment["eligible_action_cards"]:
        card = cards.get(card_id)
        if not card:
            continue
        for prerequisite in card["prerequisites"]:
            index += 1
            is_blocker = blocked and card_id == "card_destocking_v1" and prerequisite["criticality"] == "critical"
            conn.execute(
                """INSERT INTO readiness_tasks (id,case_id,action_card_id,title,owner_role,owner_user_id,criticality,state,blocker_code,blocker_note,updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (f"task_{case_id[-6:]}_{index}" if case_id != "case_ruvuma_ond2026" else _stable_task_id(prerequisite["id"]),
                 case_id, card_id, prerequisite["title"], card["owner_role"], None, prerequisite["criticality"],
                 "BLOCKED" if is_blocker else "ACKNOWLEDGED",
                 "LOGISTICS_TRANSPORT" if is_blocker else None,
                 "Two suppliers have not confirmed access to the market route." if is_blocker else None,
                 created_at),
            )


def _stable_task_id(prerequisite_id: str) -> str:
    """Keep the scripted demo task ids readable and referenceable in tests."""
    return {
        "transport_secured": "task_transport",
        "market_dates": "task_market",
        "water_access": "task_water",
        "suppliers": "task_fodder",
        "seed_tender": "task_seed",
    }.get(prerequisite_id, f"task_{prerequisite_id}")


def _sign_all(conn: Any, case_id: str) -> None:
    import hmac

    from .domain import new_id
    from .services import canonical_case_json, get_case

    case = get_case(conn, case_id)
    digest = sha256(canonical_case_json(case))
    for role, user_id in (("ews_specialist", "usr_amina"), ("county_drm_officer", "usr_david"), ("ngo_finance_lead", "usr_grace")):
        key = conn.execute("SELECT signing_key FROM users WHERE id = ?", (user_id,)).fetchone()["signing_key"]
        conn.execute(
            """INSERT INTO approvals (id,case_id,role,user_id,decision,comment,signed_digest,signature,signed_at,superseded)
               VALUES (?,?,?,?,'approve',?,?,?,?,0)""",
            (new_id("apr"), case_id, role, user_id, "Seeded demonstration approval.", digest,
             hmac.new(key.encode(), digest.encode(), "sha256").hexdigest(), now()),
        )


def seed_cases(conn: Any) -> None:
    from .db import append_event
    from .exports import generate_bundle, generate_cap, generate_husika, generate_packet

    created_at = now()
    snapshots = _seed_snapshots(conn, created_at)
    grounding = [snapshots["forecasts"], snapshots["triggers"], snapshots["pipeline"], snapshots["areas"]]
    evidence = _evidence_from(grounding)
    assessment = evaluate(grounding, "drought", DEMO_AREA[0])

    # 1. The scripted blocker case a judge advances themselves.
    live_id = "case_ruvuma_ond2026"
    _insert_case(conn, live_id, "OND 2026 drought — Ruvuma, Tanzania", "ASSESSED", assessment, evidence, created_at)
    _insert_tasks(conn, live_id, assessment, created_at, blocked=True)
    append_event(conn, live_id, "usr_david", "CASE_CREATED", {"title": "OND 2026 drought — Ruvuma, Tanzania", "mode": "exercise"})
    append_event(conn, live_id, "system", "ASSESSED", {
        "stage": assessment["stage"], "gates_passed": all(gate["passed"] for gate in assessment["gates"]),
        "compound_signals": assessment["compound_signals"], "snapshot_ids": [item["id"] for item in grounding],
    })
    append_event(conn, live_id, "usr_grace", "TASK_UPDATED", {
        "task_id": "task_transport", "state": "BLOCKED", "blocker_code": "LOGISTICS_TRANSPORT",
    })

    # 2. A completed activation with all four exports already generated.
    done_id = "case_ruvuma_ond2026_handedoff"
    _insert_case(conn, done_id, "OND 2026 drought — Ruvuma (completed activation)", "READY_FOR_REVIEW", assessment, evidence, created_at, version=4)
    _insert_tasks(conn, done_id, assessment, created_at, blocked=False)
    append_event(conn, done_id, "usr_david", "CASE_CREATED", {"title": "OND 2026 drought — Ruvuma (completed activation)", "mode": "exercise"})
    append_event(conn, done_id, "system", "ASSESSED", {"stage": assessment["stage"], "gates_passed": True})
    _sign_all(conn, done_id)
    conn.execute("UPDATE decision_cases SET state = 'APPROVED' WHERE id = ?", (done_id,))
    append_event(conn, done_id, "system", "STATE_CHANGED", {"from": "READY_FOR_REVIEW", "to": "APPROVED", "reason": "three role approvals recorded"})
    for generate in (generate_packet, generate_cap, generate_husika, generate_bundle):
        try:
            if generate is generate_husika:
                generate(conn, done_id, "usr_david", None, "en")
            else:
                generate(conn, done_id, "usr_david")
        except Exception as exc:  # noqa: BLE001 - a missing PDF backend must not break seeding
            append_event(conn, done_id, "system", "EXPORT_FAILED", {"error": str(exc)[:200]})
    conn.execute("UPDATE decision_cases SET state = 'HANDED_OFF' WHERE id = ?", (done_id,))
    append_event(conn, done_id, "usr_david", "STATE_CHANGED", {"from": "APPROVED", "to": "HANDED_OFF", "reason": "handed to authorised operators"})

    # 3. A revoked activation showing the stop-trigger path.
    revoked_id = "case_ruvuma_ond2026_revoked"
    _insert_case(conn, revoked_id, "OND 2026 drought — Ruvuma (revoked by stop trigger)", "READY_FOR_REVIEW", assessment, evidence, created_at, version=5)
    _insert_tasks(conn, revoked_id, assessment, created_at, blocked=False)
    append_event(conn, revoked_id, "usr_david", "CASE_CREATED", {"title": "OND 2026 drought — Ruvuma (revoked by stop trigger)", "mode": "exercise"})
    append_event(conn, revoked_id, "system", "ASSESSED", {"stage": assessment["stage"], "gates_passed": True})
    _sign_all(conn, revoked_id)
    conn.execute("UPDATE decision_cases SET state = 'APPROVED' WHERE id = ?", (revoked_id,))
    append_event(conn, revoked_id, "system", "STATE_CHANGED", {"from": "READY_FOR_REVIEW", "to": "APPROVED", "reason": "three role approvals recorded"})
    threshold = policy()["data"]["policy"]["stop_trigger"]["condition"]["probability_lt"]
    conn.execute("UPDATE decision_cases SET state = 'REVOKED' WHERE id = ?", (revoked_id,))
    append_event(conn, revoked_id, "system", "STOP_TRIGGER_FIRED", {"condition": f"P < {threshold}", "observed_probability": 0.22})
    append_event(conn, revoked_id, "system", "STATE_CHANGED", {
        "from": "APPROVED", "to": "REVOKED",
        "reason": f"Exercise stop trigger P < {threshold}: observed probability 0.22", "observed_probability": 0.22,
    })
    try:
        generate_cap(conn, revoked_id, "usr_david")
    except Exception as exc:  # noqa: BLE001
        append_event(conn, revoked_id, "system", "EXPORT_FAILED", {"error": str(exc)[:200]})
