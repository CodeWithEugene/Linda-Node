from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import assists
from .auth import current_user, login, require_role
from .config import CONTENT_ROOT, settings
from .db import RecordedVersionConflict, append_event, connection, init_db, reset_demo, transaction
from .exports import (
    cap_xml,
    exported_payload,
    generate_bundle,
    generate_cap,
    generate_husika,
    generate_packet,
    husika_payload,
    published_cap_feed,
)
from .husika_contract import metadata as husika_contract_metadata
from .integration import (
    activation_record,
    create_key,
    create_webhook,
    delete_webhook,
    deliver_webhooks_for_case,
    delivery_statuses,
    list_activations,
    list_keys,
    list_webhooks,
    require_partner_key,
    revoke_key,
    verify_activation,
)
from .library import action_cards, policy
from .services import (
    attach_evidence_and_assess,
    case_events,
    case_summary,
    create_case,
    get_case,
    record_approval,
    revoke_for_stop_trigger,
    transition_case,
    update_task,
    verify_approvals,
    verify_event_chain,
)
from .sources import areas as source_areas
from .sources import (
    get_snapshot,
    list_snapshots,
    refresh_all,
    set_source_mode,
    signals,
    source_mode,
)


class LoginInput(BaseModel):
    email: str
    password: str = Field(min_length=1)


class TaskInput(BaseModel):
    action: str
    version: int
    blocker_code: str | None = None
    note: str | None = None


class TransitionInput(BaseModel):
    to_state: str
    version: int
    reason: str | None = None


class ApprovalInput(BaseModel):
    decision: str
    version: int
    comment: str | None = None


class CaseInput(BaseModel):
    area_id: str = "KEN.3_1"
    area_name: str = "Bungoma"
    hazard: str = "drought"
    title: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)


class ExportInput(BaseModel):
    message: str | None = Field(default=None, max_length=3000)
    language: str = "en"


class AssistInput(BaseModel):
    report: str | None = Field(default=None, max_length=3000)


class KeyInput(BaseModel):
    label: str = Field(min_length=2, max_length=80)


class WebhookInput(BaseModel):
    url: str
    events: list[str]
    secret: str = Field(min_length=16, max_length=200)


class StopTriggerInput(BaseModel):
    case_id: str
    observed_probability: float = Field(default=0.22, ge=0, le=1)


class EvidenceInput(BaseModel):
    snapshot_ids: list[str] = Field(min_length=1)
    version: int | None = None


class SourceModeInput(BaseModel):
    mode: str


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="Linda Protocol API", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException):
    return JSONResponse(
        {"error": {"code": str(exc.status_code), "message": exc.detail if isinstance(exc.detail, str) else "Request failed", "detail": exc.detail}},
        status_code=exc.status_code,
    )


@app.exception_handler(RecordedVersionConflict)
async def version_conflict(_: Request, exc: RecordedVersionConflict):
    return JSONResponse(
        {"error": {
            "code": "VERSION_CONFLICT",
            "message": "This case changed. Reload before trying again.",
            "detail": {
                "supplied_version": exc.supplied_version,
                "current_version": exc.current_version,
            },
        }},
        status_code=status.HTTP_409_CONFLICT,
    )


@app.get("/healthz")
def health() -> dict[str, Any]:
    return {"status": "ok", "db": "ok", "mode": "exercise", "demo_mode": settings.demo_mode}


@app.post("/api/auth/login")
def login_route(payload: LoginInput, request: Request, response: Response) -> dict[str, Any]:
    return login(payload.email, payload.password, request, response)


@app.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout() -> Response:
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        "linda_session",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return response


