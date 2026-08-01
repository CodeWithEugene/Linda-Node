import hashlib
import hmac
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from .models import CaseEvent, DecisionCase, ExportArtifact, User

REQUIRED_ROLES = ("ews_specialist", "county_drm_officer", "ngo_finance_lead")
TERMINAL_STATES = {"REVOKED"}
TRANSITIONS = {
    "ASSESSED": {"READY_FOR_REVIEW"},
    "READY_FOR_REVIEW": {"APPROVED", "ASSESSED"},
    "APPROVED": {"HANDED_OFF", "REVOKED"},
    "HANDED_OFF": {"REVOKED"},
    "REVOKED": set(),
}


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def json_load(value: str | None, fallback: Any) -> Any:
    return json.loads(value) if value else fallback


def case_snapshot(case: DecisionCase) -> dict[str, Any]:
    return {
        "id": case.id,
        "version": case.version,
        "state": case.state,
        "assessment": json_load(case.assessment, {}),
        "tasks": json_load(case.tasks, []),
        "evidence_ids": json_load(case.evidence_ids, []),
    }


def case_digest(case: DecisionCase) -> str:
    return digest(case_snapshot(case))


def public_case(db: Session, case: DecisionCase) -> dict[str, Any]:
    exports = db.query(ExportArtifact).filter(ExportArtifact.case_id == case.id).all()
    return {
        "id": case.id,
        "title": case.title,
        "area": json_load(case.area, {}),
        "hazard": case.hazard,
        "state": case.state,
        "version": case.version,
        "assessment": json_load(case.assessment, {}),
        "tasks": json_load(case.tasks, []),
        "approvals": json_load(case.approvals, []),
        "evidence_ids": json_load(case.evidence_ids, []),
        "revocation": json_load(case.revocation, None),
        "created_at": case.created_at,
        "updated_at": case.updated_at,
        "digest": case_digest(case),
        "signatures_required": list(REQUIRED_ROLES),
        "exports": [
            {"kind": item.kind, "filename": item.filename, "sha256": item.sha256, "media_type": item.media_type,
             "created_at": item.created_at, "url": f"/api/cases/{case.id}/downloads/{item.filename}"}
            for item in exports
        ],
    }


def append_event(db: Session, case: DecisionCase, actor: str, event_type: str, payload: dict[str, Any]) -> CaseEvent:
    previous = db.query(CaseEvent).filter(CaseEvent.case_id == case.id).order_by(CaseEvent.seq.desc()).first()
    sequence = 1 if previous is None else previous.seq + 1
    occurred_at = utcnow()
    event_body = {"seq": sequence, "at": occurred_at.isoformat(), "actor": actor, "event_type": event_type,
                  "payload": payload, "previous_hash": previous.this_hash if previous else "GENESIS"}
    event = CaseEvent(id=f"evt_{uuid.uuid4().hex}", case_id=case.id, seq=sequence, at=occurred_at, actor=actor,
                      event_type=event_type, payload=canonical(payload), previous_hash=event_body["previous_hash"],
                      this_hash=digest(event_body))
    db.add(event)
    db.flush()
    return event


def verify_chain(db: Session, case: DecisionCase) -> dict[str, Any]:
    previous = "GENESIS"
    events = db.query(CaseEvent).filter(CaseEvent.case_id == case.id).order_by(CaseEvent.seq).all()
    for event in events:
        event_time = event.at if event.at.tzinfo else event.at.replace(tzinfo=timezone.utc)
        body = {"seq": event.seq, "at": event_time.isoformat(), "actor": event.actor, "event_type": event.event_type,
                "payload": json_load(event.payload, {}), "previous_hash": event.previous_hash}
        if event.previous_hash != previous or digest(body) != event.this_hash:
            return {"ok": False, "broken_seq": event.seq, "events": len(events)}
        previous = event.this_hash
    return {"ok": True, "events": len(events)}


def signature(role: str, case_hash: str, key: str) -> str:
    return hmac.new(key.encode(), f"{role}:{case_hash}".encode(), hashlib.sha256).hexdigest()


def verify_signatures(db: Session, case: DecisionCase) -> dict[str, Any]:
    approvals = json_load(case.approvals, [])
    roles = []
    signed_digests = {item["digest"] for item in approvals}
    for role in REQUIRED_ROLES:
        approval = next((item for item in approvals if item["role"] == role), None)
        user = db.query(User).filter(User.role == role).first()
        valid = bool(approval and user and approval["signature"] == signature(role, approval["digest"], user.signing_key))
        roles.append({"role": role, "present": approval is not None, "valid": valid,
                      "signer": approval.get("signer") if approval else None,
                      "signed_at": approval.get("signed_at") if approval else None,
                      "digest": approval.get("digest") if approval else None})
    return {"ok": len(signed_digests) == 1 and all(item["valid"] for item in roles),
            "signed_digest": next(iter(signed_digests)) if len(signed_digests) == 1 else None,
            "current_digest": case_digest(case), "roles": roles}


def transition(case: DecisionCase, target: str) -> None:
    if target not in TRANSITIONS.get(case.state, set()):
        raise ValueError(f"illegal transition {case.state} -> {target}")
    case.state = target
    case.version += 1
    case.updated_at = utcnow()
