"""Every guard in build.md 6.6, attempted through the API and asserted rejected."""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.db import connection, reset_demo
from app.main import app
from app.services import canonical_case_json, get_case

BLOCKED_CASE = "case_bungoma_ond2026"
DONE_CASE = "case_bungoma_ond2026_handedoff"
REVOKED_CASE = "case_bungoma_ond2026_revoked"


@pytest.fixture()
def client() -> TestClient:
    reset_demo()
    with TestClient(app) as instance:
        yield instance


def login(client: TestClient, email: str) -> None:
    assert client.post("/api/auth/login", json={"email": email, "password": "linda-demo"}).status_code == 200


def version(client: TestClient, case_id: str = BLOCKED_CASE) -> int:
    return client.get(f"/api/cases/{case_id}").json()["version"]


def transition(client: TestClient, case_id: str, to_state: str, **body: object):
    return client.post(f"/api/cases/{case_id}/transition", json={"to_state": to_state, "version": version(client, case_id), **body})


# --------------------------------------------------------------------------
# Role guards.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("email", ["observer@demo", "amina.ews@demo", "grace.ngo@demo", "admin@demo"])
def test_only_the_drm_officer_can_transition_a_case(client: TestClient, email: str) -> None:
    login(client, email)
    assert transition(client, BLOCKED_CASE, "READY_FOR_REVIEW").status_code == 403


@pytest.mark.parametrize("email", ["observer@demo", "amina.ews@demo", "grace.ngo@demo"])
def test_only_the_drm_officer_can_create_a_case(client: TestClient, email: str) -> None:
    login(client, email)
    assert client.post("/api/cases", json={"title": "Attempted case"}).status_code == 403


def test_observer_cannot_approve(client: TestClient) -> None:
    login(client, "observer@demo")
    response = client.post(f"/api/cases/{DONE_CASE}/approvals", json={"decision": "approve", "version": version(client, DONE_CASE)})
    assert response.status_code == 403


def test_observer_cannot_update_a_task(client: TestClient) -> None:
    login(client, "observer@demo")
    response = client.post(
        f"/api/cases/{BLOCKED_CASE}/tasks/task_transport",
        json={"action": "resolve", "version": version(client)},
    )
    assert response.status_code == 403


def test_a_task_can_only_be_updated_by_its_owner_role(client: TestClient) -> None:
    login(client, "david.drm@demo")  # task_transport is owned by ngo_finance_lead
    response = client.post(
        f"/api/cases/{BLOCKED_CASE}/tasks/task_transport",
        json={"action": "resolve", "version": version(client)},
    )
    assert response.status_code == 403


def test_unauthenticated_requests_are_rejected(client: TestClient) -> None:
    assert client.get("/api/cases").status_code == 401
    assert client.post("/api/cases", json={"title": "x"}).status_code == 401


# --------------------------------------------------------------------------
# Transition guards.
# --------------------------------------------------------------------------


def test_a_blocked_critical_task_prevents_review(client: TestClient) -> None:
    login(client, "david.drm@demo")
    response = transition(client, BLOCKED_CASE, "READY_FOR_REVIEW")
    assert response.status_code == 422
    assert "Transport contracts confirmed" in response.json()["error"]["detail"]


@pytest.mark.parametrize("to_state", ["APPROVED", "HANDED_OFF", "REJECTED", "INGESTED", "NOT_A_STATE"])
def test_illegal_target_states_are_rejected(client: TestClient, to_state: str) -> None:
    login(client, "david.drm@demo")
    assert transition(client, BLOCKED_CASE, to_state).status_code == 422


def test_approved_state_is_unreachable_by_direct_transition(client: TestClient) -> None:
    """APPROVED may only be produced by three valid signatures."""
    login(client, "david.drm@demo")
    assert transition(client, BLOCKED_CASE, "APPROVED").status_code == 422
    assert get_case_state(BLOCKED_CASE) == "ASSESSED"


def get_case_state(case_id: str) -> str:
    with connection() as conn:
        return get_case(conn, case_id)["state"]


def test_terminal_cases_cannot_transition_or_change_tasks(client: TestClient) -> None:
    login(client, "david.drm@demo")
    assert transition(client, REVOKED_CASE, "HANDED_OFF").status_code == 422
    login(client, "grace.ngo@demo")
    task = client.get(f"/api/cases/{REVOKED_CASE}").json()["tasks"][0]
    response = client.post(
        f"/api/cases/{REVOKED_CASE}/tasks/{task['id']}",
        json={"action": "resolve", "version": version(client, REVOKED_CASE)},
    )
    assert response.status_code == 422


def test_revocation_requires_a_reason(client: TestClient) -> None:
    login(client, "david.drm@demo")
    assert transition(client, DONE_CASE, "REVOKED").status_code == 422
    assert transition(client, DONE_CASE, "REVOKED", reason="   ").status_code == 422
    assert transition(client, DONE_CASE, "REVOKED", reason="Signal collapsed").status_code == 200


