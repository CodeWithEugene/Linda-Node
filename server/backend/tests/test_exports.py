"""Export contracts: manifest stability, CAP XSD, Husika schema, offline bundle."""

from __future__ import annotations

import io
import json
import re
import zipfile

import pytest
from fastapi.testclient import TestClient
from lxml import etree

from app.config import settings
from app.db import connection, reset_demo, transaction
from app.domain import sha256
from app.exports import (
    cap_xml,
    exported_payload,
    generate_bundle,
    generate_cap,
    husika_payload,
    packet_manifest,
    published_cap_feed,
    validate_cap,
)
from app.husika_contract import metadata as husika_metadata
from app.husika_contract import validate as validate_husika
from app.main import app
from app.services import get_case

PUBLISHED = "case_ruvuma_ond2026_handedoff"
BLOCKED = "case_ruvuma_ond2026"
CAP_NS = {"cap": "urn:oasis:names:tc:emergency:cap:1.2"}


@pytest.fixture()
def seeded() -> None:
    reset_demo()


# --------------------------------------------------------------------------
# Packet manifest.
# --------------------------------------------------------------------------


def test_manifest_hash_is_stable_across_regeneration(seeded: None) -> None:
    with connection() as conn:
        first = packet_manifest(conn, PUBLISHED)
        second = packet_manifest(conn, PUBLISHED)
    first.pop("generated_at"), second.pop("generated_at")
    first.pop("manifest_sha256"), second.pop("manifest_sha256")
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_manifest_carries_the_full_decision_record(seeded: None) -> None:
    with connection() as conn:
        manifest = packet_manifest(conn, PUBLISHED)
    assert manifest["mode"] == "exercise"
    assert "moves no funds" in manifest["disclaimer"]
    assert manifest["policy"]["version_hash"] and manifest["policy"]["raw"]
    assert manifest["event_chain"]["ok"] is True
    assert len(manifest["approvals"]) == 3
    assert all(item["signature_valid"] for item in manifest["approvals"])
    assert manifest["tranche_recommendations"]
    assert all("moves no funds" in item["disclaimer"] for item in manifest["tranche_recommendations"])
    assert all(item["payload_sha256"] for item in manifest["evidence"])
    assert re.fullmatch(r"[0-9a-f]{64}", manifest["manifest_sha256"])


def test_regeneration_creates_a_new_immutable_export(seeded: None) -> None:
    with TestClient(app) as client:
        client.post("/api/auth/login", json={"email": "david.drm@demo", "password": "linda-demo"})
        first = client.post(f"/api/cases/{PUBLISHED}/exports/packet", json={}).json()["exports"]
        second = client.post(f"/api/cases/{PUBLISHED}/exports/packet", json={}).json()["exports"]
        assert {item["id"] for item in first} & {item["id"] for item in second} == set()
        for export in first:
            assert client.get(f"/api/exports/{export['id']}/download").status_code == 200


def test_the_stored_hash_matches_the_downloaded_bytes(seeded: None) -> None:
    with connection() as conn:
        exports = [dict(row) for row in conn.execute("SELECT id FROM exports WHERE case_id = ?", (PUBLISHED,))]
        for export in exports:
            record, payload = exported_payload(conn, export["id"])
            assert record["sha256"] == sha256(payload)
    assert exports


# --------------------------------------------------------------------------
# CAP 1.2.
# --------------------------------------------------------------------------


def test_cap_validates_against_the_oasis_xsd(seeded: None) -> None:
    with connection() as conn:
        case = get_case(conn, PUBLISHED)
    validate_cap(cap_xml(case))
    validate_cap(cap_xml(case, cancel=True))


def test_cap_is_always_exercise_status(seeded: None) -> None:
    with connection() as conn:
        case = get_case(conn, PUBLISHED)
    document = etree.fromstring(cap_xml(case))
    assert document.find("cap:status", CAP_NS).text == "Exercise"
    assert document.find("cap:msgType", CAP_NS).text == "Alert"
    assert etree.fromstring(cap_xml(case, cancel=True)).find("cap:msgType", CAP_NS).text == "Cancel"


def test_cap_carries_the_gadm_geocode(seeded: None) -> None:
    with connection() as conn:
        case = get_case(conn, PUBLISHED)
    document = etree.fromstring(cap_xml(case))
    area = document.find("cap:info/cap:area", CAP_NS)
    assert area.find("cap:areaDesc", CAP_NS).text == "Ruvuma"
    assert area.find("cap:geocode/cap:valueName", CAP_NS).text == "GADM"
    assert area.find("cap:geocode/cap:value", CAP_NS).text == "TZA.22_1"


