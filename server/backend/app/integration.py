"""Versioned read-only partner API and auditable webhook delivery."""

from __future__ import annotations

import asyncio
import hmac
import ipaddress
import secrets
import socket
import sqlite3
import time
from collections import defaultdict, deque
from typing import Any
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException, Request, status

from .db import append_event, connection, hash_secret, transaction, verify_secret
from .domain import canonical_json, loads, new_id, now
from .exports import packet_manifest
from .services import get_case, verify_approvals, verify_event_chain

_key_requests: dict[str, deque[float]] = defaultdict(deque)


def create_key(conn: sqlite3.Connection, label: str) -> dict[str, str]:
    value = f"linda_{secrets.token_urlsafe(32)}"
    key_id = new_id("key")
    conn.execute("INSERT INTO integration_keys (id,label,key_hash,created_at) VALUES (?,?,?,?)", (key_id, label, hash_secret(value), now()))
    return {"id": key_id, "label": label, "key": value, "created_at": now()}


def list_keys(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return [dict(row) for row in conn.execute("SELECT id,label,created_at,revoked_at FROM integration_keys ORDER BY created_at DESC")]


def revoke_key(conn: sqlite3.Connection, key_id: str) -> None:
    if not conn.execute("UPDATE integration_keys SET revoked_at = ? WHERE id = ? AND revoked_at IS NULL", (now(), key_id)).rowcount:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Active integration key not found")


def require_partner_key(request: Request, conn: sqlite3.Connection) -> dict[str, Any]:
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Bearer API key is required")
    supplied = authorization.removeprefix("Bearer ")
    row = next((item for item in conn.execute("SELECT id,label,key_hash FROM integration_keys WHERE revoked_at IS NULL") if verify_secret(item["key_hash"], supplied)), None)
    if not row:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="Invalid or revoked integration key")
    timings = _key_requests[row["id"]]; cutoff = time.time() - 60
    while timings and timings[0] < cutoff: timings.popleft()
    if len(timings) >= 60:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, detail="Integration API key rate limit exceeded")
    timings.append(time.time())
    return dict(row)


def activation_record(conn: sqlite3.Connection, case_id: str) -> dict[str, Any]:
    case = get_case(conn, case_id)
    if case["state"] not in {"APPROVED", "HANDED_OFF", "REVOKED"}:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Only approved, handed-off, or revoked activations are published")
    exports = [dict(row) for row in conn.execute("SELECT id,kind,sha256,generated_at,meta_json FROM exports WHERE case_id = ? ORDER BY generated_at DESC", (case_id,))]
    manifest_export = next((item for item in exports if item["kind"] == "packet_json"), None)
    return {
        "mode": "exercise", "disclaimer": "Hackathon demonstration only. Linda does not send public alerts or move funds.",
        "id": case["id"], "title": case["title"], "area": {"id": case["area_id"], "name": case["area_name"]}, "hazard": case["hazard"], "stage": case["stage"], "ndma_phase": case["assessment"].get("ndma_phase"), "state": case["state"],
        "assessment": case["assessment"], "action_cards": [{"id": card["id"], "title": card["title"], "budget": card["budget"]} for card in case["action_cards"]],
        "approvals": verify_approvals(conn, case_id)["signatures"], "evidence": case["evidence"],
        "compound_signals": case["assessment"].get("compound_signals", []), "manifest_sha256": loads(manifest_export["meta_json"], {}).get("manifest_sha256") if manifest_export else None,
        "links": {"self": f"/integration/v1/activations/{case_id}", "cap": f"/integration/v1/activations/{case_id}/cap.xml", "husika_payload": f"/integration/v1/activations/{case_id}/husika-payload.json", "verify": f"/integration/v1/activations/{case_id}/verify"},
    }


def list_activations(conn: sqlite3.Connection, *, since: str | None = None, area: str | None = None, hazard: str | None = None, state: str | None = None, limit: int = 50, cursor: str | None = None) -> dict[str, Any]:
    clauses = ["state IN ('APPROVED','HANDED_OFF','REVOKED')"]; params: list[str] = []
    if since: clauses.append("updated_at >= ?"); params.append(since)
    if area: clauses.append("area_id = ?"); params.append(area)
    if hazard: clauses.append("hazard = ?"); params.append(hazard)
    if state: clauses.append("state = ?"); params.append(state)
    if cursor:
        try:
            cursor_time, cursor_id = cursor.rsplit("|", 1)
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Malformed activation cursor") from exc
        clauses.append("(updated_at < ? OR (updated_at = ? AND id < ?))")
        params.extend([cursor_time, cursor_time, cursor_id])
    rows = conn.execute(
        f"SELECT id,updated_at FROM decision_cases WHERE {' AND '.join(clauses)} ORDER BY updated_at DESC, id DESC LIMIT ?",
        [*params, limit + 1],
    ).fetchall()
    page = rows[:limit]
    next_cursor = f"{page[-1]['updated_at']}|{page[-1]['id']}" if len(rows) > limit and page else None
    return {"mode": "exercise", "disclaimer": "Hackathon demonstration only.", "items": [activation_record(conn, row["id"]) for row in page], "next": next_cursor}


