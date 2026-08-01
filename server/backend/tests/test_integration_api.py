"""Partner API contract: auth, rate limit, frozen response shape, webhooks."""

from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from app import integration
from app.db import connection, reset_demo
from app.domain import canonical_json
from app.main import app

SCHEMA = Path(__file__).resolve().parents[1] / "content" / "schemas" / "integration" / "activation.v1.schema.json"
PUBLISHED = "case_ruvuma_ond2026_handedoff"
UNPUBLISHED = "case_ruvuma_ond2026"


@pytest.fixture()
def admin() -> TestClient:
    reset_demo()
    with TestClient(app) as client:
        client.post("/api/auth/login", json={"email": "admin@demo", "password": "linda-demo"})
        yield client


def issue_key(admin: TestClient, label: str = "test partner") -> str:
    return admin.post("/api/admin/integration-keys", json={"label": label}).json()["key"]


def auth(key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}"}


# --------------------------------------------------------------------------
# Public surfaces.
# --------------------------------------------------------------------------


def test_public_surfaces_need_no_key(admin: TestClient) -> None:
    for path in ("/cap/feed.xml", "/integration/v1/openapi.json", "/integration/v1/docs",
                 "/integration/v1/schemas/activation.json", "/healthz"):
        assert admin.get(path).status_code == 200, path


def test_the_cap_feed_publishes_approved_and_revoked_activations(admin: TestClient) -> None:
    body = admin.get("/cap/feed.xml").text
    assert PUBLISHED in body
    assert "case_ruvuma_ond2026_revoked" in body
    assert "<status>Exercise</status>" in body or "Exercise" in body
    assert UNPUBLISHED not in body.replace(f"{UNPUBLISHED}_handedoff", "").replace(f"{UNPUBLISHED}_revoked", "")


def test_the_filtered_openapi_only_exposes_integration_paths(admin: TestClient) -> None:
    paths = admin.get("/integration/v1/openapi.json").json()["paths"]
    assert paths
    assert all(path.startswith("/integration/") or path == "/cap/feed.xml" for path in paths)
    assert "/api/cases" not in paths


# --------------------------------------------------------------------------
# API-key auth.
# --------------------------------------------------------------------------


def test_missing_or_malformed_keys_are_rejected(admin: TestClient) -> None:
    assert admin.get("/integration/v1/activations").status_code == 401
    assert admin.get("/integration/v1/activations", headers={"Authorization": "Bearer nope"}).status_code == 401
    assert admin.get("/integration/v1/activations", headers={"Authorization": "Basic abc"}).status_code == 401


def test_a_valid_key_reads_activations(admin: TestClient) -> None:
    response = admin.get("/integration/v1/activations", headers=auth(issue_key(admin)))
    assert response.status_code == 200
    body = response.json()
    assert body["mode"] == "exercise"
    assert body["disclaimer"]
    assert {item["id"] for item in body["items"]} == {PUBLISHED, "case_ruvuma_ond2026_revoked"}


def test_a_revoked_key_stops_working(admin: TestClient) -> None:
    key = issue_key(admin, "short lived")
    key_id = admin.get("/api/admin/integration-keys").json()[0]["id"]
    assert admin.get("/integration/v1/activations", headers=auth(key)).status_code == 200
    assert admin.delete(f"/api/admin/integration-keys/{key_id}").status_code == 204
    assert admin.get("/integration/v1/activations", headers=auth(key)).status_code == 401


def test_keys_are_stored_hashed_and_shown_once(admin: TestClient) -> None:
    key = issue_key(admin)
    with connection() as conn:
        rows = [dict(row) for row in conn.execute("SELECT * FROM integration_keys")]
    assert all(key not in row["key_hash"] for row in rows)
    assert all("key" not in item for item in admin.get("/api/admin/integration-keys").json())


def test_the_rate_limit_is_enforced_per_key(admin: TestClient) -> None:
    key = issue_key(admin, "rate limited")
    integration._key_requests.clear()
    codes = [admin.get("/integration/v1/activations", headers=auth(key)).status_code for _ in range(62)]
    assert codes.count(429) >= 1
    assert codes[0] == 200


