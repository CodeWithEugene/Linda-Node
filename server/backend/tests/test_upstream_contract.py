"""Live ICPAC contract checks. Opt in with `pytest -m contract --contract`.

These fail loudly when upstream changes the field names or response envelopes
that the adapters depend on — the recorded fixtures cannot detect that drift on
their own.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.config import settings
from app.sources import normalise_areas, normalise_forecasts, normalise_triggers, validate_source

pytestmark = pytest.mark.contract
TIMEOUT = 30


def get(path: str) -> Any:
    response = httpx.get(f"{settings.icpac_base}{path}", timeout=TIMEOUT)
    response.raise_for_status()
    return response.json()


def test_live_trigger_endpoints_still_normalise_and_validate() -> None:
    payload = normalise_triggers(
        get("/api/triggers/rules/"),
        get("/api/triggers/events/"),
        get("/api/triggers/actions/"),
        get("/api/triggers/check-logs/?page_size=20"),
    )
    assert not validate_source("triggers", payload)
    assert payload["rules"], "upstream returned no trigger rules"
    assert all(rule["area_id"] for rule in payload["rules"]), "area_gid mapping drifted"
    assert all(rule["indicator"] != "unknown" for rule in payload["rules"]), "indicator_code mapping drifted"


def test_the_upstream_action_type_set_has_not_changed() -> None:
    """The pitch rests on this: ICPAC dispatches email_alert and dashboard_update."""
    payload = normalise_triggers([], [], get("/api/triggers/actions/"), [])
    assert {item["action_type"] for item in payload["actions"]} == {"email_alert", "dashboard_update"}


def test_live_forecast_statistics_still_carry_return_period_probabilities() -> None:
    available = get("/api/datasets/forecasts/available/?forecast_type=return_period")
    issues = available.get("forecasts", available.get("results", []))
    assert issues, "no seasonal forecast issues published"
    issue = next((item for item in issues if item.get("target_season") == "OND"), issues[0])
    stats = get(
        f"/api/datasets/forecasts/stats/?admin_level=1&valid_date={issue['valid_date']}"
        f"&lead_months={issue['lead_months']}&min_probability=0&country=KEN"
    )
    assert stats.get("stats"), "stats endpoint returned no admin rows"
    assert "avg_prob_rp3" in stats["stats"][0], "return-period probability field drifted"
    payload = normalise_forecasts(available, stats)
    assert not validate_source("forecasts", payload)
    assert all(0 <= item["probability"] <= 1 for item in payload["forecasts"])


def test_live_areas_still_expose_gadm_identifiers() -> None:
    payload = normalise_areas(get("/api/areas/areas/?level=1&code=KEN"))
    assert not validate_source("areas", payload)
    assert any(item["id"] == "KEN.3_1" for item in payload["areas"]), "Bungoma GADM id missing upstream"


def test_the_vendored_husika_spec_still_matches_upstream() -> None:
    from app.domain import sha256
    from app.husika_contract import SPEC_PATH, metadata

    response = httpx.get("https://api.ingestor.husika.icpac.net/openapi.json", timeout=TIMEOUT)
    response.raise_for_status()
    live = response.json()
    vendored = metadata()
    assert vendored["sha256"] == sha256(SPEC_PATH.read_bytes())
    for name in ("ThreatCreate", "BroadcastCreate", "BroadcastMessageBase", "ContentLocationCreate"):
        assert name in live["components"]["schemas"], f"{name} disappeared from the Husika contract"
