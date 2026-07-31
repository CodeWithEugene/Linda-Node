"""Transactional case operations and non-bypassable state-machine guards."""

from __future__ import annotations

import hmac
import sqlite3
from typing import Any

from fastapi import HTTPException, status

from .db import RecordedVersionConflict, append_event, parse_case
from .domain import (
    BLOCKER_CODES,
    SIGNER_ROLES,
    TERMINAL_STATES,
    canonical_json,
    loads,
    new_id,
    now,
    sha256,
)
from .library import action_cards
from .policy_engine import evaluate


def _not_found() -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, detail="Decision case not found")


def get_case(conn: sqlite3.Connection, case_id: str) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM decision_cases WHERE id = ?", (case_id,)).fetchone()
    if not row:
        raise _not_found()
    case = parse_case(row)
    case["tasks"] = [dict(row) for row in conn.execute("SELECT * FROM readiness_tasks WHERE case_id = ? ORDER BY updated_at", (case_id,))]
    approvals = [dict(row) for row in conn.execute(
        """SELECT approvals.*, users.display_name, users.org FROM approvals
           JOIN users ON users.id = approvals.user_id WHERE case_id = ? ORDER BY signed_at""", (case_id,)
    )]
    case["approvals"] = approvals
    case["exports"] = []
    for row in conn.execute("SELECT * FROM exports WHERE case_id = ? ORDER BY generated_at DESC", (case_id,)):
        exported = dict(row)
        exported["meta"] = loads(exported.pop("meta_json"), {})
        case["exports"].append(exported)
    ids = set(case["action_card_ids"])
    case["action_cards"] = [card for card in action_cards() if card["id"] in ids]
    return case


def case_summary(case: dict[str, Any]) -> dict[str, Any]:
    return {key: case[key] for key in ("id", "area_id", "area_name", "hazard", "title", "state", "stage", "version", "created_at", "updated_at")}


def canonical_case_json(case: dict[str, Any], signed_state: str | None = None) -> str:
    """The exact payload that three role signatures attest to."""
    payload = {
        "case_id": case["id"], "area_id": case["area_id"], "area_name": case["area_name"],
        "hazard": case["hazard"], "state": signed_state or case["state"],
        "policy_version_id": case["policy_version_id"], "assessment": case["assessment"],
        "evidence_hashes": sorted(item.get("payload_sha256", "") for item in case["evidence"]),
        "tasks": sorted(
            [{"id": task["id"], "state": task["state"], "blocker_code": task["blocker_code"]} for task in case["tasks"]],
            key=lambda item: item["id"],
        ),
    }
    return canonical_json(payload)


def materialize_readiness_tasks(
    conn: sqlite3.Connection, case_id: str, eligible_card_ids: list[str], actor_id: str = "system"
) -> list[dict[str, Any]]:
    """Create each eligible card prerequisite exactly once.

    The deterministic assessment owner calls this at the assessment boundary;
    task mutation and critical-path guarding stay owned by this workflow. The
    owner and criticality always come from the reviewed action-card library.
    """
    case = get_case(conn, case_id)
    cards = {card["id"]: card for card in action_cards()}
    created: list[dict[str, Any]] = []
    for card_id in eligible_card_ids:
        card = cards.get(card_id)
        if not card or card_id not in case["action_card_ids"]:
            continue
        for prerequisite in card.get("prerequisites", []):
            exists = conn.execute(
                "SELECT 1 FROM readiness_tasks WHERE case_id = ? AND action_card_id = ? AND title = ?",
                (case_id, card_id, prerequisite["title"]),
            ).fetchone()
            if exists:
                continue
            task = {
                "id": new_id("task"), "case_id": case_id, "action_card_id": card_id,
                "title": prerequisite["title"], "owner_role": card["owner_role"],
                "owner_user_id": None, "criticality": prerequisite["criticality"],
                "state": "PENDING", "blocker_code": None, "blocker_note": None,
                "updated_at": now(),
            }
            conn.execute(
                """INSERT INTO readiness_tasks
                   (id,case_id,action_card_id,title,owner_role,owner_user_id,criticality,state,blocker_code,blocker_note,updated_at)
                   VALUES (:id,:case_id,:action_card_id,:title,:owner_role,:owner_user_id,:criticality,:state,:blocker_code,:blocker_note,:updated_at)""",
                task,
            )
            created.append(task)
    if created:
        append_event(conn, case_id, actor_id, "READINESS_TASKS_MATERIALIZED", {
            "eligible_card_ids": eligible_card_ids,
            "task_ids": [task["id"] for task in created],
        })
    return created


