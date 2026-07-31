import pytest
from fastapi.testclient import TestClient

from app import assists
from app.db import connection, reset_demo, transaction
from app.exports import cap_xml, husika_payload, validate_cap
from app.main import app
from app.services import get_case, verify_event_chain

CASE_ID = "case_bungoma_ond2026"


def sign_in(client: TestClient, email: str) -> None:
    response = client.post("/api/auth/login", json={"email": email, "password": "linda-demo"})
    assert response.status_code == 200, response.text


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
