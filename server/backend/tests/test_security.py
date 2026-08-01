"""Injection, rate limiting, and fail-closed policy loading."""

from __future__ import annotations

import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from app import auth, library
from app.db import connection, reset_demo, transaction
from app.exports import _render_packet, exported_payload, generate_bundle, packet_manifest
from app.library import PolicyInvalid
from app.main import app

XSS = "<script>alert('linda')</script>"
BLOCKED = "case_bungoma_ond2026"
PUBLISHED = "case_bungoma_ond2026_handedoff"


@pytest.fixture()
def client() -> TestClient:
    reset_demo()
    auth._attempts.clear()
    with TestClient(app) as instance:
        yield instance


def login(client: TestClient, email: str) -> None:
    assert client.post("/api/auth/login", json={"email": email, "password": "linda-demo"}).status_code == 200


def test_a_script_tag_in_a_blocker_note_is_escaped_in_rendered_exports(client: TestClient) -> None:
    login(client, "grace.ngo@demo")
    version = client.get(f"/api/cases/{BLOCKED}").json()["version"]
    assert client.post(
        f"/api/cases/{BLOCKED}/tasks/task_fodder",
        json={"action": "block", "version": version, "blocker_code": "STAFFING", "note": XSS},
    ).status_code == 200

    with transaction() as conn:
        bundle = generate_bundle(conn, PUBLISHED, "usr_david")
    # The note travels with its own case, but the renderer must escape any note.
    login(client, "grace.ngo@demo")
    stored = client.get(f"/api/cases/{BLOCKED}").json()["tasks"]
    assert any(task["blocker_note"] == XSS for task in stored)

    with connection() as conn:
        _, payload = exported_payload(conn, bundle["id"])
    dossier = zipfile.ZipFile(io.BytesIO(payload)).read("dossier.html").decode()
    assert "<script>alert" not in dossier


def test_untrusted_text_is_escaped_in_every_rendered_html_surface() -> None:
    """JSON manifests carry the literal value; HTML renderings must escape it."""
    reset_demo()
    with transaction() as conn:
        conn.execute("UPDATE readiness_tasks SET title = ? WHERE case_id = ?", (XSS, PUBLISHED))
        conn.execute("UPDATE decision_cases SET title = ? WHERE id = ?", (XSS, PUBLISHED))
        manifest = packet_manifest(conn, PUBLISHED)
    for template in ("packet.html", "offline_dossier.html"):
        rendered = _render_packet(manifest, template)
        assert "<script>alert" not in rendered
        assert "&lt;script&gt;" in rendered


def test_the_husika_message_body_is_length_bounded(client: TestClient) -> None:
    login(client, "david.drm@demo")
    response = client.post(f"/api/cases/{PUBLISHED}/exports/husika", json={"message": "x" * 4000})
    assert response.status_code == 422


def test_login_is_rate_limited(client: TestClient) -> None:
    for _ in range(5):
        assert client.post("/api/auth/login", json={"email": "david.drm@demo", "password": "wrong"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "david.drm@demo", "password": "wrong"}).status_code == 429
    assert client.post("/api/auth/login", json={"email": "david.drm@demo", "password": "linda-demo"}).status_code == 429


def test_a_forged_session_cookie_is_rejected(client: TestClient) -> None:
    client.cookies.set("linda_session", "forged.header.signature")
    assert client.get("/api/me").status_code == 401


def test_passwords_are_never_returned(client: TestClient) -> None:
    login(client, "david.drm@demo")
    body = client.get("/api/me").json()
    assert set(body) == {"id", "email", "display_name", "role", "org"}


def test_an_invalid_policy_refuses_to_load(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    library._policy_document.cache_clear()
    broken = tmp_path / "content"
    (broken / "actions").mkdir(parents=True)
    (broken / "policy.yaml").write_text("policy:\n  name: broken\n", encoding="utf-8")
    monkeypatch.setattr(library, "CONTENT_ROOT", broken)
    with pytest.raises(PolicyInvalid, match="policy.yaml failed schema validation"):
        library.policy()
    library._policy_document.cache_clear()


def test_an_invalid_action_card_refuses_to_load(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    library._action_card_documents.cache_clear()
    broken = tmp_path / "content"
    (broken / "actions").mkdir(parents=True)
    (broken / "actions" / "bad.yaml").write_text("id: not_a_card_id\nhazard: drought\n", encoding="utf-8")
    monkeypatch.setattr(library, "CONTENT_ROOT", broken)
    with pytest.raises(PolicyInvalid, match="bad.yaml failed schema validation"):
        library.action_cards()
    library._action_card_documents.cache_clear()


def test_the_shipped_library_is_valid() -> None:
    library._policy_document.cache_clear()
    library._action_card_documents.cache_clear()
    report = library.validate_library()
    assert report["schema_valid"] is True
    assert report["action_cards"] == 6
