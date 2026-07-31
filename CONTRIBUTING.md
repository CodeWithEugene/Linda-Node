# Contributing to Linda Protocol

Linda Protocol is an exercise-only activation-readiness workspace. Contributions should make the evidence-to-decision workflow clearer, safer, and easier to verify. Do not add alert delivery, fund movement, or autonomous decision-making.

## Before you begin

Read the [README](README.md), then use the component guides in `server/backend` and `client/frontend`. The README is the public entry point and source of truth for local setup, safety framing, and the current demo workflow.

## Local development

```bash
cd server/backend
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
cp .env.example .env

cd ../../client/frontend
npm ci
```

Run the API on port `8001` and Vite on port `5173` as described in the README. Use `DEMO_MODE=true` while developing unless you are deliberately testing a source-adapter failure path.

## Engineering rules

1. **Human authority is non-negotiable.** Deterministic code evaluates policy; a human records approvals. AI output must never change case state, eligibility, tasks, approvals, or money movement.
2. **Keep provenance intact.** Source snapshots, policy assumptions, user-entered updates, and AI explanations must remain distinguishable in storage, APIs, exports, and the UI.
3. **Preserve the audit record.** Do not add an update or delete path for `case_events`. Mutations must respect optimistic case versions and record the relevant event.
4. **Treat external input as untrusted.** Validate API input, escape rendered text, and keep field reports out of system prompts. Assist calls use structured JSON only.
5. **Never commit secrets.** `.env` files, API keys, webhook secrets, and generated runtime data stay local.
6. **Keep scope deliberate.** Telegram, SMS/USSD delivery, payments, beneficiary selection, and live Husika write calls are not part of this project.

## Verification

Run the relevant checks before opening a pull request:

```bash
cd server/backend
.venv/bin/ruff check app tests
.venv/bin/pytest -q

cd ../../client/frontend
npm run build
npm test -- --passWithNoTests
```

When changing a workflow, also exercise the role-based demo path in a browser. At minimum, verify a blocked task, a rejected stale version, the three-role approval path, and the affected export or partner endpoint.

## Pull requests

Create branches from `main` using a conventional prefix such as `feat/`, `fix/`, `docs/`, or `test/`. Use Conventional Commit messages.

In the pull request description, include:

- The user or workflow problem addressed.
- The behaviour changed and its trust or safety impact.
- Tests and manual verification performed.
- Any source, policy, OpenAPI, or fixture changes that reviewers should inspect.

## Reporting issues

Use GitHub Issues for reproducible bugs and feature proposals. Do not report security vulnerabilities publicly; follow the [security policy](SECURITY.md).

## License

By contributing, you agree that your contribution is licensed under the [MIT License](LICENSE).