def test_only_an_admin_can_manage_keys_and_webhooks(admin: TestClient) -> None:
    admin.post("/api/auth/login", json={"email": "david.drm@demo", "password": "linda-demo"})
    assert admin.get("/api/admin/integration-keys").status_code == 403
    assert admin.post("/api/admin/webhooks", json={"url": "https://example.com/hook", "events": ["activation.approved"], "secret": "0123456789abcdef"}).status_code == 403


# --------------------------------------------------------------------------
# Frozen response shape — a change here is a breaking API change.
# --------------------------------------------------------------------------


def test_the_activation_record_matches_the_published_schema(admin: TestClient) -> None:
    record = admin.get(f"/integration/v1/activations/{PUBLISHED}", headers=auth(issue_key(admin))).json()
    Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8"))).validate(record)


def test_the_activation_record_keeps_its_documented_keys(admin: TestClient) -> None:
    record = admin.get(f"/integration/v1/activations/{PUBLISHED}", headers=auth(issue_key(admin))).json()
    assert set(record) == {
        "mode", "disclaimer", "id", "title", "area", "hazard", "stage", "ndma_phase", "state",
        "assessment", "action_cards", "approvals", "evidence", "compound_signals",
        "manifest_sha256", "links",
    }
    assert set(record["links"]) == {"self", "cap", "husika_payload", "verify"}
    assert record["mode"] == "exercise"


def test_unpublished_cases_are_not_readable_by_partners(admin: TestClient) -> None:
    key = issue_key(admin)
    assert admin.get(f"/integration/v1/activations/{UNPUBLISHED}", headers=auth(key)).status_code == 404


def test_per_activation_views_are_available(admin: TestClient) -> None:
    key = issue_key(admin)
    assert admin.get(f"/integration/v1/activations/{PUBLISHED}/cap.xml", headers=auth(key)).status_code == 200
    husika = admin.get(f"/integration/v1/activations/{PUBLISHED}/husika-payload.json", headers=auth(key)).json()
    assert husika["mode"] == "exercise"
    report = admin.get(f"/integration/v1/activations/{PUBLISHED}/verify", headers=auth(key)).json()
    assert report["event_chain"]["ok"] is True
    assert report["signatures"]["three_role_approval_valid"] is True
    assert report["manifest"]


def test_verification_reports_a_tampered_record(admin: TestClient) -> None:
    key = issue_key(admin)
    with connection() as conn:
        first = conn.execute("SELECT id FROM case_events WHERE case_id = ? ORDER BY seq LIMIT 1", (PUBLISHED,)).fetchone()
        conn.execute("UPDATE case_events SET data = ? WHERE id = ?", ('{"tampered":true}', first["id"]))
        conn.commit()
    report = admin.get(f"/integration/v1/activations/{PUBLISHED}/verify", headers=auth(key)).json()
    assert report["event_chain"]["ok"] is False


def test_pagination_uses_an_opaque_cursor(admin: TestClient) -> None:
    key = issue_key(admin)
    first = admin.get("/integration/v1/activations?limit=1", headers=auth(key)).json()
    assert len(first["items"]) == 1 and first["next"]
    second = admin.get(f"/integration/v1/activations?limit=1&cursor={first['next']}", headers=auth(key)).json()
    assert second["items"][0]["id"] != first["items"][0]["id"]
    assert admin.get("/integration/v1/activations?limit=1&cursor=malformed", headers=auth(key)).status_code == 422


def test_filters_narrow_the_collection(admin: TestClient) -> None:
    key = issue_key(admin)
    revoked = admin.get("/integration/v1/activations?state=REVOKED", headers=auth(key)).json()
    assert {item["state"] for item in revoked["items"]} == {"REVOKED"}
    assert admin.get("/integration/v1/activations?area=KEN.99_1", headers=auth(key)).json()["items"] == []


# --------------------------------------------------------------------------
# Webhooks.
# --------------------------------------------------------------------------