def test_cap_severity_maps_from_the_stage(seeded: None) -> None:
    with connection() as conn:
        case = get_case(conn, PUBLISHED)
    for stage, expected in (("go", ("Immediate", "Severe")), ("set", ("Expected", "Moderate")), ("ready", ("Future", "Minor"))):
        info = etree.fromstring(cap_xml({**case, "stage": stage})).find("cap:info", CAP_NS)
        assert (info.find("cap:urgency", CAP_NS).text, info.find("cap:severity", CAP_NS).text) == expected


def test_cap_export_is_refused_before_approval(seeded: None) -> None:
    with transaction() as conn, pytest.raises(ValueError):
        generate_cap(conn, BLOCKED, "usr_david")


def test_the_public_feed_only_lists_published_activations(seeded: None) -> None:
    with connection() as conn:
        feed = published_cap_feed(conn).decode()
    assert PUBLISHED in feed
    assert "case_ruvuma_ond2026_revoked" in feed
    assert feed.count("<entry") == 2


# --------------------------------------------------------------------------
# Husika contract.
# --------------------------------------------------------------------------


def test_husika_payload_validates_against_the_vendored_spec(seeded: None) -> None:
    with connection() as conn:
        case = get_case(conn, PUBLISHED)
    payload = husika_payload(case)
    validate_husika(payload)
    assert payload["mode"] == "exercise"
    assert "does not send" in payload["disclaimer"]
    assert payload["openapi_snapshot"]["sha256"] == husika_metadata()["sha256"]


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("threat", "event_type"), "invented_hazard"),
        (("threat", "severity"), "catastrophic"),
        (("threat", "urgency"), "whenever"),
        (("message", "language"), "klingon"),
    ],
)
def test_a_wrong_enum_fails_husika_validation(seeded: None, path: tuple[str, str], value: str) -> None:
    with connection() as conn:
        case = get_case(conn, PUBLISHED)
    payload = husika_payload(case)
    payload["requests"][path[0]][path[1]] = value
    with pytest.raises(ValueError, match="Husika OpenAPI validation failed"):
        validate_husika(payload)


def test_the_husika_body_is_human_editable_and_carries_the_language(seeded: None) -> None:
    with connection() as conn:
        case = get_case(conn, PUBLISHED)
    payload = husika_payload(case, "Zoezi: tahadhari ya ukame.", "sw")
    validate_husika(payload)
    assert payload["requests"]["message"]["language"] == "sw"
    assert payload["requests"]["message"]["message"] == "Zoezi: tahadhari ya ukame."


# --------------------------------------------------------------------------
# Air-gapped bundle.
# --------------------------------------------------------------------------


def test_the_bundle_contains_every_artifact_and_matching_checksums(seeded: None) -> None:
    with transaction() as conn:
        record = generate_bundle(conn, PUBLISHED, "usr_david")
    with connection() as conn:
        _, payload = exported_payload(conn, record["id"])
    archive = zipfile.ZipFile(io.BytesIO(payload))
    assert set(archive.namelist()) == {"dossier.html", "manifest.json", "alert.cap.xml", "checksums.txt"}
    recorded = dict(
        reversed(line.split("  ", 1)) for line in archive.read("checksums.txt").decode().splitlines()
    )
    for name in ("dossier.html", "manifest.json", "alert.cap.xml"):
        assert recorded[name] == sha256(archive.read(name)), name
    validate_cap(archive.read("alert.cap.xml"))
    json.loads(archive.read("manifest.json"))


def test_the_offline_dossier_makes_no_external_requests(seeded: None) -> None:
    with transaction() as conn:
        record = generate_bundle(conn, PUBLISHED, "usr_david")
    with connection() as conn:
        _, payload = exported_payload(conn, record["id"])
    dossier = zipfile.ZipFile(io.BytesIO(payload)).read("dossier.html").decode()
    for pattern in (r'src\s*=\s*["\']https?://', r'href\s*=\s*["\']https?://', r'@import', r'<script[^>]+src='):
        assert not re.search(pattern, dossier, re.IGNORECASE), pattern


# --------------------------------------------------------------------------
# Nothing secret ever leaves the system.
# --------------------------------------------------------------------------


SECRET_MARKERS = ("signing_key", "password_hash", "key_hash", "LINDA_SECRET", "BLOB_READ_WRITE_TOKEN")


def test_no_export_contains_a_secret(seeded: None) -> None:
    with connection() as conn:
        conn.execute("SELECT 1")
        signing_keys = [row["signing_key"] for row in conn.execute("SELECT signing_key FROM users")]
        exports = [dict(row) for row in conn.execute("SELECT id, kind FROM exports")]
        for export in exports:
            _, payload = exported_payload(conn, export["id"])
            text = payload.decode("utf-8", errors="ignore")
            for marker in SECRET_MARKERS:
                assert marker not in text, f"{export['kind']} leaked {marker}"
            for key in signing_keys:
                assert key not in text, f"{export['kind']} leaked a signing key"
            assert settings.secret not in text
    assert exports