def test_handoff_requires_at_least_one_export(client: TestClient) -> None:
    reset_demo()
    with TestClient(app) as amina, TestClient(app) as david, TestClient(app) as grace:
        for instance, email in ((amina, "amina.ews@demo"), (david, "david.drm@demo"), (grace, "grace.ngo@demo")):
            login(instance, email)
        for task_id in ("task_transport",):
            grace.post(f"/api/cases/{BLOCKED_CASE}/tasks/{task_id}", json={"action": "resolve", "version": version(grace)})
        assert transition(david, BLOCKED_CASE, "READY_FOR_REVIEW").status_code == 200
        for instance in (amina, david, grace):
            assert instance.post(
                f"/api/cases/{BLOCKED_CASE}/approvals",
                json={"decision": "approve", "version": version(instance)},
            ).status_code == 200
        assert get_case_state(BLOCKED_CASE) == "APPROVED"
        assert transition(david, BLOCKED_CASE, "HANDED_OFF").status_code == 422
        assert david.post(f"/api/cases/{BLOCKED_CASE}/exports/cap", json={}).status_code == 200
        assert transition(david, BLOCKED_CASE, "HANDED_OFF").status_code == 200


# --------------------------------------------------------------------------
# Approval guards.
# --------------------------------------------------------------------------


def test_approvals_are_rejected_outside_review(client: TestClient) -> None:
    login(client, "amina.ews@demo")
    response = client.post(f"/api/cases/{BLOCKED_CASE}/approvals", json={"decision": "approve", "version": version(client)})
    assert response.status_code == 422


def test_a_role_cannot_sign_twice(client: TestClient) -> None:
    reset_demo()
    with TestClient(app) as david, TestClient(app) as amina:
        login(david, "david.drm@demo")
        login(amina, "amina.ews@demo")
        david.post(f"/api/cases/{BLOCKED_CASE}/tasks/task_transport", json={"action": "resolve", "version": version(david)})
        login(david, "grace.ngo@demo")
        david.post(f"/api/cases/{BLOCKED_CASE}/tasks/task_transport", json={"action": "resolve", "version": version(david)})
        login(david, "david.drm@demo")
        assert transition(david, BLOCKED_CASE, "READY_FOR_REVIEW").status_code == 200
        assert amina.post(f"/api/cases/{BLOCKED_CASE}/approvals", json={"decision": "approve", "version": version(amina)}).status_code == 200
        assert amina.post(f"/api/cases/{BLOCKED_CASE}/approvals", json={"decision": "approve", "version": version(amina)}).status_code == 409


def test_two_signatures_do_not_approve_a_case(client: TestClient) -> None:
    reset_demo()
    with TestClient(app) as david, TestClient(app) as amina, TestClient(app) as grace:
        login(david, "david.drm@demo")
        login(amina, "amina.ews@demo")
        login(grace, "grace.ngo@demo")
        grace.post(f"/api/cases/{BLOCKED_CASE}/tasks/task_transport", json={"action": "resolve", "version": version(grace)})
        assert transition(david, BLOCKED_CASE, "READY_FOR_REVIEW").status_code == 200
        amina.post(f"/api/cases/{BLOCKED_CASE}/approvals", json={"decision": "approve", "version": version(amina)})
        david.post(f"/api/cases/{BLOCKED_CASE}/approvals", json={"decision": "approve", "version": version(david)})
        assert get_case_state(BLOCKED_CASE) == "READY_FOR_REVIEW"
        assert david.get(f"/api/cases/{BLOCKED_CASE}/approvals/verify").json()["three_role_approval_valid"] is False


def test_blockers_require_a_taxonomy_code_and_note(client: TestClient) -> None:
    login(client, "grace.ngo@demo")
    for body in (
        {"action": "block", "version": version(client)},
        {"action": "block", "version": version(client), "blocker_code": "NOT_A_CODE", "note": "x"},
        {"action": "block", "version": version(client), "blocker_code": "STAFFING", "note": "  "},
    ):
        assert client.post(f"/api/cases/{BLOCKED_CASE}/tasks/task_fodder", json=body).status_code == 422


# --------------------------------------------------------------------------
# Signing.
# --------------------------------------------------------------------------


def test_the_signed_snapshot_is_canonical_and_state_independent() -> None:
    reset_demo()
    with connection() as conn:
        case = get_case(conn, DONE_CASE)
    first = canonical_case_json(case)
    reordered = {key: case[key] for key in reversed(list(case))}
    assert canonical_case_json(reordered) == first
    assert canonical_case_json({**case, "state": "REVOKED"}) == first
    assert "state" not in json.loads(first)


def test_all_three_seeded_signatures_cover_the_same_digest(client: TestClient) -> None:
    login(client, "observer@demo")
    report = client.get(f"/api/cases/{DONE_CASE}/approvals/verify").json()
    assert report["three_role_approval_valid"] is True
    assert {item["digest"] for item in report["signatures"]} == {report["current_digest"]}
    assert all(item["signature_valid"] for item in report["signatures"])
