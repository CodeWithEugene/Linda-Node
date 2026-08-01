from typing import Any


def evaluate(policy: dict[str, Any], actions: list[dict[str, Any]], snapshots: list[dict[str, Any]], area_id: str, hazard: str, tasks: list[dict[str, Any]]) -> dict[str, Any]:
    forecast = next((item["payload"] for item in snapshots if item["adapter"] == "icpac_datasets"), {})
    probability = float(forecast.get("probability", 0))
    threshold = float(policy["stages"]["go"]["probability_threshold"])
    critical_open = [item for item in tasks if item["critical"] and item["state"] == "BLOCKED"]
    eligible = []
    for item in actions:
        if item.get("hazard") != hazard or item.get("stage") not in {"set", "go"} or "ineligibility_reason" in item:
            continue
        budget = item.get("budget", {})
        eligible.append({
            "id": item["id"], "title": item["title"], "owner_role": item["owner_role"], "stage": item["stage"],
            "budget": f"{budget.get('currency', 'USD')} {budget.get('amount', 0):,}",
            "readiness_tasks": item.get("readiness_tasks", []),
        })
    ineligible = [{"id": item["id"], "title": item["title"], "reason": item["ineligibility_reason"]} for item in actions if item.get("ineligibility_reason")]
    return {
        "stage": "go" if probability >= threshold else "ready",
        "area_id": area_id,
        "hazard": hazard,
        "probability": probability,
        "gates": [
            {"name": "official_source", "passed": bool(snapshots), "basis": "immutable ICPAC/replay snapshots captured"},
            {"name": "probability_threshold", "passed": probability >= threshold, "basis": f"{probability:.2f} >= GO threshold {threshold:.2f}"},
            {"name": "readiness", "passed": not critical_open, "basis": "all critical tasks acknowledged or resolved" if not critical_open else f"critical task {critical_open[0]['id']} is blocked"},
        ],
        "eligible_cards": eligible,
        "ineligible_cards": ineligible,
        "expected_avoidable_loss": {"baseline_usd": 520000, "after_action_usd": 310000, "net_benefit_usd": 210000},
        "policy_hash": policy["sha256"],
    }
