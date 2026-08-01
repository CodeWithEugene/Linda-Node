<p align="center">
  <img src="docs/brand/linda-node-logo-horizontal.png" alt="Linda Node" width="360" />
</p>

<h1 align="center">Security Policy</h1>

Linda Node handles upstream evidence, approval records, export artifacts, partner API credentials, and webhook configuration. Incorrect trust boundaries here can mislead responders, misattribute a decision, or expose sensitive operational information — so security reports are taken seriously even where the deployment is a demonstration.

---

## Supported version

Security fixes are applied to the latest `main` branch. Development branches and local demo databases are not supported release channels.

## Reporting a vulnerability

**Do not open a public GitHub issue for a security vulnerability.**

- Use **GitHub Security Advisories** for this repository: **Security → Report a vulnerability**.
- Include the affected component, reproduction steps, impact, and any relevant request or response details.
- Expect an acknowledgement within 72 hours and a status update within seven days.

Please allow a reasonable remediation window before publishing details. Good-faith security research is welcome.

---

## High-priority areas

1. **Authentication and roles** — bypassing session validation, the role dependencies, login rate limiting, or administrator-only routes.
2. **Decision integrity** — forging or modifying approvals, canonical digests, HMAC signatures, exports, or the hash-chained event log; producing `APPROVED` without three valid distinct-role signatures.
3. **State-machine guards** — advancing a case with an unresolved critical task, incomplete approvals, a stale version, or out of a terminal state.
4. **Provenance integrity** — causing a synthetic or fabricated value to be labelled `official_source`, defeating the verbatim-body hashing, or making a stage appear where no policy condition passed.
5. **Personal data** — any path that emits an unmasked upstream email address through an API response, UI render, packet, CAP document, offline bundle, or partner payload.
6. **Partner credentials and webhooks** — exposing integration API keys or webhook secrets, bypassing key revocation or the rate limit, or using a webhook subscription for SSRF against loopback, link-local, or private-range addresses.
7. **Export and file handling** — leaking secrets or environment values into a generated artifact, unsafe path handling in the export store, or an offline dossier that makes an external request.
8. **AI trust boundary** — prompt injection, schema bypass, or any assist output that can mutate policy, tasks, approvals, exports, or case state.

---

## Security model in brief

| Control | Implementation |
|---|---|
| Sessions | HTTP-only cookie carrying a compact HS256 token signed with `LINDA_SECRET`; 24-hour expiry |
| Passwords | Argon2 where available, PBKDF2-SHA256 (200k iterations) otherwise; never returned by any endpoint |
| Login abuse | Five failed attempts per IP per five minutes, then HTTP 429 |
| Authorisation | FastAPI role dependencies on every mutating route; `observer` reads everything and mutates nothing |
| Decision integrity | HMAC-SHA256 over a canonical, sorted-key case snapshot, per-user server-held keys |
| Audit integrity | Append-only, hash-chained `case_events`; a verification endpoint walks the chain and reports the first break |
| Concurrency | Optimistic case versions under `BEGIN IMMEDIATE`; a stale write returns 409 and records the rejection |
| Partner keys | Argon2-hashed, shown once at creation, revocable, 60 requests per minute per key |
| Webhook egress | Public HTTPS only; hostnames resolving to loopback, link-local, or RFC1918 addresses are rejected before any request |
| Untrusted text | Pydantic-validated input, HTML-escaped rendering, field reports passed to assists as data and never concatenated into a system prompt |
| Personal data | Recursive email masking applied on every read path |

**On the cryptography.** Signing provides integrity protection and non-repudiation *within this system* using server-held keys. It is correctly described as a cryptographically signed decision record. It is **not** PKI, not a digital signature in the legal sense, and not a blockchain — please do not report it as though it claimed to be.

**On `status=Exercise`.** CAP documents deliberately carry `status=Exercise` so a downstream aggregator can never mistake this feed for an accredited operational source. A change that removes or weakens that label is a security issue, not a feature.

---

## Deployment expectations

- Keep `.env`, runtime SQLite databases, generated exports, and API keys out of Git. `var/` is gitignored.
- Use a strong, unique `LINDA_SECRET` outside local development.
- Set `COOKIE_SECURE=true` and configure a narrow `CORS_ORIGINS` allowlist behind HTTPS.
- Store production workflow state in Postgres and exports in a **private** blob store — never on a serverless function filesystem.
- Treat every upstream payload and blocker report as untrusted input.
- Rotate partner API keys and webhook secrets when a subscriber changes.

## Out of scope

- Vulnerabilities requiring physical access to an unlocked device.
- Volumetric denial-of-service attacks.
- Defects in third-party platforms — including ICPAC source systems, Husika services, NVIDIA NIM, Vercel, or GitHub. Report those to the relevant provider unless Linda Node is directly at fault.
- The documented absence of self-registration, password reset, and OAuth. Users are seeded by design.