@app.get("/api/me")
def me(user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    return user


@app.get("/api/sources/status")
def sources_status(_: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    with transaction() as conn:
        snapshots = refresh_all(conn)
        return {"mode": source_mode(conn), "sources": [{key: item[key] for key in ("id", "adapter", "endpoint_url", "retrieved_at", "payload_sha256", "schema_ok", "freshness", "meta")} for item in snapshots]}


@app.post("/api/sources/refresh")
def sources_refresh(_: dict[str, Any] = Depends(require_role("county_drm_officer", "ews_specialist", "admin"))) -> dict[str, Any]:
    with transaction() as conn:
        snapshots = refresh_all(conn, force=True)
        return {"mode": source_mode(conn), "snapshot_ids": [item["id"] for item in snapshots]}


@app.get("/api/sources/snapshots")
def source_snapshots(adapter: str | None = None, limit: int = Query(50, ge=1, le=100), _: dict[str, Any] = Depends(current_user)) -> list[dict[str, Any]]:
    with connection() as conn:
        return [{**item, "payload": {"available": True, "keys": list(item["payload"].keys())}} for item in list_snapshots(conn, adapter, limit)]


@app.get("/api/sources/snapshots/{snapshot_id}")
def source_snapshot(snapshot_id: str, _: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    with connection() as conn:
        try: return get_snapshot(conn, snapshot_id)
        except KeyError as exc: raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Source snapshot not found") from exc


@app.get("/api/signals")
def signal_inbox(_: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    with transaction() as conn: return signals(conn)


@app.get("/api/areas")
def areas(country: str | None = None, level: int | None = None, _: dict[str, Any] = Depends(current_user)) -> list[dict[str, Any]]:
    with transaction() as conn: return source_areas(conn, country, level)


@app.get("/api/cases")
def cases(state: str | None = None, area: str | None = None, _: dict[str, Any] = Depends(current_user)) -> list[dict[str, Any]]:
    with connection() as conn:
        query = "SELECT * FROM decision_cases"; clauses: list[str] = []; params: list[str] = []
        if state: clauses.append("state = ?"); params.append(state)
        if area: clauses.append("area_id = ?"); params.append(area)
        if clauses: query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY updated_at DESC"
        return [case_summary(get_case(conn, row["id"])) for row in conn.execute(query, params)]


@app.post("/api/cases", status_code=status.HTTP_201_CREATED)
def create_case_route(payload: CaseInput, user: dict[str, Any] = Depends(require_role("county_drm_officer"))) -> dict[str, Any]:
    with transaction() as conn: return create_case(conn, user, payload.area_id, payload.area_name, payload.hazard, payload.title, payload.evidence)


@app.get("/api/cases/{case_id}")
def case_detail(case_id: str, _: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    with connection() as conn: return get_case(conn, case_id)


@app.post("/api/cases/{case_id}/evidence")
def attach_evidence(case_id: str, payload: EvidenceInput, user: dict[str, Any] = Depends(require_role("county_drm_officer", "ews_specialist"))) -> dict[str, Any]:
    with transaction() as conn:
        try: snapshots = [get_snapshot(conn, snapshot_id) for snapshot_id in payload.snapshot_ids]
        except KeyError as exc: raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Source snapshot not found") from exc
        return attach_evidence_and_assess(conn, case_id, user, snapshots, payload.version)


@app.post("/api/cases/{case_id}/assess")
def assess(case_id: str, payload: EvidenceInput, user: dict[str, Any] = Depends(require_role("county_drm_officer"))) -> dict[str, Any]:
    with transaction() as conn:
        try: snapshots = [get_snapshot(conn, snapshot_id) for snapshot_id in payload.snapshot_ids]
        except KeyError as exc: raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Source snapshot not found") from exc
        return attach_evidence_and_assess(conn, case_id, user, snapshots, payload.version)


@app.post("/api/cases/{case_id}/tasks/{task_id}")
def task_mutation(case_id: str, task_id: str, payload: TaskInput, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    with transaction() as conn: return update_task(conn, case_id, task_id, user, payload.action, payload.version, payload.blocker_code, payload.note)


@app.post("/api/cases/{case_id}/transition")
def transition(case_id: str, payload: TransitionInput, background: BackgroundTasks, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    with transaction() as conn: case = transition_case(conn, case_id, user, payload.to_state, payload.version, payload.reason)
    if case["state"] == "REVOKED": background.add_task(deliver_webhooks_for_case, case_id, "activation.revoked")
    return case


@app.post("/api/cases/{case_id}/approvals")
def approval(case_id: str, payload: ApprovalInput, background: BackgroundTasks, user: dict[str, Any] = Depends(require_role("ews_specialist", "county_drm_officer", "ngo_finance_lead"))) -> dict[str, Any]:
    with transaction() as conn: case, became_approved = record_approval(conn, case_id, user, payload.decision, payload.comment, payload.version)
    if became_approved: background.add_task(deliver_webhooks_for_case, case_id, "activation.approved")
    return case


@app.get("/api/cases/{case_id}/approvals/verify")
def approval_verification(case_id: str, _: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    with connection() as conn: return verify_approvals(conn, case_id)


@app.get("/api/cases/{case_id}/events")
def events(case_id: str, _: dict[str, Any] = Depends(current_user)) -> list[dict[str, Any]]:
    with connection() as conn: return case_events(conn, case_id)


@app.get("/api/cases/{case_id}/events/verify")
def event_verification(case_id: str, _: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    with connection() as conn: return verify_event_chain(conn, case_id)


@app.post("/api/cases/{case_id}/assists/{assist_name}")
def assist(case_id: str, assist_name: str, payload: AssistInput, user: dict[str, Any] = Depends(require_role("ews_specialist", "county_drm_officer", "ngo_finance_lead"))) -> dict[str, Any]:
    # Do not hold a SQLite write transaction while waiting for Gemini. The
    # assist is read-only and its result cannot transition a case.
    with connection() as conn:
        case = get_case(conn, case_id)
    try:
        if assist_name == "matcher":
            result = asyncio.run(assists.run_matcher(case))
        elif assist_name == "explainer":
            result = asyncio.run(assists.run_explainer(case))
        elif assist_name == "blockers" and payload.report:
            result = asyncio.run(assists.run_blocker(payload.report))
        else:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Supported assists are explainer, matcher, and blockers; blockers requires report text")
    except assists.AssistUnavailable as exc:
        with transaction() as conn:
            append_event(conn, case_id, f"assist:{assist_name}", "ASSIST_FAILED", {"reason": str(exc)})
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, detail="Assist unavailable — deterministic workflow is unaffected") from exc
    with transaction() as conn:
        append_event(conn, case_id, f"assist:{assist_name}", "ASSIST_RAN", {"output": result})
    return result


@app.get("/api/assists/status")
def assist_availability(_: dict[str, Any] = Depends(current_user)) -> dict[str, Any]: return assists.assist_status()


@app.post("/api/cases/{case_id}/exports/{export_kind}")
def exports(case_id: str, export_kind: str, payload: ExportInput, user: dict[str, Any] = Depends(current_user)) -> dict[str, Any]:
    if export_kind in {"packet", "cap", "bundle"} and user["role"] != "county_drm_officer": raise HTTPException(status.HTTP_403_FORBIDDEN, detail="County DRM Officer role required")
    if export_kind == "husika" and user["role"] not in {"county_drm_officer", "ngo_finance_lead"}: raise HTTPException(status.HTTP_403_FORBIDDEN, detail="County DRM Officer or NGO & Finance Lead role required")
    try:
        with transaction() as conn:
            if export_kind == "packet": return {"exports": generate_packet(conn, case_id, user["id"])}
            if export_kind == "cap": return {"exports": [generate_cap(conn, case_id, user["id"])]}
            if export_kind == "husika": return {"exports": [generate_husika(conn, case_id, user["id"], payload.message, payload.language)]}
            if export_kind == "bundle": return {"exports": [generate_bundle(conn, case_id, user["id"])]}
            raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Unknown export kind")
    except ValueError as exc: raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@app.get("/api/exports/{export_id}/download")
def download(export_id: str, _: dict[str, Any] = Depends(current_user)) -> Response:
    with connection() as conn:
        try: record, payload = exported_payload(conn, export_id)
        except FileNotFoundError as exc: raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Export not found") from exc
    suffix = {"packet_pdf": "pdf", "cap_xml": "xml", "field_bundle": "zip", "packet_json": "json", "husika_payload": "json"}.get(record["kind"], "json")
    media_type = {"pdf": "application/pdf", "xml": "application/xml", "zip": "application/zip"}.get(suffix, "application/json")
    return Response(payload, media_type=media_type, headers={"Content-Disposition": f'attachment; filename="{record["id"]}.{suffix}"'})


@app.get("/api/library/policy")
def library_policy(_: dict[str, Any] = Depends(current_user)) -> dict[str, Any]: return policy()


@app.get("/api/library/actions")
def library_actions(_: dict[str, Any] = Depends(current_user)) -> list[dict[str, Any]]: return action_cards()


@app.get("/api/library/husika-contract")
def husika_contract(_: dict[str, Any] = Depends(current_user)) -> dict[str, Any]: return husika_contract_metadata()


@app.get("/api/audit")
def audit(case_id: str | None = None, event_type: str | None = None, actor: str | None = None, start: str | None = None, end: str | None = None, _: dict[str, Any] = Depends(current_user)) -> list[dict[str, Any]]:
    with connection() as conn:
        query = "SELECT * FROM case_events"; clauses: list[str] = []; params: list[str] = []
        if case_id: clauses.append("case_id = ?"); params.append(case_id)
        if event_type: clauses.append("event_type = ?"); params.append(event_type)
        if actor: clauses.append("actor_id = ?"); params.append(actor)
        if start: clauses.append("created_at >= ?"); params.append(start)
        if end: clauses.append("created_at <= ?"); params.append(end)
        if clauses: query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY seq DESC"
        from .domain import loads
        return [{**dict(row), "data": loads(row["data"], {})} for row in conn.execute(query, params)]


@app.get("/api/admin/integration-keys")
def get_keys(_: dict[str, Any] = Depends(require_role("admin"))) -> list[dict[str, Any]]:
    with connection() as conn: return list_keys(conn)


@app.post("/api/admin/integration-keys", status_code=201)
def post_key(payload: KeyInput, _: dict[str, Any] = Depends(require_role("admin"))) -> dict[str, Any]:
    with transaction() as conn: return create_key(conn, payload.label)


@app.delete("/api/admin/integration-keys/{key_id}", status_code=204)
def delete_key(key_id: str, _: dict[str, Any] = Depends(require_role("admin"))) -> Response:
    with transaction() as conn: revoke_key(conn, key_id)
    return Response(status_code=204)


@app.get("/api/admin/webhooks")
@app.get("/integration/v1/webhooks")
def get_webhooks(_: dict[str, Any] = Depends(require_role("admin"))) -> list[dict[str, Any]]:
    with connection() as conn: return list_webhooks(conn)


@app.post("/api/admin/webhooks", status_code=201)
@app.post("/integration/v1/webhooks", status_code=201)
def post_webhook(payload: WebhookInput, _: dict[str, Any] = Depends(require_role("admin"))) -> dict[str, Any]:
    with transaction() as conn: return create_webhook(conn, payload.url, payload.events, payload.secret)


@app.delete("/api/admin/webhooks/{webhook_id}", status_code=204)
@app.delete("/integration/v1/webhooks/{webhook_id}", status_code=204)
def remove_webhook(webhook_id: str, _: dict[str, Any] = Depends(require_role("admin"))) -> Response:
    with transaction() as conn: delete_webhook(conn, webhook_id)
    return Response(status_code=204)


@app.post("/api/admin/seed")
def seed(_: dict[str, Any] = Depends(require_role("admin"))) -> dict[str, str]: reset_demo(); return {"status": "seeded"}


@app.post("/api/admin/replay-mode")
def replay_mode(payload: SourceModeInput, _: dict[str, Any] = Depends(require_role("admin"))) -> dict[str, str]:
    try:
        with transaction() as conn: return {"mode": set_source_mode(conn, payload.mode)}
    except ValueError as exc: raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)) from exc


@app.post("/api/admin/simulate-stop-trigger")
def simulate_stop_trigger(payload: StopTriggerInput, background: BackgroundTasks, _: dict[str, Any] = Depends(require_role("admin"))) -> dict[str, Any]:
    with transaction() as conn:
        case = revoke_for_stop_trigger(conn, payload.case_id, payload.observed_probability)
    background.add_task(deliver_webhooks_for_case, payload.case_id, "activation.revoked")
    return case


@app.get("/api/cases/{case_id}/webhook-deliveries")
def case_webhook_deliveries(case_id: str, _: dict[str, Any] = Depends(current_user)) -> list[dict[str, Any]]:
    with connection() as conn:
        get_case(conn, case_id)
        return delivery_statuses(conn, case_id)


@app.get("/cap/feed.xml")
def cap_feed() -> Response:
    with connection() as conn: return Response(published_cap_feed(conn), media_type="application/atom+xml")


def _partner_auth(request: Request) -> dict[str, Any]:
    with connection() as conn: return require_partner_key(request, conn)


@app.get("/integration/v1/activations")
def integration_activations(request: Request, since: str | None = None, area: str | None = None, hazard: str | None = None, state: str | None = None, limit: int = Query(50, ge=1, le=100), cursor: str | None = None) -> dict[str, Any]:
    with connection() as conn: require_partner_key(request, conn); return list_activations(conn, since=since, area=area, hazard=hazard, state=state, limit=limit, cursor=cursor)


@app.get("/integration/v1/activations/{case_id}")
def integration_activation(case_id: str, request: Request) -> dict[str, Any]:
    with connection() as conn: require_partner_key(request, conn); return activation_record(conn, case_id)


@app.get("/integration/v1/activations/{case_id}/cap.xml")
def integration_cap(case_id: str, request: Request) -> Response:
    with connection() as conn:
        require_partner_key(request, conn); case = get_case(conn, case_id)
        return Response(cap_xml(case, case["state"] == "REVOKED"), media_type="application/xml")


@app.get("/integration/v1/activations/{case_id}/husika-payload.json")
def integration_husika(case_id: str, request: Request) -> dict[str, Any]:
    with connection() as conn: require_partner_key(request, conn); return husika_payload(get_case(conn, case_id))


@app.get("/integration/v1/activations/{case_id}/verify")
def integration_verify(case_id: str, request: Request) -> dict[str, Any]:
    with connection() as conn: require_partner_key(request, conn); return verify_activation(conn, case_id)


@app.get("/integration/v1/openapi.json")
def integration_openapi() -> dict[str, Any]:
    schema = app.openapi()
    schema["paths"] = {path: value for path, value in schema["paths"].items() if path.startswith("/integration/") or path == "/cap/feed.xml"}
    return schema


@app.get("/integration/v1/schemas/activation.json")
def integration_activation_schema() -> dict[str, Any]:
    path = Path(CONTENT_ROOT) / "schemas" / "integration" / "activation.v1.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


@app.get("/integration/v1/docs", response_class=HTMLResponse)
def integration_docs() -> str:
    return """<!doctype html><html lang='en'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>Linda Protocol Integration API</title><style>body{margin:0;background:#f6f8f5;color:#17251a;font:16px/1.55 system-ui,sans-serif}main{max-width:980px;margin:auto;padding:48px 24px}h1,h2{line-height:1.15}h1{font-size:2.4rem}section{background:#fff;border:1px solid #d7e0d8;border-radius:12px;padding:24px;margin:20px 0}code,pre{font-family:ui-monospace,SFMono-Regular,Menlo,monospace}code{background:#edf3ee;padding:2px 5px;border-radius:4px}pre{background:#17251a;color:#f6fff7;padding:16px;border-radius:8px;overflow:auto}.badge{display:inline-block;background:#dcefe0;color:#125c26;border-radius:99px;padding:4px 9px;font-weight:700;font-size:.8rem}.method{color:#125c26;font-weight:800}a{color:#075eaa}</style></head><body><main><span class='badge'>Integration API · v1</span><h1>Linda Protocol partner API</h1><p>Read approved and revoked activation records, their provenance, approvals, exports, and verification results. This boundary is read-only: people make decisions inside Linda; partners consume verifiable records.</p><section><h2>Quick start</h2><p>Create an API key in the Linda Admin workspace, then call the activation collection with a bearer token. Public documentation, schema, and CAP feed require no key.</p><pre>curl --request GET /integration/v1/activations?state=APPROVED \\\n  --header 'Authorization: Bearer linda_your_api_key'</pre><p>Limits are 60 requests per minute per key. Use the opaque <code>next</code> cursor from a response for pagination.</p></section><section><h2>Endpoints</h2><ul><li><span class='method'>GET</span> <code>/cap/feed.xml</code> — public CAP 1.2 Atom feed.</li><li><span class='method'>GET</span> <code>/integration/v1/openapi.json</code> — public OpenAPI contract.</li><li><span class='method'>GET</span> <code>/integration/v1/schemas/activation.json</code> — public activation JSON Schema.</li><li><span class='method'>GET</span> <code>/integration/v1/activations</code> — API key; paginated approved/revoked records.</li><li><span class='method'>GET</span> <code>/integration/v1/activations/{id}</code> — API key; full activation record.</li><li><span class='method'>GET</span> <code>/integration/v1/activations/{id}/cap.xml</code>, <code>/husika-payload.json</code>, <code>/verify</code> — API key; export and verification views.</li></ul></section><section><h2>Webhooks and verification</h2><p>Administrators may register an HTTPS webhook for <code>activation.approved</code> and <code>activation.revoked</code>. Deliveries include <code>X-Linda-Event</code>, <code>X-Linda-Delivery</code>, and <code>X-Linda-Signature: sha256=&lt;HMAC&gt;</code> over the raw JSON body. Use the verification endpoint to recompute the event chain, approvals, and manifest hash.</p></section><section><h2>Exercise status</h2><p>Every response carries <code>mode: exercise</code> and a disclaimer. Linda validates Husika-compatible payloads but does not dispatch alerts, move funds, or claim a partner has adopted this API. Breaking changes will use <code>/v2</code>.</p><p><a href='/integration/v1/openapi.json'>Open OpenAPI JSON</a> · <a href='/cap/feed.xml'>Open CAP feed</a> · <a href='/integration/v1/schemas/activation.json'>Open activation schema</a></p></section></main></body></html>"""


static_root = Path("/app/static")
if static_root.is_dir():
    app.mount("/", StaticFiles(directory=static_root, html=True), name="web")
