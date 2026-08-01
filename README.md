# Linda Protocol

Linda Protocol is an auditable activation-readiness control plane between early-warning evidence and authorised partner action. It records why an action is recommended, what remains blocked, who co-signed the decision, and which handoff artifacts were generated. It does not dispatch public alerts or release funds.

## Run locally

```powershell
Copy-Item .env.example .env
python -m pip install -e .\backend[dev]
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`.

The seeded exercise personas all use password `linda-demo`:

- `amina.ews@demo` - EWS Specialist
- `david.drm@demo` - County DRM Officer
- `grace.ngo@demo` - NGO/Finance Lead
- `observer@demo` - Observer
- `admin@demo` - Administrator

For the rapid local walkthrough, the interface exposes a persona selector. The API also implements JWT login at `POST /api/auth/login`.

## Exercise workflow

1. Inspect replayed ICPAC/replay evidence with source URL, retrieval time, and SHA-256 provenance.
2. Resolve the transport readiness blocker as the County DRM Officer.
3. Send the case for review.
4. Co-sign as the EWS Specialist, County DRM Officer, and NGO/Finance Lead.
5. Generate the decision packet, CAP alert, Husika payload, and field bundle.
6. Mark the case handed off.
7. Switch to Admin, simulate the stop trigger, and generate the CAP cancellation artifact.
8. Inspect the hash-chained audit log and signature verification.

## Architecture

- FastAPI with typed request/response schemas, CORS, health check, static SPA serving, and versioned integration routes.
- SQLite by default through SQLAlchemy 2.0, with an Alembic initial migration and a Postgres Docker profile.
- Durable source snapshots, decision cases, case events, exports, integration API keys, and webhook subscriptions.
- Canonical JSON digesting and HMAC-SHA256 role signatures.
- Versioned YAML policy and action-card library in `backend/content/`.
- Replay fixtures in `fixtures/`; all public artifacts are marked `Exercise`.

## Verification

```powershell
python -m pytest backend\tests -q
powershell -ExecutionPolicy Bypass -File .\scripts\smoke-test.ps1
```

The integration documentation is available at `/integration/v1/docs`; activation resources require an API key issued from the Admin API. The CAP Atom feed at `/cap/feed.xml` remains public.

## Claims discipline

Linda validates and records governed activation decisions. It does not claim to be an ICPAC or Husika production integration, dispatch public alerts, move money, make scientific forecasts, or use PKI/blockchain signatures. CAP artifacts and integration responses are explicitly exercise-mode records.

## Acknowledgements

Linda Protocol uses recorded ICPAC-style fixture data, GADM-style identifiers, FastAPI, SQLAlchemy, Alembic, and the CAP 1.2 format. Source provenance is visible in the application and every generated exercise record.
