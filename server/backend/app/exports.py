"""Immutable packet, CAP, Husika, and offline-bundle generators."""

from __future__ import annotations

import html
import io
import json
import sqlite3
import zipfile
from pathlib import Path
from string import Template
from typing import Any
from xml.etree import ElementTree as ET

from lxml import etree
from weasyprint import HTML

from .config import CONTENT_ROOT, EXPORT_ROOT
from .db import append_event
from .domain import canonical_json, new_id, now, sha256
from .husika_contract import metadata as husika_contract_metadata
from .husika_contract import validate as validate_husika_contract
from .library import policy
from .services import case_events, get_case, verify_approvals, verify_event_chain

CAP_NS = "urn:oasis:names:tc:emergency:cap:1.2"
ET.register_namespace("", CAP_NS)
CAP_XSD_PATH = Path(CONTENT_ROOT).parents[0] / "fixtures" / "cap" / "cap12.xsd"
CAP_SCHEMA = etree.XMLSchema(etree.parse(str(CAP_XSD_PATH)))
TEMPLATE_ROOT = Path(CONTENT_ROOT) / "templates"


def _export_path(case_id: str, export_id: str, suffix: str) -> Path:
    folder = EXPORT_ROOT / case_id
    folder.mkdir(parents=True, exist_ok=True)
    return folder / f"{export_id}.{suffix}"


