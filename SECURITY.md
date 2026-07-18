# Security Policy

Linda Node is an early-warning and anticipatory-action platform serving vulnerable communities in the Greater Horn of Africa. Security issues here are not just technical — a compromised alert channel, a spoofed trigger, or leaked user locations can cause real-world harm. We take reports seriously.

## Supported Versions

| Version | Supported |
|---|---|
| `main` branch | ✅ |
| Anything else | ❌ |

The project is under active development for the [IGAD Hackathon 2026](https://igad-husika-hackathon.devpost.com/); only the latest `main` is supported.

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

- Report privately via **GitHub Security Advisories**: *Security → Report a vulnerability* on this repository.
- You should receive an acknowledgment within **72 hours** and a status update within **7 days**.
- Please include: affected component (bot, API, dashboard, ingestion, financing module), reproduction steps, and impact assessment.

We ask for a reasonable disclosure window before publication so a fix can ship first. Good-faith research is welcome; we will not pursue action against researchers acting responsibly.

## Areas of Particular Sensitivity

If you find issues in any of these, please flag them as high priority:

1. **User location data** — registered users share GPS pins. Any exposure of `users.location` or de-anonymization of community reports is a critical issue.
2. **The Anticipatory Financing Module** — anything that lets an attacker forge, inflate, or bypass the Triangulation Engine (official trigger + community consensus + AI plausibility) to produce a fraudulent "Proof of Risk" dossier.
3. **Alert integrity** — spoofing or tampering with proactive alerts (fake warnings erode community trust and can cause panic or dangerous inaction).
4. **Telegram webhook authentication** — the webhook must validate Telegram's secret token; Mini App requests must validate `initData` per the [Telegram spec](https://core.telegram.org/bots/webapps#validating-data-received-via-the-mini-app).
5. **Prompt injection** — community reports are untrusted input processed by LLMs. Reports must never be able to alter agent behavior, exfiltrate data, or influence alert content for other users.
6. **Secrets** — no credentials, API keys, or `.env` files may ever be committed. If you find one in history, report it immediately.

## Out of Scope

- Vulnerabilities in third-party platforms we depend on (Telegram, Supabase, Google Gemini, ICPAC platforms) — report those upstream.
- Denial-of-service via volumetric traffic.
- Issues requiring physical access to a user's unlocked device.
