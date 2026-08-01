"""Deterministic policy engine: boundaries, gates, and the no-fabrication rule."""

from __future__ import annotations

from typing import Any

import pytest

from app.library import policy
from app.policy_engine import (
    detect_compound_signals,
    evaluate,
    evaluate_stop_trigger,
    observed_signal,
)

AREA = "TZA.22_1"
INDICATOR = "spi3_chirps_forecast"
STAGES = policy()["data"]["policy"]["stages"]


def forecast_snapshot(probability: float, *, quantile: float = 0.33, lead_months: int = 3, area: str = AREA, retrieved_at: str = "2999-01-01T00:00:00Z") -> dict[str, Any]:
    return {
        "adapter": "forecasts", "schema_ok": True, "retrieved_at": retrieved_at,
        "payload": {"forecasts": [{
            "id": "f1", "name": "test", "area_id": area, "area_name": "Ruvuma", "hazard": "drought",
            "indicator": INDICATOR, "probability": probability, "quantile": quantile,
            "lead_months": lead_months, "probability_source": "unit test",
        }]},
    }


def events_snapshot(*hazards: str, area: str = AREA, status: str = "active") -> dict[str, Any]:
    return {
        "adapter": "triggers", "schema_ok": True, "retrieved_at": "2999-01-01T00:00:00Z",
        "payload": {"events": [
            {"id": str(index), "name": f"{hazard} signal", "area_id": area, "hazard": hazard, "status": status}
            for index, hazard in enumerate(hazards)
        ]},
    }


# --------------------------------------------------------------------------
# Stage boundaries: at / just below / just above every threshold.
# --------------------------------------------------------------------------


@pytest.mark.parametrize("stage_name", ["ready", "set", "go"])
def test_probability_exactly_at_the_threshold_reaches_that_stage(stage_name: str) -> None:
    condition = STAGES[stage_name]["condition"]
    assessment = evaluate([forecast_snapshot(condition["probability_gte"], quantile=condition["quantile"])], "drought", AREA)
    assert assessment["stage"] == stage_name


@pytest.mark.parametrize("stage_name", ["ready", "set", "go"])
def test_probability_just_below_the_threshold_does_not_reach_that_stage(stage_name: str) -> None:
    condition = STAGES[stage_name]["condition"]
    assessment = evaluate([forecast_snapshot(condition["probability_gte"] - 0.001, quantile=condition["quantile"])], "drought", AREA)
    reached = assessment["stage"]
    assert reached != stage_name or reached is None


def test_highest_satisfied_stage_wins() -> None:
    assert evaluate([forecast_snapshot(0.63, quantile=0.20)], "drought", AREA)["stage"] == "go"
    assert evaluate([forecast_snapshot(0.52)], "drought", AREA)["stage"] == "set"
    assert evaluate([forecast_snapshot(0.36)], "drought", AREA)["stage"] == "ready"


def test_quantile_outside_the_policy_band_blocks_every_stage() -> None:
    assessment = evaluate([forecast_snapshot(0.99, quantile=0.90)], "drought", AREA)
    assert assessment["stage"] is None


def test_lead_time_below_the_stage_minimum_blocks_that_stage() -> None:
    # SET requires at least one month of lead; GO has no lead requirement but a
    # tighter quantile, so a zero-lead 0.55 signal reaches no stage at all.
    assessment = evaluate([forecast_snapshot(0.55, lead_months=0)], "drought", AREA)
    assert assessment["stage"] is None


# --------------------------------------------------------------------------
# The no-fabrication rule (build.md 6.17).
# --------------------------------------------------------------------------


def test_zero_signal_produces_no_stage_and_says_so() -> None:
    assessment = evaluate([forecast_snapshot(0.0)], "drought", AREA)
    assert assessment["stage"] is None
    assert assessment["ndma_phase"] is None
    assert assessment["recommendation"] == "no activation recommended"
    assert not assessment["eligible_action_cards"]
    assert [gate for gate in assessment["gates"] if gate["id"] == "signal_present"][0]["passed"] is False


def test_a_forecast_for_another_area_is_never_borrowed() -> None:
    assessment = evaluate([forecast_snapshot(0.9, area="KEN.99_1")], "drought", AREA)
    assert assessment["observed_signal"]["probability"] is None
    assert assessment["stage"] is None


def test_no_evidence_at_all_is_not_an_activation() -> None:
    assessment = evaluate([], "drought", AREA)
    assert assessment["stage"] is None
    assert assessment["cost_loss"]["expected_avoidable_loss_usd"] == 0


def test_observed_signal_picks_the_strongest_reading_for_the_area() -> None:
    snapshots = [forecast_snapshot(0.41), forecast_snapshot(0.58)]
    assert observed_signal(snapshots, AREA)["probability"] == 0.58


# --------------------------------------------------------------------------
# Gates.
# --------------------------------------------------------------------------


def gate(assessment: dict[str, Any], gate_id: str) -> dict[str, Any]:
    return next(item for item in assessment["gates"] if item["id"] == gate_id)


def test_stale_evidence_fails_the_freshness_gate() -> None:
    assessment = evaluate([forecast_snapshot(0.52, retrieved_at="2020-01-01T00:00:00Z")], "drought", AREA)
    assert gate(assessment, "source_freshness")["passed"] is False


def test_schema_failure_on_any_snapshot_fails_the_schema_gate() -> None:
    bad = {**forecast_snapshot(0.52), "schema_ok": False}
    assessment = evaluate([bad], "drought", AREA)
    assert gate(assessment, "schema_valid")["passed"] is False
    assert "forecasts" in gate(assessment, "schema_valid")["detail"]


