<p align="center">
  <img src="docs/brand/linda-node-logo-horizontal.png" alt="Linda Node" width="440" />
</p>

<p align="center">
  <strong>An auditable activation-readiness control plane for the Greater Horn of Africa.</strong><br />
  Live ICPAC evidence in, a governed and verifiable activation record out.
</p>

<p align="center">
  <img alt="CI" src="https://img.shields.io/badge/CI-ruff%20%C2%B7%20pytest%20%C2%B7%20tsc%20%C2%B7%20vitest-1B5E20" />
  <img alt="Tests" src="https://img.shields.io/badge/tests-139%20backend%20%2B%2013%20frontend-1B5E20" />
  <img alt="Coverage" src="https://img.shields.io/badge/region-214%20admin--1%20units%20%C2%B7%2011%20countries-E8552A" />
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-555" /></a>
</p>

---

## Contents

1. [The problem](#1-the-problem)
2. [What Linda Node is](#2-what-linda-node-is)
3. [What it looks like right now](#3-what-it-looks-like-right-now)
4. [How it works](#4-how-it-works)
5. [Upstream data surfaces](#5-upstream-data-surfaces)
6. [Honesty guarantees](#6-honesty-guarantees)
7. [The golden workflow](#7-the-golden-workflow)
8. [Screens](#8-screens)
9. [The integration API](#9-the-integration-api)
10. [Repository map](#10-repository-map)
11. [Quick start](#11-quick-start)
12. [Configuration](#12-configuration)
13. [Deployment](#13-deployment)
14. [Testing and verification](#14-testing-and-verification)
15. [Scope, limits, and safety](#15-scope-limits-and-safety)
16. [Acknowledgements](#16-acknowledgements)

---

## 1. The problem

Early warning information for the Greater Horn of Africa is already good and already public. ICPAC operates seasonal forecasting, a multi-hazard thresholds and triggers platform, and — through Husika — SMS, USSD, mobile, web, and multilingual last-mile delivery.

The gap is not warning. It is the **operational bridge between a forecast crossing a threshold and a funded, accountable action starting**:

> Which pre-agreed action should start now, who must approve it, what evidence supports that decision, what is blocking readiness — and can anyone prove it afterwards?

ICPAC's own trigger engine makes the shape of the gap concrete. Its `/api/triggers/actions/` endpoint dispatches exactly two action types today:

```
email_alert   ·   dashboard_update
```

**Linda Node is the third action type: governed activation.**

---

## 2. What Linda Node is

A single deployable web application that sits between ICPAC's data surfaces and downstream communication, and turns a signal into an **immutable, exportable, independently verifiable decision record**.

It is deliberately **not** an alert-delivery system, a fund-disbursement system, a forecasting model, or an autonomous decision-maker. Husika owns the last mile. ICPAC owns the science. Linda Node owns the decision path between them.

| Linda Node does | Linda Node never does |
|---|---|
| Capture upstream evidence verbatim, hashed and provenance-labelled | Compute its own hazard model, index, or exposure score |
| Evaluate a versioned, code-reviewed policy in deterministic Python | Let an LLM decide a threshold, eligibility, or an approval |
| Require three distinct named roles to co-sign an activation | Move money, or select beneficiaries |
| Generate PDF, CAP 1.2, Husika-shaped, and offline-bundle artifacts | Dispatch an alert or call a Husika write endpoint |
| Publish a documented, read-only API partners can consume and verify | Accept inbound writes from partners |

---

## 3. What it looks like right now

The application opens on a **live regional readiness ranking**: every admin-1 unit ICPAC publishes return-period statistics for — **214 units across 11 countries** — evaluated against the same versioned policy and drawn on ICPAC's own GADM vector tiles.

Most of the region reaches no stage, and Linda Node says so plainly. That is the point: the ordinary output of an activation system is *"no activation recommended"*, and a system that cannot say that cannot be trusted when it does recommend action.

At the time of writing, the recorded OND 2026 forecast puts three units over a threshold:

| Admin-1 unit | Country | rp3 exceedance | Stage | Reached via |
|---|---|---:|---|---|
| Ruvuma | Tanzania | 51.8 % | **SET** · NDMA Alarm | drought policy (SPI-3 / CHIRPS seasonal forecast) |
| Mtwara | Tanzania | 44.9 % | READY · NDMA Alert | drought policy |
| Bungoma | Kenya | 0.4 % | READY · NDMA Alert | **heat policy**, from ICPAC's own live trigger event |

That last row is the whole architecture in one line. ICPAC's rule for Bungoma is `hazard_type: heat_raw`, TMAX ≥ 23 °C — and ICPAC's indicator registry declares TMAX **monitoring-only, no forecast support**. Heat readiness therefore cannot be probability-driven, so the heat policy maps ICPAC's own `severity_level` onto a readiness stage. Linda Node consumes their classification; it never invents one.

---

## 4. How it works

```
┌─────────────────────────────────────────────────────────────────────────┐
│ UPSTREAM (ICPAC, public)                                                │
│  /api/triggers/{rules,events,actions,check-logs}                        │
│  /api/datasets/forecasts/{available,stats}  ·  /api/datasets/indicators │
│  /api/areas/areas/  ·  /tileserv/{layer}/{z}/{x}/{y}.pbf                │
│  ibf-thresholds-triggers exceedance CSV (03_prob_csv_q.py shape)        │
└───────────────────────────────┬─────────────────────────────────────────┘
                                │  verbatim body stored, hashed BEFORE parsing,
                                │  JSON-Schema validated, emails masked on read
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ DETERMINISTIC POLICY ENGINE           (pure functions · no IO · no LLM) │
│  drought → probability basis   (SPI-3/CHIRPS seasonal exceedance)       │
│  heat    → upstream severity   (ICPAC severity_level → stage)           │
│  flood   → upstream severity   (ICPAC severity_level → stage)           │
│  Ready–Set–Go stages · 6 gates · cost–loss trace · stop trigger         │
│  No stage met ⇒ stage = null ⇒ "no activation recommended"              │
└───────────────────────────────┬─────────────────────────────────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ CASE STATE MACHINE + APPEND-ONLY HASH-CHAINED AUDIT                     │
│  INGESTED → ASSESSED → READY_FOR_REVIEW → APPROVED → HANDED_OFF         │
│                    ↘ NEEDS_EVIDENCE   ↘ REJECTED    ↘ REVOKED           │
│  Readiness tasks · blocker taxonomy · critical-path guard               │
│  3 distinct roles co-sign · HMAC-SHA256 over a canonical case snapshot  │
└───────────────────────────────┬─────────────────────────────────────────┘
                                ▼
┌──────────────────────────────────┬──────────────────────────────────────┐
│ IMMUTABLE EXPORTS                │ CONSUMABLE INTEGRATION API           │
│  Activation Decision Packet      │  /integration/v1/activations         │
│    (PDF + hashed JSON manifest)  │  /…/{id}/cap.xml                     │
│  CAP 1.2 XML (Alert and Cancel)  │  /…/{id}/husika-payload.json         │
│  Husika-shaped payload           │  /…/{id}/verify                      │
│  Air-gapped .zip field bundle    │  public CAP Atom feed · webhooks     │
└──────────────────────────────────┴──────────────────────────────────────┘
                                ▲
                    ┌───────────┴───────────┐
                    │ 3 CONSTRAINED ASSISTS │  read-only, schema-forced,
                    │ Gemini 2.5 Flash      │  cannot change any state
                    └───────────────────────┘
```

### Technology

| Layer | Choice |
|---|---|
| Backend | Python 3.12 · FastAPI · Pydantic v2 · SQLite (WAL) locally, Neon Postgres in production |
| Policy | Versioned YAML, JSON-Schema validated at startup, hash-pinned at runtime |
| Frontend | React 18 · TypeScript 5 · Vite 5 · Material UI v6 · TanStack Query v5 |
| Maps | MapLibre GL over ICPAC pg_tileserv vector tiles; Leaflet + OSM for per-case context |
| Exports | WeasyPrint (ReportLab fallback) · lxml + OASIS CAP 1.2 XSD · jsonschema |
| AI | `google-genai`, `gemini-2.5-flash`, structured output only — optional and fully degradable |
| Tests | pytest · Vitest · React Testing Library |

---

## 5. Upstream data surfaces

Every surface below is public, verified live, and consumed through a typed adapter with caching, schema validation, and replay fallback.

| ICPAC surface | What Linda Node takes from it |
|---|---|
| `/api/triggers/rules/` | Trigger rules — area (`area_gid`), indicator (`indicator_code`), threshold, severity, active state |
| `/api/triggers/events/` | Detected events, the basis for heat and flood readiness |
| `/api/triggers/actions/` | The two upstream action types — the gap Linda Node fills |
| `/api/triggers/check-logs/` | Upstream monitoring cadence, shown as a freshness signal |
| `/api/datasets/forecasts/available/` | 13 published forecast issues across 4 seasons |
| `/api/datasets/forecasts/stats/` | Admin-1 return-period exceedance for **all 11 countries in one call** |
| `/api/datasets/indicators/` | The registry that decides which hazards can be forecast at all |
| `/api/areas/areas/` | GADM admin-1 index (`fields=id,name`), plus per-country geometry on demand |
| `/tileserv/{layer}/{z}/{x}/{y}.pbf` | GADM admin-1 vector tiles, joined to statistics on `gid_1` |
| `icpac-igad/ibf-thresholds-triggers` | Exceedance-probability CSV in the `03_prob_csv_q.py` column layout |
| `api.ingestor.husika.icpac.net/openapi.json` | Vendored contract every handoff payload is validated against |

Return-period statistics are percentages; Linda Node reads `avg_prob_rp3`, divides by 100, and records that mapping on every record as `probability_source`. `rp3` is treated as the 0.33 quantile tail — stated in the policy, never hidden.

---

## 6. Honesty guarantees

These are enforced in code and covered by tests, because they are the difference between a demo and something an agency could adopt.

| Guarantee | How it is enforced |
|---|---|
| **A stage is never invented.** With no qualifying signal, `stage` is `null`, `ndma_phase` is `null`, `recommendation` is `"no activation recommended"`, and the `signal_present` gate fails. | `app/policy_engine.py`; `tests/test_policy_engine.py` |
| **Hashes cover the verbatim upstream body**, taken *before* parsing. A reviewer reproduces any snapshot hash with `curl <url> \| shasum -a 256`. | `app/sources.py::_store`; per-endpoint hashes exposed in `meta.parts` |
| **Personal addresses are masked on every read path.** ICPAC trigger rules carry named individuals' emails; the recorded fixture keeps them for provenance, but no API response, UI render, packet, or export ever shows one. | `app/redaction.py`; a parameterised test sweeps every endpoint and export |
| **Synthetic values can never pose as official.** Recorded evidence outranks a synthetic fixture; a synthetic observation is labelled `policy_assumption`, sets `synthetic_observation: true`, and raises a UI banner. | `observed_signal()`; `tests/test_policy_engine.py` |
| **A malformed rulebook stops the process.** Policies and action cards are JSON-Schema validated at startup. | `app/library.py::validate_library` |
| **`schema_ok` can actually fail.** Each source payload is validated against a schema in `content/schemas/sources/`, and a failure blocks assessment at the `schema_valid` gate. | `validate_source()` |
| **The stop trigger is a condition, not a button.** An injected observation is evaluated against `policy.stop_trigger`; above threshold the case stands and the evaluation is still recorded. | `services.evaluate_stop_trigger_for_case` |
| **Cached, stale, and replay data are never presented as live.** | Freshness badge on every snapshot, plus a banner when data is stale, invalid, or synthetic |
| **The audit log has no update or delete path anywhere in the codebase.** | `append_event()` is the only writer; a tamper test proves detection |

---

## 7. The golden workflow

1. **Regional Readiness** ranks all 214 admin-1 units live. Open a case from the ranking or by clicking the map.
2. The deterministic engine evaluates the hazard's policy and writes an **Assessment**: stage, six gates, stage trace, cost–loss trace with per-operand provenance, eligible and ineligible action cards with reasons, compound signals, and the armed stop trigger.
3. Eligible cards materialise **readiness tasks** owned by named roles. Owners acknowledge, resolve, decline, or file a blocker with a taxonomy code. A blocked *critical* task makes review impossible — enforced by the API, not just the button.
4. **Three distinct roles co-sign** — EWS Specialist, County DRM Officer, NGO & Finance Lead. Each signature is `HMAC-SHA256(user key, sha256(canonical case snapshot))`. Three valid signatures, and only that, produce `APPROVED`.
5. **Exports** generate: Activation Decision Packet (PDF + hashed JSON manifest), CAP 1.2 XML validated against the OASIS XSD, a Husika payload validated against the vendored OpenAPI contract, and an air-gapped `.zip` whose offline dossier makes zero external requests.
6. **Stop-trigger evaluation** can move an approved case to `REVOKED`, producing a CAP `Cancel`.
7. The **audit log** replays every event, hash-chained and verifiable in the UI.
8. The activation is simultaneously published on Linda Node's **own consumable API** — CAP feed, versioned REST, signed webhooks.

New evidence re-assesses the case, marks prior approvals `superseded`, and requires fresh signatures. Nothing is ever deleted.

---

## 8. Screens

| Screen | Purpose |
|---|---|
| **Regional Readiness** (`/`) | 214 units ranked by stage then exceedance; stat tiles; country rollup; MapLibre choropleth on ICPAC vector tiles; grounding-evidence hashes |
| **Signal Inbox** (`/signals`) | Trigger rules, detected events, seasonal forecasts, pipeline files; ICPAC's upstream action types; source health; provenance dialog |
| **Decision Cases** (`/cases`) | All cases with stage and state |
| **Case detail** (`/cases/:id`) | Evidence & trace · Actions & Readiness · Approvals · Handoffs & Exports · Audit log |
| **Audit Log** (`/audit`) | Filterable append-only event history across all cases |
| **Policy & Actions** (`/library`) | Three hazard policies, the action-card library, and ICPAC's indicator registry |
| **Sources** (`/sources`) | Per-adapter provenance, hashes, schema state, refresh |
| **API & Partners** (`/integrations`) | The developer documentation, also public at `/developers` |
| **Admin** (`/admin`) | Source mode, forecast issue, synthetic escalation, stop-trigger evaluation, partner keys, webhooks, demo recovery |

Every asynchronous view implements loading, empty, and error states. Role-gated controls are disabled and explained rather than hidden, so the permission model is visible — while the API remains the enforcer.

---

## 9. The integration API

Linda Node is not only a consumer of ICPAC APIs; it **publishes one**. This is the answer to "how would ICPAC actually adopt this?"

**Public — no key required**

```
GET /cap/feed.xml                              CAP 1.2 Atom feed of published activations
GET /integration/v1/openapi.json               machine-readable contract
GET /integration/v1/schemas/activation.json    frozen v1 response schema
GET /integration/v1/docs                       human documentation
GET /healthz                                   liveness
```

**API key required** (`Authorization: Bearer linda_…`, 60 req/min/key)

```
GET /integration/v1/activations                paginated, filterable, opaque cursor
GET /integration/v1/activations/{id}           full record: trace, approvals, provenance
GET /integration/v1/activations/{id}/cap.xml
GET /integration/v1/activations/{id}/husika-payload.json
GET /integration/v1/activations/{id}/verify    server-side recomputation of every hash
```

```bash
curl --request GET \
  --url 'https://linda-node.vercel.app/integration/v1/activations?state=APPROVED' \
  --header 'Authorization: Bearer linda_your_api_key'
```

**Webhooks.** Administrators register an HTTPS endpoint for `activation.approved` and `activation.revoked`. Each delivery carries `X-Linda-Event`, `X-Linda-Delivery` (matching the stored audit row), and `X-Linda-Signature: sha256=HMAC(secret, raw body)`. Loopback, link-local, and RFC1918 destinations are rejected before any request is made.

**Design principles.** Read-only and outbound-only — partners consume, humans decide inside Linda Node. Versioned and contract-stable: the v1 response shape is frozen by a published JSON Schema and a snapshot test, so a shape change fails CI. Standards-first: CAP 1.2 is the primary path because Husika's model is already CAP-shaped. Verifiable by the consumer: every payload carries the hashes and signatures needed to check integrity independently.

**Phrasing discipline.** Linda Node exposes an API Husika *could* integrate through CAP, REST, or webhooks, and validates its payloads against Husika's published schema. It has never called a Husika write endpoint, and adoption is ICPAC's decision.

---

## 10. Repository map

```
Linda-Node/
├── README.md                     ← you are here
├── CONTRIBUTING.md · SECURITY.md · LICENSE
├── docs/brand/                   horizontal + vertical logo masters
├── docker-compose.yml            one-container local demo
├── .github/workflows/ci.yml      lint · schema load · tests · build · upstream contract
│
├── server/backend/               FastAPI service  ── see server/backend/README.md
│   ├── app/
│   │   ├── main.py               routes, CORS, error shape, SPA mount
│   │   ├── config.py             typed settings; boots on LINDA_SECRET alone
│   │   ├── db.py                 schema, migrations, transactions, append_event
│   │   ├── demo_seed.py          the three seeded cases
│   │   ├── sources.py            adapters, verbatim capture, hashing, replay
│   │   ├── redaction.py          email masking on every read path
│   │   ├── library.py            hash-pinned policies and action cards
│   │   ├── policy_engine.py      pure deterministic assessment
│   │   ├── regional.py           the 214-unit regional view
│   │   ├── services.py           case service, guards, signing, audit chain
│   │   ├── exports.py            packet · CAP · Husika · offline bundle
│   │   ├── integration.py        partner API, keys, signed webhooks
│   │   └── assists.py            three constrained Gemini assists
│   ├── content/
│   │   ├── policies/{drought,heat,flood}.yaml
│   │   ├── actions/*.yaml        six action cards
│   │   ├── schemas/              policy · action card · sources · assists · integration
│   │   └── templates/            packet.html · offline_dossier.html
│   ├── fixtures/                 recorded ICPAC responses · CAP XSD · Husika spec
│   └── tests/                    139 tests + 5 opt-in live contract tests
│
└── client/frontend/              React SPA  ── see client/frontend/README.md
    ├── public/                   favicons, wordmark, manifest, social card
    └── src/
        ├── App.tsx               shell, routing, data-mode banner
        ├── Logo.tsx              wordmark component
        ├── RegionalMap.tsx       MapLibre choropleth on ICPAC tiles
        ├── components.tsx        provenance, freshness, hash, stage primitives
        └── features/             regional · inbox · case · library · audit · admin · developers · login
```

---

## 11. Quick start

**Requirements:** Python 3.12+, Node.js 20+, and (for local PDF rendering) native Pango/Cairo — or just Docker.

### One container

```bash
cp server/backend/.env.example server/backend/.env   # set LINDA_SECRET
docker compose up --build
```

Open <http://localhost:8000>.

### Two processes

```bash
# Terminal 1 — API on :8001
cd server/backend
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
cp .env.example .env
.venv/bin/uvicorn app.main:app --reload --port 8001

# Terminal 2 — web client on :5173
cd client/frontend
npm ci
npm run dev
```

Open <http://127.0.0.1:5173>. Vite proxies `/api`, `/cap`, and `/integration` to the API.

On macOS, if WeasyPrint cannot find its native libraries:

```bash
brew install pango cairo gdk-pixbuf
export DYLD_FALLBACK_LIBRARY_PATH="$(brew --prefix pango)/lib:$(brew --prefix glib)/lib:$(brew --prefix cairo)/lib:$(brew --prefix gdk-pixbuf)/lib"
```

### Walkthrough

All seeded personas use the password `linda-demo`. Seeding creates three cases on **Ruvuma, Tanzania** — a real unit whose recorded ICPAC statistic genuinely crosses SET — so a first-time visitor sees the whole arc immediately: one live blocked case, one completed `HANDED_OFF` case with all four exports already generated, and one `REVOKED` case.

| Persona | Role | Part in the walkthrough |
|---|---|---|
| `david.drm@demo` | County DRM Officer | Creates cases, sends for review, hands off, revokes |
| `grace.ngo@demo` | NGO & Finance Lead | Resolves the seeded transport blocker, co-signs |
| `amina.ews@demo` | EWS Specialist | Co-signs the evidence record |
| `observer@demo` | Read-only observer | Inspects everything, mutates nothing |
| `admin@demo` | Administrator | Source mode, forecast issue, escalation, keys, webhooks, recovery |

1. Sign in as **David**. Regional Readiness opens on the live ranking — toggle *All 214* to see how much of the region reaches no stage.
2. Open the Ruvuma case, or click any unit on the map to create one.
3. Sign in as **Grace**, resolve the transport blocker under *Actions & Readiness*.
4. Sign in as **David**, send for review.
5. Sign in as **Amina**, **David**, then **Grace** to record the three signatures. The third produces `APPROVED`.
6. Back as **David**: generate all four exports, verify the chain and the signatures, mark handed off.
7. As **admin**, use *Stop-trigger evaluation*. Above the policy threshold the case stands and the evaluation is recorded; below it, the case is revoked and a CAP `Cancel` becomes available.

---

## 12. Configuration

Copy [`server/backend/.env.example`](server/backend/.env.example) to `server/backend/.env`. The API boots with only `LINDA_SECRET` set.

| Variable | Default | Purpose |
|---|---|---|
| `LINDA_SECRET` | dev fallback | Signing secret for session cookies. **Set a real value in production.** |
| `DATABASE_URL` | `sqlite:///var/linda.db` | SQLite locally; Neon Postgres URL in production |
| `DEMO_MODE` | `true` | Enables replay fallback and auto-seed on an empty database |
| `ICPAC_BASE` | `https://eatriggersthresholds.icpac.net` | Upstream base URL |
| `HTTP_TIMEOUT_S` | `8` | Per-request upstream timeout |
| `SNAPSHOT_TTL_MIN` | `30` | Cache lifetime before an adapter refetches |
| `GEMINI_API_KEY` | — | Optional. Absent ⇒ assist buttons disabled, workflow unaffected |
| `GEMINI_MODEL` | `gemini-2.5-flash` | Assist model |
| `CORS_ORIGINS` | localhost | Comma-separated browser origins allowed to use cookie sessions |
| `COOKIE_SECURE` | `false` | Set `true` behind HTTPS |
| `PUBLIC_BASE_URL` | `http://localhost:8000` | Used for CAP feed URLs |
| `LINDA_BLOB_READ_WRITE_TOKEN` | — | Server-only token for the private Vercel Blob export store |
| `LINDA_API_ORIGIN` | — | Server-only upstream URL for the Vercel frontend proxy |
| `VITE_LINDA_API_ORIGIN` | — | Public build-time API origin; prefer the proxy for cookie sessions |

---

## 13. Deployment

**Docker (one container).** `server/backend/Dockerfile` installs WeasyPrint's native dependencies; CI bakes the built SPA into `/app/static`, which FastAPI serves with SPA fallback. `docker compose up` then `:8000` works from a clean clone.

**Vercel (two projects, currently in production).** The React client is served at `linda-node.vercel.app`; its server-side proxy forwards `/api`, `/cap`, and `/integration` to the FastAPI project at `linda-protocol-api.vercel.app`, keeping the HTTP-only session cookie on the frontend origin. (The API project keeps its original hostname; renaming it would require re-pointing `LINDA_API_ORIGIN` and re-issuing partner keys.)

The API project's root directory is `server/backend`; `api/index.py` runs FastAPI as a Vercel Function, Neon Postgres holds workflow state, and private Vercel Blob holds generated exports. Configure `LINDA_SECRET`, `COOKIE_SECURE=true`, `PUBLIC_BASE_URL`, `CORS_ORIGINS`, `DATABASE_URL`, and `LINDA_BLOB_READ_WRITE_TOKEN`. Configure the frontend project with `LINDA_API_ORIGIN` and redeploy after changing it.

Because a serverless invocation ends with its response, webhook retry pacing adapts automatically (`VERCEL=1` ⇒ one prompt retry; a long-lived container gets the full 1 m / 5 m / 25 m backoff).

**Operations.** `/healthz` returns `{status, db, mode, demo_mode}`. Structured JSON logs. `POST /api/admin/seed` restores the seeded scenario in seconds.

---

## 14. Testing and verification

```bash
cd server/backend
.venv/bin/ruff check app tests
.venv/bin/python -c "from app.library import validate_library; print(validate_library())"
.venv/bin/pytest -q                      # 139 tests

cd ../../client/frontend
npx tsc -b --noEmit
npm test                                 # 13 tests
npm run build
```

The backend suite covers:

- **Policy engine** — every stage boundary at, just below, and just above each threshold; all six gates; both stop-trigger shapes; cost–loss arithmetic against hand-computed figures; the no-fabrication rule; area isolation; synthetic-versus-recorded ranking; purity and repeatability.
- **State machine** — every legal transition, plus **every illegal one attempted through the API and asserted rejected**: observer and non-owner role bypass, direct `APPROVED` transitions, two-signature approval, blocked critical tasks, terminal states, missing revocation reasons, handoff without an export.
- **Signing** — canonical-JSON stability under key reordering, digest determinism, HMAC verification, supersession on re-assessment, the distinct-roles rule.
- **Adapters** — live ICPAC field mapping, schema accept and reject, email masking across every endpoint and export, verbatim-body hashing, TTL cache, forced refresh, escalation-step selection, stale fallback.
- **Exports** — manifest hash stability, CAP validated against the OASIS XSD (Alert *and* Cancel), stage→severity mapping, GADM geocode, Husika payloads validated against the vendored spec with negative enum tests, bundle checksums, and a zero-external-request assertion on the offline dossier.
- **Partner API** — key auth, revocation, rate limiting, cursor pagination, a frozen response shape checked against the published JSON Schema, tamper detection, webhook signature and retry behaviour, and delivery-id/audit-row correlation.
- **Security** — HTML escaping of untrusted text, login rate limiting, forged-cookie rejection, no secrets in any export, fail-closed policy loading.

A separate opt-in job calls the **real** ICPAC and Husika endpoints and fails loudly if upstream shapes drift:

```bash
.venv/bin/pytest -q -m contract --contract
```

It also runs daily and on `workflow_dispatch` in CI.

---

## 15. Scope, limits, and safety

- **Deliberately out of scope:** Telegram or SMS/USSD delivery, any climate or hazard model of our own, automatic fund disbursement, beneficiary selection, automatic public alerting, and live calls to Husika write APIs. Linda Guide provides curated workspace help only; it is not an operational or emergency advisor.
- **The demo policies are illustrative.** Thresholds, costs, and effectiveness values are team-authored and are *not* official ICPAC, NDMA, county-government, or financing-partner policy. Every policy file states this, and the disclaimer appears in the UI and in every packet.
- **Tranche lines are recommendations.** "Release" is a recorded recommendation requiring the human approvals on record. Linda Node moves no money and says so wherever money appears.
- **Signing is integrity protection within this system.** Server-held keys, HMAC-SHA256 — a *cryptographically signed decision record*, not PKI, not digital signatures in the legal sense, not a blockchain.
- **CAP documents carry `status = Exercise`.** This is deliberate and load-bearing: a CAP document marked `Actual` from a non-accredited sender could be ingested by a real alert aggregator. The workspace UI is otherwise free of demo framing — what a visitor sees is live ICPAC data.
- **Personas are fictional.** Named ICPAC individuals appearing in upstream trigger rules are masked everywhere.
- **No self-registration, password reset, or OAuth.** Seeded users only.

---

## 16. Acknowledgements

Built on public work by others, with thanks:

- **ICPAC / IGAD** — the Thresholds & Triggers platform, seasonal forecast and indicator APIs, GADM area services, pg_tileserv vector tiles, and the `icpac-igad/ibf-thresholds-triggers` scientific pipeline whose CSV layout this project reads.
- **Husika** (developed by Bunifu Technologies) — the published Data Ingestor OpenAPI contract every handoff payload is validated against.
- **GADM 4.1** — administrative boundaries and the identifiers used as join keys throughout.
- **OASIS** — the Common Alerting Protocol 1.2 standard and XSD.
- **IGAD Regional Roadmap for Anticipatory Action**, the **Kenya Anticipatory Action Roadmap**, and the **Kenya Disaster Risk Management Act** — the policy framing this project serves.
- **IFRC** Early Action Protocol practice — the two-tranche budget pattern the action cards follow.
- Open source: FastAPI, Pydantic, httpx, jsonschema, lxml, WeasyPrint, ReportLab, React, Material UI, TanStack Query, MapLibre GL, Leaflet, Vite, pytest, Vitest, Ruff.
- **Google Gemini** — the three constrained, optional assists.

---

<p align="center">
  <img src="docs/brand/linda-node-logo-vertical.png" alt="" width="90" /><br />
  <sub>MIT licensed · see <a href="LICENSE">LICENSE</a> · report vulnerabilities via <a href="SECURITY.md">SECURITY.md</a></sub>
</p>
