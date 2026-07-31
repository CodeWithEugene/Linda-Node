# Linda Protocol

Linda Protocol is an Exercise-only, human-governed activation-readiness
workspace for anticipatory action. It makes the path from evidence and policy
to readiness tasks, multi-role approval, immutable exports, and partner-ready
handoff inspectable. It does not release funds or send public alerts.

The build plan and acceptance criteria live in [what-to-build.md](what-to-build.md).
`research.md` records the product rationale and external-contract research.

## What is implemented

The repository keeps the requested deployment layout:

```
client/frontend  React + TypeScript + Material UI application
server/backend   FastAPI + SQLite application
```

The current Person 2 slice provides:

- Role-based cookie authentication for the seeded fictional personas.
- Reviewed YAML Policy and Action Card Library, readiness tasks, blocker
  taxonomy, guarded case transitions, version-conflict events, and three-role
  HMAC approval records.
- Action, approval, export, audit, policy-library, and administrator screens.
- Immutable JSON/PDF activation packets (WeasyPrint), XSD-validated CAP 1.2
  alerts, offline bundles with checksums, and schema-exact Husika handoff JSON.
- A documented `/integration/v1` API, scoped bearer API keys, signed outbound
  webhooks, paginated activations, public CAP feed, and public contract schema.
- Constrained Gemini Action Matcher and Blocker Structurer assists. They have
  versioned prompts, JSON schemas, a 10-second timeout, retry once on invalid
  output, and never change policy, tasks, approvals, or case state.

Signal ingestion/replay, evidence views, deterministic policy evaluation,
source snapshots, and map display belong to the Person 1 boundary and are
represented by explicit integration seams in this slice.

## Run locally

Backend (Python 3.12+):

```bash
cd server/backend
python -m venv .venv
.venv/bin/pip install -e '.[dev]'
cp .env.example .env
.venv/bin/uvicorn app.main:app --reload --port 8001
```

Frontend (Node 20+):

```bash
cd client/frontend
npm install
npm run dev
```

The browser opens at `http://localhost:5173`. The API runs at
`http://localhost:8001`; its CORS allowlist is configured through
`CORS_ORIGINS`.

Port `8001` avoids a commonly occupied local `8000` service. To use another
API origin, set `LINDA_API_ORIGIN` before starting Vite.

## Demo access and safety

All demo accounts use password `linda-demo`:

- `amina.ews@demo` — EWS Specialist
- `david.drm@demo` — County DRM Officer
- `grace.ngo@demo` — NGO & Finance Lead
- `observer@demo` — read-only
- `admin@demo` — demo recovery, partner keys, and webhook subscriptions

These are fictional personas. There is no self-registration, password reset,
or OAuth flow. Login is rate-limited to five failed attempts per IP over five
minutes. Set `COOKIE_SECURE=true` when serving over HTTPS.

Decision approvals are a **cryptographically signed decision record
(HMAC-SHA256) within this demo system**. The signing keys are server-held; this
is integrity protection and non-repudiation within the demo only. It is not
PKI, an external digital-signature service, or blockchain.

Every export, CAP entry, Husika handoff, and partner response is labelled
`Exercise`. The Husika payload validates against the vendored, published
Ingestor OpenAPI snapshot, but Linda never makes a write call to Husika. Its
UI wording is deliberate: “Ready for dispatch by an authorised Husika
operator — Linda Protocol does not send.”

## Verification

```bash
cd server/backend
.venv/bin/ruff check app tests
.venv/bin/pytest -q

cd ../../client/frontend
npm run build
```

The backend suite covers state guards, three-role approval, export and partner
verification, version-conflict events, event-chain tampering, CAP XSD
validation, Husika contract rejection, and constrained-AI card validation.