def supersede_approvals_for_reassessment(
    conn: sqlite3.Connection, case_id: str, actor_id: str = "system"
) -> int:
    """Keep old signatures, but make a changed assessment unsigned again."""
    get_case(conn, case_id)
    updated = conn.execute(
        "UPDATE approvals SET superseded = 1 WHERE case_id = ? AND superseded = 0", (case_id,)
    ).rowcount
    if updated:
        append_event(conn, case_id, actor_id, "APPROVALS_SUPERSEDED", {"count": updated})
    return updated


def _require_version(
    conn: sqlite3.Connection, case: dict[str, Any], supplied_version: int, actor_id: str
) -> None:
    if case["version"] != supplied_version:
        append_event(conn, case["id"], actor_id, "CONFLICT_REJECTED", {
            "supplied_version": supplied_version,
            "current_version": case["version"],
        })
        raise RecordedVersionConflict(case["version"], supplied_version)


def _bump_case(conn: sqlite3.Connection, case: dict[str, Any], *, state: str | None = None) -> int:
    version = case["version"] + 1
    updated = conn.execute(
        "UPDATE decision_cases SET state = ?, version = ?, updated_at = ? WHERE id = ? AND version = ?",
        (state or case["state"], version, now(), case["id"], case["version"]),
    )
    if not updated.rowcount:
        # BEGIN IMMEDIATE should make this unreachable, but keep the data
        # invariant explicit if a future storage backend changes behaviour.
        latest = conn.execute("SELECT version FROM decision_cases WHERE id = ?", (case["id"],)).fetchone()
        current = latest["version"] if latest else case["version"]
        append_event(conn, case["id"], "system", "CONFLICT_REJECTED", {
            "supplied_version": case["version"], "current_version": current,
        })
        raise RecordedVersionConflict(current, case["version"])
    return version


def update_task(
    conn: sqlite3.Connection,
    case_id: str,
    task_id: str,
    actor: dict[str, Any],
    action: str,
    supplied_version: int,
    blocker_code: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    case = get_case(conn, case_id)
    _require_version(conn, case, supplied_version, actor["id"])
    if case["state"] in TERMINAL_STATES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Terminal cases cannot change readiness tasks")
    task = next((item for item in case["tasks"] if item["id"] == task_id), None)
    if not task:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Readiness task not found")
    if actor["role"] != task["owner_role"]:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Only the task's owner role can update it")
    states = {"acknowledge": "ACKNOWLEDGED", "resolve": "RESOLVED", "decline": "DECLINED", "block": "BLOCKED"}
    if action not in states:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Unknown task action")
    next_state = states[action]
    if next_state in {"BLOCKED", "DECLINED"}:
        if blocker_code not in BLOCKER_CODES or not note or not note.strip():
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Blockers require a taxonomy code and explanatory note")
    else:
        blocker_code, note = None, None
    changed_at = now()
    conn.execute(
        """UPDATE readiness_tasks SET state = ?, blocker_code = ?, blocker_note = ?, owner_user_id = ?, updated_at = ? WHERE id = ?""",
        (next_state, blocker_code, note, actor["id"], changed_at, task_id),
    )
    _bump_case(conn, case)
    append_event(conn, case_id, actor["id"], "TASK_UPDATED", {
        "task_id": task_id, "action": action, "state": next_state, "blocker_code": blocker_code, "note": note,
    })
    return get_case(conn, case_id)


def transition_case(
    conn: sqlite3.Connection, case_id: str, actor: dict[str, Any], to_state: str, supplied_version: int, reason: str | None = None,
) -> dict[str, Any]:
    case = get_case(conn, case_id)
    _require_version(conn, case, supplied_version, actor["id"])
    source = case["state"]
    if source in TERMINAL_STATES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Terminal cases cannot transition")
    if actor["role"] != "county_drm_officer":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Only the County DRM Officer can perform this transition")
    if (source, to_state) == ("ASSESSED", "READY_FOR_REVIEW"):
        failed_gates = [gate["id"] for gate in case["assessment"].get("gates", []) if not gate.get("passed")]
        blocking_tasks = [task["title"] for task in case["tasks"] if task["criticality"] == "critical" and task["state"] not in {"ACKNOWLEDGED", "RESOLVED"}]
        if failed_gates or blocking_tasks:
            message = "Cannot send for review"
            if failed_gates:
                message += f": failed gates: {', '.join(failed_gates)}"
            if blocking_tasks:
                message += f"; blocked critical tasks: {', '.join(blocking_tasks)}"
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=message)
    elif (source, to_state) == ("APPROVED", "HANDED_OFF"):
        if not conn.execute("SELECT 1 FROM exports WHERE case_id = ? LIMIT 1", (case_id,)).fetchone():
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Generate at least one export before handing off")
    elif to_state == "REVOKED" and source in {"APPROVED", "HANDED_OFF"}:
        if not reason or not reason.strip():
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="A revocation reason is required")
    else:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=f"Illegal transition {source} → {to_state}")
    _bump_case(conn, case, state=to_state)
    append_event(conn, case_id, actor["id"], "STATE_CHANGED", {"from": source, "to": to_state, "reason": reason})
    return get_case(conn, case_id)


