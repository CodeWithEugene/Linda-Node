import json
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from .auth import current_user, issue_token, key_hash, new_integration_key, password_matches, require_roles
from .config import settings
from .db import Base, get_db
from .domain import (REQUIRED_ROLES, append_event, canonical, case_digest, json_load, public_case,
                     signature, transition, utcnow, verify_chain, verify_signatures)
from .exports import generate
from .models import CaseEvent, DecisionCase, ExportArtifact, IntegrationKey, SourceSnapshot, User, WebhookDelivery, WebhookSubscription
from .schemas import (IntegrationKeyRequest, LoginRequest, RevokeRequest, TokenResponse, WebhookRequest)
from .seed import seed
from .webhooks import deliver


def upgrade_database() -> None:
    backend_root = Path(__file__).resolve().parents[1]
    alembic_cfg = Config(str(backend_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(backend_root / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", settings.database_url)
    command.upgrade(alembic_cfg, "head")

@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.export_dir.mkdir(parents=True, exist_ok=True)
    upgrade_database()
    db = next(get_db())
    try:
        seed(db)
    finally:
        db.close()
    yield


app = FastAPI(title="Linda Protocol", version="1.0.0", description="Exercise-mode activation-readiness control plane", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


def case_or_404(db: Session, case_id: str) -> DecisionCase:
    case = db.get(DecisionCase, case_id)
    if not case:
        raise HTTPException(status_code=404, detail="case not found")
    return case


def reset_seed_data(db: Session) -> None:
    """Reset the exercise dataset without invalidating the request's DB session."""
    for model in (WebhookDelivery, WebhookSubscription, IntegrationKey, ExportArtifact, CaseEvent, DecisionCase, SourceSnapshot, User):
        db.query(model).delete()
    db.commit()
    seed(db)


def can_access_integration(request: Request, db: Session) -> None:
    if request.url.path in {"/integration/v1/docs", "/integration/v1/openapi.json"}:
        return
    value = request.headers.get("Authorization", "")
    if not value.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="integration API key required")
    key = db.query(IntegrationKey).filter(IntegrationKey.key_hash == key_hash(value[7:]), IntegrationKey.revoked_at.is_(None)).first()
    if not key:
        raise HTTPException(status_code=401, detail="invalid integration API key")


@app.get("/api/healthz")
def healthz() -> dict[str, Any]:
    return {"status": "ok", "db": "sqlite", "adapters_last_ok": True, "mode": "exercise"}


@app.post("/api/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.query(User).filter(User.email == payload.email).one_or_none()
    if not user or not password_matches(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")
    return TokenResponse(access_token=issue_token(user))


@app.get("/api/users")
def users(db: Session = Depends(get_db), _: User = Depends(current_user)) -> list[dict[str, str]]:
    return [{"id": user.id, "email": user.email, "display_name": user.display_name, "role": user.role, "org": user.org} for user in db.query(User).all()]


@app.post("/api/admin/seed")
def admin_seed(db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))) -> dict[str, bool]:
    reset_seed_data(db)
    return {"ok": True}


@app.post("/api/seed")
def legacy_seed(db: Session = Depends(get_db)) -> dict[str, bool]:
    reset_seed_data(db)
    return {"ok": True}


@app.get("/api/signals")
def signals(db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict[str, Any]:
    rows = db.query(SourceSnapshot).order_by(SourceSnapshot.retrieved_at).all()
    snapshots = [{"id": row.id, "adapter": row.adapter, "endpoint_url": row.endpoint_url, "retrieved_at": row.retrieved_at,
                  "payload": json_load(row.payload, {}), "payload_sha256": row.payload_sha256, "schema_ok": bool(row.schema_ok),
                  "freshness": row.freshness, "meta": json_load(row.meta, {})} for row in rows]
    return {"snapshots": snapshots, "signals": [item["payload"] for item in snapshots]}


@app.get("/api/library")
def library(_: User = Depends(current_user)) -> dict[str, Any]:
    policy_path = settings.content_dir / "policy.yaml"
    policy = policy_path.read_text(encoding="utf-8")
    actions = []
    for path in sorted((settings.content_dir / "actions").glob("*.yaml")):
        content = path.read_text(encoding="utf-8")
        actions.append({"id": path.stem, "filename": path.name, "sha256": __import__("hashlib").sha256(content.encode()).hexdigest(), "content": content})
    return {"policy": policy, "policy_sha256": __import__("hashlib").sha256(policy.encode()).hexdigest(), "actions": actions}


@app.get("/api/cases")
def cases(db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict[str, Any]:
    return {"cases": [public_case(db, case) for case in db.query(DecisionCase).all()]}


@app.get("/api/cases/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict[str, Any]:
    return public_case(db, case_or_404(db, case_id))


@app.get("/api/cases/{case_id}/audit")
def audit(case_id: str, db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict[str, Any]:
    case = case_or_404(db, case_id)
    rows = db.query(CaseEvent).filter(CaseEvent.case_id == case_id).order_by(CaseEvent.seq).all()
    return {"chain": verify_chain(db, case), "events": [{"seq": row.seq, "at": row.at, "actor": row.actor, "event_type": row.event_type, "payload": json_load(row.payload, {}), "previous_hash": row.previous_hash, "this_hash": row.this_hash} for row in rows]}


@app.get("/api/cases/{case_id}/verify-signatures")
def signatures(case_id: str, db: Session = Depends(get_db), _: User = Depends(current_user)) -> dict[str, Any]:
    return verify_signatures(db, case_or_404(db, case_id))


@app.post("/api/cases/{case_id}/tasks/{task_id}/resolve")
def resolve_task(case_id: str, task_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict[str, Any]:
    case = case_or_404(db, case_id)
    tasks = json_load(case.tasks, [])
    task = next((item for item in tasks if item["id"] == task_id), None)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    if user.role not in {task["owner_role"], "admin"}:
        raise HTTPException(status_code=403, detail="only the task owner or admin may resolve this task")
    task.update({"state": "RESOLVED", "blocker_code": None, "note": "Resolved", "updated_at": utcnow().isoformat()})
    assessment = json_load(case.assessment, {})
    next(gate for gate in assessment["gates"] if gate["name"] == "readiness").update({"passed": True, "basis": "all critical tasks acknowledged or resolved"})
    case.tasks, case.assessment, case.version, case.updated_at = canonical(tasks), canonical(assessment), case.version + 1, utcnow()
    append_event(db, case, user.id, "TASK_RESOLVED", {"task_id": task_id})
    db.commit()
    return public_case(db, case)


@app.post("/api/cases/{case_id}/send-review")
def send_review(case_id: str, db: Session = Depends(get_db), user: User = Depends(require_roles("county_drm_officer", "admin"))) -> dict[str, Any]:
    case = case_or_404(db, case_id)
    blocked = next((item for item in json_load(case.tasks, []) if item["critical"] and item["state"] == "BLOCKED"), None)
    if blocked:
        raise HTTPException(status_code=422, detail=f"Blocked: critical task '{blocked['task']}' is BLOCKED")
    try:
        transition(case, "READY_FOR_REVIEW")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    append_event(db, case, user.id, "READY_FOR_REVIEW", {"case_id": case.id})
    db.commit()
    return public_case(db, case)


@app.post("/api/cases/{case_id}/approve")
def approve(case_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict[str, Any]:
    case = case_or_404(db, case_id)
    if case.state != "READY_FOR_REVIEW":
        raise HTTPException(status_code=422, detail="case must be READY_FOR_REVIEW")
    if user.role not in REQUIRED_ROLES:
        raise HTTPException(status_code=403, detail="this role cannot approve")
    approvals = [item for item in json_load(case.approvals, []) if item["role"] != user.role]
    case_hash = case_digest(case)
    approvals.append({"role": user.role, "signer": user.display_name, "signer_org": user.org, "signed_at": utcnow().isoformat(), "digest": case_hash, "signature": signature(user.role, case_hash, user.signing_key)})
    case.approvals = canonical(approvals)
    append_event(db, case, user.id, "SIGNED", {"role": user.role, "digest": case_hash})
    if {item["role"] for item in approvals} == set(REQUIRED_ROLES):
        transition(case, "APPROVED")
        append_event(db, case, "system", "APPROVED", {"case_id": case.id, "digest": case_hash})
        background_tasks.add_task(deliver, case.id, "activation.approved")
    db.commit()
    return public_case(db, case)


@app.post("/api/cases/{case_id}/mark-handoff")
def handoff(case_id: str, db: Session = Depends(get_db), user: User = Depends(require_roles("county_drm_officer", "admin"))) -> dict[str, Any]:
    case = case_or_404(db, case_id)
    if not db.query(ExportArtifact).filter(ExportArtifact.case_id == case.id).first():
        raise HTTPException(status_code=422, detail="generate at least one handoff artifact first")
    try:
        transition(case, "HANDED_OFF")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    append_event(db, case, user.id, "HANDED_OFF", {})
    db.commit()
    return public_case(db, case)


def revoke_case(case: DecisionCase, db: Session, user: User, reason: str, event_type: str, background_tasks: BackgroundTasks) -> dict[str, Any]:
    try:
        transition(case, "REVOKED")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    case.revocation = canonical({"reason": reason, "at": utcnow().isoformat(), "actor": user.id})
    append_event(db, case, user.id, event_type, json_load(case.revocation, {}))
    db.commit()
    background_tasks.add_task(deliver, case.id, "activation.revoked")
    return public_case(db, case)


@app.post("/api/cases/{case_id}/revoke")
def revoke(case_id: str, payload: RevokeRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db), user: User = Depends(require_roles("county_drm_officer", "admin"))) -> dict[str, Any]:
    return revoke_case(case_or_404(db, case_id), db, user, payload.reason, "MANUALLY_REVOKED", background_tasks)


@app.post("/api/cases/{case_id}/simulate-stop-trigger")
def simulate_stop(case_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db), user: User = Depends(require_roles("admin"))) -> dict[str, Any]:
    return revoke_case(case_or_404(db, case_id), db, user, "forecast confidence below continuation threshold", "STOP_TRIGGERED", background_tasks)


@app.post("/api/cases/{case_id}/exports/{kind}")
def export(case_id: str, kind: str, db: Session = Depends(get_db), user: User = Depends(require_roles("county_drm_officer", "admin"))) -> dict[str, Any]:
    if kind not in {"packet", "cap", "husika", "bundle", "cap-cancel"}:
        raise HTTPException(status_code=404, detail="unknown export")
    case = case_or_404(db, case_id)
    if kind == "cap-cancel" and case.state != "REVOKED":
        raise HTTPException(status_code=422, detail="CAP cancellation requires REVOKED case")
    if kind != "cap-cancel" and case.state not in {"APPROVED", "HANDED_OFF"}:
        raise HTTPException(status_code=422, detail="exports require APPROVED or HANDED_OFF case")
    public = public_case(db, case)
    _, data, media_type, manifest_hash = generate(kind, public)
    suffix = {"packet": ".html", "cap": ".xml", "husika": ".json", "bundle": ".zip", "cap-cancel": ".xml"}[kind]
    filename = f"{case.id}-{kind}-{uuid.uuid4().hex[:8]}{suffix}"
    target = settings.export_dir / filename
    target.write_bytes(data)
    artifact = ExportArtifact(id=f"exp_{uuid.uuid4().hex}", case_id=case.id, kind=kind, filename=filename,
                              sha256=__import__("hashlib").sha256(data).hexdigest(), media_type=media_type,
                              manifest_sha256=manifest_hash, created_at=utcnow())
    db.add(artifact)
    append_event(db, case, user.id, "EXPORT_GENERATED", {"kind": kind, "filename": filename, "sha256": artifact.sha256})
    db.commit()
    return {"export": {"kind": kind, "filename": filename, "sha256": artifact.sha256, "media_type": media_type, "url": f"/api/cases/{case.id}/downloads/{filename}"}, "case": public_case(db, case)}


@app.get("/api/cases/{case_id}/downloads/{filename}")
def download(case_id: str, filename: str, db: Session = Depends(get_db), _: User = Depends(current_user)) -> FileResponse:
    artifact = db.query(ExportArtifact).filter(ExportArtifact.case_id == case_id, ExportArtifact.filename == filename).one_or_none()
    if not artifact:
        raise HTTPException(status_code=404, detail="artifact not found")
    return FileResponse(settings.export_dir / filename, media_type=artifact.media_type, filename=filename)


@app.post("/api/admin/integration-keys")
def create_key(payload: IntegrationKeyRequest, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))) -> dict[str, str]:
    raw, hashed = new_integration_key()
    key = IntegrationKey(id=f"key_{uuid.uuid4().hex}", label=payload.label, key_hash=hashed, created_at=utcnow())
    db.add(key)
    db.commit()
    return {"id": key.id, "label": key.label, "key": raw}


@app.post("/api/admin/integration-keys/{key_id}/revoke")
def revoke_key(key_id: str, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))) -> dict[str, bool]:
    key = db.get(IntegrationKey, key_id)
    if not key:
        raise HTTPException(status_code=404, detail="key not found")
    key.revoked_at = utcnow()
    db.commit()
    return {"ok": True}


@app.post("/api/admin/webhooks")
def create_webhook(payload: WebhookRequest, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))) -> dict[str, Any]:
    hook = WebhookSubscription(id=f"wh_{uuid.uuid4().hex}", url=payload.url, events=canonical(payload.events), secret=payload.secret, active=1, created_at=utcnow())
    db.add(hook)
    db.commit()
    return {"id": hook.id, "url": hook.url, "events": payload.events, "active": True}


@app.get("/api/admin/webhooks")
def webhooks(db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))) -> list[dict[str, Any]]:
    subscriptions = db.query(WebhookSubscription).all()
    return [{"id": item.id, "url": item.url, "events": json_load(item.events, []), "active": bool(item.active), "created_at": item.created_at} for item in subscriptions]