def _store(conn: sqlite3.Connection, case_id: str, actor_id: str, kind: str, suffix: str, payload: bytes, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    export_id = new_id("exp")
    path = _export_path(case_id, export_id, suffix)
    path.write_bytes(payload)
    record = {"id": export_id, "case_id": case_id, "kind": kind, "file_path": str(path), "sha256": sha256(payload), "generated_by": actor_id, "generated_at": now(), "meta_json": canonical_json(meta or {})}
    conn.execute(
        """INSERT INTO exports (id,case_id,kind,file_path,sha256,generated_by,generated_at,meta_json)
           VALUES (:id,:case_id,:kind,:file_path,:sha256,:generated_by,:generated_at,:meta_json)""", record,
    )
    append_event(conn, case_id, actor_id, "EXPORT_GENERATED", {"export_id": export_id, "kind": kind, "sha256": record["sha256"]})
    return {**record, "meta": meta or {}}


def packet_manifest(conn: sqlite3.Connection, case_id: str) -> dict[str, Any]:
    case = get_case(conn, case_id)
    approvals = verify_approvals(conn, case_id)
    event_check = verify_event_chain(conn, case_id)
    events = case_events(conn, case_id)
    task_history = [event for event in events if event["event_type"] in {"TASK_UPDATED", "READINESS_TASKS_MATERIALIZED"}]
    ai_explanations = [event for event in events if event["event_type"] == "ASSIST_RAN"]
    release_lines = []
    for card in case["action_cards"]:
        readiness = card["budget"]["readiness_tranche"]
        release_lines.append({
            "card_id": card["id"],
            "recommended_release": f"readiness_tranche {card['budget']['currency']} {readiness['amount']} upon recorded human approvals",
            "disclaimer": "Recommendation only; Linda Protocol moves no funds.",
        })
    body = {
        "mode": "exercise",
        "disclaimer": "Linda Protocol hackathon demonstration. This record moves no funds. HMAC protects integrity within this demo system; it is not PKI, blockchain, or an external digital-signature service.",
        "case": {key: case[key] for key in ("id", "title", "area_id", "area_name", "hazard", "state", "stage", "policy_version_id", "version")},
        "policy": {"version_hash": case["policy_version_id"], "raw": policy()["raw"]},
        "assessment": case["assessment"], "evidence": case["evidence"], "tasks": case["tasks"], "task_history": task_history,
        "action_cards": [{key: card[key] for key in ("id", "title", "owner_role", "budget", "disclaimer")} for card in case["action_cards"]],
        "tranche_recommendations": release_lines, "approvals": approvals["signatures"],
        "compound_signals": case["assessment"].get("compound_signals", []),
        "ai_explanations": ai_explanations, "event_chain": event_check, "generated_at": now(),
    }
    body["manifest_sha256"] = sha256(canonical_json(body))
    return body


def _render_packet(manifest: dict[str, Any], template_name: str) -> str:
    case = manifest["case"]
    task_rows = "".join(f"<tr><td>{html.escape(task['title'])}</td><td>{task['state']}</td><td>{task.get('blocker_code') or '—'}</td></tr>" for task in manifest["tasks"])
    approval_rows = "".join(
        f"<tr><td>{html.escape(item['role'])}</td><td>{html.escape(item['decision'])}</td><td><code>{item['digest']}</code></td><td><code>{item.get('signature', '—')}</code></td></tr>"
        for item in manifest["approvals"]
    )
    values = {
        "case_id": case["id"], "case_title": html.escape(case["title"]),
        "area_id": html.escape(case["area_id"]), "area_name": html.escape(case["area_name"]),
        "hazard": html.escape(case["hazard"]), "state": html.escape(case["state"]),
        "assessment": html.escape(json.dumps(manifest["assessment"], indent=2)),
        "evidence": html.escape(json.dumps(manifest["evidence"], indent=2)),
        "action_cards": html.escape(json.dumps(manifest["tranche_recommendations"], indent=2)),
        "ai_explanations": html.escape(json.dumps(manifest["ai_explanations"], indent=2)),
        "task_rows": task_rows, "approval_rows": approval_rows,
        "manifest_sha256": manifest["manifest_sha256"],
    }
    return Template((TEMPLATE_ROOT / template_name).read_text(encoding="utf-8")).safe_substitute(values)


def generate_packet(conn: sqlite3.Connection, case_id: str, actor_id: str) -> list[dict[str, Any]]:
    manifest = packet_manifest(conn, case_id)
    json_export = _store(conn, case_id, actor_id, "packet_json", "json", canonical_json(manifest).encode(), {"manifest_sha256": manifest["manifest_sha256"]})
    pdf = HTML(string=_render_packet(manifest, "packet.html")).write_pdf()
    pdf_export = _store(conn, case_id, actor_id, "packet_pdf", "pdf", pdf, {"manifest_sha256": manifest["manifest_sha256"], "renderer": "weasyprint"})
    return [json_export, pdf_export]


def cap_xml(case: dict[str, Any], cancel: bool = False) -> bytes:
    tag = lambda name: f"{{{CAP_NS}}}{name}"
    alert = ET.Element(tag("alert"))
    cap_time = now().replace("Z", "+00:00")
    fields = {"identifier": case["id"], "sender": "linda-protocol-demo", "sent": cap_time, "status": "Exercise", "msgType": "Cancel" if cancel else "Alert", "scope": "Restricted", "restriction": "hackathon demonstration"}
    for key, value in fields.items(): ET.SubElement(alert, tag(key)).text = value
    info = ET.SubElement(alert, tag("info"))
    stage = case.get("stage") or "ready"
    mapping = {"go": ("Immediate", "Severe", "Likely"), "set": ("Expected", "Moderate", "Likely"), "ready": ("Future", "Minor", "Possible")}
    urgency, severity, certainty = mapping.get(stage, mapping["ready"])
    for key, value in {"language": "en", "category": "Met", "event": case["hazard"].title(), "urgency": urgency, "severity": severity, "certainty": certainty, "effective": cap_time, "onset": cap_time, "senderName": "Linda Protocol demo", "headline": f"Exercise: {case['hazard'].title()} readiness for {case['area_name']}", "description": f"Linda Protocol exercise activation for {case['area_name']}.", "instruction": "Human-reviewed readiness recommendation only. Linda Protocol does not send public alerts or move funds."}.items(): ET.SubElement(info, tag(key)).text = value
    area = ET.SubElement(info, tag("area")); ET.SubElement(area, tag("areaDesc")).text = case["area_name"]
    geocode = ET.SubElement(area, tag("geocode")); ET.SubElement(geocode, tag("valueName")).text = "GADM"; ET.SubElement(geocode, tag("value")).text = case["area_id"]
    return ET.tostring(alert, encoding="utf-8", xml_declaration=True)


def validate_cap(payload: bytes) -> None:
    try:
        document = etree.fromstring(payload)
        CAP_SCHEMA.assertValid(document)
    except (etree.XMLSyntaxError, etree.DocumentInvalid) as exc:
        raise ValueError(f"CAP 1.2 XSD validation failed: {exc}") from exc


def generate_cap(conn: sqlite3.Connection, case_id: str, actor_id: str) -> dict[str, Any]:
    case = get_case(conn, case_id)
    if case["state"] not in {"APPROVED", "HANDED_OFF", "REVOKED"}:
        raise ValueError("CAP exports require an approved, handed-off, or revoked case")
    payload = cap_xml(case, cancel=case["state"] == "REVOKED")
    validate_cap(payload)
    return _store(conn, case_id, actor_id, "cap_xml", "xml", payload, {"validated": True, "status": "Exercise", "xsd_sha256": sha256(CAP_XSD_PATH.read_bytes())})


def husika_payload(case: dict[str, Any], message: str | None = None, language: str = "en") -> dict[str, Any]:
    contract = husika_contract_metadata()
    document = message or f"Exercise: {case['hazard'].title()} readiness action for {case['area_name']} is {case['state']}."
    stage = case.get("stage") or "ready"
    threat_level = {"go": "warning", "set": "watch", "ready": "advisory"}.get(stage, "advisory")
    severity = {"go": "high", "set": "medium", "ready": "low"}.get(stage, "low")
    urgency = {"go": "immediate", "set": "expected", "ready": "future"}.get(stage, "future")
    payload = {
        "mode": "exercise",
        "disclaimer": "Ready for dispatch by an authorised Husika operator — Linda Protocol does not send.",
        "openapi_snapshot": contract,
        "requests": {
            "threat": {"org_public_id": "", "title": case["title"], "summary": document[:280], "description": document, "event_type": case["hazard"], "urgency": urgency, "certainty": "likely", "severity": severity, "threat_level": threat_level, "content_status": "draft", "issue_time": now(), "effective_time": now(), "affected_area_description": f"{case['area_name']} ({case['area_id']})"},
            "broadcast": {"org_public_id": "", "title": case["title"], "threat_id": None, "forecast_id": None, "feed_id": None, "secondary_broadcast_id": None},
            "message": {"language": language, "message": document},
            "location": {"gid_1": case["area_id"], "org_public_id": "", "project_id": None, "threat_id": None, "forecast_id": None, "feed_id": None, "broadcast_id": None},
        },
    }
    validate_husika_contract(payload)
    return payload


def generate_husika(conn: sqlite3.Connection, case_id: str, actor_id: str, message: str | None, language: str) -> dict[str, Any]:
    case = get_case(conn, case_id)
    if case["state"] not in {"APPROVED", "HANDED_OFF", "REVOKED"}:
        raise ValueError("Husika payloads require an approved, handed-off, or revoked case")
    payload = husika_payload(case, message, language)
    return _store(conn, case_id, actor_id, "husika_payload", "json", canonical_json(payload).encode(), {"contract_valid": True, "openapi_snapshot_sha256": payload["openapi_snapshot"]["sha256"], "language": language})


def generate_bundle(conn: sqlite3.Connection, case_id: str, actor_id: str) -> dict[str, Any]:
    case = get_case(conn, case_id)
    if case["state"] not in {"APPROVED", "HANDED_OFF", "REVOKED"}:
        raise ValueError("Offline bundles require an approved, handed-off, or revoked case")
    manifest = packet_manifest(conn, case_id)
    dossier = _render_packet(manifest, "offline_dossier.html").encode()
    cap = cap_xml(case, cancel=case["state"] == "REVOKED")
    validate_cap(cap)
    contents = {"dossier.html": dossier, "manifest.json": canonical_json(manifest).encode(), "alert.cap.xml": cap}
    contents["checksums.txt"] = "\n".join(f"{sha256(data)}  {name}" for name, data in contents.items()).encode()
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as bundle:
        for name, data in contents.items(): bundle.writestr(name, data)
    return _store(conn, case_id, actor_id, "field_bundle", "zip", output.getvalue(), {"contents": list(contents), "offline": True})


def exported_file(conn: sqlite3.Connection, export_id: str) -> tuple[dict[str, Any], Path]:
    row = conn.execute("SELECT * FROM exports WHERE id = ?", (export_id,)).fetchone()
    if not row:
        raise FileNotFoundError(export_id)
    record = dict(row); path = Path(record["file_path"])
    if not path.is_file():
        raise FileNotFoundError(export_id)
    return record, path


def published_cap_feed(conn: sqlite3.Connection) -> bytes:
    atom = "http://www.w3.org/2005/Atom"; ET.register_namespace("", atom)
    feed = ET.Element(f"{{{atom}}}feed"); ET.SubElement(feed, f"{{{atom}}}title").text = "Linda Protocol Exercise CAP Feed"; ET.SubElement(feed, f"{{{atom}}}updated").text = now()
    for row in conn.execute("SELECT * FROM decision_cases WHERE state IN ('APPROVED','HANDED_OFF','REVOKED') ORDER BY updated_at DESC"):
        case = get_case(conn, row["id"]); entry = ET.SubElement(feed, f"{{{atom}}}entry"); ET.SubElement(entry, f"{{{atom}}}id").text = case["id"]; ET.SubElement(entry, f"{{{atom}}}title").text = case["title"]; ET.SubElement(entry, f"{{{atom}}}updated").text = case["updated_at"]; content = ET.SubElement(entry, f"{{{atom}}}content", {"type": "application/xml"}); content.text = cap_xml(case, case["state"] == "REVOKED").decode()
    return ET.tostring(feed, encoding="utf-8", xml_declaration=True)
