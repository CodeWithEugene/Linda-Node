import json
from datetime import datetime, timezone
from pathlib import Path

from .base import SnapshotCapture, SourceAdapter


class ReplayAdapter(SourceAdapter):
    """Fixture adapter with exactly the same output contract as live adapters."""

    def __init__(self, fixture_root: Path = Path("fixtures")):
        self.fixture_root = fixture_root

    def fetch(self) -> list[SnapshotCapture]:
        items = [
            ("icpac_triggers", self.fixture_root / "icpac" / "triggers.json"),
            ("icpac_datasets", self.fixture_root / "icpac" / "forecast.json"),
            ("replay", self.fixture_root / "replay_ond2026" / "rainfall-trigger.json"),
        ]
        captured_at = datetime(2026, 7, 22, 9, tzinfo=timezone.utc)
        captures = []
        for adapter, path in items:
            payload = json.loads(path.read_text(encoding="utf-8"))
            captures.append(SnapshotCapture(adapter, payload["source"], captured_at, payload, "replay", {"fixture": str(path)}))
        return captures
