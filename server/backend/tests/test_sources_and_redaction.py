"""Adapters, provenance hashing, schema validation, and email redaction."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import sources
from app.db import connection, reset_demo, transaction
from app.domain import sha256
from app.main import app
from app.redaction import EMAIL_PATTERN, mask_email, redact
from app.sources import (
    normalise_areas,
    normalise_forecasts,
    normalise_triggers,
    parse_pipeline_csv,
    refresh_adapter,
    validate_source,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "replay"
REAL_ADDRESSES = ("crimson.sikolia@igad.int", "crimsonmukweyi@gmail.com")


def fixture(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------
# Redaction (build.md 6.2).
# --------------------------------------------------------------------------


def test_mask_email_keeps_the_domain_and_one_initial() -> None:
    assert mask_email("crimson.sikolia@igad.int") == "c***@igad.int"
    assert mask_email("not-an-address") == "not-an-address"


def test_redact_walks_nested_structures() -> None:
    payload = {"a": [{"emails": "one@x.org, two@y.net"}], "b": {"c": "plain"}, "d": 3}
    masked = redact(payload)
    assert masked["a"][0]["emails"] == "o***@x.org, t***@y.net"
    assert masked["b"]["c"] == "plain"
    assert masked["d"] == 3


def test_the_recorded_fixture_still_contains_the_real_addresses() -> None:
    """Provenance is preserved on disk; masking is a read-path concern."""
    raw = (FIXTURES / "triggers.json").read_text(encoding="utf-8")
    assert all(address in raw for address in REAL_ADDRESSES)


@pytest.mark.parametrize("address", REAL_ADDRESSES)
def test_no_endpoint_leaks_a_personal_address(address: str) -> None:
    reset_demo()
    with TestClient(app) as client:
        assert client.post("/api/auth/login", json={"email": "david.drm@demo", "password": "linda-demo"}).status_code == 200
        paths = [
            "/api/signals", "/api/sources/status", "/api/sources/snapshots",
            "/api/cases", "/api/cases/case_bungoma_ond2026",
            "/api/cases/case_bungoma_ond2026/events", "/api/audit", "/cap/feed.xml",
        ]
        snapshots = client.get("/api/sources/snapshots").json()
        paths += [f"/api/sources/snapshots/{item['id']}" for item in snapshots]
        for path in paths:
            body = client.get(path).text
            assert address not in body, f"{path} leaked {address}"
            assert "c***@igad.int" in body or address.split("@")[0] not in body


def test_generated_exports_carry_no_personal_address() -> None:
    reset_demo()
    with TestClient(app) as client:
        client.post("/api/auth/login", json={"email": "david.drm@demo", "password": "linda-demo"})
        exports = client.get("/api/cases/case_bungoma_ond2026_handedoff").json()["exports"]
        assert exports
        for export in exports:
            content = client.get(f"/api/exports/{export['id']}/download").content
            for address in REAL_ADDRESSES:
                assert address.encode() not in content, f"{export['kind']} leaked {address}"


# --------------------------------------------------------------------------
# Normalisation of the real ICPAC field names.
# --------------------------------------------------------------------------


def test_trigger_rules_map_upstream_field_names() -> None:
    raw = fixture("triggers.json")
    payload = normalise_triggers(raw["rules"], raw["events"], raw["actions"], raw["check_logs"])
    rule = next(item for item in payload["rules"] if item["name"] == "Bungoma Triggers")
    assert rule["area_id"] == "KEN.3_1"          # upstream: area_gid
    assert rule["indicator"] == "tmax"            # upstream: indicator_code
    assert rule["severity"] == "moderate"         # upstream: severity_level
    assert rule["hazard"] == "heat"               # upstream: hazard_type "heat_raw"
    assert rule["active"] is True                 # upstream: is_active
    assert not validate_source("triggers", payload)


def test_upstream_action_types_are_captured_verbatim() -> None:
    """The pitch anchor: ICPAC's engine has exactly email_alert and dashboard_update."""
    raw = fixture("triggers.json")
    payload = normalise_triggers(raw["rules"], raw["events"], raw["actions"], raw["check_logs"])
    assert {item["action_type"] for item in payload["actions"]} == {"email_alert", "dashboard_update"}


