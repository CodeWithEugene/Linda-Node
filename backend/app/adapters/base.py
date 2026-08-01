from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class SnapshotCapture:
    adapter: str
    endpoint_url: str
    retrieved_at: datetime
    payload: dict[str, Any]
    freshness: str
    meta: dict[str, Any]


class SourceAdapter(ABC):
    @abstractmethod
    def fetch(self) -> list[SnapshotCapture]:
        """Fetch, validate, and return immutable raw captures."""
