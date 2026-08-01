# Linda Protocol

Linda Protocol is an exercise-only, human-governed workspace for turning early-warning evidence into a reviewable activation-readiness decision. It helps disaster-risk teams answer four practical questions: what evidence supports action, which pre-agreed actions are ready, who must approve, and what still blocks delivery.

It is deliberately not an alert-delivery system, a fund-disbursement system, or an autonomous decision-maker. Every public artifact is labelled **Exercise**. Linda never sends an alert through Husika and never moves money.

## What it shows

Linda opens on a **live regional readiness ranking**: every admin-1 unit ICPAC publishes return-period statistics for — 214 units across the 11 Greater Horn of Africa countries — evaluated against the same versioned policy, drawn on ICPAC's own GADM vector tiles.

Most of the region reaches no stage, and Linda says so. That is the point: the interesting output of an activation system is usually *"no activation recommended"*, and a system that cannot say that cannot be trusted when it does recommend one. At the time of writing the recorded OND 2026 forecast puts three units over a threshold — Ruvuma (Tanzania) at SET, Mtwara (Tanzania) at READY on the drought policy, and Bungoma (Kenya) at READY on the heat policy, driven by ICPAC's own live trigger rule.

## What it does

- Captures source snapshots by storing each upstream body **verbatim** and hashing it *before* parsing, so a reviewer can reproduce the recorded SHA-256 with `curl <url> | shasum -a 256`. Every snapshot carries its retrieval time, JSON Schema result, and a clear live, cached, stale, or replay label.
- Masks every personal email address present in upstream trigger rules on every API response, UI render, packet, and export.
- Creates a decision case for an administrative area and evaluates a versioned YAML policy in deterministic code. When no stage condition is met it reports **"no activation recommended"** rather than inferring a stage.
- Materialises readiness tasks from approved action cards and prevents review when a critical task is unresolved.
- Records three distinct role approvals using HMAC-SHA256 over a canonical case snapshot.
- Produces immutable decision artifacts: a PDF/JSON packet, CAP 1.2 XML, Husika-shaped JSON validated against a vendored OpenAPI snapshot, and an offline ZIP bundle.
- Exposes approved or revoked activations through a documented, read-only partner API and signed webhooks.
- Surfaces ICPAC's own trigger action types (`email_alert`, `dashboard_update`) read live from `/api/triggers/actions/` — the gap Linda's governed activation fills.
- Applies a hazard-specific policy: drought readiness is probability-driven from the SPI-3/CHIRPS seasonal forecast, while heat and flood readiness follow ICPAC's own detected trigger events, because their registry publishes TMAX and rainfall as monitoring-only indicators. Linda maps ICPAC's `severity_level` to a stage; it never classifies severity itself.
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

The demo policy and action cards are illustrative. They are not official ICPAC, county-government, or financing-partner policy. Both are JSON Schema-validated at startup: an invalid rulebook stops the process rather than producing assessments nobody reviewed.

### Live data, not a staged scenario

Nothing in the default path is synthetic. The seeded cases run on **Ruvuma, Tanzania** — a real admin-1 unit whose recorded ICPAC statistic (51.8% rp3 exceedance for OND 2026) genuinely crosses the SET threshold. The pipeline CSV, the trigger rules, the boundary index and the forecast statistics are all verbatim recorded upstream responses.

A labelled synthetic escalation remains available to an administrator as a "what if the signal grows" control. Whenever it is active, the assessment carries `synthetic_observation: true`, the probability is labelled `policy_assumption` rather than `official_source`, and a banner says so — recorded evidence always outranks a synthetic reading when both are attached.

### Upstream surfaces consumed

| ICPAC surface | Used for |
|---|---|
| `/api/triggers/{rules,events,actions,check-logs}` | Trigger rules, detected events, the two upstream action types, and monitoring cadence |
| `/api/datasets/forecasts/{available,stats}` | 13 published forecast issues across 4 seasons; admin-1 return-period statistics for all 11 countries in one call |
| `/api/datasets/indicators/` | The indicator registry that determines which hazards can be forecast at all |
| `/api/areas/areas/` | GADM admin-1 index (`fields=id,name`) plus per-country geometry on demand |
| `/tileserv/{layer}/{z}/{x}/{y}.pbf` | GADM admin-1 vector tiles, joined to the statistics on `gid_1` |
| `api.ingestor.husika.icpac.net/openapi.json` | Vendored contract that every Husika handoff payload validates against |

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

