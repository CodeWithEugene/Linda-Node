"""Source snapshots with live-first retrieval and explicit replay fallback.

The public ICPAC endpoints are deliberately treated as an upstream dependency,
not an assumed SLA.  Each response body is retained **verbatim** and hashed
before any parsing, so a reviewer can reproduce the recorded SHA-256 with
`curl <url> | shasum -a 256`.  A separate normalised view carries the small,
stable shape the workflow reads, and every snapshot records whether that view
passed its JSON Schema.  Personal email addresses present in upstream trigger
rules are masked on every read path (build.md 6.2).
"""

from __future__ import annotations

import csv
import io
import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx
from jsonschema import Draft202012Validator

from .config import CONTENT_ROOT, settings
from .domain import canonical_json, loads, new_id, now, sha256
from .redaction import redact

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "replay"
SCHEMA_ROOT = Path(CONTENT_ROOT) / "schemas" / "sources"
BACKEND_ROOT = Path(__file__).resolve().parents[1]

# Keep the raw payload of the most recent snapshots per source; older rows keep
# their hash and metadata but their bodies are pruned so the demo database stays
# small even though the Kenya boundary payload is several megabytes.
RAW_HISTORY_PER_SOURCE = 3
RAW_RESPONSE_PREVIEW_CHARS = 120_000

SOURCE_LABELS = {
    "triggers": "ICPAC Thresholds & Triggers — rules, events, actions, check logs",
    "forecasts": "ICPAC seasonal return-period forecast statistics for every GHA admin-1 unit",
    "areas": "ICPAC GADM admin-1 index for the 11 Greater Horn of Africa countries",
    "indicators": "ICPAC indicator registry (which indicators support forecasting)",
    "pipeline": "ibf-thresholds-triggers exceedance-probability CSV",
}
SOURCE_ORDER = ("triggers", "forecasts", "areas", "indicators", "pipeline")

# The 11 countries ICPAC publishes admin-1 statistics for.
GHA_COUNTRIES: tuple[tuple[str, str], ...] = (
    ("KEN", "Kenya"), ("ETH", "Ethiopia"), ("SOM", "Somalia"), ("SSD", "South Sudan"),
    ("SDN", "Sudan"), ("DJI", "Djibouti"), ("ERI", "Eritrea"), ("UGA", "Uganda"),
    ("TZA", "Tanzania"), ("RWA", "Rwanda"), ("BDI", "Burundi"),
)
COUNTRY_NAMES = dict(GHA_COUNTRIES)

# ICPAC's public pg_tileserv catalogue. Vector tiles are served from
# /tileserv/{layer}/{z}/{x}/{y}.pbf and carry the GADM id in `gid_1`, which is
# the same join key as the statistics endpoint.
TILE_LAYER = "boundary.gadm_41_admin_level_1_boundary"
TILE_JOIN_PROPERTY = "gid_1"


def _schema(name: str) -> Draft202012Validator:
    return Draft202012Validator(json.loads((SCHEMA_ROOT / f"{name}.schema.json").read_text(encoding="utf-8")))


def validate_source(adapter: str, payload: dict[str, Any]) -> list[str]:
    """Return schema errors instead of raising: a bad snapshot is evidence too."""
    validator = _schema(adapter)
    return [f"{error.json_path}: {error.message}" for error in list(validator.iter_errors(payload))[:5]]


