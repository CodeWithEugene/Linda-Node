import json
import uuid
from datetime import datetime, timezone

from .adapters.replay import ReplayAdapter
from .auth import password_hash
from .domain import append_event, canonical, digest
from .models import DecisionCase, SourceSnapshot, User
from .policy import evaluate, load_library


def seed(db) -> None:
    if db.query(User).count():
        return
    now = datetime.now(timezone.utc)
    people = [
        ("usr_ews", "amina.ews@demo", "Amina Otieno", "ews_specialist", "ICPAC demo persona", "ews-demo-signing-key"),
        ("usr_drm", "david.drm@demo", "David Wekesa", "county_drm_officer", "Bungoma County DRM", "drm-demo-signing-key"),
        ("usr_ngo", "grace.ngo@demo", "Grace Achieng", "ngo_finance_lead", "KRCS demo persona", "ngo-demo-signing-key"),
        ("usr_observer", "observer@demo", "Observer", "observer", "Linda Protocol", "observer-demo-signing-key"),
        ("usr_admin", "admin@demo", "Admin", "admin", "Linda Protocol", "admin-demo-signing-key"),
    ]
    for user_id, email, name, role, org, signing_key in people:
        db.add(User(id=user_id, email=email, display_name=name, role=role, org=org,
                    password_hash=password_hash("linda-demo"), signing_key=signing_key, created_at=now))
    evidence_ids = []
    for capture in ReplayAdapter().fetch():
        raw = canonical(capture.payload)
        snapshot_id = "snap_" + digest(capture.payload)[:12]
        evidence_ids.append(snapshot_id)
        db.add(SourceSnapshot(id=snapshot_id, adapter=capture.adapter, endpoint_url=capture.endpoint_url,
                              retrieved_at=capture.retrieved_at, payload=raw, payload_sha256=digest(capture.payload),
                              schema_ok=1, freshness=capture.freshness, meta=canonical(capture.meta)))
    assessment = {
        "stage": "go", "area_id": "KEN.3_1", "hazard": "drought", "probability": 0.63,
        "gates": [
            {"name": "official_source", "passed": True, "basis": "ICPAC trigger and forecast snapshots captured"},
            {"name": "probability_threshold", "passed": True, "basis": "0.63 >= GO threshold 0.60"},
            {"name": "readiness", "passed": False, "basis": "critical transport task is blocked"},
        ],
        "eligible_cards": [
            {"id": "water-trucking", "title": "Pre-position water trucking contracts", "owner_role": "county_drm_officer", "stage": "go", "budget": "Action tranche USD 100,000 at GO"},
            {"id": "cash-readiness", "title": "Prepare shock-responsive cash transfer roster", "owner_role": "ngo_finance_lead", "stage": "set", "budget": "Readiness tranche USD 18,000 at READY"},
        ],
        "ineligible_cards": [{"id": "seed-distribution", "title": "Seed distribution", "reason": "lead time exceeds available window"}],
        "expected_avoidable_loss": {"baseline_usd": 520000, "after_action_usd": 310000, "net_benefit_usd": 210000},
        "policy_hash": digest("demo policy v1"),
    }
    tasks = [
        {"id": "task_transport", "task": "Transport contracts confirmed", "action_card": "water-trucking", "owner_role": "county_drm_officer", "critical": True, "state": "BLOCKED", "blocker_code": "LOGISTICS_TRANSPORT", "note": "Supplier confirmation pending", "updated_at": now.isoformat()},
        {"id": "task_roster", "task": "Cash transfer roster verified", "action_card": "cash-readiness", "owner_role": "ngo_finance_lead", "critical": True, "state": "ACKNOWLEDGED", "blocker_code": None, "note": "", "updated_at": now.isoformat()},
        {"id": "task_forecast", "task": "Forecast evidence reviewed", "action_card": "water-trucking", "owner_role": "ews_specialist", "critical": False, "state": "ACKNOWLEDGED", "blocker_code": None, "note": "", "updated_at": now.isoformat()},
    ]
    policy, actions = load_library(__import__("pathlib").Path("backend/content"))
    assessment = evaluate(policy, actions, [{"adapter": capture.adapter, "payload": capture.payload} for capture in ReplayAdapter().fetch()], "KEN.3_1", "drought", tasks)
    case = DecisionCase(id="case_bungoma_ond2026", title="OND 2026 drought - Bungoma",
                        area=canonical({"id": "KEN.3_1", "name": "Bungoma", "country": "KEN"}), hazard="drought",
                        state="ASSESSED", version=1, assessment=canonical(assessment), tasks=canonical(tasks),
                        approvals="[]", evidence_ids=canonical(evidence_ids), created_at=now, updated_at=now)
    db.add(case)
    db.flush()
    append_event(db, case, "system", "SEEDED", {"case_id": case.id})
    append_event(db, case, "system", "ASSESSED", {"assessment": assessment})
    append_event(db, case, "system", "TASK_BLOCKED", {"task_id": "task_transport", "code": "LOGISTICS_TRANSPORT"})
    db.commit()
