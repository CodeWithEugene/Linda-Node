<p align="center">
  <img src="../../docs/brand/linda-node-logo-horizontal.png" alt="Linda Node" width="380" />
</p>

<h1 align="center">Linda Node API</h1>

<p align="center">
  FastAPI service: source capture, deterministic policy assessment, the case state machine,<br />
  multi-role signing, the hash-chained audit trail, exports, and the partner integration API.
</p>

---

## Contents

1. [Run locally](#run-locally)
2. [Module map](#module-map)
3. [Data model](#data-model)
4. [Source adapters and provenance](#source-adapters-and-provenance)
5. [Policy engine](#policy-engine)
6. [Regional view](#regional-view)
7. [Case service, guards, and signing](#case-service-guards-and-signing)
8. [Constrained AI assists](#constrained-ai-assists)
9. [Exports](#exports)
10. [Integration API and webhooks](#integration-api-and-webhooks)
11. [REST surface](#rest-surface)
12. [Seeded demo data](#seeded-demo-data)
13. [Failure posture](#failure-posture)
14. [Deployment](#deployment)
15. [Testing](#testing)

---

## Run locally

```bash
cd server/backend
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
cp .env.example .env
.venv/bin/uvicorn app.main:app --reload --port 8001
```

The service listens on `http://127.0.0.1:8001`; interactive API documentation is at `/docs`.

The application boots with only `LINDA_SECRET` set — everything else has a working default. On an empty database in `DEMO_MODE` it migrates, validates the policy library, and seeds itself. A malformed policy or action card **stops the process** rather than producing assessments against an unreviewed rulebook.

WeasyPrint needs native Pango and Cairo to render PDF packets. The Docker image installs them; on macOS see the root README. Where they are unavailable (including Vercel Functions), a portable ReportLab renderer takes over automatically.

---

## Module map

| Module | Responsibility |
|---|---|
| `app/main.py` | Route definitions, CORS, the `{"error": {code, message, detail}}` shape, optimistic-concurrency handler, SPA mount |
| `app/config.py` | Frozen dataclass settings read from the environment; detects serverless runtimes |
| `app/db.py` | SQLite and Postgres schema, additive migrations, `BEGIN IMMEDIATE` transactions, `append_event` |
| `app/domain.py` | Canonical JSON, SHA-256, ULID-style sortable ids, role and blocker vocabularies |
| `app/redaction.py` | Email masking applied on every read path |
| `app/sources.py` | Adapters, verbatim capture, hashing, schema validation, caching, replay, on-demand geometry, tile source |
| `app/library.py` | Hash-pinned, schema-validated policies (one per hazard) and action cards |
| `app/policy_engine.py` | Pure deterministic assessment — no IO, no LLM, no randomness |
| `app/regional.py` | Applies each hazard's policy across all 214 admin-1 units |
| `app/services.py` | Case CRUD, state-machine guards, readiness tasks, approvals, signing, chain verification |
| `app/exports.py` | Packet (PDF + manifest), CAP 1.2, Husika payload, air-gapped bundle |
| `app/husika_contract.py` | Vendored Husika OpenAPI spec and local validation |
| `app/integration.py` | Partner API records, API keys, rate limiting, signed webhooks with SSRF guards |
| `app/assists.py` | Three constrained Gemini assists with schema enforcement and hard failure paths |
| `app/auth.py` | Cookie session (compact HS256), role dependencies, login rate limiting |
| `app/blob_store.py` | Export storage — local filesystem or private Vercel Blob |
| `app/demo_seed.py` | The three seeded cases, built through the same normalisers as live data |

---

## Data model

All ids are ULID-style sortable text. Timestamps are UTC ISO-8601. JSON columns are written with sorted keys so hashes are stable.

| Table | Notes |
|---|---|
| `users` | Seeded only. Argon2 password hash, per-user HMAC signing key. |
| `source_snapshots` | **Immutable.** Verbatim `payload_raw`, normalised `payload_json`, `payload_sha256` over the raw body, `schema_ok`, `freshness`, `logical_key`, and `meta` carrying per-endpoint hashes. Raw bodies older than the three most recent per source are pruned; hashes remain. |
| `decision_cases` | Assessment, evidence, eligible card ids, stage, and an optimistic `version`. |
| `readiness_tasks` | Owner role, criticality, state, blocker code and note. |
| `approvals` | One live decision per role per case; `superseded` retains history. |
| `case_events` | **Append-only, hash-chained.** `this_hash = sha256(prev_hash + canonical(data) + event_type + actor)`. No update or delete path exists anywhere in the codebase. |
| `exports` | One row per generated artifact, hashed. Files are never overwritten. |
| `integration_keys` | Argon2 hash of the bearer key; the key itself is shown once. |
| `webhook_subscriptions`, `webhook_deliveries` | Subscription config and every delivery attempt. |

**Invariants:** every state change writes exactly one `STATE_CHANGED` event inside the same transaction; a mutation whose supplied `version` is stale returns HTTP 409 and records a `CONFLICT_REJECTED` event; an export row is written only after its bytes are hashed.

---

## Source adapters and provenance

Adapters: `triggers`, `forecasts`, `areas`, `indicators`, `pipeline`.

Retrieval order:

1. A snapshot for the same logical query younger than `SNAPSHOT_TTL_MIN` is reused and labelled `cached`.
2. Otherwise fetch with httpx. **The response body is retained verbatim and hashed before any parsing** — a reviewer reproduces the hash with `curl <url> | shasum -a 256`, and `meta.parts` carries a hash per endpoint for multi-request adapters.
3. The normalised view is validated against `content/schemas/sources/<adapter>.schema.json`. A failure stores the snapshot with `schema_ok=0` plus the errors; it does not crash the case, and the `schema_valid` gate then fails.
4. On upstream failure the newest stored snapshot is returned as `stale` with the error attached; if none exists and `DEMO_MODE` is on, the replay fixture is used and labelled `replay`.

**Field mapping.** Upstream names differ from what the workflow reads, and the adapter is where that is reconciled: `area_gid → area_id`, `indicator_code → indicator`, `severity_level → severity`, `hazard_type → hazard`, `is_active → active`. Probabilities come from `/api/datasets/forecasts/stats/` (`avg_prob_rp3`, a percentage, divided by 100 and recorded as `probability_source`) — not from `/available/`, which carries no probability at all.

**Redaction.** ICPAC trigger rules carry named individuals' notification addresses. Fixtures keep them for provenance; `redact()` masks them in every API response, UI render, packet, and export. A parameterised test sweeps every endpoint and every export for the real addresses.

**Geometry.** The admin-1 index is fetched with `fields=id,name` for all 11 countries (a few KB each). Per-country geometry — megabytes — is fetched only on demand via `GET /api/areas/{country}/geometry` and cached under its own logical key.

---

## Policy engine

Pure functions in `app/policy_engine.py`. No IO, no LLM, no randomness; the same inputs always produce the same assessment.

**One policy per hazard**, in `content/policies/`, each JSON-Schema validated and hash-pinned:

| Hazard | Signal basis | Why |
|---|---|---|
| `drought` | `probability` — SPI-3 / CHIRPS seasonal exceedance vs Ready–Set–Go thresholds | SPI-3/CHIRPS is the only indicator ICPAC's registry marks `supports_forecast: true` |
| `heat` | `upstream_severity` — ICPAC `severity_level` on an active trigger event | TMAX is monitoring-only upstream, so there is no probability to threshold |
| `flood` | `upstream_severity` | CHIRPS rainfall is likewise monitoring-only |

Linda Node does **not** classify heat or flood severity. It maps ICPAC's classification onto a readiness stage, and the policy file says so.

**Assessment output:** `stage` (or `null`), `ndma_phase`, `recommendation`, `signal_basis`, `observed_signal` (with its own origin and `synthetic` flag), six `gates`, a `stage_trace`, a `cost_loss` trace where every operand carries `official_source` / `policy_assumption` / `user_entered`, `eligible_action_cards`, `ineligible` with per-card reasons, `compound_signals`, and the armed `stop_trigger`.

**Gates:** `signal_present`, `source_freshness`, `schema_valid`, `data_completeness`, `lead_time`, `net_benefit`.

**The no-fabrication rule.** `stage` starts as `None` and is only ever set by a condition that passes. With no qualifying signal the assessment reports `"no activation recommended"` and the `signal_present` gate fails, so the workflow cannot advance.

**Provenance ranking.** When both recorded and synthetic observations are attached, recorded always wins. A synthetic observation is labelled `policy_assumption`, prefixed `SYNTHETIC demo fixture — …`, and sets `synthetic_observation: true`.

**Compound signals** require the *same* admin area, at least two different hazard categories, active upstream events, and a stage already reached. It is a deterministic overlap check and is never described as an index.

**Stop trigger** has two shapes: a collapsing probability (`probability_lt`) for drought, and `resolved_upstream` for the monitoring-driven hazards.

---

## Regional view

`GET /api/regional` applies each hazard's policy across every admin-1 unit ICPAC publishes statistics for. One unfiltered call to the statistics endpoint returns all 214 units across 11 countries; trigger events are joined by area so a unit can carry both a seasonal drought probability and a monitored heat or flood event.

The response contains the selected forecast issue, all 13 available issues, per-adapter grounding evidence with hashes, the three policy version hashes, totals, a country rollup, the ranked units, and the tile source descriptor (`tile_url`, `source_layer`, `join_property`) the frontend uses to draw the choropleth.

---

## Case service, guards, and signing

```
INGESTED → ASSESSED                    system, after evaluate()
ASSESSED → READY_FOR_REVIEW            county_drm_officer; all gates passed AND no critical task blocked
ASSESSED → NEEDS_EVIDENCE              a signer role, or the system on gate failure
NEEDS_EVIDENCE → ASSESSED              system, on new evidence
READY_FOR_REVIEW → APPROVED            system, when the third distinct-role signature lands
READY_FOR_REVIEW → REJECTED            any signer records 'reject'
APPROVED → HANDED_OFF                  county_drm_officer, after ≥1 export
APPROVED | HANDED_OFF → REVOKED        stop trigger, or manual with a mandatory reason
```

Terminal states are `REJECTED` and `REVOKED`. Guards proven by tests that attempt to break them through the API: no assist and no observer can cause a transition; a blocked critical task blocks review; `APPROVED` is unreachable by direct transition; new evidence supersedes prior approvals.

**Signing.** `canonical_case_json(case)` is sorted-key JSON of the case id, area, hazard, policy version, assessment, sorted evidence hashes, and sorted task states. It deliberately **excludes `state`** — a signature attests to the decision facts, and the third signature itself advances the case, so including the state would invalidate every signature the instant it landed. `signed_digest = sha256(canonical)`, `signature = HMAC-SHA256(user.signing_key, digest)`.

This is integrity protection and non-repudiation *within this system*, using server-held keys. Call it a cryptographically signed decision record — not PKI, not a blockchain.

---

## Constrained AI assists

Three assists, all optional. With `GEMINI_API_KEY` unset the buttons render disabled and the entire workflow remains completable.

| Assist | Output schema | Hard constraint |
|---|---|---|
| Evidence Explainer | `{summary, cited_snapshot_ids[], missing_inputs[]}` | Every cited snapshot id must exist on the case, or the call fails |
| Action Matcher | `{candidates: [{card_id, rationale, rank}]}` | `card_id` must be in the deterministically eligible set; it can only re-rank |
| Blocker Structurer | `{code, severity, summary, needs_human_review}` | `code` must be in the fixed taxonomy; the output is a suggestion a human confirms |

Structured output with an explicit JSON schema, temperature 0.2, 10-second timeout, one retry with the validator error appended, then `AssistUnavailable` and an `ASSIST_FAILED` event. Untrusted text such as a field report is passed as data, never concatenated into a system prompt. No assist can change case state, eligibility, tasks, approvals, or exports.

---

## Exports

| Export | Contents and validation |
|---|---|
| `packet_json` + `packet_pdf` | Case snapshot, full policy text and hash, assessment traces, evidence provenance, task history, three signatures with digests, tranche recommendation lines, AI explanations in a labelled box, event-chain head hash, and a `manifest_sha256` over the sorted body |
| `cap_xml` | CAP 1.2, validated against the bundled OASIS XSD. `status=Exercise` always; `msgType=Cancel` on the revoked path. Urgency/severity/certainty map from the stage; `geocode` carries the GADM id |
| `husika_payload` | Threat, broadcast, message, and location request bodies validated against the vendored Husika ingestor OpenAPI schemas. **No HTTP call to Husika is ever made** |
| `field_bundle` | `.zip` with `dossier.html` (zero external requests), `manifest.json`, `alert.cap.xml`, and `checksums.txt` |

Packets are generated from the **persisted** case record, never in-memory UI state. Regeneration produces a new export id and file; prior files stay downloadable.

---

## Integration API and webhooks

Read-only and outbound-only. Public: the CAP feed, the OpenAPI contract, the frozen activation schema, and the docs page. API-key protected: the activation collection and per-activation record, CAP, Husika payload, and verification report. Keys are Argon2-hashed, shown once, revocable, and rate limited to 60 requests per minute.

The v1 response shape is frozen by `content/schemas/integration/activation.v1.schema.json` with `additionalProperties: false` and asserted by a snapshot test — a shape change fails CI.

Webhooks fire on `APPROVED` and `REVOKED`. Each delivery carries `X-Linda-Event`, `X-Linda-Delivery` (which is also the stored delivery row id), and `X-Linda-Signature: sha256=HMAC(secret, raw body)`. Subscription URLs must be public HTTPS; loopback, link-local, and RFC1918 addresses are rejected before any request. Retry pacing adapts to the runtime: a long-lived container gets 1 m / 5 m / 25 m backoff, while a serverless invocation makes one prompt retry, because background work does not outlive the response there.

---

## REST surface

| Route group | Purpose |
|---|---|
| `/api/auth/*`, `/api/me` | Cookie-session authentication and identity |
| `/api/regional` | Region-wide readiness across every admin-1 unit |
| `/api/signals`, `/api/sources/*`, `/api/areas`, `/api/areas/{country}/geometry` | Signal inbox, snapshot provenance, refresh, area index and geometry |
| `/api/cases/*` | Creation, assessment, evidence, tasks, transitions, approvals, assists, exports, events, verification |
| `/api/exports/{id}/download` | Immutable artifact download |
| `/api/library/*` | Policies, action cards, ICPAC indicator registry, tile source, Husika contract metadata |
| `/api/audit` | Filterable cross-case event history |
| `/api/admin/*` | Source mode, forecast issue, escalation step, stop-trigger evaluation, keys, webhooks, seed |
| `/integration/v1/*` | Versioned partner records and verification |
| `/cap/feed.xml`, `/healthz` | Public feed and liveness |

Errors use `{"error": {"code", "message", "detail"}}`. Case mutations require the current `version` and return HTTP 409 on a stale write.

---

## Seeded demo data

Seeding builds **three cases on Ruvuma, Tanzania** (`TZA.22_1`) — a real admin-1 unit whose recorded ICPAC statistic (51.8 % rp3 exceedance for OND 2026) genuinely crosses the SET threshold. Nothing in the default seed is synthetic, and the snapshots are produced by the same normalisers and schemas the live adapters use.

| Case | State | Why it exists |
|---|---|---|
| `case_ruvuma_ond2026` | `ASSESSED`, critical transport task `BLOCKED` | The case a visitor drives themselves |
| `case_ruvuma_ond2026_handedoff` | `HANDED_OFF` with all four exports | Finished artifacts to inspect in ten seconds |
| `case_ruvuma_ond2026_revoked` | `REVOKED` with a CAP `Cancel` | The stop-trigger path |

Every persona uses the password `linda-demo`: `amina.ews@demo`, `david.drm@demo`, `grace.ngo@demo`, `observer@demo`, `admin@demo`. All are fictional.

`POST /api/admin/seed` restores this state. `POST /api/admin/replay-mode` switches `live_first` / `replay_only`. `POST /api/admin/replay-step` selects the labelled synthetic escalation (0 = recorded statistics; 1–3 step a probability across the thresholds). `POST /api/admin/forecast-issue` picks any of the 13 published issues.

---

## Failure posture

| Failure | Behaviour |
|---|---|
| Upstream timeout, 5xx, or schema drift | Serve the last snapshot as `stale` with a visible badge; replay fallback only in `DEMO_MODE`, always labelled |
| No live signal crosses a threshold | Report "no activation recommended" — never fabricate |
| Gemini down or returning invalid JSON | Assist marked unavailable, `ASSIST_FAILED` recorded, zero workflow impact |
| Concurrent edits | Optimistic version check → 409 plus a `CONFLICT_REJECTED` event |
| Guard violation via a direct API call | 422 naming the failed guard |
| Export regeneration | New immutable file; prior exports stay downloadable |
| Database missing or empty at boot | Auto-migrate and auto-seed in `DEMO_MODE` |
| Invalid policy or action card | Startup fails loudly |

---

## Deployment

Set the Vercel project root to `server/backend`. `api/index.py` exports the FastAPI application for Vercel Functions and `vercel.json` routes the API, CAP, integration, and health paths to it. In production use Neon Postgres via `DATABASE_URL` and private Vercel Blob via `LINDA_BLOB_READ_WRITE_TOKEN` — never the function filesystem for workflow state or exports.

Set `LINDA_SECRET`, `COOKIE_SECURE=true`, `PUBLIC_BASE_URL`, and `CORS_ORIGINS`. `Dockerfile.vercel` is the container alternative.

---

## Testing

```bash
.venv/bin/ruff check app tests
.venv/bin/python -c "from app.library import validate_library; print(validate_library())"
.venv/bin/pytest -q                         # 139 tests
.venv/bin/pytest -q -m contract --contract  # 5 live upstream contract tests
```

| File | Covers |
|---|---|
| `test_policy_engine.py` | Stage boundaries, gates, both stop triggers, cost–loss arithmetic, no-fabrication, area isolation, synthetic ranking, purity |
| `test_state_machine.py` | Every legal transition and every illegal one attempted through the API, role guards, canonical-JSON stability |
| `test_sources_and_redaction.py` | Field mapping, schema accept/reject, redaction sweep, verbatim hashing, cache and replay behaviour |
| `test_exports.py` | Manifest stability, CAP XSD, Husika negative enums, bundle checksums, offline dossier, no secrets |
| `test_integration_api.py` | Key auth, revocation, rate limit, frozen shape, pagination, tamper detection, webhook signature and retry |
| `test_security.py` | HTML escaping, login rate limit, forged cookie, fail-closed policy loading |
| `test_workflow.py` | The end-to-end golden path through HTTP |
| `test_upstream_contract.py` | Opt-in; calls the real ICPAC and Husika endpoints and fails on drift |
