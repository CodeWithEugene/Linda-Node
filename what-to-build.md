# Linda Protocol — Complete Build Specification

**Status:** authoritative build document. Supersedes README.md (old concept) for implementation purposes. Derived from `research.md` Parts I–III (Codex, Claude Code, Antigravity), all verified 22 July 2026.
**Deadline:** submit on Devpost before **31 July 2026, 17:00 EAT** — 9 calendar days from 22 July.
**Rule of interpretation:** if anything in this document conflicts with `research.md`, this document wins. If something is not in this document, it is **not built** for the hackathon.

---

## Table of contents

1. [What we are building (and not building)](#1-what-we-are-building-and-not-building)
2. [The one golden workflow](#2-the-one-golden-workflow)
3. [Repository layout](#3-repository-layout)
4. [Technology stack (pinned)](#4-technology-stack-pinned)
5. [Domain model and database schema](#5-domain-model-and-database-schema)
6. [Backend specification (FastAPI)](#6-backend-specification-fastapi)
   - 6.1 Configuration and environment
   - 6.2 Upstream source adapters
   - 6.3 Replay fixture engine
   - 6.4 Deterministic policy engine (`policy.yaml`)
   - 6.5 Action card library
   - 6.6 Case state machine
   - 6.7 Multi-role approval and signing
   - 6.8 Readiness tasks and blocker taxonomy
   - 6.9 Compound signal detection
   - 6.10 Constrained AI assists (Gemini)
   - 6.11 Activation Decision Packet generator
   - 6.12 CAP 1.2 exporter
   - 6.13 Husika handoff exporter
   - 6.14 Air-gapped field bundle exporter
   - 6.15 Authentication and roles
   - 6.16 REST API surface (complete)
   - 6.17 Failure posture (required behaviors)
   - 6.18 Consumable integration API (for Husika and partners)
7. [Frontend specification (React + Material UI)](#7-frontend-specification-react--material-ui)
   - 7.1 App shell, theme, navigation
   - 7.2 Screen 1: Signal Inbox
   - 7.3 Screen 2: Decision Case — Evidence ("Why this action?")
   - 7.4 Screen 3: Decision Case — Action Cards & Readiness Board
   - 7.5 Screen 4: Decision Case — Approvals
   - 7.6 Screen 5: Decision Case — Handoffs & Exports
   - 7.7 Screen 6: Audit Log
   - 7.8 Screen 7: Policy & Action Library viewer
   - 7.9 Map component
   - 7.10 Cross-cutting frontend rules
8. [Seed data and demo scenario](#8-seed-data-and-demo-scenario)
9. [Testing requirements](#9-testing-requirements)
10. [Deployment](#10-deployment)
11. [Nine-day build plan with exit criteria](#11-nine-day-build-plan-with-exit-criteria)
12. [Cut order if behind schedule](#12-cut-order-if-behind-schedule)
13. [Claims discipline (submission and demo)](#13-claims-discipline-submission-and-demo)
14. [Definition of done](#14-definition-of-done)

---

## 1. What we are building (and not building)

**Linda Protocol** is a single deployable web application: an auditable **activation-readiness control plane** that sits between ICPAC's Thresholds & Triggers platform and downstream communication (Husika, CAP). It answers, for a county disaster officer and their partners: *which pre-agreed action should start now, who must approve it, what evidence supports it, and what is blocking readiness* — and produces an immutable, exportable record of the decision.

The pitch anchor (verified live): ICPAC's own trigger engine at `eatriggersthresholds.icpac.net` has exactly two action types — `email_alert` and `dashboard_update`. **Linda Protocol is the third action type: governed activation.**

### Explicit non-goals — never build, never claim

| Not built | Reason |
|---|---|
| Telegram bot, SMS/USSD gateway, Africa's Talking integration, PWA/APK, voice/TTS | Husika owns delivery (incl. `*445#` USSD); Speedykom is building Husika TTS now |
| Chatbot / conversational Q&A | Husika + `arco-ibf` scenario-chat territory |
| Any climate/hazard model, SPI computation, Bayesian network, exposure index of our own invention | ICPAC's Layer-1 science exists (`bn-ibf`, `ibf-thresholds-triggers`); we consume and cite |
| Automatic fund disbursement, beneficiary selection, automatic public alerting | Governance red lines — tranche "release" is a *recorded recommendation requiring human approval*, never money movement |
| Live calls to Husika write APIs | OAuth2-gated; we validate payloads against their published schema, we do not dispatch |
| A new scientific "compound hazard index" | We implement deterministic *signal overlap detection* only (§6.9), clearly labeled |
| Multi-agent "platform" theatre | Exactly three constrained AI assists (§6.10) |

---

## 2. The one golden workflow

Every feature exists to make this single path work end-to-end, live, in front of a judge:

```
1. Signal Inbox shows live ICPAC data:
   a. Trigger rules + detected events from /api/triggers/ (incl. "Bungoma Triggers", authored by judge Crimson Sikolia)
   b. The OND 2026 return-period seasonal forecast (El Niño season) from /api/datasets/forecasts/
   Each with: source URL, retrieved_at, SHA-256 of raw payload, freshness status.
2. Officer opens/creates a Decision Case for an admin area (GADM id, e.g. KEN.3_1).
3. Policy engine evaluates policy.yaml deterministically →
   stage (READY / SET / GO), gates passed/failed, expected-avoidable-loss trace, eligible action cards.
4. Readiness Board: each eligible action card spawns tasks assigned to named roles;
   owners acknowledge or file structured blockers; critical blocker → case cannot advance.
5. Approvals: three roles co-sign (Climate/EWS Specialist, County DRM Officer, NGO/Finance Lead).
   Each signature = HMAC-SHA256 over the canonical case snapshot. 3-of-3 required → APPROVED.
6. Exports fire (all generated, none "sent"):
   a. Activation Decision Packet — PDF + hashed JSON manifest
   b. CAP 1.2 XML alert + Atom feed entry
   c. Husika-ready payload validated against api.ingestor.husika.icpac.net OpenAPI schema
   d. Air-gapped field bundle (.zip: offline HTML dossier + signed manifest + CAP XML)
7. Stop-trigger evaluation on new data can move the case to REVOKED, with the reason logged.
8. Audit Log screen replays every event of the case, hash-chained.
9. The approved (or revoked) activation is simultaneously published on Linda's OWN consumable
   integration API (§6.18): CAP Atom feed + versioned REST endpoints + signed webhooks — the
   surface Husika or any partner system could integrate against. Integration flows both ways:
   we validate against Husika's published schema, and we publish a schema they can consume.
```

If any step of this workflow is not demonstrable, the product is not done — regardless of what else exists.

---

## 3. Repository layout

Monorepo, two deployable units, one docker-compose.

```
Linda-Node/
├── what-to-build.md              # this file
├── research.md                   # evidence base (Parts I–III)
├── README.md                     # REWRITE at day 8 to describe Linda Protocol (see §11)
├── docker-compose.yml            # api + web + (optional) postgres
├── .env.example
├── backend/
│   ├── pyproject.toml
│   ├── alembic/                  # migrations (works for SQLite and Postgres)
│   ├── app/
│   │   ├── main.py               # FastAPI app factory, routers, CORS, exception handlers
│   │   ├── config.py             # pydantic-settings; every env var typed here
│   │   ├── db.py                 # SQLAlchemy 2.0 engine/session
│   │   ├── models.py             # ORM models (mirror §5 exactly)
│   │   ├── schemas.py            # Pydantic v2 request/response schemas
│   │   ├── auth.py               # JWT session, role guard dependencies
│   │   ├── adapters/
│   │   │   ├── base.py           # SourceAdapter protocol: fetch → validate → snapshot
│   │   │   ├── icpac_triggers.py # /api/triggers/{rules,events,actions,check-logs}
│   │   │   ├── icpac_datasets.py # /api/datasets/*, forecasts, stats
│   │   │   ├── icpac_areas.py    # /api/areas/areas/ (GADM ids + geometry)
│   │   │   ├── icpac_pipeline.py # IcpacPipelineAdapter: CSV/NetCDF from ibf-thresholds-triggers
│   │   │   └── replay.py         # fixture loader (same Snapshot output type)
│   │   ├── policy/
│   │   │   ├── engine.py         # pure functions: evaluate(policy, snapshots, area) → Assessment
│   │   │   ├── loader.py         # policy.yaml + action cards, schema-validated, versioned by hash
│   │   │   └── costloss.py       # expected avoidable loss + net benefit trace
│   │   ├── cases/
│   │   │   ├── service.py        # case CRUD, event append, optimistic concurrency
│   │   │   ├── state_machine.py  # transitions + guards (single source of truth)
│   │   │   ├── tasks.py          # readiness tasks, blockers
│   │   │   └── approvals.py      # canonical JSON, HMAC signing, verification
│   │   ├── assists/
│   │   │   ├── client.py         # Gemini structured-output wrapper, timeouts, schema retry
│   │   │   ├── explainer.py      # Evidence Explainer
│   │   │   ├── matcher.py        # Approved-Action Matcher
│   │   │   ├── blockers.py       # Blocker Structurer
│   │   │   └── prompts.py        # ALL prompts, versioned constants
│   │   ├── exports/
│   │   │   ├── packet.py         # HTML→PDF (WeasyPrint) + JSON manifest + hashing
│   │   │   ├── cap.py            # CAP 1.2 XML + Atom feed
│   │   │   ├── husika.py         # payload builder + OpenAPI schema validation
│   │   │   └── bundle.py         # air-gapped zip assembler
│   │   ├── api/
│   │   │   ├── routes_sources.py
│   │   │   ├── routes_cases.py
│   │   │   ├── routes_exports.py
│   │   │   ├── routes_admin.py   # seed/replay switches (auth: admin only)
│   │   │   └── routes_public.py  # /healthz, /cap/feed.xml
│   │   └── templates/            # packet.html, offline_dossier.html (inline CSS only)
│   ├── content/
│   │   ├── policy.yaml           # versioned decision policy (§6.4)
│   │   ├── actions/*.yaml        # action card library (§6.5)
│   │   └── schemas/              # JSON Schemas: policy, action card, assist outputs, manifest
│   ├── fixtures/
│   │   ├── icpac/*.json          # recorded real API responses (with retrieved_at + hash)
│   │   ├── replay_ond2026/*.json # demo scenario snapshots (§8)
│   │   ├── husika_openapi/ingestor.openapi.json   # vendored snapshot of their spec
│   │   └── cap/cap12.xsd         # CAP 1.2 schema for validation tests
│   └── tests/                    # §9
└── frontend/
    ├── package.json
    ├── vite.config.ts
    └── src/
        ├── main.tsx              # ThemeProvider, CssBaseline, QueryClientProvider, Router
        ├── theme.ts              # MUI theme (§7.1)
        ├── api/                  # typed client (generated from FastAPI OpenAPI via openapi-typescript)
        ├── auth/                 # login page, session context, role guard
        ├── layout/               # AppShell: AppBar, Drawer, breadcrumbs
        ├── components/           # shared: ProvenanceChip, FreshnessBadge, StateChip,
        │                         #   HashBlock, RoleAvatar, EmptyState, ErrorPanel, ConfirmDialog
        ├── features/
        │   ├── inbox/            # Signal Inbox
        │   ├── case/             # case detail: evidence, actions, approvals, handoffs tabs
        │   ├── audit/            # audit log
        │   ├── library/          # policy + action card viewer
        │   └── map/              # MapLibre wrapper
        └── i18n/strings.ts       # UI strings in one file (English; sw stretch only)
```

**Frontend framework decision:** Vite + React 18 SPA (not Next.js). Rationale: MUI + MapLibre are pure client-side; there is no SEO/SSR need; a SPA removes an entire class of hydration/SSR-cache issues and deploys as static files served by the FastAPI container, so demo = one URL. (If the team insists on Next.js, use App Router + `@mui/material-nextjs` AppRouterCacheProvider — but the default is Vite.)

---

## 4. Technology stack (pinned)

| Layer | Choice | Version pin | Notes |
|---|---|---|---|
| Backend | Python + FastAPI | Python 3.12, fastapi ≥0.115 | uvicorn worker |
| Validation | Pydantic v2 + pydantic-settings | ≥2.8 | all IO typed |
| ORM/DB | SQLAlchemy 2.0 + Alembic; **SQLite (WAL)** default; Postgres 16 optional | — | Single-file DB is a demo asset, not a compromise; schema is Postgres-compatible |
| HTTP client | httpx | ≥0.27 | timeouts + retries (§6.2) |
| Geo | shapely (centroids/point-in-polygon only) | ≥2.0 | **No PostGIS** — geometry comes from ICPAC areas API/tiles; we store GeoJSON |
| PDF | WeasyPrint | ≥62 | packet + offline dossier print CSS |
| XML | lxml | ≥5 | CAP generation + XSD validation |
| Schema validation | jsonschema | ≥4.23 | policy/action/assist/Husika payloads |
| LLM | google-genai SDK, model `gemini-2.5-flash` (env-configurable) | latest | structured output (JSON schema) only |
| Frontend | React 18 + TypeScript 5 + Vite 5 | — | SPA |
| UI kit | **MUI (Material UI) v6**: `@mui/material`, `@mui/icons-material`, `@mui/x-data-grid`, `@mui/lab` (Timeline) | ≥6.1 | Emotion styling engine (default) |
| Data fetching | TanStack Query v5 | — | all server state; no Redux |
| Router | react-router v6 | — | |
| Map | maplibre-gl | ≥4 | ICPAC pg_tileserv vector tiles |
| Forms | react-hook-form + zod | — | blocker/approval dialogs |
| Testing (BE) | pytest, pytest-asyncio, respx (httpx mocking) | — | |
| Testing (FE) | Vitest + React Testing Library; Playwright for the E2E golden path | — | |
| CI | GitHub Actions: lint (ruff, eslint), typecheck (mypy --strict on policy/ and cases/, tsc), tests, schema checks | — | CI badge in README |

---

## 5. Domain model and database schema

All tables via Alembic migration 001. Conventions: `id` TEXT ULID primary keys; all timestamps UTC ISO-8601 TEXT (SQLite) / timestamptz (Postgres); JSON columns as TEXT written with `json.dumps(..., sort_keys=True)`.

```sql
-- Users are seeded; no self-registration.
CREATE TABLE users (
  id            TEXT PRIMARY KEY,
  email         TEXT UNIQUE NOT NULL,
  display_name  TEXT NOT NULL,
  role          TEXT NOT NULL CHECK (role IN
                  ('ews_specialist','county_drm_officer','ngo_finance_lead','observer','admin')),
  org           TEXT NOT NULL,               -- e.g. 'ICPAC', 'Bungoma County DRM', 'KRCS'
  password_hash TEXT NOT NULL,               -- argon2
  signing_key   TEXT NOT NULL,               -- per-user random 32-byte hex; HMAC key (§6.7)
  created_at    TEXT NOT NULL
);

-- Immutable raw upstream captures. NEVER updated, NEVER deleted.
CREATE TABLE source_snapshots (
  id             TEXT PRIMARY KEY,
  adapter        TEXT NOT NULL,              -- 'icpac_triggers','icpac_datasets','icpac_areas',
                                             -- 'icpac_pipeline','replay'
  endpoint_url   TEXT NOT NULL,              -- exact URL or fixture path
  retrieved_at   TEXT NOT NULL,
  payload        TEXT NOT NULL,              -- raw JSON/CSV body, verbatim
  payload_sha256 TEXT NOT NULL,
  schema_ok      INTEGER NOT NULL,           -- passed adapter schema validation
  freshness      TEXT NOT NULL CHECK (freshness IN ('live','cached','stale','replay')),
  meta           TEXT NOT NULL DEFAULT '{}'  -- adapter-specific (issue date, season, area filter…)
);

-- Versioned content: a row per distinct file hash, loaded at startup.
CREATE TABLE policy_versions (
  id           TEXT PRIMARY KEY,             -- = sha256 of canonical file content
  kind         TEXT NOT NULL CHECK (kind IN ('policy','action_card')),
  name         TEXT NOT NULL,                -- 'policy.yaml' or action card id
  content      TEXT NOT NULL,                -- full YAML text
  loaded_at    TEXT NOT NULL
);

CREATE TABLE admin_areas (
  id        TEXT PRIMARY KEY,                -- GADM id from ICPAC, e.g. 'KEN.3_1'
  name      TEXT NOT NULL,                   -- 'Bungoma'
  country   TEXT NOT NULL,                   -- 'KEN'
  level     INTEGER NOT NULL,
  geometry  TEXT,                            -- GeoJSON from ICPAC areas API (nullable)
  centroid_lon REAL, centroid_lat REAL
);

CREATE TABLE decision_cases (
  id                 TEXT PRIMARY KEY,
  area_id            TEXT NOT NULL REFERENCES admin_areas(id),
  hazard             TEXT NOT NULL CHECK (hazard IN ('drought','flood','heat')),
  title              TEXT NOT NULL,
  state              TEXT NOT NULL CHECK (state IN
                       ('INGESTED','ASSESSED','NEEDS_EVIDENCE','READY_FOR_REVIEW',
                        'APPROVED','HANDED_OFF','REJECTED','REVOKED')),
  policy_version_id  TEXT NOT NULL REFERENCES policy_versions(id),
  assessment         TEXT,                   -- full Assessment JSON (§6.4 output), set at ASSESSED
  stage              TEXT CHECK (stage IN ('ready','set','go')),
  version            INTEGER NOT NULL DEFAULT 1,   -- optimistic concurrency
  created_by         TEXT NOT NULL REFERENCES users(id),
  created_at         TEXT NOT NULL,
  updated_at         TEXT NOT NULL
);

-- Which snapshots ground a case (many-to-many, append-only).
CREATE TABLE case_evidence (
  id           TEXT PRIMARY KEY,
  case_id      TEXT NOT NULL REFERENCES decision_cases(id),
  snapshot_id  TEXT NOT NULL REFERENCES source_snapshots(id),
  kind         TEXT NOT NULL CHECK (kind IN
                 ('trigger_rule','trigger_event','forecast','pipeline_csv','area','manual_note')),
  label        TEXT NOT NULL,
  added_by     TEXT NOT NULL REFERENCES users(id),
  added_at     TEXT NOT NULL
);

CREATE TABLE readiness_tasks (
  id             TEXT PRIMARY KEY,
  case_id        TEXT NOT NULL REFERENCES decision_cases(id),
  action_card_id TEXT NOT NULL,              -- references policy_versions.id of the card
  title          TEXT NOT NULL,
  owner_role     TEXT NOT NULL,              -- one of the user roles
  owner_user_id  TEXT REFERENCES users(id),
  criticality    TEXT NOT NULL CHECK (criticality IN ('critical','normal')),
  state          TEXT NOT NULL CHECK (state IN
                   ('PENDING','ACKNOWLEDGED','BLOCKED','RESOLVED','DECLINED')),
  blocker_code   TEXT,                       -- from taxonomy (§6.8); required when BLOCKED/DECLINED
  blocker_note   TEXT,
  updated_at     TEXT NOT NULL
);

CREATE TABLE approvals (
  id            TEXT PRIMARY KEY,
  case_id       TEXT NOT NULL REFERENCES decision_cases(id),
  role          TEXT NOT NULL CHECK (role IN
                  ('ews_specialist','county_drm_officer','ngo_finance_lead')),
  user_id       TEXT NOT NULL REFERENCES users(id),
  decision      TEXT NOT NULL CHECK (decision IN ('approve','reject','request_evidence')),
  comment       TEXT,
  signed_digest TEXT NOT NULL,               -- sha256 of canonical case snapshot at signing time
  signature     TEXT NOT NULL,               -- HMAC-SHA256(user.signing_key, signed_digest)
  signed_at     TEXT NOT NULL,
  superseded    INTEGER NOT NULL DEFAULT 0,  -- set when case is re-assessed after signing
  UNIQUE (case_id, role, superseded)         -- one live decision per role per case
);

-- Append-only, hash-chained audit trail. The core trust artifact.
CREATE TABLE case_events (
  seq        INTEGER PRIMARY KEY AUTOINCREMENT,
  id         TEXT UNIQUE NOT NULL,
  case_id    TEXT NOT NULL REFERENCES decision_cases(id),
  actor_id   TEXT NOT NULL,                  -- user id or 'system' or 'assist:<name>'
  event_type TEXT NOT NULL,                 -- CASE_CREATED, EVIDENCE_ATTACHED, ASSESSED,
                                            -- TASK_UPDATED, ASSIST_RAN, ASSIST_FAILED,
                                            -- STATE_CHANGED, APPROVAL_RECORDED, APPROVALS_SUPERSEDED,
                                            -- PACKET_GENERATED, EXPORT_GENERATED,
                                            -- STOP_TRIGGER_FIRED, CONFLICT_REJECTED
  data       TEXT NOT NULL,                  -- event payload JSON
  prev_hash  TEXT NOT NULL,                  -- hash of previous event row for this case ('' for first)
  this_hash  TEXT NOT NULL,                  -- sha256(prev_hash + canonical(data) + event_type + actor)
  created_at TEXT NOT NULL
);

CREATE TABLE exports (
  id          TEXT PRIMARY KEY,
  case_id     TEXT NOT NULL REFERENCES decision_cases(id),
  kind        TEXT NOT NULL CHECK (kind IN ('packet_pdf','packet_json','cap_xml',
                                            'husika_payload','field_bundle')),
  file_path   TEXT NOT NULL,                 -- under var/exports/
  sha256      TEXT NOT NULL,
  generated_by TEXT NOT NULL REFERENCES users(id),
  generated_at TEXT NOT NULL
);
```

**Invariants (enforce in service layer + tests):**
- `case_events` has no UPDATE/DELETE code path anywhere in the codebase.
- Every state change writes exactly one `STATE_CHANGED` event inside the same transaction.
- `decision_cases.version` must match the client-supplied version on every mutation; mismatch → HTTP 409 + `CONFLICT_REJECTED` event.
- An export row is written only after its file's hash is computed; export files are never overwritten (regeneration = new id, new file).

---

## 6. Backend specification (FastAPI)

### 6.1 Configuration and environment

`.env.example` (all read via `config.py`; the app must boot with only `LINDA_SECRET` and `DEMO_MODE=true` set):

```
LINDA_SECRET=                # JWT signing secret (required)
DATABASE_URL=sqlite:///var/linda.db
DEMO_MODE=true               # true → replay adapter allowed as fallback; banner shown in UI
GEMINI_API_KEY=              # optional; assists disabled gracefully if empty
GEMINI_MODEL=gemini-2.5-flash
ICPAC_BASE=https://eatriggersthresholds.icpac.net
HTTP_TIMEOUT_S=8
SNAPSHOT_TTL_MIN=30          # cache TTL before refetch
CORS_ORIGINS=http://localhost:5173
PUBLIC_BASE_URL=http://localhost:8000
```

### 6.2 Upstream source adapters

Common contract (`adapters/base.py`): every adapter method returns a `Snapshot` (maps to `source_snapshots`). Behavior, in order:
1. If a snapshot for the same logical query is younger than `SNAPSHOT_TTL_MIN` → return it (`freshness='cached'`).
2. Else fetch with httpx: timeout `HTTP_TIMEOUT_S`, 2 retries with exponential backoff on 5xx/timeouts, no retry on 4xx.
3. Store the **verbatim** response body + SHA-256 before any parsing.
4. Validate against the adapter's JSON Schema (`content/schemas/`). Validation failure → snapshot saved with `schema_ok=0`, adapter raises `UpstreamSchemaError` (surfaced in UI, never crashes a case).
5. On any fetch failure: return latest stored snapshot marked `stale`; if none and `DEMO_MODE`, delegate to the replay adapter (`freshness='replay'`).

Endpoints per adapter (all verified live 22 July 2026):

**`icpac_triggers.py`** — `GET {ICPAC_BASE}/api/triggers/rules/`, `/api/triggers/events/`, `/api/triggers/actions/`, `/api/triggers/check-logs/?page_size=20`. Parse into typed models: `TriggerRule` (id, name, area code, indicator, operator, threshold value/type, severity, active, notification emails **masked** — display `c***@igad.int`, never a real person's full address), `TriggerEvent`, `TriggerAction` (the email/dashboard action types — shown verbatim in the UI; this is the pitch), `CheckLog`.

**`icpac_datasets.py`** — `/api/datasets/`, `/api/datasets/indicators/`, `/api/datasets/forecasts/available/?forecast_type=return_period`, `/api/datasets/forecasts/seasons/?forecast_type=return_period`, `/api/datasets/forecasts/stats/?admin_level=1&valid_date={d}&lead_months={n}&min_probability=0&country={iso3}`. Typed models for the indicator registry and per-area return-period probability stats.

**`icpac_areas.py`** — `/api/areas/areas/?level={n}&code={iso3}` (GeoJSON FeatureCollection). Populates `admin_areas` (id, name, geometry, centroid). Runs at seed; refresh on demand via admin route.

**`icpac_pipeline.py` (`IcpacPipelineAdapter`)** — parses local files in the formats produced by `icpac-igad/ibf-thresholds-triggers`: the exceedance-probability CSVs of `03_prob_csv_q.py` (admin unit, season, quantile, probability) and optionally SPI NetCDF via `xarray` (guarded import; NetCDF is first in the cut order, §12). Output: the same `Snapshot` type + parsed per-area probability records. Ship 1–2 sample files in `fixtures/`, labeled with provenance. Purpose: prove file-level interoperability with ICPAC's scientific pipeline — not to run their pipeline.

**Redaction rule (all adapters):** raw payloads are stored verbatim in the DB, but any personal email address appearing in upstream data is masked in every API response, UI render, packet, and export.

### 6.3 Replay fixture engine

`adapters/replay.py` serves recorded snapshots from `fixtures/replay_ond2026/` with identical shape to live adapters, `freshness='replay'`. Requirements:
- Fixtures are real recorded responses (retrieved 22 July 2026) **plus** one synthetic escalation sequence (labeled `"synthetic": true` in meta) in which SPI-3 exceedance for the demo county steps across the READY→SET→GO thresholds — because the live OND 2026 signal may not cross any threshold during demo week.
- A global toggle (admin route + UI banner): `live_first` (default) or `replay_only` (for recording the video with no network). The UI **always** shows which mode produced each snapshot. Cached/stale/replay data is never presented as live — hard product rule.

### 6.4 Deterministic policy engine (`policy.yaml`)

Pure functions; no IO, no LLM, no randomness; 100% unit-test coverage target on `policy/`.

`content/policy.yaml` structure (validated by `content/schemas/policy.schema.json` at startup; the app refuses to boot on an invalid policy):

```yaml
policy:
  name: linda-demo-drought-policy
  authors: ["<team>"]
  disclaimer: >
    Team-authored demonstration policy. Thresholds, costs and effectiveness values are
    illustrative and are NOT official ICPAC, NDMA, or government policy.
  hazard: drought
  ndma_phase_mapping:            # display-only mapping to Kenya-native vocabulary
    ready: Alert
    set: Alarm
    go: Emergency
  stages:                        # Ready–Set–Go double confirmation (WFP Mozambique pattern, NHESS 2024)
    ready:
      indicator: spi3_chirps_forecast
      condition: { probability_gte: 0.35, quantile: 0.33, min_lead_months: 2 }
    set:
      indicator: spi3_chirps_forecast
      condition: { probability_gte: 0.50, quantile: 0.33, min_lead_months: 1 }
    go:
      indicator: spi3_chirps_forecast
      condition: { probability_gte: 0.60, quantile: 0.20 }
  gates:                         # ALL must pass for a stage recommendation
    - id: source_freshness      # newest grounding snapshot < 45 days (seasonal cadence)
    - id: schema_valid          # all grounding snapshots schema_ok
    - id: data_completeness     # exposure + cost fields present on every eligible card
    - id: lead_time             # card lead_time_days fits before valid_date
  stop_trigger:
    description: revoke if the signal collapses
    condition: { probability_lt: 0.30, on_indicator: spi3_chirps_forecast }
  cost_loss:
    exposed_households: { source: manual, value: 12000,
                          citation: "team estimate for demo; replace with WorldPop-derived figure" }
    loss_per_household_usd: 180
    margin_usd: 5000             # net benefit must exceed this
skill_display:                   # optional; shown beside triggers only when a published source is configured
  hit_rate: null
  false_alarm_ratio: null
```

`engine.evaluate(policy, snapshots, area, action_cards) -> Assessment` returns:

```json
{
  "policy_version_id": "…",
  "stage": "set",
  "ndma_phase": "Alarm",
  "gates": [{"id":"source_freshness","passed":true,"detail":"snapshot 2026-07-22, 0d old"}],
  "stage_trace": [{"stage":"ready","condition":"P>=0.35 @q0.33","observed":0.52,"passed":true}],
  "cost_loss_trace": {
    "expected_avoidable_loss": "P 0.52 × 12000 hh × $180 × eff 0.35 = $393,120",
    "action_cost": "$118,000", "net_expected_benefit": "$275,120", "exceeds_margin": true,
    "every_input_source": [{"field":"exposed_households","source":"manual","citation":"…"}]
  },
  "eligible_action_cards": ["card_destocking_v1","card_water_trucking_v1"],
  "ineligible": [{"card":"card_seed_distribution_v1","reason":"lead_time gate failed (needs 60d, have 41d)"}],
  "stop_trigger": {"armed": true, "condition":"P<0.30", "last_checked": "…"},
  "compound_signals": []
}
```

Every number in the trace carries its source label: `official_source` (from a snapshot) / `policy_assumption` (from policy.yaml) / `user_entered`. The UI renders these as distinct chip colors (§7.10). The LLM never touches this object except to *read* it.

### 6.5 Action card library

`content/actions/*.yaml`, one card per file, schema-validated. Card shape:

```yaml
id: card_destocking_v1
hazard: drought
title: Commercial destocking support
description: Facilitate early livestock offtake at fair prices before body-condition collapse.
owner_role: ngo_finance_lead
supporting_roles: [county_drm_officer]
lead_time_days: 30
stage_required: set              # earliest stage at which this card becomes eligible
budget:                          # two-tranche anatomy (IFRC EAP pattern; cite EAP2022KE02 as pattern source)
  currency: USD
  readiness_tranche: { amount: 18000, released_at_stage: ready,
                       items: ["transport framework contracts","market-day coordination"] }
  action_tranche:    { amount: 100000, released_at_stage: go,
                       items: ["price support","offtake logistics"] }
effectiveness: 0.35              # fraction of loss avoided; policy_assumption
prerequisites:
  - { id: transport_secured, title: "Transport contracts confirmed", criticality: critical }
  - { id: market_dates, title: "Market days scheduled with county", criticality: normal }
evidence_required: [forecast, trigger_event]
citations:
  - "IFRC Kenya drought EAP2022KE02 (budget-tranche pattern)"
disclaimer: Illustrative demo card, not an official SOP.
```

Ship **6 cards** — drought: destocking, water trucking, fodder pre-positioning, seed distribution (deliberately failing lead-time in the demo scenario); flood: evacuation-route pre-positioning, NFI pre-positioning (for the compound-signal beat). "Tranche release" is recorded as a **recommendation line in the packet** (`recommended_release: readiness_tranche $18,000 upon this approval`) — the system moves no money and says so on every surface where money appears.

### 6.6 Case state machine

`cases/state_machine.py` — the only place transitions are defined:

```
INGESTED → ASSESSED                      (system, after evaluate())
ASSESSED → NEEDS_EVIDENCE                (any signer role; or system when a gate fails)
ASSESSED → READY_FOR_REVIEW              (county_drm_officer; guard: all gates passed AND
                                          no critical task in PENDING/BLOCKED/DECLINED)
NEEDS_EVIDENCE → ASSESSED                (system, on new evidence + re-evaluate)
READY_FOR_REVIEW → APPROVED              (system, when 3rd distinct-role 'approve' signature lands)
READY_FOR_REVIEW → REJECTED              (any signer role records 'reject')
READY_FOR_REVIEW → NEEDS_EVIDENCE        (any signer records 'request_evidence')
APPROVED → HANDED_OFF                    (county_drm_officer, after ≥1 export generated)
APPROVED | HANDED_OFF → REVOKED          (system via stop-trigger; or county_drm_officer manually
                                          with mandatory reason)
```

Guards that must be impossible to bypass (proven by tests that attempt them through the API):
- No AI assist, and no `observer`, can cause any transition.
- A case with a `critical` task not in `ACKNOWLEDGED`/`RESOLVED` cannot enter `READY_FOR_REVIEW`.
- `APPROVED` is reachable **only** via three valid signatures from three distinct roles (§6.7).
- New evidence → re-assessment marks prior approvals `superseded=1` (event `APPROVALS_SUPERSEDED`); signatures must be re-collected. Nothing is deleted.
- Terminal states: `REJECTED`, `REVOKED` (no transitions out; open a new case).

### 6.7 Multi-role approval and signing

- Canonical snapshot: `canonical_case_json(case)` = sorted-keys JSON of {case id, area, state, policy_version_id, assessment, task states, evidence snapshot hashes}. `signed_digest = sha256(canonical)`.
- Signature: `HMAC-SHA256(user.signing_key, signed_digest)` hex, stored with the approval; a verification endpoint recomputes both.
- The packet prints each signature (truncated), signer, role, timestamp, and the digest it covers — a judge can verify all three signatures cover the *same* case state.
- **Honesty framing (must appear in README + packet footer):** this is integrity protection and non-repudiation *within the demo system* (server-held keys). Call it a "cryptographically signed decision record (HMAC-SHA256)"; never call it PKI, digital signatures, or blockchain.
- Required roles: `ews_specialist`, `county_drm_officer`, `ngo_finance_lead` — one `approve` each; any `reject` short-circuits to REJECTED; no user can hold two roles.

### 6.8 Readiness tasks and blocker taxonomy

When a card becomes eligible, its prerequisites materialize as `readiness_tasks`. Owners act via API/UI: acknowledge, resolve, decline, or block. Blockers require a code from the fixed taxonomy (also the Blocker Structurer's output enum):

`LOGISTICS_TRANSPORT · LOGISTICS_STORAGE · FINANCE_UNAVAILABLE · FINANCE_DELAYED · AUTHORITY_APPROVAL_MISSING · DATA_MISSING · SECURITY_ACCESS · STAFFING · MARKET_CONDITIONS · OTHER`

Each blocker: code + free-text note + owner + timestamp. Critical-path logic per §6.6. The Readiness Board must visibly show a blocked critical task preventing review — this is a scripted demo beat.

### 6.9 Compound signal detection

Deterministic overlap check — **not** a scientific index (never call it "CHRI" or an "index" in UI or submission):
- Rule: if a case's admin area has ≥2 active signals of *different hazard categories* among its evidence (e.g., drought forecast ≥ ready-stage AND a flood/rainfall trigger event from `/api/triggers/events/`), set `compound_signals: ["drought","flood"]` on the Assessment.
- Effect: a MUI `Alert severity="warning"` "Compound signals present" banner on the case; the action-card matcher includes cards of both hazards; the packet lists both signal chains.
- Implementation: one pure function over the evidence set, ~50 lines + tests. Anything more is out of scope.

### 6.10 Constrained AI assists (Gemini)

Common wrapper (`assists/client.py`): structured output with an explicit JSON schema per assist; temperature 0.2; 10s timeout; on invalid JSON → one retry with the validator error appended; on second failure → raise `AssistUnavailable`, write `ASSIST_FAILED` event, UI shows "Assist unavailable — deterministic workflow unaffected." Assist output is stored as an event and rendered **only** in clearly-labeled "AI explanation" surfaces. If `GEMINI_API_KEY` is empty, assist buttons render disabled with a tooltip — the golden workflow must be fully completable with assists off.

| Assist | Input | Output schema (in `content/schemas/`) | Hard prohibitions (enforced by schema + prompt) |
|---|---|---|---|
| **Evidence Explainer** | Assessment JSON + snapshot metadata | `{summary: string, cited_snapshot_ids: string[], missing_inputs: string[]}` | May not emit numbers absent from input; every claim cites a snapshot id; lists missing inputs instead of inferring |
| **Action Matcher** | Assessment + full card library | `{candidates: [{card_id, rationale, rank}]}` — `card_id` constrained to an enum of existing ids | Cannot invent cards, costs, or commitments; deterministic eligibility (§6.4) filters its output — it only re-ranks/narrates within the eligible set |
| **Blocker Structurer** | Free-text field report | `{code: <taxonomy enum>, severity: 'critical'\|'normal', summary, needs_human_review: bool}` | Output is a *suggestion*; a human confirms before any task state changes |

Prompt rules (`prompts.py`): every system prompt states the assist's read-only role, forbids financial promises and certainty inflation, and instructs refusal via `missing_inputs`/`needs_human_review` rather than guessing. Untrusted text (field reports) is passed as data, never concatenated into system prompts.

### 6.11 Activation Decision Packet generator

`exports/packet.py`. Two artifacts, generated together, both hashed and recorded in `exports`:

1. **`packet.json` (manifest)** — machine-readable: case snapshot; every evidence item (adapter, URL, retrieved_at, sha256, freshness); policy version hash + full gate/stage/cost-loss traces; task history; the three approvals (role, signer, digest, signature, timestamp); compound signals; tranche recommendation lines; event-chain head hash; generation timestamp. Top-level `manifest_sha256` computed over the sorted-keys body.
2. **`packet.pdf`** — WeasyPrint from `templates/packet.html`: header (case, area, hazard, state, packet id + hash); provenance table; "Why this action" trace rendered verbatim; action cards with tranche lines ("recommended release — requires the recorded human approvals; this document moves no funds"); readiness board final state incl. blockers; approval block with three signatures; AI-explanation section clearly boxed and labeled; footer citing the Thresholds platform, IGAD AA Roadmap, Kenya DRM Act 2026, the repo URL, and the policy disclaimer.

Rule: packets are generated from the **persisted** case record, never from in-memory UI state; regeneration produces a new export id and file (old files immutable).

### 6.12 CAP 1.2 exporter

`exports/cap.py`:
- Build CAP 1.2 XML per the OASIS schema (`fixtures/cap/cap12.xsd`): `alert` → identifier (case id), sender `linda-protocol-demo`, sent, status **`Exercise`** (never `Actual` — this is a demo; say so in the video), msgType `Alert` (and **`Cancel`** on the REVOKED path — implement both), scope `Restricted`, restriction "hackathon demonstration".
- `info`: category `Met`; event from hazard; urgency/severity/certainty mapped from stage (`go→Immediate/Severe/Likely`, `set→Expected/Moderate/Likely`, `ready→Future/Minor/Possible`); onset = valid_date; `area` with `areaDesc` = area name and `geocode` `{valueName:"GADM", value:"KEN.3_1"}`; polygon from stored geometry when present.
- Every generated CAP file must validate against the XSD in tests.
- **Public Atom feed:** `GET /cap/feed.xml` lists CAP entries for APPROVED/HANDED_OFF/REVOKED cases (unauthenticated — the interoperability showpiece; only Exercise-status alerts ever appear).

### 6.13 Husika handoff exporter

`exports/husika.py`:
- Vendor `fixtures/husika_openapi/ingestor.openapi.json` — a snapshot of `https://api.ingestor.husika.icpac.net/openapi.json` retrieved 22 July 2026; record its sha256.
- Build a payload for Husika's ingestor content-creation shape (threat/broadcast): event type from their 17-value enum (`drought`, `flood`, …), threat level (`warning`/`watch`/`advisory`/`statement` mapped from stage), severity/urgency/certainty enums, language from their 14-language enum (demo: `en`, `sw`), title/body composed from the approved case (body is the human-reviewed message, editable in the Handoff screen before generation), area targeting via the GADM reference.
- Validate the payload against the schema extracted from the vendored spec (`jsonschema`); the same validation runs in CI (§9).
- Output = downloadable JSON + on-screen chip "validates against Husika ingestor OpenAPI (spec snapshot sha256 …)". **No HTTP call to Husika is ever made.** UI copy, exactly: "Ready for dispatch by an authorised Husika operator."

### 6.14 Air-gapped field bundle exporter

`exports/bundle.py` — one click on an APPROVED/HANDED_OFF case produces `linda-bundle-<caseid>.zip`:
- `dossier.html` — self-contained offline dossier from `templates/offline_dossier.html`: **zero external requests** (inline CSS, system font stack, inline SVG mini-map from stored geometry; no JS beyond optional inline vanilla section-toggles). Same content as the PDF packet.
- `manifest.json` — the packet manifest (§6.11).
- `alert.cap.xml` — the CAP export.
- `checksums.txt` — sha256 of every file in the bundle.
- Test: Playwright opens `dossier.html` from `file://` with network disabled and asserts zero network requests and visible content.

### 6.15 Authentication and roles

- Seeded users only (§8): email+password (argon2) login → JWT (24h) in an httpOnly cookie; `GET /api/me` returns profile+role.
- FastAPI dependencies: `require_role(*roles)` on every mutating route per §6.16. `observer` reads everything, mutates nothing.
- No self-registration, no password reset, no OAuth — out of scope; stated in README.
- Hygiene: CORS restricted to configured origins; all inputs Pydantic-validated; no secrets in exports (tested); login rate-limited (slowapi, 5/min/IP).

### 6.16 REST API surface (complete)

All under `/api` except public routes. All responses typed with Pydantic; errors as `{"error": {"code","message","detail"}}`. Roles: drm = county_drm_officer, ews = ews_specialist, ngo = ngo_finance_lead.

| Method & path | Auth (roles) | Purpose |
|---|---|---|
| `POST /api/auth/login` · `POST /api/auth/logout` · `GET /api/me` | public / any | session |
| `GET /api/sources/status` | any | per-adapter: last snapshot, freshness, mode (live/replay) |
| `POST /api/sources/refresh` | drm, ews, admin | force refetch all adapters; returns new snapshot ids |
| `GET /api/sources/snapshots?adapter=&limit=` | any | snapshot list (payload truncated) |
| `GET /api/sources/snapshots/{id}` | any | full snapshot incl. raw payload (emails masked) |
| `GET /api/signals` | any | merged Signal Inbox: trigger rules+events, forecast issues, pipeline files — each with snapshot ref |
| `GET /api/areas?country=&level=` | any | admin areas |
| `POST /api/cases` | drm | create case {area_id, hazard, title, evidence snapshot ids} |
| `GET /api/cases?state=&area=` · `GET /api/cases/{id}` | any | list / detail (detail embeds assessment, tasks, approvals, evidence, compound signals) |
| `POST /api/cases/{id}/evidence` | drm, ews | attach snapshot(s); triggers re-assessment |
| `POST /api/cases/{id}/assess` | drm (also called internally) | run policy engine; writes Assessment; INGESTED→ASSESSED |
| `POST /api/cases/{id}/transition` | per §6.6 | body {to_state, version, reason?}; 409 on version mismatch; 422 naming the failed guard |
| `POST /api/cases/{id}/tasks/{taskId}` | task owner_role | {action: acknowledge/resolve/decline/block, blocker_code?, note?, version} |
| `POST /api/cases/{id}/approvals` | ews, drm, ngo | {decision, comment?, version} → digest, sign, may auto-transition |
| `GET /api/cases/{id}/approvals/verify` | any | recompute digests/signatures; per-signature validity |
| `POST /api/cases/{id}/assists/{explainer\|matcher\|blockers}` | drm, ews, ngo | run assist; 503 `AssistUnavailable` handled by UI |
| `POST /api/cases/{id}/exports/{packet\|cap\|husika\|bundle}` | drm (packet/cap/bundle); drm or ngo (husika) | generate; returns export row |
| `GET /api/exports/{id}/download` | any | file download |
| `GET /api/cases/{id}/events` | any | full hash-chained event log |
| `GET /api/cases/{id}/events/verify` | any | walk the chain; first broken link or ok |
| `GET /api/library/policy` · `GET /api/library/actions` | any | active policy + cards with version hashes |
| `POST /api/admin/replay-mode` | admin | {mode: live_first \| replay_only} |
| `POST /api/admin/seed` | admin | idempotent re-seed (demo recovery lever) |
| `POST /api/admin/simulate-stop-trigger` | admin | inject the stop-condition replay snapshot → fires revocation (scripted demo beat) |
| `GET /healthz` · `GET /cap/feed.xml` | public | liveness; CAP Atom feed |
| `/integration/v1/*` (activations, verify, husika-payload, webhooks, docs) | public docs/feed; API key for data; admin for key/webhook management | the consumable integration API — full contract in §6.18 |

### 6.17 Failure posture (required behaviors)

| Failure | Required behavior |
|---|---|
| ICPAC API timeout/5xx/schema drift | Serve last snapshot as `stale` with visible badge; adapter error logged as event; replay fallback only in DEMO_MODE, always labeled |
| No live signal crosses thresholds | Never fabricate: live case shows "no activation recommended"; demo uses the labeled synthetic escalation fixture |
| Gemini down / invalid JSON | §6.10 — assist marked unavailable; zero impact on the workflow |
| Concurrent edits | Optimistic version check → 409 + `CONFLICT_REJECTED` event; UI offers reload-and-retry |
| Guard violation via direct API call | 422 naming the guard; covered by tests |
| Export regeneration | New immutable file; prior exports remain downloadable |
| DB missing/empty on boot | Auto-migrate + auto-seed in DEMO_MODE |

### 6.18 Consumable integration API (for Husika and partners)

Linda Protocol is not only a consumer of ICPAC APIs — it **exposes its own documented, versioned, consumable API** so that Husika (or any partner system: NDMA, an NGO tracker, IFRC GO) could integrate approved activations without custom work. This mirrors Husika's own architecture (content created upstream → approved → disseminated) and is a first-class deliverable, not a byproduct: it is the demonstrable answer to "how would ICPAC actually adopt this?"

**Design principles**
1. **Read-only and outbound-only.** The integration API exposes *approved or revoked* activations and their evidence. It never accepts inbound writes from partners (no attack surface, no governance bypass) — partners consume; humans decide inside Linda.
2. **Versioned and contract-stable.** Everything lives under `/integration/v1/`; response shapes are frozen by published JSON Schemas in `content/schemas/integration/` and covered by snapshot tests (§9). Breaking changes would require `/v2/` — stated in the docs page.
3. **Standards-first.** The primary integration path is CAP 1.2 (§6.12) because Husika's data model is already CAP-shaped (severity/urgency/certainty/event); the REST surface exists for consumers that want the full decision record, not just the alert.
4. **Verifiable by the consumer.** Every payload carries the hashes and signatures needed for the consumer to independently verify integrity — a partner does not have to trust Linda's UI, only its math.
5. **Honestly labeled.** Every response includes `"mode": "exercise"` and a `disclaimer` field while in demo; nothing on this surface can be mistaken for an operational government feed.

**Surfaces (implement in `api/routes_integration.py`)**

| Method & path | Auth | Returns |
|---|---|---|
| `GET /integration/v1/openapi.json` + `GET /integration/v1/docs` | public | Self-describing spec + human docs page (FastAPI's generated OpenAPI, filtered to integration routes only) |
| `GET /cap/feed.xml` | public | CAP 1.2 Atom feed of approved/revoked activations (§6.12) — the zero-custom-code path into any CAP-aware system |
| `GET /integration/v1/activations?since=&area=&hazard=&state=` | API key | Paginated list of published activations: id, area (GADM id + name), hazard, stage, NDMA phase, state, approved_at/revoked_at, links |
| `GET /integration/v1/activations/{id}` | API key | Full activation record: assessment trace, action cards with tranche recommendations, approvals (role, signer org, digest, signature), evidence provenance (source URLs + snapshot hashes), packet `manifest_sha256`, compound signals |
| `GET /integration/v1/activations/{id}/cap.xml` | API key | The CAP document for this single activation |
| `GET /integration/v1/activations/{id}/husika-payload.json` | API key | The Husika-ingestor-shaped payload (§6.13) — Husika could fetch this directly and pass it through its own Level-1/Level-2 approval before dispatch |
| `GET /integration/v1/activations/{id}/verify` | API key | Server-side recomputation of manifest hash, signature validity, and event-chain integrity, returned as a machine-readable verification report |
| `POST /integration/v1/webhooks` · `GET` · `DELETE /{id}` | admin (in-app) | Manage webhook subscriptions: `{url, events: [activation.approved, activation.revoked], secret}` |

**Webhook delivery (`exports/webhooks.py`)**
- On `APPROVED` and `REVOKED` transitions, POST to each subscription: body = the `/activations/{id}` record; headers `X-Linda-Event`, `X-Linda-Delivery` (ULID), and `X-Linda-Signature: sha256=HMAC-SHA256(subscription.secret, raw_body)` — the standard pattern (GitHub-style) any integrator already knows how to verify.
- Delivery: 10s timeout, 3 retries with backoff (1m/5m/25m) via a background task; each attempt logged as a `WEBHOOK_DELIVERED`/`WEBHOOK_FAILED` case event so delivery is itself auditable. No retry queue infrastructure — a simple `asyncio` task + DB-recorded attempts is enough at this scale.
- Demo beat: a tiny "partner console" page (see §7.6 addition) or a `webhook.site` URL on screen receiving the activation the moment the third signature lands.

**Auth for partners**
- Simple API keys (`integration_keys` table: id, label, key_hash, created_at, revoked_at), issued from the Admin screen, sent as `Authorization: Bearer <key>`. Rate limit 60 req/min/key. The CAP feed and docs stay public (a feed you must authenticate to read is not a feed).

**Husika integration story (what we say and can prove)**
- Demonstrable today: Husika's ingestor could consume `husika-payload.json` (already validated against their published OpenAPI schema) or poll the CAP feed and map fields 1:1 into its CAP-shaped model; a webhook removes even the polling.
- Phrasing discipline: "Linda exposes a documented, consumable API that Husika **could** integrate via CAP, REST, or webhooks" — never "Husika integrates with Linda." The integration is real and testable from our side; adoption is ICPAC's decision, and the demo says exactly that.

**Additional schema object**

```sql
CREATE TABLE integration_keys (
  id         TEXT PRIMARY KEY,
  label      TEXT NOT NULL,               -- 'Husika (demo)', 'Partner console'
  key_hash   TEXT NOT NULL,               -- argon2 of the bearer key; key shown once at creation
  created_at TEXT NOT NULL,
  revoked_at TEXT
);

CREATE TABLE webhook_subscriptions (
  id         TEXT PRIMARY KEY,
  url        TEXT NOT NULL,
  events     TEXT NOT NULL,               -- JSON array: ["activation.approved","activation.revoked"]
  secret     TEXT NOT NULL,               -- HMAC secret for X-Linda-Signature
  active     INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);

CREATE TABLE webhook_deliveries (
  id              TEXT PRIMARY KEY,
  subscription_id TEXT NOT NULL REFERENCES webhook_subscriptions(id),
  case_id         TEXT NOT NULL,
  event           TEXT NOT NULL,
  attempt         INTEGER NOT NULL,
  status_code     INTEGER,                -- null on network failure
  delivered       INTEGER NOT NULL DEFAULT 0,
  attempted_at    TEXT NOT NULL
);
```

---

## 7. Frontend specification (React + Material UI)

### 7.1 App shell, theme, navigation

- **Theme (`theme.ts`):** MUI v6 `createTheme` with `colorSchemes: { light: true, dark: true }` (CSS-vars mode; toggle in AppBar, persisted to localStorage).
  - Palette: primary `#1B5E20` (deep green — "Linda/protect"), secondary `#0D47A1`. Severity semantics used **consistently everywhere**: ready/watch = `warning.light` amber, set = `warning.dark` orange, go/severe = `error` red, none/normal = `grey.500`, approved = `success`.
  - Typography: Roboto; `h1–h4` weight 600; `'Roboto Mono'` for hashes, endpoint URLs, and calculation traces.
  - Shape `borderRadius: 10`; density: `size="small"` defaults on tables/inputs (data-dense app).
- **AppShell (`layout/`):** `AppBar` (app name + mode banner slot + user avatar/role chip + theme toggle) over a permanent `Drawer` (240px, collapses to icons below `md`). Nav (react-router): **Signal Inbox** (`/`), **Decision Cases** (`/cases`), **Audit Log** (`/audit`), **Policy & Actions** (`/library`), **Sources** (`/sources`), divider, **Admin** (admin only).
- **Global mode banner:** when any displayed data is `stale` or `replay`, a persistent `Alert severity="info"` strip under the AppBar: "Demo replay mode — data recorded 22 Jul 2026" / "Upstream unreachable — showing cached snapshot from …". Never hidden while applicable.
- **Feedback patterns:** every mutation → `Snackbar` (success/error); state-changing actions → `ConfirmDialog` (MUI `Dialog`) naming the transition and showing the case version being acted on.

### 7.2 Screen 1: Signal Inbox (`/`)

Purpose: prove live ICPAC integration at a glance.

Layout: `Grid` two columns (stacks below `md`). Left 7/12 signal list; right 5/12 map (§7.9) + source status card.

- **Signal list:** `Tabs` — "Trigger rules & events" / "Seasonal forecasts" / "Pipeline files" — each a MUI **`DataGrid`**. Columns: signal name, area (`Chip`), indicator, value/probability, severity (`StateChip`), source (`ProvenanceChip`), retrieved (relative time + `FreshnessBadge`: green Live / grey Cached / amber Stale / blue Replay), actions.
- **`ProvenanceChip` → Snapshot dialog:** exact endpoint URL (monospace, copy `IconButton`), retrieved_at, full SHA-256 (copyable), schema-validation status, collapsible raw payload (`Accordion` + `<pre>`). This dialog is a core demo artifact — polish it.
- The Bungoma trigger rule and the OND 2026 forecast rows must be findable in <3 seconds (pinned to top by demo seed sort order).
- **Row action "Open case":** if a case exists for area+hazard → navigate; else **Create Case dialog** (area/hazard pre-filled, originating snapshots pre-checked as evidence, title auto-suggested "OND 2026 drought — Bungoma"). Enabled only for drm role; others see it disabled with tooltip "Requires County DRM Officer role".
- **Source status card:** per-adapter rows (last fetch, freshness) + role-gated "Refresh" `LoadingButton`.
- States: `Skeleton` loaders; `EmptyState` with explanation; `ErrorPanel` with retry. (All three states are mandatory on **every** screen in this app.)

### 7.3 Screen 2: Decision Case — Evidence ("Why this action?") (`/cases/:id`, tab 1)

Shared case-page frame (tabs 1–4): header with title, area, hazard chip, **state `Stepper`** (horizontal: Ingested → Assessed → Review → Approved → Handed off; REJECTED/REVOKED render as a red error step), stage chip with NDMA phase ("SET · NDMA: Alarm"), compound-signal `Alert` when present, case `version` shown subtly (tooltip: optimistic concurrency).

Tab 1 content:
- **Evidence list:** `List` of items — kind icon, label, `ProvenanceChip`, freshness. "Attach evidence" (drm/ews) → dialog of recent snapshots as `Checkbox` rows.
- **Gate results:** one `Card` per gate — `CheckCircle`/`Cancel` icon, gate name, detail line. A failed gate names exactly what is missing ("exposure figure absent on card_seed_distribution — fix the card or remove it from policy").
- **Stage trace:** small `Table`: stage, condition (monospace), observed value, pass/fail.
- **Cost-loss trace:** `Card` with the formula line by line (monospace), each operand followed by its source chip — green `official source` / amber `policy assumption` / blue `user entered`. Legend in the `CardHeader`; same legend appears in the packet.
- **AI Evidence Explainer panel:** `Card` with dashed outline + `SmartToy` icon + header "AI explanation — generated from the trace above; cannot alter it." Body: summary with cited snapshot ids as chips; `missing_inputs` as a warning list. `LoadingButton` "Run explainer"; disabled when assists off; `AssistUnavailable` renders inline, not as a toast.

### 7.4 Screen 3: Action Cards & Readiness Board (`/cases/:id`, tab 2)

- **Eligible cards:** `Card` grid (2-up ≥`md`). Each: title, owner `RoleAvatar`, lead time, stage badge, **budget block** — "Readiness tranche $18,000 · at READY" / "Action tranche $100,000 · at GO" with `Info` tooltip: "Recorded recommendation only — Linda Protocol moves no funds." Ineligible cards render collapsed/greyed with the failing reason as red caption (seed guarantees one, e.g. seed distribution failing lead time).
- **Action Matcher strip:** dashed AI panel (same visual language as 7.3): rank + one-line rationale per eligible card. Never shows a card the deterministic filter excluded.
- **Readiness Board:** `DataGrid` of tasks: task, action card, owner role+user, criticality (`Chip color="error"` when critical), state (StateChip: Pending grey / Acknowledged blue / Blocked red / Resolved green / Declined dark red), blocker code+note, updated. Row actions per role: Acknowledge / Resolve / Decline / **Report blocker** — dialog: free-text + "Suggest classification" (Blocker Structurer pre-fills a `Select` of taxonomy codes + severity; human confirms) + submit.
- **Advance banner:** sticky bottom `Paper`: either contained `Button` "Send for review" (drm only, enabled only when guards pass) or a red explanation: "Blocked: critical task 'Transport contracts confirmed' is BLOCKED (LOGISTICS_TRANSPORT)". The button is disabled while blocked — and the API guard is the backstop, not the UI.

### 7.5 Screen 4: Approvals (`/cases/:id`, tab 3)

- **Co-signature matrix:** three `Card`s (row; stack on mobile) — EWS Specialist / County DRM Officer / NGO & Finance Lead. Each: one-line description of what the role attests, status `Chip` (Awaiting grey / Approved green with signer+time / Rejected red / Superseded amber), and — for the logged-in user's own role while READY_FOR_REVIEW — buttons **Approve & sign** / Request evidence / Reject (comment dialog).
- **Signing dialog:** shows the canonical digest (monospace, full), a summary of what the signature covers ("assessment v3, 6 tasks, 4 evidence snapshots"), and a required checkbox "I have reviewed the evidence trace." Success → sober `Snackbar` "Signature recorded — 2 of 3 roles approved."
- **Verification panel:** `Accordion` "Verify signatures" → calls the verify endpoint; renders each signature's validity and that all cover the same digest. (Demo beat: judges watch live verification.)
- **Superseded flow:** amber `Alert` explaining approvals were superseded by re-assessment and must be re-collected.

### 7.6 Screen 5: Handoffs & Exports (`/cases/:id`, tab 4)

Enabled from APPROVED. Four export `Card`s:
1. **Activation Decision Packet** — Generate → PDF + JSON rows with sha256 (`HashBlock`: monospace, copy button, first/last 8 chars, tooltip full) + downloads. Regenerate note: creates a new immutable export.
2. **CAP 1.2 alert** — Generate → XML preview `Dialog` (`<pre>`), chips "validated against CAP 1.2 XSD ✓" and status **Exercise**, link to public `/cap/feed.xml`.
3. **Husika payload** — message body editor (`TextField multiline`, pre-composed, human-editable; language `Select` en/sw) → Generate → JSON preview + green chip "Validates against Husika ingestor OpenAPI (spec sha256 …) ✓" + the exact sentence: *"Ready for dispatch by an authorised Husika operator — Linda Protocol does not send."*
4. **Air-gapped field bundle** — Generate → zip download + contents list + checksums.

Below the export cards, an **Integration card** (§6.18): shows this activation's consumable endpoints as copyable monospace rows (`/integration/v1/activations/{id}`, `…/cap.xml`, `…/husika-payload.json`, `…/verify`, plus the public feed URL), webhook delivery status per subscription (green check + timestamp / red retry count, from `webhook_deliveries`), and a link to `/integration/v1/docs`. Caption: "Consumable by Husika or any partner system — read-only, verifiable, Exercise-labeled."

Bottom: "Mark as handed off" (drm; requires ≥1 export) → HANDED_OFF. **Revocation panel** (APPROVED/HANDED_OFF): shows the armed stop-trigger condition; manual revoke (drm, reason required). When the stop-trigger fires (admin simulate route during demo), the case banner turns red — "REVOKED — stop trigger: P fell to 0.22 on snapshot …" — and a CAP `Cancel` export becomes available; subscribed webhooks receive `activation.revoked`.

**Admin screen addition (`/admin`):** API-key management (create with label → key shown once → revoke) and webhook subscription management (URL, events, secret, active toggle, last-delivery status) — plain MUI `DataGrid` + dialogs; this is also where the demo's "partner console" webhook is registered.

### 7.7 Screen 6: Audit Log (`/audit` + per-case "Log" tab)

- Per-case: MUI **`Timeline`** (`@mui/lab`) — dot color by event type; each item: event type, actor (user chip / "system" / "assist:<name>" with robot icon), relative + absolute time, expandable payload (`Accordion` + `<pre>`), `this_hash` (`HashBlock`).
- Chain banner: "Verify chain" → green `Alert` "37 events, hash chain intact" or red with the first broken seq.
- Global `/audit`: `DataGrid` across cases with filters (case, actor, event type, date range) — read-only, all roles.

### 7.8 Screen 7: Policy & Action Library (`/library`)

- **Policy tab:** active `policy.yaml` read-only (syntax-highlighted), version hash, the disclaimer in a prominent `Alert severity="warning"`, and stages/gates/stop-trigger rendered as a friendly table.
- **Action cards tab:** all cards using the same Card component as 7.4 + raw YAML accordion + version hash. Editing happens in git, not the UI — an `Info` alert states: "Policies are code-reviewed files; the running version is hash-pinned."

### 7.9 Map component

`features/map/AreaMap.tsx` — MapLibre GL:
- Basemap: Carto raster tiles (light/dark matching theme) — no API-key dependency.
- Vector overlay: ICPAC pg_tileserv `boundary.gadm_41_admin_level_1` (tile URL taken from `/tileserv/index.json`), styled: thin grey outlines; areas with signals filled by severity color at 35% opacity; selected case area bold outline.
- Interactions: hover popup (area name, top signal); click → same "Open case" flow as the inbox. The map is context, not the product — keep it modest.
- Fallback: if tiles fail within 5s, render stored GeoJSON geometries client-side + stale-tiles notice. The demo must not depend on ICPAC's tile server being up.

### 7.10 Cross-cutting frontend rules

1. **Provenance colors are law:** green = official source, amber = policy assumption, blue = user-entered, dashed outline = AI output. Legend reachable from an AppBar help icon.
2. Every async view implements `Skeleton`, `EmptyState`, and `ErrorPanel` with retry. No blank screens; no uncaught-promise toasts.
3. All server state via TanStack Query (`staleTime` 30s) with invalidation on every mutation; case detail refetches after any mutation returning a new `version`.
4. Role-gating in UI = disabled + tooltip (never hidden), so the demo can *show* the permission model; the API remains the enforcer.
5. Responsive: judges may open the URL on phones — AppShell collapses, grids stack, DataGrids use `columnVisibilityModel` on narrow screens. Test at 375px width.
6. Accessibility floor: every `IconButton` has `aria-label`; severity color always paired with text; visible focus; Lighthouse a11y ≥ 90.
7. No i18n framework — `strings.ts` constant map centralizes copy; Swahili UI is out of scope (the *Husika payload* carries sw content — that is the multilingual story).
8. Bundle hygiene: route-level code splitting (`React.lazy`); maplibre chunk lazy-loaded; target < 450 KB initial gzip.

---

## 8. Seed data and demo scenario

`POST /api/admin/seed` (idempotent) + auto-seed on empty DB in DEMO_MODE:

- **Users (password `linda-demo`, printed in README):**
  `amina.ews@demo` (ews_specialist, ICPAC-affiliated demo persona) · `david.drm@demo` (county_drm_officer, Bungoma County) · `grace.ngo@demo` (ngo_finance_lead, KRCS demo persona) · `observer@demo` · `admin@demo`. All personas fictional; say so in README.
- **Areas:** Kenya admin-1 from the live areas API (fixture fallback), Bungoma (`KEN.3_1`) guaranteed present.
- **Snapshots:** recorded real fixtures — trigger rules/events/actions/check-logs (22 Jul 2026), OND 2026 return-period forecast availability + stats, indicator registry — plus the **synthetic escalation sequence** (three forecast snapshots stepping P 0.32 → 0.52 → 0.63, each `synthetic:true`) and one synthetic rainfall trigger event for the compound-signal beat.
- **Cases:** (1) "OND 2026 drought — Bungoma" at ASSESSED with one critical task BLOCKED (the scripted blocker beat); (2) a completed HANDED_OFF case with all four exports generated (judges inspect finished artifacts immediately); (3) a REVOKED case showing the stop-trigger path.
- **Action cards:** the 6 cards of §6.5.
- Demo recovery: re-running seed restores exactly this state in < 10 s.

---

## 9. Testing requirements

CI (GitHub Actions) runs all of these on every push; a red build blocks merge to main.

**Unit (pytest):**
- Policy engine: every stage boundary (P at / just below / just above each threshold), every gate pass/fail, stop-trigger, cost-loss arithmetic vs hand-computed values, ineligibility reasons.
- State machine: every legal transition; **every illegal transition attempted and asserted rejected** — including assist/observer actors, approval with only 2 signatures, review with a blocked critical task, transitions out of terminal states.
- Approvals: canonical-JSON stability (key order, whitespace), digest determinism, signature verification, superseding on re-assessment, distinct-roles rule.
- Event chain: append + verify; tamper test (mutate a row in the test DB → verify reports the broken link).
- Adapters: schema accept/reject; email masking; TTL cache logic (respx-mocked).
- Exporters: packet manifest hash stability; CAP validates vs XSD (incl. Cancel); Husika payload validates vs vendored spec; **negative test** — a deliberately wrong enum fails validation; bundle checksums match.
- Assists: mocked Gemini — valid path, invalid-JSON retry path, hard-fail path, schema-violation (invented card_id) rejection.

**Contract:** recorded fixtures for every ICPAC endpoint; a manually-triggerable workflow re-fetches live endpoints and diffs schemas, failing loudly on drift — demo-week insurance.

**Integration (pytest + TestClient):** the full golden workflow via API only: seed → create → assess → tasks → block/unblock → review → 3 approvals → 4 exports → handoff → simulate stop-trigger → revoked; assertions on every intermediate state and the final event chain.

**E2E (Playwright):** the golden workflow through the real UI against a seeded backend (login as each role in sequence); the offline-bundle zero-network test (§6.14); a full `replay_only` run proving the demo works with no internet.

**Integration API (§6.18):** snapshot tests freezing every `/integration/v1/` response shape against the published JSON Schemas (a shape change fails CI — this *is* the version contract); API-key auth (valid key, revoked key, missing key, rate limit); webhook delivery — signature header verifiable with the subscription secret, retry/backoff on failure, `WEBHOOK_FAILED` event after final attempt; `verify` endpoint returns invalid for a tampered record; every integration response carries `mode: "exercise"` + disclaimer.

**Security-minded checks:** role-bypass attempts on every mutating route; XSS probe strings through blocker notes and the Husika body editor (rendered escaped); no secret/env values in any export file or integration/webhook payload; API keys stored hashed, shown once; login rate-limit.

---

## 10. Deployment

- **Images:** `backend/Dockerfile` (python:3.12-slim + WeasyPrint system deps: libpango, cairo, gdk-pixbuf). Frontend built in CI and baked into the backend image at `/app/static` (FastAPI `StaticFiles` + SPA fallback) → **one container serves everything**.
- **docker-compose.yml:** `api` (port 8000, volume for `var/` SQLite + exports) + optional `postgres` profile. `docker compose up` then `:8000` must work from a clean clone with only `.env` copied.
- **Hosting:** Fly.io or Railway (decide day 7 — whichever deploys fastest), name like `linda-protocol.fly.dev`, persistent volume for `var/`, `PUBLIC_BASE_URL` set so the CAP feed URL is correct.
- **Ops:** `/healthz` returns `{status, db, adapters_last_ok, mode}`; structured JSON logs; the deployed git SHA shown in the UI footer.
- **Demo insurance:** the deployed instance runs `live_first`; a local `replay_only` copy on the presenting laptop; the video is recorded against the deployed instance, with live data where possible and replay labeled as replay.

---

## 11. Nine-day build plan with exit criteria

| Day (date) | Build | Exit criterion (demoable, not "coded") |
|---|---|---|
| 1 (Jul 23) | Repo scaffold (backend + frontend + CI), migrations, auth + seeded users, adapters for triggers/datasets/areas with snapshot store, fixtures recorded | `GET /api/signals` returns live ICPAC data with hashes; login works; CI green |
| 2 (Jul 24) | Policy engine + action cards + schemas + full unit tests; replay engine + synthetic escalation | `POST /assess` produces the full Assessment for Bungoma from live *and* replay data; boundary tests pass |
| 3 (Jul 25) | Case service, state machine, event chain, tasks/blockers, approvals + signing; API-only integration test of the golden path | Whole workflow completable via HTTP; illegal transitions provably rejected |
| 4 (Jul 26) | Frontend: AppShell, theme, login, Signal Inbox (grid, provenance dialog, freshness badges), map | A judge-shaped human can find the Bungoma rule and OND 2026 forecast and open a case in the browser |
| 5 (Jul 27) | Frontend: case tabs 1–3 (evidence/trace, cards + readiness board, approvals) wired end-to-end | Three role logins take one case from ASSESSED to APPROVED entirely in the UI, incl. the blocker beat |
| 6 (Jul 28) | Exporters: packet PDF+manifest, CAP + feed + XSD tests, Husika payload + spec validation, air-gapped bundle; Handoffs tab; audit screens | All four exports download from the UI; CAP validates; bundle opens offline; chain-verify green |
| 7 (Jul 29) | AI assists (all three) + prompts + failure paths; compound-signal detection; stop-trigger simulation; **integration API (§6.18): read endpoints + docs + API keys + webhooks + Integration card**; deploy; Playwright E2E | Deployed URL runs the golden workflow; assists demoable AND the app fully usable with assists disabled; a webhook.site URL receives the signed `activation.approved` payload on the third signature |
| 8 (Jul 30) | **README rewrite** (Linda Protocol: what/why/run/screens/tests/acknowledgements per hackathon disclosure rules), Devpost texts (adapt research.md §27 within the 250-word caps + §13 corrections), record + edit the 5-min video (research.md §26 script + §13 corrections), polish pass (empty/error states, mobile) | A teammate reproduces setup from README alone on a clean machine; video uploaded (unlisted) |
| 9 (Jul 31) | Buffer: fixes, re-record if needed, submit by 12:00 EAT (5-hour margin), test the judge flow from an incognito phone | Devpost submission confirmed before 17:00 EAT |

Two-person split: A = backend (days 1–3, then 6–7 exporters/assists), B = frontend (days 4–6), converge days 7–9. Solo: follow the order as-is; §12 governs cuts.

## 12. Cut order if behind schedule

Cut from the top; items below the line are the product and are never cut:

1. NetCDF support in `IcpacPipelineAdapter` (keep CSV)
2. Compound-signal detection
3. Map vector-tile overlay (keep client-side GeoJSON rendering)
4. Action Matcher + Blocker Structurer assists (keep Evidence Explainer)
5. Global audit screen (keep per-case timeline)
6. Webhook subscriptions + deliveries (keep the read endpoints, docs, and CAP feed — the consumable API survives; only push notification is cut)
7. Dark mode
8. Husika payload **editor** (keep generated payload + validation)

— never cut: Signal Inbox provenance, policy trace, state machine + guards, 3-role signing, event chain, packet, CAP export + public feed, `/integration/v1/` read endpoints + docs, air-gapped bundle, replay fallback, seed script, and the tests covering all of these.

## 13. Claims discipline (submission and demo)

Use the Part III demo script (research.md §26) **with these binding corrections**:

- CAP alerts are status **Exercise**; say "demonstration alert" on camera.
- Tranches: say "records the recommended release for human authorisation" — never "releases funds" or "$25k is released now."
- Signing: say "cryptographically signed decision record (HMAC)" — never PKI / digital signatures / blockchain.
- Crimson Sikolia's rule: show the rule name with the masked email; do not read out a personal address; tone respectful ("ICPAC's own live test rules"), and note they are visibly test data, not operational policy.
- Never claim: first/only activation platform (cite 510 IBF-system and IFRC National Risk Watch as validation of the gap, then state what we add: open, ICPAC-native, multi-party approval, immutable packet); "integrates with Husika" (say: "validates against Husika's published schema, ready for authorised dispatch"); "automatic activation"; the unverified Gemini/ICPAC roadmap claim; team-authored thresholds as official policy (the policy.yaml disclaimer appears on screen in the video).
- Integration API phrasing: "Linda exposes a documented, consumable API — CAP feed, REST, webhooks — that Husika **could** integrate," demonstrated live (docs page + webhook firing on approval). Never say Husika/ICPAC "will" or "does" consume it; the demo line is: "integration works in both directions — we validate against their published schema, and we publish one they can consume."
- Acknowledge in README + the Devpost form: ICPAC APIs & platforms, GADM boundaries, MUI, MapLibre, FastAPI, WeasyPrint, Gemini, and the provenance of every fixture — the rules require disclosure of all external tools/data/APIs.

## 14. Definition of done

- [ ] Golden workflow (§2) completable on the deployed URL by the three role logins, no console errors
- [ ] Every §6.16 endpoint implemented, role-guarded, typed
- [ ] Every §7 screen implements loading/empty/error states and the provenance color system
- [ ] All §9 suites green in CI; Playwright E2E green against a clean seed
- [ ] All four exports generate, validate (XSD / OpenAPI / checksums), and download; CAP feed publicly reachable
- [ ] Chain-verify and signature-verify both demonstrable in the UI
- [ ] Integration API live on the deployed URL: `/integration/v1/docs` renders, activations readable with an API key, `verify` endpoint works, CAP feed public, and a webhook delivery with a valid `X-Linda-Signature` demonstrated end-to-end
- [ ] `replay_only` mode runs the full demo with networking disabled
- [ ] README rewritten; Devpost overview + solution ≤ 250 words each; video ≤ 5:00; repo public
- [ ] §13 claims audit performed on the final video and all submission text
- [ ] Submitted on Devpost with a confirmation screenshot saved — before 17:00 EAT, 31 July 2026
