# Linda Protocol API

Person 2's FastAPI service owns authentication, action readiness, co-signing,
audit, exports, the partner API, and constrained action/blocker assists.

```bash
cd server/backend
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
.venv/bin/uvicorn app.main:app --reload --port 8001
```

The service auto-seeds fictional demo users in `DEMO_MODE`. Every persona's
password is `linda-demo`:

- `amina.ews@demo` — Evidence & EWS Specialist
- `david.drm@demo` — County DRM Officer
- `grace.ngo@demo` — NGO & Finance Lead
- `observer@demo` — read only
- `admin@demo` — seed recovery, partner keys, and webhooks

The seed starts with a Bungoma case at `ASSESSED` and a critical transport
blocker. Resolve it as Grace, send for review as David, then approve as Amina,
David, and Grace to exercise all four exports and the integration API.

`GET /docs` provides the internal API contract. `GET /integration/v1/docs` and
`GET /cap/feed.xml` are the public partner surfaces. All are explicitly marked
`mode: exercise`; nothing sends alerts or moves funds.

The Husika payload is validated locally against the vendored live OpenAPI
snapshot in `fixtures/husika_openapi/`. Its source URL, retrieval time, and
SHA-256 are recorded in the adjacent metadata file. Refresh the pair together
when Husika publishes a new contract.