def test_forecast_probability_comes_from_the_stats_endpoint() -> None:
    raw = fixture("escalation/step2.json")
    payload = normalise_forecasts(raw["available"], raw["stats"])
    bungoma = next(item for item in payload["forecasts"] if item["area_id"] == "KEN.3_1")
    assert bungoma["probability"] == pytest.approx(0.52)   # avg_prob_rp3 52.0 percent
    assert bungoma["quantile"] == 0.33                      # rp3 tail
    assert bungoma["lead_months"] == 3
    assert "avg_prob_rp3" in bungoma["probability_source"]
    assert not validate_source("forecasts", payload)


def test_recorded_live_statistics_do_not_reach_an_activation_stage() -> None:
    """The honest baseline: the real OND 2026 signal for Bungoma is far below policy."""
    raw = fixture("forecasts.json")
    payload = normalise_forecasts(raw["available"], raw["stats"])
    assert max(item["probability"] for item in payload["forecasts"]) < 0.35


def test_areas_coerce_the_string_level_to_an_integer() -> None:
    payload = normalise_areas(fixture("areas.json"))
    assert all(isinstance(item["level"], int) for item in payload["areas"])
    assert any(item["id"] == "KEN.3_1" and item["name"] == "Bungoma" for item in payload["areas"])
    assert not validate_source("areas", payload)


def test_pipeline_csv_parses_the_icpac_column_layout() -> None:
    text = (FIXTURES / "pipeline_ond2026.csv").read_text(encoding="utf-8")
    payload = parse_pipeline_csv(text, source_file="03_prob_csv_q.py compatible output")
    bungoma = next(item for item in payload["files"] if item["area_id"] == "KEN.3_1")
    assert bungoma["probability"] == pytest.approx(0.52)
    assert bungoma["quantile"] == pytest.approx(0.33)
    assert not validate_source("pipeline", payload)


def test_pipeline_csv_skips_malformed_rows() -> None:
    payload = parse_pipeline_csv(
        "admin_id,admin_name,season,indicator,quantile,probability,lead_months\n"
        ",Nowhere,OND,spi3,0.33,0.5,3\n"
        "KEN.3_1,Bungoma,OND,spi3,0.33,not-a-number,3\n"
        "KEN.3_1,Bungoma,OND,spi3,0.33,0.41,3\n",
        source_file="unit test",
    )
    assert len(payload["files"]) == 1
    assert payload["files"][0]["probability"] == pytest.approx(0.41)


# --------------------------------------------------------------------------
# Schema validation drives schema_ok.
# --------------------------------------------------------------------------


def test_a_missing_required_field_fails_source_validation() -> None:
    assert validate_source("forecasts", {"forecasts": [{"id": "x"}]})
    assert validate_source("triggers", {"rules": []})  # events/actions absent
    assert validate_source("areas", {"areas": []})     # at least one area required


def test_a_schema_failure_is_recorded_on_the_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_demo()
    monkeypatch.setattr(sources, "normalise_areas", lambda _: {"areas": [{"id": "x"}]})
    with transaction() as conn:
        sources.set_source_mode(conn, "replay_only")
        snapshot = refresh_adapter(conn, "areas", force=True)
    assert snapshot["schema_ok"] is False
    assert snapshot["meta"]["schema_errors"]


# --------------------------------------------------------------------------
# Provenance: the recorded hash covers the verbatim upstream body.
# --------------------------------------------------------------------------


def test_snapshot_hash_covers_the_verbatim_body_not_the_parsed_view() -> None:
    reset_demo()
    with transaction() as conn:
        sources.set_source_mode(conn, "replay_only")
        snapshot = refresh_adapter(conn, "triggers", force=True)
    raw_text = (FIXTURES / "triggers.json").read_text(encoding="utf-8")
    parts = snapshot["meta"]["parts"]
    assert len(parts) == 1
    # Exactly what `shasum -a 256 fixtures/replay/triggers.json` prints.
    assert parts[0]["sha256"] == sha256(raw_text)
    assert snapshot["payload_sha256"] != sha256(json.dumps(snapshot["payload"]))


