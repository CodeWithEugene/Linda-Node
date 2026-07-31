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
    return f"{prefix}_{uuid.uuid4().hex}"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256(value: str | bytes) -> str:
    if isinstance(value, str):
        value = value.encode("utf-8")
    return hashlib.sha256(value).hexdigest()


def loads(value: str | None, fallback: Any) -> Any:
    return json.loads(value) if value else fallback
