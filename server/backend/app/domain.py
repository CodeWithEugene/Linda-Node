from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from typing import Any

ROLES = {
    "ews_specialist",
    "county_drm_officer",
    "ngo_finance_lead",
    "observer",
    "admin",
}
SIGNER_ROLES = ("ews_specialist", "county_drm_officer", "ngo_finance_lead")
BLOCKER_CODES = {
    "LOGISTICS_TRANSPORT",
    "LOGISTICS_STORAGE",
    "FINANCE_UNAVAILABLE",
    "FINANCE_DELAYED",
    "AUTHORITY_APPROVAL_MISSING",
    "DATA_MISSING",
    "SECURITY_ACCESS",
    "STAFFING",
    "MARKET_CONDITIONS",
    "OTHER",
}
TERMINAL_STATES = {"REJECTED", "REVOKED"}


def now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_id(prefix: str) -> str:
    """ULID-style: a millisecond timestamp prefix keeps ids lexicographically
    sortable, so rows written inside the same whole second still have a
    deterministic order (timestamps are stored at second resolution)."""
    milliseconds = int(datetime.now(UTC).timestamp() * 1000)
    return f"{prefix}_{milliseconds:012x}{uuid.uuid4().hex[:14]}"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256(value: str | bytes) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def loads(value: str | None, fallback: Any) -> Any:
    return json.loads(value) if value else fallback
