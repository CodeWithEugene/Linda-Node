"""Persistence for the activation-readiness workflow (SQLite locally, Postgres on Vercel).

The tables map directly to the evidence, action, approval, audit, export, and
partner API surfaces. Case events are only ever written through append_event(),
which is what keeps the audit trail append-only and hash-chained.
"""

from __future__ import annotations

import hashlib
import re
import secrets
import sqlite3
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from typing import Any

try:
    from argon2 import PasswordHasher
except ImportError:  # pragma: no cover - only helps a bare source checkout
    PasswordHasher = None  # type: ignore[misc,assignment]

from .config import settings
from .domain import canonical_json, loads, new_id, now, sha256
from .library import validate_library

try:  # PostgreSQL is only required for Vercel production deployments.
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - local SQLite users can install only the base runtime
    psycopg = None  # type: ignore[assignment]
    dict_row = None  # type: ignore[assignment]

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
  payload_raw TEXT,
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

POSTGRES_SCHEMA = """
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
  payload_raw TEXT,
  payload_sha256 TEXT NOT NULL,
  schema_ok SMALLINT NOT NULL,
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
  superseded SMALLINT NOT NULL DEFAULT 0
);
CREATE UNIQUE INDEX IF NOT EXISTS approvals_live_role ON approvals(case_id, role) WHERE superseded = 0;
CREATE TABLE IF NOT EXISTS case_events (
  seq BIGSERIAL PRIMARY KEY,
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
  active SMALLINT NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS webhook_deliveries (
  id TEXT PRIMARY KEY,
  subscription_id TEXT NOT NULL REFERENCES webhook_subscriptions(id),
  case_id TEXT NOT NULL,
  event TEXT NOT NULL,
  attempt INTEGER NOT NULL,
  status_code INTEGER,
  delivered SMALLINT NOT NULL DEFAULT 0,
  attempted_at TEXT NOT NULL
);
"""


def _postgres_sql(statement: str, params: object) -> str:
    """Translate the deliberately small SQLite query dialect used by the app."""
    if isinstance(params, Mapping):
        return re.sub(r"(?<!:):([A-Za-z_]\w*)", r"%(\1)s", statement)
    return statement.replace("?", "%s")


class PostgresConnection:
    def __init__(self, raw: Any):
        self.raw = raw

    def execute(self, statement: str, params: object = ()) -> Any:
        return self.raw.execute(_postgres_sql(statement, params), params)

    def executescript(self, script: str) -> None:
        for statement in script.split(";"):
            if statement.strip():
                self.raw.execute(statement)

    def commit(self) -> None:
        self.raw.commit()

    def rollback(self) -> None:
        self.raw.rollback()

    def close(self) -> None:
        self.raw.close()

    def __enter__(self) -> "PostgresConnection":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


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


def connection() -> Any:
    if settings.database_engine == "postgres":
        if psycopg is None or dict_row is None:
            raise RuntimeError("PostgreSQL support requires psycopg. Install the production dependencies.")
        return PostgresConnection(psycopg.connect(settings.database_url, row_factory=dict_row))
    if settings.database_path is None:  # defensive: keeps local configuration errors clear
        raise RuntimeError("SQLite requires a sqlite:/// DATABASE_URL")
    conn = sqlite3.connect(settings.database_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def transaction() -> Iterator[Any]:
    conn = connection()
    try:
        # Serialize writers before they read a version or event-chain head.
        # This prevents two requests from both validating the same case
        # version and producing competing hash-chain links.
        conn.execute("BEGIN" if settings.database_engine == "postgres" else "BEGIN IMMEDIATE")
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


def _migrate(conn: Any) -> None:
    """Additive column migrations for databases created by an earlier build."""
    for statement in ("ALTER TABLE source_snapshots ADD COLUMN payload_raw TEXT",):
        try:
            conn.execute(statement)
        except Exception:  # noqa: BLE001 - column already present on a current schema
            conn.rollback() if settings.database_engine == "postgres" else None


def init_db() -> None:
    # A malformed policy or action card must stop the process here rather than
    # produce assessments against a rulebook nobody reviewed (build.md 6.4).
    validate_library()
    with transaction() as conn:
        conn.executescript(POSTGRES_SCHEMA if settings.database_engine == "postgres" else SCHEMA)
        _migrate(conn)
        if conn.execute("SELECT COUNT(*) AS count FROM users").fetchone()["count"] == 0:
            seed_demo(conn)
        for key, value in (("source_mode", "live_first"), ("replay_step", "0")):
            if not conn.execute("SELECT 1 FROM app_settings WHERE key = ?", (key,)).fetchone():
                conn.execute("INSERT INTO app_settings (key,value) VALUES (?,?)", (key, value))


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
            """INSERT INTO users (id,email,display_name,role,org,password_hash,signing_key,created_at)
               VALUES (?,?,?,?,?,?,?,?)
               ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email, display_name = EXCLUDED.display_name,
               role = EXCLUDED.role, org = EXCLUDED.org, password_hash = EXCLUDED.password_hash,
               signing_key = EXCLUDED.signing_key, created_at = EXCLUDED.created_at""",
            (user_id, email, display_name, role, org, _password_hash("linda-demo"), secrets.token_hex(32), now()),
        )
    if conn.execute("SELECT COUNT(*) AS count FROM decision_cases").fetchone()["count"]:
        return
    from .demo_seed import seed_cases

    seed_cases(conn)


def reset_demo() -> None:
    with transaction() as conn:
        # Tests and the admin reset endpoint may be the first code to touch a
        # new database. Create the schema before clearing rows so a clean CI
        # checkout does not depend on an earlier application startup.
        conn.executescript(POSTGRES_SCHEMA if settings.database_engine == "postgres" else SCHEMA)
        for table in ("webhook_deliveries", "webhook_subscriptions", "integration_keys", "exports", "approvals", "readiness_tasks", "case_events", "decision_cases", "source_snapshots", "users"):
            conn.execute(f"DELETE FROM {table}")
        if not conn.execute("SELECT 1 FROM app_settings WHERE key = 'source_mode'").fetchone():
            conn.execute("INSERT INTO app_settings (key,value) VALUES ('source_mode','live_first')")
        seed_demo(conn)


def row_to_dict(row: Mapping[str, Any] | sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def parse_case(row: Mapping[str, Any] | sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["assessment"] = loads(item.pop("assessment_json"), {})
    item["evidence"] = loads(item.pop("evidence_json"), [])
    item["action_card_ids"] = loads(item.pop("action_card_ids_json"), [])
    return item