All seeded personas use the password `linda-demo`. Seeding creates three cases so a first-time visitor sees the whole arc immediately: the blocked case below, a completed `HANDED_OFF` case with all four exports already generated, and a `REVOKED` case showing the stop-trigger path. The public CAP feed is populated from the moment the app boots.

| Persona | Role | Use in the walkthrough |
|---|---|---|
| `david.drm@demo` | County DRM Officer | Sends a ready case for review, marks it handed off, or revokes it. |
| `grace.ngo@demo` | NGO & Finance Lead | Resolves the seeded transport blocker and co-signs. |
| `amina.ews@demo` | EWS Specialist | Co-signs the evidence record. |
| `observer@demo` | Read-only observer | Inspects the workflow without mutating it. |
| `admin@demo` | Administrator | Restores demo data, manages API keys and webhooks, and switches source mode. |

1. Sign in as David. **Regional Readiness** opens on the live ranking; toggle *All 214* to see how much of the region reaches no stage.
2. Open the case for Ruvuma, or click any unit on the map to create one.
3. Open **Decision Cases**.
4. Open the seeded Ruvuma case. It starts at `ASSESSED` with a critical transport blocker.
5. Sign in as Grace and resolve the transport task under **Actions & Readiness**.
6. Sign in as David and send the case for review.
7. Sign in as Amina, David, and Grace in turn to record the three approvals.
8. Return as David to generate exports, mark the case handed off, or demonstrate revocation.
7. As `admin@demo`, use **Stop-trigger evaluation** to inject an observation. The *policy* decides: a value above `stop_trigger.probability_lt` is recorded and the case stands; a value below it revokes the case and makes a CAP `Cancel` available. The same screen advances the labelled synthetic escalation and switches between `live_first` and `replay_only`.

For a new case, begin in **Signal Inbox**. Open a source record, create a case, and review the deterministic assessment in the **Evidence** tab. Demo fixtures keep this flow available when an upstream public endpoint is unavailable.

## Architecture and trust boundaries

| Component | Responsibility |
|---|---|
| `client/frontend` | React, TypeScript, and Material UI single-page application. |
| `server/backend` | FastAPI service, SQLite for local development or Neon Postgres on Vercel, policy evaluation, exports, and partner API. |
| Source adapter | Retrieves or replays source data, stores each upstream body verbatim, hashes it before parsing, validates the normalised view against a JSON Schema, and masks personal addresses on read. |
| Regional view | Applies each hazard's policy to all 214 admin-1 units and ranks them, without inventing a stage for any of them. |
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
| `DATABASE_URL` | SQLite URL locally; Vercel injects the Neon Postgres URL in production. |
| `DEMO_MODE` | Enables replay fallback and demo seed behaviour. |
| `ICPAC_BASE` | Base URL for public ICPAC source requests. |
| `SNAPSHOT_TTL_MIN` | Cache lifetime before the source adapter refreshes a snapshot. |
| `GEMINI_API_KEY` | Optional. When absent, assist controls are disabled and the workflow still works. |
| `CORS_ORIGINS` | Comma-separated browser origins allowed to use cookie sessions. |
| `COOKIE_SECURE` | Set to `true` behind HTTPS. |
| `LINDA_BLOB_READ_WRITE_TOKEN` | Server-only token for the private Vercel Blob store used by generated exports. |
| `LINDA_API_ORIGIN` | Server-only upstream URL used by the Vercel frontend proxy. |
| `VITE_LINDA_API_ORIGIN` | Optional public frontend build-time API origin. Prefer the Vercel proxy for cookie-session deployments. |

### Exercise labelling

