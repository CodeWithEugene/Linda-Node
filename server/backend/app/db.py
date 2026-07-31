"""SQLite persistence for the Person 2 workflow.

The tables map directly to the action, approval, audit, export, and partner API
surfaces. Events are intentionally only written through append_event().
"""

from __future__ import annotations

import hashlib
import json
import secrets
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

try:
    from argon2 import PasswordHasher
except ImportError:  # pragma: no cover - only helps a bare source checkout
    PasswordHasher = None  # type: ignore[misc,assignment]

from .config import settings
from .domain import canonical_json, loads, new_id, now, sha256
from .library import action_cards, policy

SCHEMA = """
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS users (
  id TEXT PRIMARY KEY,
  email TEXT UNIQUE NOT NULL,
  display_name TEXT NOT NULL,
  role TEXT NOT NULL,
  org TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  signing_key TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS source_snapshots (
  id TEXT PRIMARY KEY,
  adapter TEXT NOT NULL,
  endpoint_url TEXT NOT NULL,
  retrieved_at TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  payload_sha256 TEXT NOT NULL,
  schema_ok INTEGER NOT NULL,
  freshness TEXT NOT NULL,
  logical_key TEXT NOT NULL,
  meta_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS source_snapshots_lookup ON source_snapshots(logical_key, retrieved_at DESC);
CREATE TABLE IF NOT EXISTS app_settings (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS decision_cases (
  id TEXT PRIMARY KEY,
  area_id TEXT NOT NULL,
  area_name TEXT NOT NULL,
  hazard TEXT NOT NULL,
  title TEXT NOT NULL,
  state TEXT NOT NULL,
  policy_version_id TEXT NOT NULL,
  assessment_json TEXT NOT NULL DEFAULT '{}',
  evidence_json TEXT NOT NULL DEFAULT '[]',
  action_card_ids_json TEXT NOT NULL DEFAULT '[]',
  stage TEXT,
  version INTEGER NOT NULL DEFAULT 1,
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS readiness_tasks (
  id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES decision_cases(id),
  action_card_id TEXT NOT NULL,
  title TEXT NOT NULL,
  owner_role TEXT NOT NULL,
  owner_user_id TEXT,
  criticality TEXT NOT NULL,
  state TEXT NOT NULL,
  blocker_code TEXT,
  blocker_note TEXT,
  updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS approvals (
  id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES decision_cases(id),
  role TEXT NOT NULL,
  user_id TEXT NOT NULL,
  decision TEXT NOT NULL,
  comment TEXT,
  signed_digest TEXT NOT NULL,
  signature TEXT NOT NULL,
  signed_at TEXT NOT NULL,
  superseded INTEGER NOT NULL DEFAULT 0,
  UNIQUE(case_id, role, superseded)
);
CREATE TABLE IF NOT EXISTS case_events (
  seq INTEGER PRIMARY KEY AUTOINCREMENT,
  id TEXT UNIQUE NOT NULL,
  case_id TEXT NOT NULL REFERENCES decision_cases(id),
  actor_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  data TEXT NOT NULL,
  prev_hash TEXT NOT NULL,
  this_hash TEXT NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS exports (
  id TEXT PRIMARY KEY,
  case_id TEXT NOT NULL REFERENCES decision_cases(id),
  kind TEXT NOT NULL,
  file_path TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  generated_by TEXT NOT NULL,
  generated_at TEXT NOT NULL,
  meta_json TEXT NOT NULL DEFAULT '{}'
);
CREATE TABLE IF NOT EXISTS integration_keys (
  id TEXT PRIMARY KEY,
  label TEXT NOT NULL,
  key_hash TEXT NOT NULL,
  created_at TEXT NOT NULL,
  revoked_at TEXT
);
CREATE TABLE IF NOT EXISTS webhook_subscriptions (
  id TEXT PRIMARY KEY,
  url TEXT NOT NULL,
  events_json TEXT NOT NULL,
  secret TEXT NOT NULL,
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS webhook_deliveries (
  id TEXT PRIMARY KEY,
  subscription_id TEXT NOT NULL REFERENCES webhook_subscriptions(id),
  case_id TEXT NOT NULL,
  event TEXT NOT NULL,
  attempt INTEGER NOT NULL,
  status_code INTEGER,
  delivered INTEGER NOT NULL DEFAULT 0,
  attempted_at TEXT NOT NULL
);
"""


class RecordedVersionConflict(Exception):
    """A stale edit that has already been committed to the audit chain.

    Mutations use ``BEGIN IMMEDIATE`` so the stale check and the resulting
    audit event are serialised with every other writer.  The transaction
    context deliberately commits this exception; all other exceptions roll
    back as usual.
    """

    def __init__(self, current_version: int, supplied_version: int):
        self.current_version = current_version
        self.supplied_version = supplied_version
        super().__init__("This case changed. Reload before trying again.")


def connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.database_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    conn = connection()
    try:
        # Serialize writers before they read a version or event-chain head.
        # This prevents two requests from both validating the same case
        # version and producing competing hash-chain links.
        conn.execute("BEGIN IMMEDIATE")
        yield conn
        conn.commit()
    except RecordedVersionConflict:
        conn.commit()
        raise
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _password_hash(password: str) -> str:
    if PasswordHasher:
        return PasswordHasher().hash(password)
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
    return f"pbkdf2${salt}${digest}"


def hash_secret(value: str) -> str:
    """Argon2 for credentials and one-time partner API keys when available."""
    return _password_hash(value)


def verify_password(encoded: str, password: str) -> bool:
    if encoded.startswith("$argon2") and PasswordHasher:
        try:
            return PasswordHasher().verify(encoded, password)
        except Exception:
            return False
    if encoded.startswith("pbkdf2$"):
        _, salt, digest = encoded.split("$", 2)
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
        return secrets.compare_digest(actual, digest)
    return False


def verify_secret(encoded: str, value: str) -> bool:
    return verify_password(encoded, value)


def append_event(conn: sqlite3.Connection, case_id: str, actor_id: str, event_type: str, data: dict[str, Any]) -> dict[str, Any]:
    previous = conn.execute(
        "SELECT this_hash FROM case_events WHERE case_id = ? ORDER BY seq DESC LIMIT 1", (case_id,)
    ).fetchone()
    prev_hash = previous["this_hash"] if previous else ""
    created_at = now()
    payload = canonical_json(data)
    this_hash = sha256(prev_hash + payload + event_type + actor_id)
    event = {
        "id": new_id("evt"), "case_id": case_id, "actor_id": actor_id,
        "event_type": event_type, "data": payload, "prev_hash": prev_hash,
        "this_hash": this_hash, "created_at": created_at,
    }
    conn.execute(
        """INSERT INTO case_events (id,case_id,actor_id,event_type,data,prev_hash,this_hash,created_at)
           VALUES (:id,:case_id,:actor_id,:event_type,:data,:prev_hash,:this_hash,:created_at)""",
        event,
    )
    return event


def init_db() -> None:
    with transaction() as conn:
        conn.executescript(SCHEMA)
        if conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            seed_demo(conn)
        if not conn.execute("SELECT 1 FROM app_settings WHERE key = 'source_mode'").fetchone():
            conn.execute("INSERT INTO app_settings (key,value) VALUES ('source_mode','live_first')")


