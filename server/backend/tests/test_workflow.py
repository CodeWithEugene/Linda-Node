from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app import assists, db
from app.db import connection, reset_demo, transaction
from app.exports import cap_xml, husika_payload, validate_cap
from app.main import app
from app.services import get_case, verify_event_chain

CASE_ID = "case_bungoma_ond2026"


def test_reset_demo_initializes_a_fresh_database(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep test setup independent from a pre-existing local SQLite file."""
    fresh_settings = replace(
        db.settings,
        database_url=f"sqlite:///{tmp_path / 'fresh-linda.db'}",
        database_path=tmp_path / "fresh-linda.db",
        database_engine="sqlite",
    )
    monkeypatch.setattr(db, "settings", fresh_settings)

    reset_demo()

    with connection() as conn:
        assert conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"] == 5


def sign_in(client: TestClient, email: str) -> None:
    response = client.post("/api/auth/login", json={"email": email, "password": "linda-demo"})
    assert response.status_code == 200, response.text


def test_logout_clears_the_cookie_session() -> None:
    reset_demo()
    with TestClient(app) as client:
        sign_in(client, "david.drm@demo")
        assert client.get("/api/me").status_code == 200

        response = client.post("/api/auth/logout")

        assert response.status_code == 204
        assert client.get("/api/me").status_code == 401


def current_case(client: TestClient) -> dict:
    response = client.get(f"/api/cases/{CASE_ID}")
    assert response.status_code == 200, response.text
    return response.json()


def test_critical_blocker_prevents_review() -> None:
    reset_demo()
    with TestClient(app) as client:
        sign_in(client, "david.drm@demo")
        case = current_case(client)
        response = client.post(
            f"/api/cases/{CASE_ID}/transition",
            json={"to_state": "READY_FOR_REVIEW", "version": case["version"]},
        )
        assert response.status_code == 422
        assert "Transport contracts confirmed" in response.json()["error"]["detail"]


def test_three_signatures_exports_and_partner_verification() -> None:
    reset_demo()
    with TestClient(app) as david, TestClient(app) as grace, TestClient(app) as amina:
        sign_in(david, "david.drm@demo")
        sign_in(grace, "grace.ngo@demo")
        for task_id in ("task_transport", "task_fodder"):
            case = current_case(grace)
            assert grace.post(
                f"/api/cases/{CASE_ID}/tasks/{task_id}",
                json={"action": "resolve", "version": case["version"]},
            ).status_code == 200
        case = current_case(david)
        assert david.post(
            f"/api/cases/{CASE_ID}/transition",
            json={"to_state": "READY_FOR_REVIEW", "version": case["version"]},
        ).status_code == 200
        for client, email in ((amina, "amina.ews@demo"), (david, "david.drm@demo"), (grace, "grace.ngo@demo")):
            sign_in(client, email)
            case = current_case(client)
            assert client.post(
                f"/api/cases/{CASE_ID}/approvals",
                json={"decision": "approve", "version": case["version"]},
            ).status_code == 200
        case = current_case(david)
        assert case["state"] == "APPROVED"
        assert david.get(f"/api/cases/{CASE_ID}/approvals/verify").json()["three_role_approval_valid"]
        for kind in ("packet", "cap", "husika", "bundle"):
            response = david.post(f"/api/cases/{CASE_ID}/exports/{kind}", json={})
            assert response.status_code == 200, response.text
            if kind == "husika":
                assert response.json()["exports"][0]["meta"]["contract_valid"] is True
        export = david.post(f"/api/cases/{CASE_ID}/exports/packet", json={}).json()["exports"][0]
        assert david.get(f"/api/exports/{export['id']}/download").status_code == 200
        sign_in(david, "admin@demo")
        api_key = david.post("/api/admin/integration-keys", json={"label": "test partner"}).json()["key"]
        partner = david.get(f"/integration/v1/activations/{CASE_ID}", headers={"Authorization": f"Bearer {api_key}"})
        assert partner.status_code == 200
        assert partner.json()["mode"] == "exercise"
        assert david.get(
            f"/integration/v1/activations/{CASE_ID}/cap.xml",
            headers={"Authorization": f"Bearer {api_key}"},
        ).status_code == 200
        assert david.get(
            f"/integration/v1/activations/{CASE_ID}/husika-payload.json",
            headers={"Authorization": f"Bearer {api_key}"},
        ).json()["mode"] == "exercise"
        assert david.get("/integration/v1/schemas/activation.json").status_code == 200
        sign_in(david, "david.drm@demo")
        case = current_case(david)
        assert david.post(f"/api/cases/{CASE_ID}/transition", json={"to_state": "HANDED_OFF", "version": case["version"]}).status_code == 200
        case = current_case(david)
        revoked = david.post(f"/api/cases/{CASE_ID}/transition", json={"to_state": "REVOKED", "version": case["version"], "reason": "Exercise stop trigger"})
        assert revoked.status_code == 200
        assert david.get(f"/api/cases/{CASE_ID}/events/verify").json()["ok"]


def test_stale_mutation_is_rejected_and_recorded() -> None:
    reset_demo()
    with TestClient(app) as david, TestClient(app) as grace:
        sign_in(david, "david.drm@demo")
        sign_in(grace, "grace.ngo@demo")
        stale_case = current_case(david)
        assert grace.post(
            f"/api/cases/{CASE_ID}/tasks/task_fodder",
            json={"action": "resolve", "version": stale_case["version"]},
        ).status_code == 200
        rejected = david.post(
            f"/api/cases/{CASE_ID}/transition",
            json={"to_state": "READY_FOR_REVIEW", "version": stale_case["version"]},
        )
        assert rejected.status_code == 409
        assert rejected.json()["error"]["code"] == "VERSION_CONFLICT"
        events = david.get(f"/api/cases/{CASE_ID}/events").json()
        assert events[-1]["event_type"] == "CONFLICT_REJECTED"
        assert events[-1]["data"]["supplied_version"] == stale_case["version"]


def test_event_tampering_is_detected() -> None:
    reset_demo()
    with transaction() as conn:
        first = conn.execute("SELECT id FROM case_events WHERE case_id = ? ORDER BY seq LIMIT 1", (CASE_ID,)).fetchone()
        conn.execute("UPDATE case_events SET data = ? WHERE id = ?", ('{"tampered":true}', first["id"]))
    with connection() as conn:
        check = verify_event_chain(conn, CASE_ID)
    assert check["ok"] is False
    assert check["broken_seq"] is not None


def test_cap_xsd_and_husika_negative_contract_validation() -> None:
    reset_demo()
    with connection() as conn:
        case = get_case(conn, CASE_ID)
    validate_cap(cap_xml(case))
    validate_cap(cap_xml(case, cancel=True))
    payload = husika_payload(case)
    payload["requests"]["threat"]["event_type"] = "invented_hazard"
    with pytest.raises(ValueError, match="Husika OpenAPI validation failed"):
        from app.husika_contract import validate
        validate(payload)


@pytest.mark.asyncio
async def test_matcher_rejects_an_invented_card_id(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_demo()
    with connection() as conn:
        case = get_case(conn, CASE_ID)

    async def bad_matcher(_: str, __: dict) -> dict:
        return {"candidates": [{"card_id": "invented_card", "rationale": "no", "rank": 1}]}

    monkeypatch.setattr(assists, "_gemini", bad_matcher)
    with pytest.raises(assists.AssistUnavailable, match="card-id validation"):
        await assists.run_matcher(case)


def test_replay_sources_can_assess_a_new_case() -> None:
    reset_demo()
    with TestClient(app) as client:
        sign_in(client, "admin@demo")
        assert client.post("/api/admin/replay-mode", json={"mode": "replay_only"}).status_code == 200
        sign_in(client, "david.drm@demo")
        source_status = client.get("/api/sources/status")
        assert source_status.status_code == 200
        snapshots = source_status.json()["sources"]
        assert {item["adapter"] for item in snapshots} == {"triggers", "forecasts", "areas", "pipeline"}
        created = client.post("/api/cases", json={"title": "New replay assessment", "area_id": "KEN.3_1", "area_name": "Bungoma", "hazard": "drought"})
        assert created.status_code == 201
        case = created.json()
        assessed = client.post(f"/api/cases/{case['id']}/assess", json={"snapshot_ids": [item["id"] for item in snapshots], "version": case["version"]})
        assert assessed.status_code == 200, assessed.text
        result = assessed.json()
        assert result["state"] == "ASSESSED"
        assert result["assessment"]["stage"] == "set"
        assert result["assessment"]["eligible_action_cards"]
        assert result["evidence"]


def test_reassessment_supersedes_a_live_signature() -> None:
    reset_demo()
    with TestClient(app) as client:
        sign_in(client, "admin@demo")
        client.post("/api/admin/replay-mode", json={"mode": "replay_only"})
        sign_in(client, "david.drm@demo")
        sources = client.get("/api/sources/status").json()["sources"]
        case = current_case(client)
        for task_id in ("task_transport", "task_fodder"):
            sign_in(client, "grace.ngo@demo")
            task_case = current_case(client)
            assert client.post(f"/api/cases/{CASE_ID}/tasks/{task_id}", json={"action": "resolve", "version": task_case["version"]}).status_code == 200
        sign_in(client, "david.drm@demo")
        case = current_case(client)
        assert client.post(f"/api/cases/{CASE_ID}/transition", json={"to_state": "READY_FOR_REVIEW", "version": case["version"]}).status_code == 200
        sign_in(client, "amina.ews@demo")
        case = current_case(client)
        assert client.post(f"/api/cases/{CASE_ID}/approvals", json={"decision": "approve", "version": case["version"]}).status_code == 200
        reassessed = client.post(f"/api/cases/{CASE_ID}/evidence", json={"snapshot_ids": [sources[0]["id"]], "version": current_case(client)["version"]})
        assert reassessed.status_code == 200, reassessed.text
        assert reassessed.json()["state"] == "ASSESSED"
        assert any(approval["superseded"] for approval in reassessed.json()["approvals"])