def test_lead_time_gate_names_the_card_that_does_not_fit() -> None:
    assessment = evaluate([forecast_snapshot(0.52, lead_months=2)], "drought", AREA)
    reasons = {item["card"]: item["reason"] for item in assessment["ineligible"]}
    assert "card_seed_distribution_v1" in reasons
    assert "lead-time gate failed" in reasons["card_seed_distribution_v1"]


def test_stage_gate_reason_names_both_stages() -> None:
    assessment = evaluate([forecast_snapshot(0.36)], "drought", AREA)
    reasons = {item["card"]: item["reason"] for item in assessment["ineligible"]}
    assert "stage gate failed" in reasons["card_destocking_v1"]
    assert "SET" in reasons["card_destocking_v1"] and "READY" in reasons["card_destocking_v1"]


def test_net_benefit_gate_matches_a_hand_computed_figure() -> None:
    # P 0.52 x 12000 households x $180 x effectiveness 0.35 = $393,120.
    assessment = evaluate([forecast_snapshot(0.52)], "drought", AREA)
    trace = assessment["cost_loss"]
    assert trace["expected_avoidable_loss_usd"] == pytest.approx(393_120.0)
    assert trace["net_expected_benefit_usd"] == pytest.approx(393_120.0 - trace["action_cost_usd"])
    assert trace["exceeds_margin"] is True
    assert gate(assessment, "net_benefit")["passed"] is True


def test_every_cost_input_declares_its_provenance() -> None:
    sources = evaluate([forecast_snapshot(0.52)], "drought", AREA)["cost_loss"]["sources"]
    assert {item["source"] for item in sources} <= {"official_source", "policy_assumption", "user_entered"}
    assert all(item["citation"] for item in sources)


# --------------------------------------------------------------------------
# Stop trigger and compound signals.
# --------------------------------------------------------------------------


def test_stop_trigger_fires_only_below_the_policy_threshold() -> None:
    document = policy()["data"]["policy"]
    assert evaluate_stop_trigger(document, 0.22)["fired"] is True
    assert evaluate_stop_trigger(document, 0.30)["fired"] is False
    assert evaluate_stop_trigger(document, 0.99)["fired"] is False
    assert evaluate_stop_trigger(document, None)["fired"] is False


def test_compound_signals_require_two_hazards_in_the_same_area() -> None:
    snapshots = [forecast_snapshot(0.52), events_snapshot("drought", "flood")]
    assert detect_compound_signals(snapshots, AREA, "drought", "set") == ["drought", "flood"]


def test_compound_signals_ignore_other_areas() -> None:
    snapshots = [forecast_snapshot(0.52), events_snapshot("flood", area="KEN.99_1")]
    assert detect_compound_signals(snapshots, AREA, "drought", "set") == []


def test_compound_signals_ignore_resolved_events() -> None:
    snapshots = [forecast_snapshot(0.52), events_snapshot("flood", status="resolved")]
    assert detect_compound_signals(snapshots, AREA, "drought", "set") == []


def test_compound_signals_require_a_reached_stage() -> None:
    snapshots = [forecast_snapshot(0.0), events_snapshot("drought", "flood")]
    assert detect_compound_signals(snapshots, AREA, "drought", None) == []


def test_evaluate_is_pure_and_repeatable() -> None:
    snapshots = [forecast_snapshot(0.52), events_snapshot("drought", "flood")]
    first, second = evaluate(snapshots, "drought", AREA), evaluate(snapshots, "drought", AREA)
    for key in ("stage", "gates", "stage_trace", "eligible_action_cards", "ineligible", "cost_loss"):
        assert first[key] == second[key]


# --------------------------------------------------------------------------
# Synthetic fixtures must never masquerade as official evidence.
# --------------------------------------------------------------------------


def synthetic_pipeline(probability: float, area: str = AREA) -> dict[str, Any]:
    return {
        "adapter": "pipeline", "schema_ok": True, "retrieved_at": "2999-01-01T00:00:00Z",
        "freshness": "replay", "meta": {"synthetic": True},
        "payload": {"files": [{
            "id": "p1", "name": "csv", "area_id": area, "hazard": "drought", "indicator": INDICATOR,
            "probability": probability, "quantile": 0.33, "lead_months": 3, "source_file": "03_prob_csv_q.py",
        }]},
    }


def test_recorded_evidence_outranks_a_higher_synthetic_reading() -> None:
    snapshots = [{**forecast_snapshot(0.004), "meta": {}, "freshness": "live"}, synthetic_pipeline(0.52)]
    signal = observed_signal(snapshots, AREA)
    assert signal["probability"] == pytest.approx(0.004)
    assert signal["synthetic"] is False


def test_a_synthetic_observation_is_labelled_everywhere_it_appears() -> None:
    assessment = evaluate([synthetic_pipeline(0.52)], "drought", AREA)
    assert assessment["synthetic_observation"] is True
    assert assessment["observed_signal"]["synthetic"] is True
    assert assessment["observed_signal"]["source"].startswith("SYNTHETIC")
    probability_source = next(item for item in assessment["cost_loss"]["sources"] if item["field"] == "probability")
    assert probability_source["source"] == "policy_assumption"


def test_live_evidence_is_labelled_official() -> None:
    assessment = evaluate([{**forecast_snapshot(0.52), "meta": {}, "freshness": "live"}], "drought", AREA)
    assert assessment["synthetic_observation"] is False
    probability_source = next(item for item in assessment["cost_loss"]["sources"] if item["field"] == "probability")
    assert probability_source["source"] == "official_source"