def seed_demo(conn: sqlite3.Connection) -> None:
    """Idempotent demo reset data. Personas are fictional and password is documented."""
    users = [
        ("usr_amina", "amina.ews@demo", "Amina Hassan", "ews_specialist", "ICPAC"),
        ("usr_david", "david.drm@demo", "David Wekesa", "county_drm_officer", "Bungoma County DRM"),
        ("usr_grace", "grace.ngo@demo", "Grace Njeri", "ngo_finance_lead", "Kenya Red Cross"),
        ("usr_observer", "observer@demo", "Observer", "observer", "Demo observer"),
        ("usr_admin", "admin@demo", "Demo Administrator", "admin", "Linda Protocol"),
    ]
    for user_id, email, display_name, role, org in users:
        conn.execute(
            """INSERT OR REPLACE INTO users (id,email,display_name,role,org,password_hash,signing_key,created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (user_id, email, display_name, role, org, _password_hash("linda-demo"), secrets.token_hex(32), now()),
        )
    existing = conn.execute("SELECT COUNT(*) FROM decision_cases").fetchone()[0]
    if existing:
        return
    policy_id = policy()["id"]
    cards = action_cards()
    case_id = "case_bungoma_ond2026"
    created_at = now()
    fixture_root = Path(__file__).resolve().parents[1] / "fixtures" / "replay"
    seeded_snapshots: dict[str, dict[str, Any]] = {}
    for adapter, fixture_name in (("triggers", "triggers.json"), ("forecasts", "forecasts.json"), ("areas", "areas.json")):
        payload = json.loads((fixture_root / fixture_name).read_text(encoding="utf-8"))
        raw = canonical_json(payload)
        snapshot_id = f"snap_seed_{adapter}"
        seeded_snapshots[adapter] = {"id": snapshot_id, "payload": payload, "sha": sha256(raw)}
        conn.execute(
            """INSERT INTO source_snapshots (id,adapter,endpoint_url,retrieved_at,payload_json,payload_sha256,schema_ok,freshness,logical_key,meta_json)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (snapshot_id, adapter, f"fixtures/replay/{fixture_name}", created_at, raw, sha256(raw), 1, "replay", adapter, canonical_json({"mode": "replay_only", "synthetic": adapter != "areas"})),
        )
    assessment = {
        "policy_version_id": policy_id, "stage": "set", "ndma_phase": "Alarm",
        "gates": [{"id": "source_freshness", "passed": True, "detail": "Replay snapshot recorded 2026-07-22"},
                  {"id": "schema_valid", "passed": True, "detail": "All 4 snapshots passed validation"},
                  {"id": "lead_time", "passed": True, "detail": "Eligible cards have time before onset"}],
        "stage_trace": [{"stage": "ready", "condition": "P ≥ 0.35", "observed": 0.52, "passed": True},
                        {"stage": "set", "condition": "P ≥ 0.50", "observed": 0.52, "passed": True},
                        {"stage": "go", "condition": "P ≥ 0.60", "observed": 0.52, "passed": False}],
        "cost_loss": {"exposed_households": 12000, "loss_per_household_usd": 180, "expected_avoidable_loss_usd": 756000, "margin_usd": 5000},
        "eligible_action_cards": ["card_destocking_v1", "card_water_trucking_v1", "card_fodder_v1"],
        "ineligible": [{"card": "card_seed_distribution_v1", "reason": "lead-time gate failed (needs 75d; have 41d)"}],
        "compound_signals": ["drought", "flood"],
    }
    evidence = [
        {"id": seeded_snapshots["forecasts"]["id"], "kind": "forecast", "label": "OND 2026 return-period forecast", "adapter": "forecasts", "endpoint_url": "fixtures/replay/forecasts.json", "retrieved_at": created_at, "payload_sha256": seeded_snapshots["forecasts"]["sha"], "freshness": "replay", "schema_ok": True},
        {"id": seeded_snapshots["triggers"]["id"], "kind": "trigger_rule", "label": "Bungoma Triggers", "adapter": "triggers", "endpoint_url": "fixtures/replay/triggers.json", "retrieved_at": created_at, "payload_sha256": seeded_snapshots["triggers"]["sha"], "freshness": "replay", "schema_ok": True},
    ]
    conn.execute(
        """INSERT INTO decision_cases (id,area_id,area_name,hazard,title,state,policy_version_id,assessment_json,evidence_json,action_card_ids_json,stage,version,created_by,created_at,updated_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (case_id, "KEN.3_1", "Bungoma", "drought", "OND 2026 drought — Bungoma", "ASSESSED", policy_id,
         canonical_json(assessment), canonical_json(evidence), canonical_json([card["id"] for card in cards if card["hazard"] == "drought"]),
         "set", 1, "usr_david", created_at, created_at),
    )
    tasks = [
        ("task_transport", "card_destocking_v1", "Transport contracts confirmed", "ngo_finance_lead", "critical", "BLOCKED", "LOGISTICS_TRANSPORT", "Two suppliers have not confirmed access to the market route."),
        ("task_market", "card_destocking_v1", "Market days scheduled with county", "county_drm_officer", "normal", "ACKNOWLEDGED", None, None),
        ("task_water", "card_water_trucking_v1", "Water point access permissions confirmed", "county_drm_officer", "critical", "ACKNOWLEDGED", None, None),
        ("task_fodder", "card_fodder_v1", "Fodder suppliers pre-qualified", "ngo_finance_lead", "normal", "PENDING", None, None),
    ]
    for task_id, card_id, title, role, criticality, state, code, note in tasks:
        conn.execute(
            """INSERT INTO readiness_tasks (id,case_id,action_card_id,title,owner_role,owner_user_id,criticality,state,blocker_code,blocker_note,updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (task_id, case_id, card_id, title, role, None, criticality, state, code, note, created_at),
        )
    append_event(conn, case_id, "usr_david", "CASE_CREATED", {"title": "OND 2026 drought — Bungoma", "mode": "exercise"})
    append_event(conn, case_id, "system", "ASSESSED", {"stage": "set", "gates_passed": True, "compound_signals": ["drought", "flood"]})
    append_event(conn, case_id, "usr_grace", "TASK_UPDATED", {"task_id": "task_transport", "state": "BLOCKED", "blocker_code": "LOGISTICS_TRANSPORT"})


def reset_demo() -> None:
    with transaction() as conn:
        for table in ("webhook_deliveries", "webhook_subscriptions", "integration_keys", "exports", "approvals", "readiness_tasks", "case_events", "decision_cases", "source_snapshots", "users"):
            conn.execute(f"DELETE FROM {table}")
        seed_demo(conn)


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def parse_case(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["assessment"] = loads(item.pop("assessment_json"), {})
    item["evidence"] = loads(item.pop("evidence_json"), [])
    item["action_card_ids"] = loads(item.pop("action_card_ids_json"), [])
    return item