def test_each_live_endpoint_gets_its_own_reproducible_hash() -> None:
    reset_demo()
    with connection() as conn:
        snapshot = conn.execute("SELECT meta_json FROM source_snapshots WHERE adapter = 'forecasts'").fetchone()
    parts = json.loads(snapshot["meta_json"])["parts"]
    assert parts and all(item["sha256"] and item["bytes"] > 0 for item in parts)


def test_raw_payload_preview_is_bounded_and_masked() -> None:
    reset_demo()
    with TestClient(app) as client:
        client.post("/api/auth/login", json={"email": "observer@demo", "password": "linda-demo"})
        snapshots = client.get("/api/sources/snapshots").json()
        areas = next(item for item in snapshots if item["adapter"] == "areas")
        detail = client.get(f"/api/sources/snapshots/{areas['id']}").json()
        assert detail["raw"]["available"] is True
        assert len(detail["raw"]["preview"]) <= sources.RAW_RESPONSE_PREVIEW_CHARS
        assert not EMAIL_PATTERN.findall(detail["raw"]["preview"]) or "***@" in detail["raw"]["preview"]


# --------------------------------------------------------------------------
# Cache and replay behaviour.
# --------------------------------------------------------------------------


def test_a_fresh_snapshot_is_reused_instead_of_refetched() -> None:
    reset_demo()
    with transaction() as conn:
        sources.set_source_mode(conn, "replay_only")
        first = refresh_adapter(conn, "triggers", force=True)
        second = refresh_adapter(conn, "triggers")
    assert second["id"] == first["id"]


def test_force_always_creates_a_new_snapshot() -> None:
    reset_demo()
    with transaction() as conn:
        sources.set_source_mode(conn, "replay_only")
        first = refresh_adapter(conn, "triggers", force=True)
        second = refresh_adapter(conn, "triggers", force=True)
    assert second["id"] != first["id"]


def test_changing_the_escalation_step_produces_a_new_snapshot() -> None:
    reset_demo()
    with transaction() as conn:
        sources.set_source_mode(conn, "replay_only")
        sources.set_replay_step(conn, 1)
        low = refresh_adapter(conn, "forecasts", force=True)
        sources.set_replay_step(conn, 3)
        high = refresh_adapter(conn, "forecasts")
    def bungoma(snapshot: dict) -> float:
        return next(item["probability"] for item in snapshot["payload"]["forecasts"] if item["area_id"] == "KEN.3_1")
    assert bungoma(low) == pytest.approx(0.32)
    assert bungoma(high) == pytest.approx(0.63)
    assert high["id"] != low["id"]


def test_replay_snapshots_are_labelled_synthetic() -> None:
    reset_demo()
    with transaction() as conn:
        sources.set_source_mode(conn, "replay_only")
        snapshot = refresh_adapter(conn, "forecasts", force=True)
    assert snapshot["freshness"] == "replay"
    assert snapshot["meta"]["provenance"]["synthetic"] is True


def test_upstream_failure_falls_back_to_the_last_snapshot_marked_stale(monkeypatch: pytest.MonkeyPatch) -> None:
    reset_demo()
    with transaction() as conn:
        sources.set_source_mode(conn, "replay_only")
        refresh_adapter(conn, "triggers", force=True)
        sources.set_source_mode(conn, "live_first")

    def explode(_: str) -> tuple[str, dict]:
        raise sources.httpx.ConnectError("upstream down")

    monkeypatch.setattr(sources, "_get", explode)
    with transaction() as conn:
        snapshot = refresh_adapter(conn, "triggers", force=True)
    assert snapshot["freshness"] == "stale"
    assert "upstream down" in snapshot["meta"]["last_error"]