def _validate_webhook_url(url: str) -> None:
    """Reject local/private destinations before a background HTTP request.

    Webhook endpoints are administrator entered, but validating them still
    prevents an accidental or malicious subscription from reaching loopback,
    link-local, or RFC1918 services through Linda's network identity.
    """
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Webhook URL must be a public HTTPS URL without credentials")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(parsed.hostname, parsed.port or 443, type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Webhook host could not be resolved") from exc
    if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Webhook URL must resolve only to public addresses")


def create_webhook(conn: sqlite3.Connection, url: str, events: list[str], secret: str) -> dict[str, Any]:
    allowed = {"activation.approved", "activation.revoked"}
    if not events or not set(events).issubset(allowed):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Webhook events must be activation.approved and/or activation.revoked")
    _validate_webhook_url(url)
    item = {"id": new_id("wh"), "url": url, "events_json": canonical_json(events), "secret": secret, "active": 1, "created_at": now()}
    conn.execute("INSERT INTO webhook_subscriptions (id,url,events_json,secret,active,created_at) VALUES (:id,:url,:events_json,:secret,:active,:created_at)", item)
    return {**item, "events": events, "secret": None}


def list_webhooks(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    items = []
    for row in conn.execute("SELECT * FROM webhook_subscriptions ORDER BY created_at DESC"):
        item = dict(row); item["events"] = loads(item.pop("events_json"), []); item.pop("secret")
        last = conn.execute("SELECT delivered,status_code,attempted_at FROM webhook_deliveries WHERE subscription_id = ? ORDER BY attempted_at DESC LIMIT 1", (item["id"],)).fetchone()
        item["last_delivery"] = dict(last) if last else None; items.append(item)
    return items


def delete_webhook(conn: sqlite3.Connection, webhook_id: str) -> None:
    if not conn.execute("DELETE FROM webhook_subscriptions WHERE id = ?", (webhook_id,)).rowcount:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Webhook subscription not found")


def delivery_statuses(conn: sqlite3.Connection, case_id: str) -> list[dict[str, Any]]:
    """Non-secret delivery history for the case handoff screen."""
    return [dict(row) for row in conn.execute(
        """SELECT webhook_deliveries.id, webhook_subscriptions.url, webhook_deliveries.event,
                  webhook_deliveries.attempt, webhook_deliveries.status_code,
                  webhook_deliveries.delivered, webhook_deliveries.attempted_at
             FROM webhook_deliveries
             JOIN webhook_subscriptions ON webhook_subscriptions.id = webhook_deliveries.subscription_id
             WHERE webhook_deliveries.case_id = ?
             ORDER BY webhook_deliveries.attempted_at DESC""",
        (case_id,),
    )]


async def deliver_webhooks(case_id: str, event: str) -> None:
    """Run after a transition without holding a database write lock while waiting."""
    with connection() as conn:
        payload = canonical_json(activation_record(conn, case_id)).encode()
        subscriptions = [dict(row) for row in conn.execute("SELECT * FROM webhook_subscriptions WHERE active = 1") if event in loads(row["events_json"], [])]
    for subscription in subscriptions:
        delivery_id = new_id("delivery")
        signature = hmac.new(subscription["secret"].encode(), payload, "sha256").hexdigest()
        for attempt, delay in enumerate((0, 60, 300, 1500), 1):
            if delay: await asyncio.sleep(delay)
            code: int | None = None; delivered = False
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.post(subscription["url"], content=payload, headers={"Content-Type": "application/json", "X-Linda-Event": event, "X-Linda-Delivery": delivery_id, "X-Linda-Signature": f"sha256={signature}"})
                    code = response.status_code; delivered = 200 <= code < 300
            except httpx.HTTPError:
                pass
            with transaction() as conn:
                conn.execute("INSERT INTO webhook_deliveries (id,subscription_id,case_id,event,attempt,status_code,delivered,attempted_at) VALUES (?,?,?,?,?,?,?,?)", (new_id("delivery"), subscription["id"], case_id, event, attempt, code, int(delivered), now()))
                append_event(conn, case_id, "system", "WEBHOOK_DELIVERED" if delivered else "WEBHOOK_FAILED", {"subscription_id": subscription["id"], "event": event, "attempt": attempt, "status_code": code, "delivery_id": delivery_id})
            if delivered: break


async def deliver_webhooks_for_case(case_id: str, event: str) -> None:
    """Background-task entrypoint with its own short-lived database connection."""
    await deliver_webhooks(case_id, event)


def verify_activation(conn: sqlite3.Connection, case_id: str) -> dict[str, Any]:
    return {"mode": "exercise", "case_id": case_id, "event_chain": verify_event_chain(conn, case_id), "signatures": verify_approvals(conn, case_id), "manifest": packet_manifest(conn, case_id)["manifest_sha256"]}