def test_webhook_urls_must_be_public_https(admin: TestClient) -> None:
    for url in ("http://example.com/hook", "https://localhost/hook", "https://127.0.0.1/hook",
                "https://user:pass@example.com/hook"):
        response = admin.post("/api/admin/webhooks", json={"url": url, "events": ["activation.approved"], "secret": "0123456789abcdef"})
        assert response.status_code == 422, url


def test_webhook_events_are_restricted_to_the_published_pair(admin: TestClient) -> None:
    response = admin.post("/api/admin/webhooks", json={"url": "https://example.com/h", "events": ["case.deleted"], "secret": "0123456789abcdef"})
    assert response.status_code == 422


def test_webhook_secrets_are_never_returned(admin: TestClient) -> None:
    with connection() as conn:
        integration.create_webhook(conn, "https://example.com/hook", ["activation.approved"], "0123456789abcdef")
        conn.commit()
    listed = admin.get("/api/admin/webhooks").json()
    assert listed and all("secret" not in item for item in listed)


@pytest.mark.asyncio
async def test_delivery_signature_verifies_and_the_id_matches_the_audit_row(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_demo()
    secret = "0123456789abcdef0123"
    with connection() as conn:
        integration.create_webhook(conn, "https://example.com/hook", ["activation.approved"], secret)
        conn.commit()
    captured: dict[str, Any] = {}

    class Response:
        status_code = 200

    class Client:
        async def __aenter__(self) -> "Client":
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

        async def post(self, url: str, content: bytes, headers: dict[str, str]) -> Response:
            captured.update({"url": url, "body": content, "headers": headers})
            return Response()

    monkeypatch.setattr(integration.httpx, "AsyncClient", lambda **_: Client())
    await integration.deliver_webhooks(PUBLISHED, "activation.approved")

    expected = hmac.new(secret.encode(), captured["body"], hashlib.sha256).hexdigest()
    assert captured["headers"]["X-Linda-Signature"] == f"sha256={expected}"
    assert captured["headers"]["X-Linda-Event"] == "activation.approved"
    delivery_id = captured["headers"]["X-Linda-Delivery"]
    with connection() as conn:
        row = conn.execute("SELECT * FROM webhook_deliveries WHERE id = ?", (delivery_id,)).fetchone()
        events = [dict(item) for item in conn.execute(
            "SELECT * FROM case_events WHERE case_id = ? AND event_type = 'WEBHOOK_DELIVERED'", (PUBLISHED,))]
    assert row is not None and row["delivered"] == 1
    assert any(json.loads(item["data"])["delivery_id"] == delivery_id for item in events)
    # The signed body is exactly the published activation record, canonically encoded.
    with connection() as conn:
        assert captured["body"] == canonical_json(integration.activation_record(conn, PUBLISHED)).encode()


@pytest.mark.asyncio
async def test_a_failing_endpoint_is_retried_and_recorded(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_demo()
    with connection() as conn:
        integration.create_webhook(conn, "https://example.com/hook", ["activation.revoked"], "0123456789abcdef0123")
        conn.commit()
    monkeypatch.setattr(integration, "WEBHOOK_BACKOFF_SECONDS", (0, 0))

    class Client:
        async def __aenter__(self) -> "Client":
            return self

        async def __aexit__(self, *_: object) -> None:
            return None

        async def post(self, *_: object, **__: object) -> None:
            raise integration.httpx.ConnectError("refused")

    monkeypatch.setattr(integration.httpx, "AsyncClient", lambda **_: Client())
    await integration.deliver_webhooks("case_ruvuma_ond2026_revoked", "activation.revoked")
    with connection() as conn:
        attempts = [dict(row) for row in conn.execute("SELECT * FROM webhook_deliveries")]
        failed = conn.execute(
            "SELECT COUNT(*) AS count FROM case_events WHERE event_type = 'WEBHOOK_FAILED'").fetchone()["count"]
    assert len(attempts) == 2
    assert {item["attempt"] for item in attempts} == {1, 2}
    assert all(item["delivered"] == 0 and item["status_code"] is None for item in attempts)
    assert failed == 2
