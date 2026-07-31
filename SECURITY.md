# Security Policy

Linda Protocol handles evidence, approval records, export artifacts, partner API credentials, and webhook configuration. Even in exercise mode, incorrect trust boundaries can mislead responders or expose sensitive operational information.

## Supported version

Security fixes are applied to the latest `main` branch. Development branches and local demo databases are not supported release channels.

## Reporting a vulnerability

Do not open a public GitHub issue for a security vulnerability.

- Use **GitHub Security Advisories** for this repository: **Security → Report a vulnerability**.
- Include the affected component, reproduction steps, impact, and any relevant request or response details.
- Expect an acknowledgement within 72 hours and a status update within seven days.

Please allow a reasonable remediation window before publishing details. Good-faith security research is welcome.

## High-priority areas

Report these as high priority:

1. **Authentication and roles**: bypassing session validation, role checks, login rate limiting, or administrator-only routes.
2. **Decision integrity**: forging or modifying approvals, canonical digests, HMAC records, exports, or the hash-chained event log.
3. **State-machine guards**: advancing a case with unresolved critical tasks, incomplete approvals, a stale version, or from a terminal state.
4. **Partner credentials and webhooks**: exposing integration API keys or webhook secrets, bypassing API-key revocation/rate limits, or using webhooks for SSRF.
5. **Source and export data**: leaking unredacted upstream personal data, secrets, or unsafe file paths through source snapshots, generated packets, CAP, offline bundles, or partner responses.
6. **AI trust boundary**: prompt injection, schema bypass, or AI output that can mutate policy, tasks, approvals, exports, or case state.

## Security expectations

- Keep `.env`, SQLite runtime databases, generated exports, and API keys out of Git.
- Use a strong unique `LINDA_SECRET` outside local development.
- Set `COOKIE_SECURE=true` and configure a narrow `CORS_ORIGINS` allowlist behind HTTPS.
- Treat all source payloads and blocker reports as untrusted input.
- Keep all public CAP and integration responses labelled `Exercise` until an authorised operational programme replaces the demo boundary.

## Out of scope

- Vulnerabilities that require physical access to an unlocked device.
- Volumetric denial-of-service attacks.
- Security defects in third-party platforms, including ICPAC source systems, Husika services, Google Gemini, or GitHub. Report these to the relevant provider unless Linda Protocol is directly at fault.