def revoke_for_stop_trigger(
    conn: sqlite3.Connection, case_id: str, observed_probability: float
) -> dict[str, Any]:
    """System-only revocation used by the explicit, labelled demo stop trigger."""
    case = get_case(conn, case_id)
    if case["state"] not in {"APPROVED", "HANDED_OFF"}:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Stop-trigger revocation requires an approved or handed-off case",
        )
    _bump_case(conn, case, state="REVOKED")
    append_event(conn, case_id, "system", "STATE_CHANGED", {
        "from": case["state"], "to": "REVOKED",
        "reason": f"Exercise stop trigger: probability fell to {observed_probability:.2f}",
        "observed_probability": observed_probability,
    })
    return get_case(conn, case_id)


def record_approval(
    conn: sqlite3.Connection, case_id: str, actor: dict[str, Any], decision: str, comment: str | None, supplied_version: int,
) -> tuple[dict[str, Any], bool]:
    case = get_case(conn, case_id)
    _require_version(conn, case, supplied_version, actor["id"])
    if case["state"] != "READY_FOR_REVIEW":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Approvals are available only while a case is ready for review")
    if actor["role"] not in SIGNER_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Only a required signer role can record a decision")
    if decision not in {"approve", "reject", "request_evidence"}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Unknown approval decision")
    existing = conn.execute("SELECT 1 FROM approvals WHERE case_id = ? AND role = ? AND superseded = 0", (case_id, actor["role"])).fetchone()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, detail="This role has already recorded a live decision")
    user = conn.execute("SELECT signing_key FROM users WHERE id = ?", (actor["id"],)).fetchone()
    digest = sha256(canonical_case_json(case))
    signature = hmac.new(user["signing_key"].encode(), digest.encode(), "sha256").hexdigest()
    conn.execute(
        """INSERT INTO approvals (id,case_id,role,user_id,decision,comment,signed_digest,signature,signed_at,superseded)
           VALUES (?,?,?,?,?,?,?,?,?,0)""",
        (new_id("apr"), case_id, actor["role"], actor["id"], decision, comment, digest, signature, now()),
    )
    append_event(conn, case_id, actor["id"], "APPROVAL_RECORDED", {"role": actor["role"], "decision": decision, "signed_digest": digest})
    next_state: str | None = None
    if decision == "reject":
        next_state = "REJECTED"
    elif decision == "request_evidence":
        next_state = "NEEDS_EVIDENCE"
    else:
        approved_roles = {row["role"] for row in conn.execute("SELECT role FROM approvals WHERE case_id = ? AND decision = 'approve' AND superseded = 0", (case_id,))}
        if set(SIGNER_ROLES) == approved_roles:
            next_state = "APPROVED"
    _bump_case(conn, case, state=next_state)
    transitioned = next_state == "APPROVED"
    if next_state:
        append_event(conn, case_id, "system", "STATE_CHANGED", {"from": "READY_FOR_REVIEW", "to": next_state, "reason": "approval decision"})
    return get_case(conn, case_id), transitioned


def verify_approvals(conn: sqlite3.Connection, case_id: str) -> dict[str, Any]:
    case = get_case(conn, case_id)
    # The third signature atomically advances the case to APPROVED. The signed
    # decision snapshot remains READY_FOR_REVIEW through a later handoff, so
    # verification compares the decision facts rather than that bookkeeping
    # transition. Evidence reassessment supersedes signatures before it can
    # mutate assessment/evidence/task data.
    signing_state = "READY_FOR_REVIEW" if case["state"] in {"APPROVED", "HANDED_OFF"} else case["state"]
    current_digest = sha256(canonical_case_json(case, signing_state))
    results = []
    for approval in case["approvals"]:
        user = conn.execute("SELECT signing_key FROM users WHERE id = ?", (approval["user_id"],)).fetchone()
        expected = hmac.new(user["signing_key"].encode(), approval["signed_digest"].encode(), "sha256").hexdigest()
        results.append({
            "role": approval["role"], "signer": approval["display_name"], "decision": approval["decision"],
            "signed_at": approval["signed_at"], "digest": approval["signed_digest"],
            "signature": approval["signature"],
            "signature_valid": hmac.compare_digest(expected, approval["signature"]),
            "covers_current_case": approval["signed_digest"] == current_digest and not approval["superseded"],
        })
    live_approvals = [item for item in results if item["decision"] == "approve" and item["signature_valid"] and item["covers_current_case"]]
    return {"case_id": case_id, "current_digest": current_digest, "signatures": results, "three_role_approval_valid": {item["role"] for item in live_approvals} == set(SIGNER_ROLES)}


