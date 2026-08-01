from pathlib import Path

from backend.app.policy import evaluate, load_library


def test_policy_evaluation_is_deterministic_for_replay_evidence():
    policy, actions = load_library(Path("backend/content"))
    snapshots = [{"adapter": "icpac_datasets", "payload": {"probability": 0.63}}]
    tasks = [{"id": "transport", "critical": True, "state": "RESOLVED"}]
    assessment = evaluate(policy, actions, snapshots, "KEN.3_1", "drought", tasks)
    assert assessment["stage"] == "go"
    assert all(gate["passed"] for gate in assessment["gates"])
    assert {item["id"] for item in assessment["eligible_cards"]} == {"water-trucking", "cash-readiness"}