def source_mode(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT value FROM app_settings WHERE key = 'source_mode'").fetchone()
    return row["value"] if row else "live_first"


def replay_step(conn: sqlite3.Connection) -> int:
    """0 = recorded ICPAC statistics; 1-3 = the labelled synthetic escalation."""
    row = conn.execute("SELECT value FROM app_settings WHERE key = 'replay_step'").fetchone()
    try:
        return max(0, min(3, int(row["value"]))) if row else 0
    except (TypeError, ValueError):
        return 0


def set_replay_step(conn: sqlite3.Connection, step: int) -> int:
    if step not in (0, 1, 2, 3):
        raise ValueError("Escalation step must be 0 (recorded statistics) or 1-3 (synthetic sequence)")
    conn.execute(
        "INSERT INTO app_settings (key,value) VALUES ('replay_step',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (str(step),),
    )
    return step


def forecast_issue(conn: sqlite3.Connection) -> str | None:
    row = conn.execute("SELECT value FROM app_settings WHERE key = 'forecast_issue'").fetchone()
    return row["value"] if row and row["value"] else None


def set_forecast_issue(conn: sqlite3.Connection, issue_id: str | None) -> str | None:
    conn.execute(
        "INSERT INTO app_settings (key,value) VALUES ('forecast_issue',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (issue_id or "",),
    )
    return issue_id


def set_source_mode(conn: sqlite3.Connection, mode: str) -> str:
    if mode not in {"live_first", "replay_only"}:
        raise ValueError("Source mode must be live_first or replay_only")
    conn.execute(
        "INSERT INTO app_settings (key,value) VALUES ('source_mode',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (mode,),
    )
    return mode


# --------------------------------------------------------------------------
# Normalisation: live ICPAC field names -> the stable shape Linda reads.
# Upstream uses area_gid/indicator_code/severity_level/hazard_type; the schemas
# in content/schemas/sources/ define what the workflow actually requires.
# --------------------------------------------------------------------------

HAZARD_BY_CATEGORY = {"drought": "drought", "heat": "heat", "flood": "flood", "rainfall": "flood"}


def _hazard_from(value: str | None) -> str:
    text = (value or "").lower()
    for key, hazard in HAZARD_BY_CATEGORY.items():
        if key in text:
            return hazard
    return "drought"


def _results(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [item for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict):
        for key in ("results", "rules", "events", "actions", "forecasts", "stats", "files"):
            value = raw.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
    return []


def normalise_triggers(rules_raw: Any, events_raw: Any, actions_raw: Any, checks_raw: Any) -> dict[str, Any]:
    rules = [
        {
            "id": str(item.get("id")),
            "name": item.get("name") or "Unnamed rule",
            "area_id": item.get("area_gid") or item.get("area_id") or "",
            "area_name": item.get("area_name"),
            "indicator": item.get("indicator_code") or item.get("indicator") or "unknown",
            "indicator_name": item.get("indicator_name"),
            "hazard": _hazard_from(item.get("hazard_type")),
            "severity": item.get("severity_level") or item.get("severity"),
            "threshold_value": item.get("threshold_value"),
            "threshold_operator": item.get("condition_operator"),
            "active": bool(item.get("is_active", item.get("active", True))),
            "notification_emails": item.get("notification_emails"),
        }
        for item in _results(rules_raw)
    ]
    events = []
    for item in _results(events_raw):
        rule = item.get("rule") if isinstance(item.get("rule"), dict) else {}
        events.append({
            "id": str(item.get("id")),
            "name": item.get("name") or rule.get("name") or "Detected trigger event",
            "area_id": item.get("area_gid") or rule.get("area_gid") or item.get("area_id") or "",
            "area_name": item.get("area_name") or rule.get("area_name"),
            "indicator": rule.get("indicator_code") or item.get("indicator") or "unknown",
            "hazard": _hazard_from(rule.get("hazard_type") or item.get("hazard")),
            "value": item.get("current_value", item.get("value")),
            "threshold_value": item.get("threshold_value"),
            "severity": item.get("severity_level") or item.get("severity"),
            "status": item.get("status", "active"),
            "detected_at": item.get("date_detected"),
        })
    actions = []
    for item in _results(actions_raw):
        event = item.get("trigger_event") if isinstance(item.get("trigger_event"), dict) else {}
        actions.append({
            "id": str(item.get("id")),
            "name": item.get("name") or "Trigger action",
            "action_type": item.get("action_type") or "unknown",
            "status": item.get("status") or ("completed" if item.get("date_completed") else "scheduled"),
            "area_id": event.get("area_gid") or item.get("area_gid"),
            "area_name": event.get("area_name") or item.get("area_name"),
            "scheduled_date": item.get("scheduled_date"),
        })
    checks = [
        {
            "id": str(item.get("id")),
            "check_type": item.get("check_type"),
            "check_date": item.get("check_date"),
            "total_rules_checked": item.get("total_rules_checked"),
            "triggers_detected": item.get("triggers_detected"),
            "actions_triggered": item.get("actions_triggered"),
            "status": item.get("status"),
        }
        for item in _results(checks_raw)[:20]
    ]
    return {"rules": rules, "events": events, "actions": actions, "check_logs": checks}


# ICPAC publishes return-period exceedance statistics as percentages per admin
# unit. rp3 is the 1-in-3-year tail, which the demo policy expresses as the
# 0.33 quantile. The mapping is recorded on every record via probability_source.
RETURN_PERIOD_QUANTILE = {"rp3": 0.33, "rp5": 0.20, "rp10": 0.10}


def normalise_forecasts(available_raw: Any, stats_raw: Any) -> dict[str, Any]:
    issues = [
        {
            "id": str(item.get("id")),
            "target_season": item.get("target_season"),
            "target_year": item.get("target_year"),
            "valid_date": item.get("valid_date"),
            "lead_months": int(item.get("lead_months") or 0),
            "indicator": item.get("indicator") or "spi3",
            "data_source": item.get("data_source"),
            "forecast_type": item.get("forecast_type"),
        }
        for item in _results(available_raw)
    ]
    issue = next((item for item in issues if item.get("target_season") == "OND"), issues[0] if issues else {})
    stats = stats_raw.get("stats", []) if isinstance(stats_raw, dict) else _results(stats_raw)
    indicator = f"{issue.get('indicator', 'spi3')}_{issue.get('data_source', 'chirps')}_forecast"
    forecasts = []
    for item in stats:
        if not isinstance(item, dict):
            continue
        admin_id = item.get("admin_id") or ""
        probability = round(float(item.get("avg_prob_rp3") or 0) / 100, 4)
        forecasts.append({
            "id": f"{issue.get('id', 'forecast')}-{admin_id}",
            "name": f"{issue.get('target_season', 'Season')} {issue.get('target_year', '')} return-period exceedance".strip(),
            "area_id": admin_id,
            "area_name": item.get("admin_name"),
            "country": admin_id.split(".")[0],
            "country_name": COUNTRY_NAMES.get(admin_id.split(".")[0], item.get("parent_name")),
            "hazard": "drought",
            "indicator": indicator,
            "probability": min(max(probability, 0.0), 1.0),
            "quantile": RETURN_PERIOD_QUANTILE["rp3"],
            "lead_months": int(issue.get("lead_months") or 0),
            "valid_date": issue.get("valid_date"),
            "severity": "moderate" if probability >= 0.35 else "low",
            "probability_source": "ICPAC /api/datasets/forecasts/stats/ avg_prob_rp3 (percent) ÷ 100",
            "return_periods": {
                key: round(float(item.get(f"avg_prob_{key}") or 0) / 100, 4)
                for key in ("rp3", "rp5", "rp10", "rp20", "rp50")
                if item.get(f"avg_prob_{key}") is not None
            },
            "pixels": item.get("total_pixels"),
        })
    forecasts.sort(key=lambda item: item["probability"], reverse=True)
    return {"forecasts": forecasts, "issues": issues, "issue": issue}


def normalise_indicators(raw: Any) -> dict[str, Any]:
    """ICPAC's own indicator registry: which indicators can actually be forecast."""
    return {"indicators": [
        {
            "code": item.get("full_code") or item.get("code"),
            "name": item.get("name"),
            "category": item.get("category_code"),
            "data_source": item.get("data_source_code"),
            "unit": item.get("unit"),
            "description": item.get("description"),
            "supports_forecast": bool(item.get("supports_forecast")),
            "supports_monitoring": bool(item.get("supports_monitoring")),
            "timescale_months": item.get("timescale_months"),
        }
        for item in _results(raw)
    ]}


def normalise_areas(raw: Any) -> dict[str, Any]:
    features = raw.get("features", []) if isinstance(raw, dict) else []
    areas = []
    for feature in features:
        properties = feature.get("properties", {}) if isinstance(feature, dict) else {}
        identifier = properties.get("id") or feature.get("id")
        if not identifier:
            continue
        try:
            level = int(properties.get("level", 1))
        except (TypeError, ValueError):
            level = 1
        country = str(identifier).split(".")[0]
        areas.append({
            "id": str(identifier),
            "name": properties.get("name") or str(identifier),
            "country": country,
            "country_name": COUNTRY_NAMES.get(country, country),
            "level": level,
            "geometry": feature.get("geometry"),
        })
    return {"areas": areas}


def merge_areas(payloads: list[dict[str, Any]]) -> dict[str, Any]:
    merged: dict[str, dict[str, Any]] = {}
    for payload in payloads:
        for area in payload.get("areas", []):
            merged[area["id"]] = area
    return {"areas": sorted(merged.values(), key=lambda item: item["id"])}


def parse_pipeline_csv(text: str, *, source_file: str) -> dict[str, Any]:
    """Parse the exceedance-probability CSV shape of `03_prob_csv_q.py`.

    Columns: admin_id, admin_name, season, quantile, probability, lead_months.
    This is file-level interoperability with ICPAC's scientific pipeline; Linda
    does not run that pipeline.
    """
    files = []
    for index, row in enumerate(csv.DictReader(io.StringIO(text))):
        if not row.get("admin_id"):
            continue
        try:
            probability = float(row.get("probability") or 0)
            quantile = float(row.get("quantile") or 0.33)
            lead_months = int(float(row.get("lead_months") or 0))
        except ValueError:
            continue
        files.append({
            "id": f"pipeline_{row['admin_id']}_{index}",
            "name": f"{row.get('season', 'Season')} {row.get('indicator', 'SPI-3')} exceedance probability",
            "area_id": row["admin_id"],
            "area_name": row.get("admin_name"),
            "hazard": "drought",
            "indicator": row.get("indicator") or "spi3_chirps_forecast",
            "probability": min(max(probability, 0.0), 1.0),
            "quantile": quantile,
            "lead_months": lead_months,
            "severity": "moderate" if probability >= 0.35 else "low",
            "format": "exceedance-probability CSV",
            "source_file": source_file,
        })
    return {"files": files}


# --------------------------------------------------------------------------
# Snapshot storage
# --------------------------------------------------------------------------


def _recent(conn: sqlite3.Connection, adapter: str) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT * FROM source_snapshots WHERE logical_key = ? ORDER BY retrieved_at DESC, id DESC LIMIT 1", (adapter,)
    ).fetchone()
    return _hydrate(row) if row else None


def _hydrate(row: Any) -> dict[str, Any]:
    item = dict(row)
    item["payload"] = redact(loads(item.pop("payload_json"), {}))
    item["meta"] = loads(item.pop("meta_json"), {})
    item["schema_ok"] = bool(item["schema_ok"])
    raw = item.pop("payload_raw", None)
    item["raw_available"] = bool(raw)
    item["_raw"] = raw
    return item


def _fresh(snapshot: dict[str, Any]) -> bool:
    try:
        retrieved = datetime.fromisoformat(snapshot["retrieved_at"].replace("Z", "+00:00"))
        return datetime.now(UTC) - retrieved < timedelta(minutes=settings.snapshot_ttl_min)
    except (KeyError, ValueError, AttributeError):
        return False


def _prune_raw(conn: sqlite3.Connection, adapter: str) -> None:
    keep = [
        row["id"]
        for row in conn.execute(
            "SELECT id FROM source_snapshots WHERE logical_key = ? ORDER BY retrieved_at DESC, id DESC LIMIT ?",
            (adapter, RAW_HISTORY_PER_SOURCE),
        )
    ]
    if not keep:
        return
    placeholders = ",".join("?" for _ in keep)
    conn.execute(
        f"UPDATE source_snapshots SET payload_raw = NULL WHERE logical_key = ? AND payload_raw IS NOT NULL AND id NOT IN ({placeholders})",
        (adapter, *keep),
    )


def _store_with_key(
    conn: sqlite3.Connection,
    adapter: str,
    logical_key: str,
    endpoint: str,
    payload: dict[str, Any],
    freshness: str,
    *,
    raw_parts: dict[str, str],
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _store(conn, adapter, endpoint, payload, freshness, raw_parts=raw_parts, meta=meta, logical_key=logical_key)


def _store(
    conn: sqlite3.Connection,
    adapter: str,
    endpoint: str,
    payload: dict[str, Any],
    freshness: str,
    *,
    raw_parts: dict[str, str],
    meta: dict[str, Any] | None = None,
    logical_key: str | None = None,
) -> dict[str, Any]:
    """Persist one snapshot. The recorded hash covers the verbatim upstream body."""
    raw_document = canonical_json(raw_parts)
    errors = validate_source(adapter, payload)
    item = {
        "id": new_id("snap"),
        "adapter": adapter,
        "endpoint_url": endpoint,
        "retrieved_at": now(),
        "payload_json": canonical_json(payload),
        "payload_raw": raw_document,
        "payload_sha256": sha256(raw_document),
        "schema_ok": 0 if errors else 1,
        "freshness": freshness,
        "logical_key": logical_key or adapter,
        "meta_json": canonical_json({
            **(meta or {}),
            "label": SOURCE_LABELS.get(adapter, adapter),
            "schema_errors": errors,
            "parts": [
                {"url": url, "sha256": sha256(body), "bytes": len(body.encode("utf-8"))}
                for url, body in sorted(raw_parts.items())
            ],
        }),
    }
    conn.execute(
        """INSERT INTO source_snapshots
        (id,adapter,endpoint_url,retrieved_at,payload_json,payload_raw,payload_sha256,schema_ok,freshness,logical_key,meta_json)
        VALUES (:id,:adapter,:endpoint_url,:retrieved_at,:payload_json,:payload_raw,:payload_sha256,:schema_ok,:freshness,:logical_key,:meta_json)""",
        item,
    )
    _prune_raw(conn, logical_key or adapter)
    return _hydrate(item)


def _get(url: str) -> tuple[str, Any]:
    """Fetch once, keep the verbatim body, then parse it."""
    response = httpx.get(url, timeout=settings.http_timeout_s)
    response.raise_for_status()
    return response.text, response.json()


def _fixture_text(name: str) -> tuple[str, str]:
    path = FIXTURE_ROOT / name
    return path.read_text(encoding="utf-8"), str(path.relative_to(BACKEND_ROOT))


def _replay(conn: sqlite3.Connection, adapter: str, mode: str, reason: str | None = None) -> dict[str, Any]:
    meta: dict[str, Any] = {"mode": mode, "fixture": True, "synthetic": adapter != "areas"}
    if reason:
        meta["fallback_reason"] = reason
    if adapter == "pipeline":
        text, location = _fixture_text("pipeline_ond2026.csv")
        return _store(conn, adapter, location, parse_pipeline_csv(text, source_file="03_prob_csv_q.py compatible output"),
                      "replay", raw_parts={location: text}, meta={**meta, "format": "exceedance_probability_csv"})
    if adapter == "triggers":
        text, location = _fixture_text("triggers.json")
        raw = json.loads(text)
        payload = normalise_triggers(raw.get("rules"), raw.get("events"), raw.get("actions"), raw.get("check_logs"))
        return _store(conn, adapter, location, payload, "replay", raw_parts={location: text}, meta=meta)
    if adapter == "indicators":
        text, location = _fixture_text("indicators.json")
        return _store(conn, adapter, location, normalise_indicators(json.loads(text)), "replay",
                      raw_parts={location: text}, meta={**meta, "synthetic": False})
    if adapter == "forecasts":
        step = replay_step(conn)
        name = f"escalation/step{step}.json" if step else "forecasts.json"
        text, location = _fixture_text(name)
        raw = json.loads(text)
        payload = normalise_forecasts(raw.get("available"), raw.get("stats"))
        return _store(conn, adapter, location, payload, "replay", raw_parts={location: text},
                      meta={**meta, "escalation_step": step, "provenance": raw.get("_provenance", {})})
    text, location = _fixture_text("areas.json")
    return _store(conn, adapter, location, normalise_areas(json.loads(text)), "replay", raw_parts={location: text}, meta=meta)


def _forecast_issue(available: Any, requested: str | None = None) -> dict[str, Any]:
    issues = _results(available)
    if not issues:
        return {}
    if requested:
        chosen = next((item for item in issues if str(item.get("id")) == requested), None)
        if chosen:
            return chosen
    return next((item for item in issues if item.get("target_season") == "OND"), issues[0])


def _fetch_live(conn: sqlite3.Connection, adapter: str, mode: str) -> dict[str, Any]:
    base = settings.icpac_base
    if adapter == "triggers":
        urls = {
            "rules": f"{base}/api/triggers/rules/",
            "events": f"{base}/api/triggers/events/",
            "actions": f"{base}/api/triggers/actions/",
            "check_logs": f"{base}/api/triggers/check-logs/?page_size=20",
        }
        bodies = {name: _get(url) for name, url in urls.items()}
        payload = normalise_triggers(*(bodies[name][1] for name in ("rules", "events", "actions", "check_logs")))
        raw_parts = {urls[name]: bodies[name][0] for name in urls}
        return _store(conn, adapter, urls["rules"], payload, "live", raw_parts=raw_parts, meta={"mode": mode})

    if adapter == "forecasts":
        # One unfiltered call returns every GHA admin-1 unit for the issue, so
        # the regional view is a single upstream request rather than eleven.
        available_url = f"{base}/api/datasets/forecasts/available/?forecast_type=return_period"
        available_text, available = _get(available_url)
        issue = _forecast_issue(available, forecast_issue(conn))
        stats_url = (
            f"{base}/api/datasets/forecasts/stats/?admin_level=1"
            f"&valid_date={issue.get('valid_date', '2026-10-01')}"
            f"&lead_months={issue.get('lead_months', 3)}&min_probability=0"
        )
        stats_text, stats = _get(stats_url)
        payload = normalise_forecasts(available, stats)
        return _store(conn, adapter, stats_url, payload, "live",
                      raw_parts={available_url: available_text, stats_url: stats_text},
                      meta={"mode": mode, "issue_id": issue.get("id"), "coverage": "all GHA countries"})

    if adapter == "areas":
        # `fields=id,name` returns the admin-1 index without geometry (a few KB
        # per country instead of megabytes); geometry is fetched per country on
        # demand by area_geometry().
        raw_parts: dict[str, str] = {}
        payloads = []
        for iso3, _ in GHA_COUNTRIES:
            url = f"{base}/api/areas/areas/?level=1&code={iso3}&fields=id,name"
            text, raw = _get(url)
            raw_parts[url] = text
            payloads.append(normalise_areas(raw))
        payload = merge_areas(payloads)
        return _store(conn, adapter, f"{base}/api/areas/areas/?level=1&fields=id,name", payload, "live",
                      raw_parts=raw_parts,
                      meta={"mode": mode, "countries": [iso3 for iso3, _ in GHA_COUNTRIES], "geometry": "on demand"})

    if adapter == "indicators":
        url = f"{base}/api/datasets/indicators/"
        text, raw = _get(url)
        return _store(conn, adapter, url, normalise_indicators(raw), "live", raw_parts={url: text}, meta={"mode": mode})

    raise ValueError(f"{adapter} has no live endpoint")


def refresh_adapter(conn: sqlite3.Connection, adapter: str, force: bool = False) -> dict[str, Any]:
    if adapter not in SOURCE_LABELS:
        raise ValueError(f"Unknown source adapter: {adapter}")
    cached = _recent(conn, adapter)
    mode = source_mode(conn)
    # Changing the escalation step or the source mode must produce a new
    # snapshot rather than silently reusing the cached one. Snapshots stay
    # append-only; only the cache-hit condition is narrowed.
    stale_selection = bool(cached) and (
        (mode == "replay_only" and (
            cached["freshness"] != "replay"
            or (adapter == "forecasts" and cached["meta"].get("escalation_step", 0) != replay_step(conn))
        ))
        # A different published forecast issue is different evidence, not a
        # cache hit on the same query.
        or (adapter == "forecasts" and mode != "replay_only" and forecast_issue(conn)
            and cached["meta"].get("issue_id") != forecast_issue(conn))
    )
    if cached and _fresh(cached) and not force and not stale_selection:
        cached["freshness"] = "cached" if cached["freshness"] != "replay" else "replay"
        return cached
    if mode == "replay_only" or adapter == "pipeline":
        return _replay(conn, adapter, mode)
    try:
        return _fetch_live(conn, adapter, mode)
    except (httpx.HTTPError, ValueError, KeyError, json.JSONDecodeError) as exc:
        if cached:
            cached["freshness"] = "stale"
            cached["meta"] = {**cached["meta"], "last_error": str(exc)[:300]}
            return cached
        if not settings.demo_mode:
            raise RuntimeError(f"{adapter} is unavailable and no cached snapshot exists") from exc
        return _replay(conn, adapter, mode, reason=str(exc)[:300])


def refresh_all(conn: sqlite3.Connection, force: bool = False) -> list[dict[str, Any]]:
    return [refresh_adapter(conn, adapter, force) for adapter in SOURCE_ORDER]


def _public(item: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in item.items() if not key.startswith("_")}


def list_snapshots(conn: sqlite3.Connection, adapter: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    query = "SELECT * FROM source_snapshots"
    params: list[Any] = []
    if adapter:
        query += " WHERE adapter = ?"
        params.append(adapter)
    query += " ORDER BY retrieved_at DESC, id DESC LIMIT ?"
    params.append(limit)
    return [_public(_hydrate(row)) for row in conn.execute(query, params)]


def get_snapshot(conn: sqlite3.Connection, snapshot_id: str, *, include_raw: bool = False) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM source_snapshots WHERE id = ?", (snapshot_id,)).fetchone()
    if not row:
        raise KeyError(snapshot_id)
    item = _hydrate(row)
    raw = item.pop("_raw", None)
    if include_raw:
        # Raw bodies can be several megabytes (the Kenya boundary payload is
        # ~3.6 MB). Send a bounded preview plus the per-endpoint hashes a
        # reviewer needs to verify the full body themselves.
        if raw is None:
            item["raw"] = {"available": False, "note": "Verbatim body pruned; per-endpoint hashes remain in meta.parts."}
        else:
            redacted = json.dumps(redact(json.loads(raw)), indent=2, ensure_ascii=False)
            item["raw"] = {
                "available": True,
                "truncated": len(redacted) > RAW_RESPONSE_PREVIEW_CHARS,
                "bytes": len(raw.encode("utf-8")),
                "preview": redacted[:RAW_RESPONSE_PREVIEW_CHARS],
            }
    return _public(item)


def signals(conn: sqlite3.Connection) -> dict[str, Any]:
    latest = {adapter: refresh_adapter(conn, adapter) for adapter in SOURCE_ORDER}

    def tag(adapter: str, key: str) -> list[dict[str, Any]]:
        snapshot = latest[adapter]
        return [
            {**item, "snapshot_id": snapshot["id"], "freshness": snapshot["freshness"], "source_adapter": adapter}
            for item in snapshot["payload"].get(key, [])
        ]

    return {
        "mode": source_mode(conn),
        "rules": tag("triggers", "rules"),
        "events": tag("triggers", "events"),
        "forecasts": tag("forecasts", "forecasts"),
        "pipeline": tag("pipeline", "files"),
        "upstream_actions": tag("triggers", "actions"),
        "check_logs": tag("triggers", "check_logs"),
    }


def areas(conn: sqlite3.Connection, country: str | None = None, level: int | None = None) -> list[dict[str, Any]]:
    snapshot = refresh_adapter(conn, "areas")
    records = snapshot["payload"].get("areas", [])
    return [
        item for item in records
        if (not country or item.get("country") == country) and (level is None or item.get("level") == level)
    ]


def latest_probability(conn: sqlite3.Connection, area_id: str, indicator: str | None = None) -> dict[str, Any] | None:
    """Newest observed exceedance probability for an area, used by the stop trigger."""
    for adapter, key in (("forecasts", "forecasts"), ("pipeline", "files")):
        snapshot = refresh_adapter(conn, adapter)
        for record in snapshot["payload"].get(key, []):
            if record.get("area_id") == area_id and (not indicator or record.get("indicator") == indicator):
                return {
                    "probability": float(record.get("probability", 0)),
                    "indicator": record.get("indicator"),
                    "snapshot_id": snapshot["id"],
                    "freshness": snapshot["freshness"],
                }
    return None


def area_geometry(conn: sqlite3.Connection, country: str) -> dict[str, Any]:
    """Admin-1 geometry for one country, cached as its own snapshot.

    The full GADM payload is megabytes per country, so the regional index keeps
    geometry out and callers pull only the country they are drawing.
    """
    country = country.upper()
    if country not in COUNTRY_NAMES:
        raise ValueError(f"{country} is not a Greater Horn of Africa country published by ICPAC")
    key = f"areas_geom:{country}"
    row = conn.execute(
        "SELECT * FROM source_snapshots WHERE logical_key = ? ORDER BY retrieved_at DESC, id DESC LIMIT 1", (key,)
    ).fetchone()
    if row:
        snapshot = _hydrate(row)
        if _fresh(snapshot):
            return {"country": country, "areas": snapshot["payload"].get("areas", []), "snapshot_id": snapshot["id"], "freshness": "cached"}
    mode = source_mode(conn)
    if mode != "replay_only":
        try:
            url = f"{settings.icpac_base}/api/areas/areas/?level=1&code={country}"
            text, raw = _get(url)
            payload = normalise_areas(raw)
            item = _store_with_key(conn, "areas", key, url, payload, "live", raw_parts={url: text}, meta={"mode": mode, "country": country})
            return {"country": country, "areas": payload["areas"], "snapshot_id": item["id"], "freshness": "live"}
        except (httpx.HTTPError, ValueError, KeyError, json.JSONDecodeError):
            pass
    text, location = _fixture_text("areas.json")
    payload = normalise_areas(json.loads(text))
    areas = [item for item in payload["areas"] if item["country"] == country]
    return {"country": country, "areas": areas, "snapshot_id": None, "freshness": "replay"}


def tile_source() -> dict[str, Any]:
    """ICPAC's public pg_tileserv admin-1 layer, joined on the same GADM id."""
    return {
        "layer": TILE_LAYER,
        "catalog_url": f"{settings.icpac_base}/tileserv/index.json",
        "tile_url": f"{settings.icpac_base}/tileserv/{TILE_LAYER}/{{z}}/{{x}}/{{y}}.pbf",
        "source_layer": TILE_LAYER,
        "join_property": TILE_JOIN_PROPERTY,
        "attribution": "Boundaries: GADM 4.1 via ICPAC pg_tileserv",
        "min_zoom": 0,
        "max_zoom": 12,
    }