Public alert artifacts carry `status = Exercise` inside the CAP XML itself, and Husika payloads carry a "not dispatched" disclaimer. That is deliberate and is **not** cosmetic: a CAP document marked `Actual` from a non-accredited sender could be ingested by a real alert aggregator. The workspace UI is otherwise free of demo chrome — what a visitor sees is live ICPAC data.

### Vercel production deployment

The production deployment uses two Vercel projects. The React client is served at `linda-protocol.vercel.app`; its server-side proxy forwards `/api`, `/cap`, and `/integration` requests to the FastAPI project at `linda-protocol-api.vercel.app`. This keeps the HTTP-only session cookie on the frontend origin.

The API project's root directory is `server/backend`. Its `api/index.py` entrypoint runs FastAPI as a Vercel Function, Neon Postgres holds workflow state, and private Vercel Blob holds generated exports. Configure the API project with `LINDA_SECRET`, `COOKIE_SECURE=true`, `PUBLIC_BASE_URL=https://linda-protocol.vercel.app`, `CORS_ORIGINS=https://linda-protocol.vercel.app`, `DATABASE_URL`, and `LINDA_BLOB_READ_WRITE_TOKEN`. Configure the frontend project with `LINDA_API_ORIGIN=https://linda-protocol-api.vercel.app`, then redeploy it after changing that value.

The included `Dockerfile.vercel` remains available for container-based deployments. The function path uses a pure-Python PDF fallback if WeasyPrint's native rendering libraries are unavailable in the serverless runtime.

## Safety and limitations

- Assessments are never fabricated: with no qualifying signal the system says "no activation recommended" and blocks the workflow at the `signal_present` gate.
- Synthetic demo values are labelled everywhere they appear and are ranked *below* recorded upstream evidence when both are attached.
- The demo uses fictional accounts and server-held HMAC keys. Its approval records are integrity protection inside this demo, not PKI, blockchain, or an external digital-signature service.
- Husika payloads validate against a vendored published contract. Linda does not call Husika write endpoints.
- CAP documents have status `Exercise` only.
- Source data and policy assumptions must be validated with authorised partners before any operational deployment.

## Verification

```bash
cd server/backend
.venv/bin/ruff check app tests
.venv/bin/python -c "from app.library import validate_library; print(validate_library())"
.venv/bin/pytest -q

cd ../../client/frontend
npx tsc -b --noEmit
npm test
npm run build
```

The backend suite (139 tests) covers:

- **Policy engine** — every stage boundary at, just below, and just above each threshold; every gate; both stop-trigger shapes; cost-loss arithmetic against hand-computed figures; the no-fabrication rule; area isolation; synthetic-versus-recorded ranking; purity.
- **State machine** — every legal transition plus every illegal one attempted through the API and asserted rejected, including observer and non-owner role bypass, direct `APPROVED` transitions, two-signature approval, blocked critical tasks, and terminal states.
- **Signing** — canonical-JSON stability, digest determinism, signature verification, supersession on re-assessment.
- **Adapters** — live ICPAC field mapping, schema accept/reject, email masking across every endpoint and export, verbatim-body hashing, TTL cache, escalation steps, and stale fallback.
- **Exports** — manifest hash stability, CAP validated against the OASIS XSD (Alert and Cancel), Husika payloads validated against the vendored spec with negative enum tests, bundle checksums, and a zero-external-request check on the offline dossier.
- **Partner API** — key auth, revocation, rate limiting, cursor pagination, a frozen response shape checked against the published JSON Schema, tamper detection, and webhook signature/retry behaviour.
- **Security** — HTML escaping of untrusted text, login rate limiting, forged-cookie rejection, no secrets in any export, and fail-closed policy loading.

A separate opt-in job hits the real ICPAC and Husika endpoints and fails loudly if the upstream shapes drift:

```bash
cd server/backend
.venv/bin/pytest -q -m contract --contract
```

It also runs on a daily schedule and via `workflow_dispatch` in CI.

## Documentation

- [Backend guide](server/backend/README.md)
- [Frontend guide](client/frontend/README.md)
- [Contributing guide](CONTRIBUTING.md)
- [Security policy](SECURITY.md)

## License

MIT. See [LICENSE](LICENSE).