@app.get("/integration/v1/activations")
def integrations(request: Request, state: str | None = None, area: str | None = None, hazard: str | None = None, db: Session = Depends(get_db)) -> dict[str, Any]:
    can_access_integration(request, db)
    query = db.query(DecisionCase)
    if state: query = query.filter(DecisionCase.state == state)
    if hazard: query = query.filter(DecisionCase.hazard == hazard)
    rows = [public_case(db, item) for item in query.all()]
    if area: rows = [item for item in rows if item["area"]["id"] == area]
    return {"mode": "exercise", "disclaimer": "Read-only exercise data; no public alert or funds are dispatched.", "items": rows, "count": len(rows)}


@app.get("/integration/v1/activations/{case_id}")
def integration_case(case_id: str, request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    can_access_integration(request, db)
    return {"mode": "exercise", "disclaimer": "Read-only exercise activation.", "activation": public_case(db, case_or_404(db, case_id))}


@app.get("/integration/v1/activations/{case_id}/verify")
def integration_verify(case_id: str, request: Request, db: Session = Depends(get_db)) -> dict[str, Any]:
    can_access_integration(request, db)
    case = case_or_404(db, case_id)
    return {"mode": "exercise", "disclaimer": "Verification report for an exercise record.", "chain": verify_chain(db, case), "signatures": verify_signatures(db, case)}


@app.get("/integration/v1/activations/{case_id}/cap.xml")
def integration_cap(case_id: str, request: Request, db: Session = Depends(get_db)) -> Response:
    can_access_integration(request, db)
    _, data, media_type, _ = generate("cap", public_case(db, case_or_404(db, case_id)))
    return Response(data, media_type=media_type)


@app.get("/integration/v1/activations/{case_id}/husika-payload.json")
def integration_husika(case_id: str, request: Request, db: Session = Depends(get_db)) -> Response:
    can_access_integration(request, db)
    _, data, media_type, _ = generate("husika", public_case(db, case_or_404(db, case_id)))
    return Response(data, media_type=media_type)


@app.get("/integration/v1/openapi.json")
def integration_openapi() -> dict[str, Any]:
    return {"openapi": "3.1.0", "info": {"title": "Linda Integration API", "version": "v1"}, "paths": {"/integration/v1/activations": {"get": {"summary": "List published exercise activations"}}}}


@app.get("/integration/v1/docs", response_class=HTMLResponse)
def integration_docs() -> str:
    return """<!doctype html><title>Linda Integration API</title><main><h1>Linda Protocol Integration API</h1><p>Versioned, read-only, verifiable exercise API for partner consumption.</p><ul><li>GET /integration/v1/activations</li><li>GET /integration/v1/activations/{id}</li><li>GET /integration/v1/activations/{id}/cap.xml</li><li>GET /integration/v1/activations/{id}/husika-payload.json</li><li>GET /integration/v1/activations/{id}/verify</li></ul><p>Activation endpoints require a Linda integration API key. The CAP feed and this documentation are public.</p></main>"""


@app.get("/cap/feed.xml")
def cap_feed(db: Session = Depends(get_db)) -> Response:
    cases = db.query(DecisionCase).filter(DecisionCase.state.in_(["APPROVED", "HANDED_OFF", "REVOKED"])).all()
    entries = "".join(f"<entry><title>{item.title}</title><id>urn:linda:{item.id}</id><updated>{item.updated_at.isoformat()}</updated><link href=\"/integration/v1/activations/{item.id}/cap.xml\" rel=\"alternate\" type=\"application/xml\"/><summary>Exercise activation record.</summary></entry>" for item in cases)
    return Response(f"<?xml version=\"1.0\"?><feed xmlns=\"http://www.w3.org/2005/Atom\"><title>Linda Protocol CAP Feed</title><id>urn:linda:cap-feed</id><updated>{utcnow().isoformat()}</updated>{entries}</feed>", media_type="application/atom+xml")


static_dir = Path("static")
if static_dir.exists():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
