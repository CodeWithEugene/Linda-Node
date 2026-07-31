# Linda Protocol API

The FastAPI service owns the exercise workflow: authentication, source snapshots, deterministic policy assessment, readiness tasks, multi-role approvals, audit events, exports, and the partner-facing integration API.

## Run locally

```bash
cd server/backend
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
cp .env.example .env
.venv/bin/uvicorn app.main:app --reload --port 8001
```

The service listens on `http://127.0.0.1:8001`; internal interactive API documentation is at `http://127.0.0.1:8001/docs`.

WeasyPrint needs native Pango and Cairo libraries to render PDF packets. The Docker image installs them. For a macOS development environment, install Homebrew packages and set `DYLD_FALLBACK_LIBRARY_PATH` as described in the root README.

## Vercel deployment

Set the Vercel project's root directory to `server/backend`. The `api/index.py` module exports the FastAPI application for Vercel Functions; `vercel.json` routes the API, CAP, integration, and health paths to it. In production, use Neon Postgres through `DATABASE_URL` and private Vercel Blob through `LINDA_BLOB_READ_WRITE_TOKEN`; do not use the function filesystem for workflow state or exports.

Set `LINDA_SECRET`, `COOKIE_SECURE=true`, `PUBLIC_BASE_URL=https://linda-protocol.vercel.app`, and `CORS_ORIGINS=https://linda-protocol.vercel.app`. The supplied `Dockerfile.vercel` is an alternative for a container-based Vercel deployment. PDF packet generation uses WeasyPrint when its native libraries are available and a portable ReportLab renderer otherwise.

## Demo data

With `DEMO_MODE=true`, the API seeds fictional users and a Bungoma case at `ASSESSED` with a critical transport blocker. Every persona uses password `linda-demo`.

| Email | Role |
|---|---|
| `amina.ews@demo` | EWS Specialist |
| `david.drm@demo` | County DRM Officer |
| `grace.ngo@demo` | NGO & Finance Lead |
| `observer@demo` | Read-only observer |
| `admin@demo` | Demo recovery, source-mode, partner-key, and webhook administrator |

The demo also seeds replay snapshots for triggers, forecasts, and areas. An administrator can restore the scenario with `POST /api/admin/seed` or switch between `live_first` and `replay_only` with `POST /api/admin/replay-mode`.

## Key API groups

| Route group | Purpose |
|---|---|
| `/api/auth/*`, `/api/me` | Cookie-session authentication and current identity. |
| `/api/sources/*`, `/api/signals`, `/api/areas` | Source status, immutable snapshots, refresh, signal inbox, and area records. |
| `/api/cases/*` | Case creation, assessment, evidence attachment, tasks, transitions, approvals, assists, exports, and audit verification. |
| `/api/library/*` | Read-only policy, action-card, and Husika-contract material. |
| `/api/admin/*` | Demo recovery, source mode, integration keys, and webhooks. |
| `/integration/v1/*` | Versioned, read-only partner records and integrity verification. |
| `/cap/feed.xml` | Public Exercise CAP Atom feed. |

Errors use the shape `{"error": {"code", "message", "detail"}}`. Case mutations require the current case version and return HTTP 409 for stale writes.

## Source and assessment behaviour

Each source response is stored with raw JSON, retrieval time, SHA-256, validation state, and freshness. The source adapter supports live-first retrieval with cached, stale, or replay fallback. The deterministic policy engine evaluates only persisted snapshots and versioned action-card YAML. It does not use Gemini.

When new evidence re-assesses a case, existing approvals are retained but marked superseded. The case returns to `ASSESSED` and must be reviewed and signed again.

## Integration contract

`GET /integration/v1/docs` describes the public partner surface. API-key-protected activation records include provenance, approvals, exports, and integrity verification. CAP documents, Husika payloads, and all partner responses are labelled `Exercise`.

Husika payloads are validated locally against `fixtures/husika_openapi/ingestor.openapi.json`. The API does not call Husika write endpoints.

## Verify

```bash
cd server/backend
.venv/bin/ruff check app tests
.venv/bin/pytest -q
```

The test suite covers workflow guards, exports, partner verification, source-backed assessment, reassessment, and constrained-assist validation.
