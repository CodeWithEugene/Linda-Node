from pathlib import Path
from typing import Any

import yaml

from ..domain import digest


def load_library(content_dir: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    policy_text = (content_dir / "policy.yaml").read_text(encoding="utf-8")
    policy = yaml.safe_load(policy_text)
    policy["sha256"] = digest(policy_text)
    actions = []
    for path in sorted((content_dir / "actions").glob("*.yaml")):
        raw = path.read_text(encoding="utf-8")
        action = yaml.safe_load(raw)
        action["sha256"] = digest(raw)
        actions.append(action)
    return policy, actions
