"""Contract tests for the full API run once the project dependencies are installed."""
from fastapi.testclient import TestClient

from backend.app.main import app


def test_health_and_seeded_case_are_available():
    with TestClient(app) as client:
        assert client.get("/api/healthz").status_code == 200
        assert client.post("/api/seed").status_code == 200
        response = client.get("/api/cases", headers={"X-Demo-User": "david.drm@demo"})
        assert response.status_code == 200
        assert response.json()["cases"][0]["state"] == "ASSESSED"


def test_integration_endpoints_require_a_key():
    with TestClient(app) as client:
        client.post("/api/seed")
        assert client.get("/integration/v1/activations").status_code == 401


def test_task_owner_guard_and_integration_key_flow():
    with TestClient(app) as client:
        client.post("/api/seed")
        case_id = client.get("/api/cases", headers={"X-Demo-User": "david.drm@demo"}).json()["cases"][0]["id"]
        forbidden = client.post(
            f"/api/cases/{case_id}/tasks/task_transport/resolve",
            headers={"X-Demo-User": "observer@demo"},
        )
        assert forbidden.status_code == 403
        key_response = client.post(
            "/api/admin/integration-keys",
            headers={"X-Demo-User": "admin@demo"},
            json={"label": "contract test"},
        )
        assert key_response.status_code == 200
        key = key_response.json()["key"]
        response = client.get("/integration/v1/activations", headers={"Authorization": f"Bearer {key}"})
        assert response.status_code == 200
        assert response.json()["mode"] == "exercise"