def case_events(conn: sqlite3.Connection, case_id: str) -> list[dict[str, Any]]:
    get_case(conn, case_id)
    events = []
    for row in conn.execute("SELECT * FROM case_events WHERE case_id = ? ORDER BY seq", (case_id,)):
        event = dict(row)
        event["data"] = loads(event["data"], {})
        events.append(event)
    return events


def verify_event_chain(conn: sqlite3.Connection, case_id: str) -> dict[str, Any]:
    chain = case_events(conn, case_id)
    previous = ""
    for event in chain:
        expected = sha256(previous + canonical_json(event["data"]) + event["event_type"] + event["actor_id"])
        if event["prev_hash"] != previous or event["this_hash"] != expected:
            return {"ok": False, "events": len(chain), "broken_seq": event["seq"], "expected_hash": expected}
        previous = event["this_hash"]
    return {"ok": True, "events": len(chain), "head_hash": previous}


def create_case(conn: sqlite3.Connection, actor: dict[str, Any], area_id: str, area_name: str, hazard: str, title: str, evidence: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if actor["role"] != "county_drm_officer":
        raise HTTPException(status.HTTP_403_FORBIDDEN, detail="Only the County DRM Officer can create a case")
    card_ids = [card["id"] for card in action_cards() if card["hazard"] == hazard]
    created = now()
    case_id = new_id("case")
    conn.execute(
        """INSERT INTO decision_cases (id,area_id,area_name,hazard,title,state,policy_version_id,assessment_json,evidence_json,action_card_ids_json,stage,version,created_by,created_at,updated_at)
           VALUES (?,?,?,?,?,'INGESTED','unassessed','{}',?,?,NULL,1,?,?,?)""",
        (case_id, area_id, area_name, hazard, title, canonical_json(evidence or []), canonical_json(card_ids), actor["id"], created, created),
    )
    append_event(conn, case_id, actor["id"], "CASE_CREATED", {"title": title, "area_id": area_id, "hazard": hazard})
    return get_case(conn, case_id)


def attach_evidence_and_assess(
    conn: sqlite3.Connection, case_id: str, actor: dict[str, Any], snapshots: list[dict[str, Any]], supplied_version: int | None = None,
) -> dict[str, Any]:
    """Persist selected immutable snapshots, then deterministically re-assess.

    The caller has already authorisation-checked the actor.  Snapshots are
    copied as compact provenance records, preserving a case even if a source
    adapter later refreshes or disappears.
    """
    case = get_case(conn, case_id)
    if case["state"] in TERMINAL_STATES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Terminal cases cannot be re-assessed")
    if supplied_version is not None:
        _require_version(conn, case, supplied_version, actor["id"])
    merged = {item.get("id"): item for item in case["evidence"]}
    for snapshot in snapshots:
        merged[snapshot["id"]] = {
            "id": snapshot["id"], "kind": "forecast" if snapshot["adapter"] == "forecasts" else "trigger_event" if snapshot["adapter"] == "triggers" else "area",
            "label": f"{snapshot['adapter'].replace('_', ' ').title()} snapshot",
            "adapter": snapshot["adapter"], "endpoint_url": snapshot["endpoint_url"], "retrieved_at": snapshot["retrieved_at"],
            "payload_sha256": snapshot["payload_sha256"], "freshness": snapshot["freshness"], "schema_ok": bool(snapshot["schema_ok"]),
        }
    evidence = list(merged.values())
    assessment = evaluate(snapshots, case["hazard"])
    if case["state"] in {"READY_FOR_REVIEW", "NEEDS_EVIDENCE"}:
        supersede_approvals_for_reassessment(conn, case_id, actor["id"])
    next_state = "ASSESSED"
    version = _bump_case(conn, case, state=next_state)
    conn.execute("UPDATE decision_cases SET assessment_json = ?, evidence_json = ?, policy_version_id = ?, stage = ?, version = ? WHERE id = ?", (canonical_json(assessment), canonical_json(evidence), assessment["policy_version_id"], assessment["stage"], version, case_id))
    materialize_readiness_tasks(conn, case_id, assessment["eligible_action_cards"], actor["id"])
    append_event(conn, case_id, actor["id"], "ASSESSED", {"from": case["state"], "stage": assessment["stage"], "gates_passed": all(gate["passed"] for gate in assessment["gates"]), "snapshot_ids": [item["id"] for item in snapshots]})
    return get_case(conn, case_id)
