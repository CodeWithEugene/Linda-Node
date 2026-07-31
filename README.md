# Linda Protocol

Linda Protocol is an exercise-only, human-governed workspace for turning early-warning evidence into a reviewable activation-readiness decision. It helps disaster-risk teams answer four practical questions: what evidence supports action, which pre-agreed actions are ready, who must approve, and what still blocks delivery.

It is deliberately not an alert-delivery system, a fund-disbursement system, or an autonomous decision-maker. Every public artifact is labelled **Exercise**. Linda never sends an alert through Husika and never moves money.

## What it does

- Captures source snapshots with retrieval time, SHA-256 hash, validation state, and a clear live, cached, stale, or replay label.
- Creates a decision case for an administrative area and evaluates a versioned YAML policy in deterministic code.
- Materialises readiness tasks from approved action cards and prevents review when a critical task is unresolved.
- Records three distinct role approvals using HMAC-SHA256 over a canonical case snapshot.
- Produces immutable decision artifacts: a PDF/JSON packet, CAP 1.2 XML, Husika-shaped JSON validated against a vendored OpenAPI snapshot, and an offline ZIP bundle.
- Exposes approved or revoked activations through a documented, read-only partner API and signed webhooks.
- Offers constrained Gemini assists for explaining evidence, ranking already-eligible action cards, and structuring blocker reports. Assists cannot change policy, tasks, approvals, or case state.

## Product flow

```text
ICPAC source or replay fixture
        │  snapshot + hash + freshness
        ▼
Deterministic policy assessment
        │
        ▼
Readiness tasks and blockers ──► three-role approval
        │                                │
        └──────────────► immutable exports and partner-ready handoff
```

The demo policy and action cards are illustrative. They are not official ICPAC, county-government, or financing-partner policy.

## Quick start

Requirements:

- Python 3.12 or newer
- Node.js 20 or newer
- Native Pango/Cairo libraries for local PDF generation, or Docker for the packaged environment

### 1. Start the API

```bash
cd server/backend
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
cp .env.example .env
.venv/bin/uvicorn app.main:app --reload --port 8001
```

On macOS with Homebrew, install the PDF-rendering libraries if WeasyPrint cannot start:

```bash
brew install pango cairo gdk-pixbuf
export DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix pango)/lib:$(brew --prefix glib)/lib:$(brew --prefix cairo)/lib:$(brew --prefix gdk-pixbuf)/lib"
```

### 2. Start the web client

In a second terminal:

```bash
cd client/frontend
npm ci
npm run dev
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173). Vite proxies `/api`, `/cap`, and `/integration` to `http://127.0.0.1:8001`. Set `LINDA_API_ORIGIN` before starting Vite to use another API origin.

### One-container demo

For a packaged local environment, copy `server/backend/.env.example` to `server/backend/.env`, set a real `LINDA_SECRET`, then run:

```bash
docker compose up --build
```

The container serves the web client and API at `http://localhost:8000`. The `linda-data` volume retains SQLite data and generated exports.

## Demo walkthrough

All seeded personas use the password `linda-demo`.

| Persona | Role | Use in the walkthrough |
|---|---|---|
| `david.drm@demo` | County DRM Officer | Sends a ready case for review, marks it handed off, or revokes it. |
| `grace.ngo@demo` | NGO & Finance Lead | Resolves the seeded transport blocker and co-signs. |
| `amina.ews@demo` | EWS Specialist | Co-signs the evidence record. |
| `observer@demo` | Read-only observer | Inspects the workflow without mutating it. |
| `admin@demo` | Administrator | Restores demo data, manages API keys and webhooks, and switches source mode. |

1. Sign in as David and open **Decision Cases**.
2. Open the seeded Bungoma case. The case starts at `ASSESSED` with a critical transport blocker.
3. Sign in as Grace and resolve the transport task under **Actions & Readiness**.
4. Sign in as David and send the case for review.
5. Sign in as Amina, David, and Grace in turn to record the three approvals.
6. Return as David to generate exports, mark the case handed off, or demonstrate revocation.

For a new case, begin in **Signal Inbox**. Open a source record, create a case, and review the deterministic assessment in the **Evidence** tab. Demo fixtures keep this flow available when an upstream public endpoint is unavailable.

## Architecture and trust boundaries

| Component | Responsibility |
|---|---|
| `client/frontend` | React, TypeScript, and Material UI single-page application. |
| `server/backend` | FastAPI service, SQLite persistence, policy evaluation, exports, and partner API. |
| Source adapter | Retrieves or replays source data, preserves raw snapshots, and exposes freshness/provenance. |
| Policy and action library | Versioned YAML inputs used by deterministic assessment logic. |
| Audit chain | Append-only case events linked by SHA-256 hashes. |
| Partner surface | CAP feed, versioned read API, verification report, API keys, and signed outbound webhooks. |

The source adapter defaults to `live_first`, but the demo seed includes replay snapshots. Cached, stale, and replay data are intentionally never presented as live.

## Integration surfaces

The following public endpoints are available without a partner key:

- `GET /healthz`
- `GET /cap/feed.xml`
- `GET /integration/v1/openapi.json`
- `GET /integration/v1/docs`
- `GET /integration/v1/schemas/activation.json`

Partner activation records require a bearer key created by an administrator:

```text
GET /integration/v1/activations
GET /integration/v1/activations/{id}
GET /integration/v1/activations/{id}/cap.xml
GET /integration/v1/activations/{id}/husika-payload.json
GET /integration/v1/activations/{id}/verify
```

Webhook subscriptions are administrator-managed. Deliveries include `X-Linda-Event`, `X-Linda-Delivery`, and an HMAC `X-Linda-Signature` over the raw request body.

## Configuration

Copy [`server/backend/.env.example`](server/backend/.env.example) to `server/backend/.env`. Important settings include:

| Variable | Purpose |
|---|---|
| `LINDA_SECRET` | Required secret for signed login sessions. |
| `DATABASE_URL` | SQLite database URL; defaults to `sqlite:///var/linda.db`. |
| `DEMO_MODE` | Enables replay fallback and demo seed behaviour. |
| `ICPAC_BASE` | Base URL for public ICPAC source requests. |
| `SNAPSHOT_TTL_MIN` | Cache lifetime before the source adapter refreshes a snapshot. |
| `GEMINI_API_KEY` | Optional. When absent, assist controls are disabled and the workflow still works. |
| `CORS_ORIGINS` | Comma-separated browser origins allowed to use cookie sessions. |
| `COOKIE_SECURE` | Set to `true` behind HTTPS. |

## Safety and limitations

- The demo uses fictional accounts and server-held HMAC keys. Its approval records are integrity protection inside this demo, not PKI, blockchain, or an external digital-signature service.
- Husika payloads validate against a vendored published contract. Linda does not call Husika write endpoints.
- CAP documents have status `Exercise` only.
- Source data and policy assumptions must be validated with authorised partners before any operational deployment.

## Verification

```bash
cd server/backend
.venv/bin/ruff check app tests
.venv/bin/pytest -q

cd ../../client/frontend
npm run build
npm test -- --passWithNoTests
```

The backend workflow suite covers guarded transitions, blocker handling, three-role signatures, immutable exports, CAP and Husika validation, partner verification, audit-chain tampering, source-backed assessment, and approval supersession on reassessment.

## Documentation

- [Backend guide](server/backend/README.md)
- [Frontend guide](client/frontend/README.md)
- [Contributing guide](CONTRIBUTING.md)
- [Security policy](SECURITY.md)

## License

MIT. See [LICENSE](LICENSE).
