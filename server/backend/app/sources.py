"""Source snapshots with live-first retrieval and explicit replay fallback.

The public ICPAC endpoints are deliberately treated as an upstream dependency,
not an assumed SLA.  Each response is retained verbatim, hashed, and exposed
with its freshness so the UI can never present replay data as live evidence.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from .config import settings
from .domain import canonical_json, loads, new_id, now, sha256

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "replay"
SOURCE_DEFINITIONS = {
    "triggers": ("/api/triggers/rules/", "triggers.json"),
    "forecasts": ("/api/datasets/forecasts/available/?forecast_type=return_period", "forecasts.json"),
    "areas": ("/api/areas/areas/?level=1&code=KEN", "areas.json"),
}


def source_mode(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT value FROM app_settings WHERE key = 'source_mode'").fetchone()
    return row["value"] if row else "live_first"


def set_source_mode(conn: sqlite3.Connection, mode: str) -> str:
    if mode not in {"live_first", "replay_only"}:
        raise ValueError("Source mode must be live_first or replay_only")
    conn.execute("INSERT INTO app_settings (key,value) VALUES ('source_mode',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (mode,))
    return mode


def _fixture(adapter: str) -> tuple[dict[str, Any], str]:
    _, name = SOURCE_DEFINITIONS[adapter]
    path = FIXTURE_ROOT / name
    return json.loads(path.read_text(encoding="utf-8")), str(path.relative_to(Path(__file__).resolve().parents[1]))


def _recent(conn: sqlite3.Connection, adapter: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM source_snapshots WHERE logical_key = ? ORDER BY retrieved_at DESC LIMIT 1", (adapter,)).fetchone()
    if not row:
        return None
    item = dict(row)
    item["payload"] = loads(item.pop("payload_json"), {})
    item["meta"] = loads(item.pop("meta_json"), {})
    return item


def _fresh(snapshot: dict[str, Any]) -> bool:
    try:
        retrieved = datetime.fromisoformat(snapshot["retrieved_at"].replace("Z", "+00:00"))
        return datetime.now(UTC) - retrieved < timedelta(minutes=settings.snapshot_ttl_min)
    except (KeyError, ValueError):
        return False


def _store(conn: sqlite3.Connection, adapter: str, endpoint: str, payload: dict[str, Any], freshness: str, schema_ok: bool, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    raw = canonical_json(payload)
    item = {
        "id": new_id("snap"), "adapter": adapter, "endpoint_url": endpoint,
        "retrieved_at": now(), "payload_json": raw, "payload_sha256": sha256(raw),
        "schema_ok": int(schema_ok), "freshness": freshness, "logical_key": adapter,
        "meta_json": canonical_json(meta or {}),
    }
    conn.execute("""INSERT INTO source_snapshots
        (id,adapter,endpoint_url,retrieved_at,payload_json,payload_sha256,schema_ok,freshness,logical_key,meta_json)
        VALUES (:id,:adapter,:endpoint_url,:retrieved_at,:payload_json,:payload_sha256,:schema_ok,:freshness,:logical_key,:meta_json)""", item)
    return {**item, "payload": payload, "meta": meta or {}}


def _normalise(adapter: str, raw: Any) -> dict[str, Any]:
    """Keep original data but expose the small stable shape the workflow needs."""
    if adapter == "triggers":
        if isinstance(raw, list):
            rules = raw
        elif isinstance(raw, dict):
            rules = raw.get("results", raw.get("rules", []))
        else:
            rules = []
        return {"rules": rules, "events": []}
    if adapter == "forecasts":
        if isinstance(raw, list):
            forecasts = raw
        elif isinstance(raw, dict):
            forecasts = raw.get("results", raw.get("forecasts", []))
        else:
            forecasts = []
        return {"forecasts": forecasts}
    if isinstance(raw, dict) and "features" in raw:
        areas = [{"id": feature.get("properties", {}).get("id", feature.get("id")), "name": feature.get("properties", {}).get("name", feature.get("id")), "country": "KEN", "level": 1, "geometry": feature.get("geometry")} for feature in raw["features"]]
        return {"areas": areas}
    return raw if isinstance(raw, dict) else {"areas": []}


def refresh_adapter(conn: sqlite3.Connection, adapter: str, force: bool = False) -> dict[str, Any]:
    if adapter not in SOURCE_DEFINITIONS:
        raise ValueError(f"Unknown source adapter: {adapter}")
    cached = _recent(conn, adapter)
    if cached and _fresh(cached) and not force:
        cached["freshness"] = "cached"
        return cached
    mode = source_mode(conn)
    endpoint_path, _ = SOURCE_DEFINITIONS[adapter]
    if mode != "replay_only":
        try:
            if adapter == "triggers":
                rules_response = httpx.get(f"{settings.icpac_base}{endpoint_path}", timeout=settings.http_timeout_s)
                events_response = httpx.get(f"{settings.icpac_base}/api/triggers/events/", timeout=settings.http_timeout_s)
                rules_response.raise_for_status(); events_response.raise_for_status()
                payload = _normalise(adapter, rules_response.json())
                raw_events = events_response.json()
                payload["events"] = raw_events.get("results", raw_events) if isinstance(raw_events, dict) else raw_events
            else:
                response = httpx.get(f"{settings.icpac_base}{endpoint_path}", timeout=settings.http_timeout_s)
                response.raise_for_status()
                payload = _normalise(adapter, response.json())
            return _store(conn, adapter, f"{settings.icpac_base}{endpoint_path}", payload, "live", True, {"mode": mode})
        except (httpx.HTTPError, ValueError, json.JSONDecodeError) as exc:
            if cached:
                cached["freshness"] = "stale"
                cached["meta"] = {**cached["meta"], "last_error": str(exc)}
                return cached
            if not settings.demo_mode:
                raise RuntimeError(f"{adapter} is unavailable and no cached snapshot exists") from exc
    payload, fixture_path = _fixture(adapter)
    return _store(conn, adapter, fixture_path, payload, "replay", True, {"mode": mode, "synthetic": adapter != "areas"})


def refresh_all(conn: sqlite3.Connection, force: bool = False) -> list[dict[str, Any]]:
    return [refresh_adapter(conn, adapter, force) for adapter in SOURCE_DEFINITIONS]


def list_snapshots(conn: sqlite3.Connection, adapter: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    query = "SELECT * FROM source_snapshots"; params: list[Any] = []
    if adapter:
        query += " WHERE adapter = ?"; params.append(adapter)
    query += " ORDER BY retrieved_at DESC LIMIT ?"; params.append(limit)
    items = []
    for row in conn.execute(query, params):
        item = dict(row); item["payload"] = loads(item.pop("payload_json"), {}); item["meta"] = loads(item.pop("meta_json"), {})
        items.append(item)
    return items


def get_snapshot(conn: sqlite3.Connection, snapshot_id: str) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM source_snapshots WHERE id = ?", (snapshot_id,)).fetchone()
    if not row:
        raise KeyError(snapshot_id)
    item = dict(row); item["payload"] = loads(item.pop("payload_json"), {}); item["meta"] = loads(item.pop("meta_json"), {})
    return item


def signals(conn: sqlite3.Connection) -> dict[str, Any]:
    latest = {adapter: refresh_adapter(conn, adapter) for adapter in SOURCE_DEFINITIONS}
    trigger = latest["triggers"]
    return {
        "mode": source_mode(conn),
        "rules": [{**item, "snapshot_id": trigger["id"], "freshness": trigger["freshness"]} for item in trigger["payload"].get("rules", [])],
        "events": [{**item, "snapshot_id": trigger["id"], "freshness": trigger["freshness"]} for item in trigger["payload"].get("events", [])],
        "forecasts": [{**item, "snapshot_id": latest["forecasts"]["id"], "freshness": latest["forecasts"]["freshness"]} for item in latest["forecasts"]["payload"].get("forecasts", [])],
    }


def areas(conn: sqlite3.Connection, country: str | None = None, level: int | None = None) -> list[dict[str, Any]]:
    snapshot = refresh_adapter(conn, "areas")
    records = snapshot["payload"].get("areas", [])
    return [item for item in records if (not country or item.get("country") == country) and (level is None or item.get("level") == level)]
