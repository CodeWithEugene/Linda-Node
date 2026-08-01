<p align="center">
  <img src="docs/brand/linda-node-logo-horizontal.png" alt="Linda Node" width="360" />
</p>

<h1 align="center">Contributing to Linda Node</h1>

Linda Node is an activation-readiness control plane. Contributions should make the path from evidence to an approved, verifiable decision clearer, safer, and easier to audit. Do not add alert delivery, fund movement, or autonomous decision-making.

---

## Before you begin

Read the [root README](README.md) for the architecture and honesty guarantees, then the component guides in [`server/backend`](server/backend/README.md) and [`client/frontend`](client/frontend/README.md).

## Local development

```bash
cd server/backend
python3 -m venv .venv
.venv/bin/python -m pip install -e '.[dev]'
cp .env.example .env
.venv/bin/uvicorn app.main:app --reload --port 8001

cd ../../client/frontend
npm ci
npm run dev
```

Keep `DEMO_MODE=true` while developing unless you are deliberately testing a source-adapter failure path.

---

## Engineering rules

These are not style preferences. Each one is enforced somewhere in the test suite, and breaking one changes what the product is allowed to claim.

1. **Human authority is non-negotiable.** Deterministic code evaluates policy; a human records approvals. AI output must never change case state, eligibility, tasks, approvals, or money movement.

2. **Never fabricate a stage.** If no policy condition passes, the stage is `null` and the assessment says *"no activation recommended"*. Do not introduce a default, a fallback, or a "closest" stage. This is the single most important guarantee in the codebase.

3. **Hash the verbatim body, before parsing.** Upstream responses are stored exactly as received and hashed at that point, so any reviewer can reproduce a snapshot hash with `curl <url> | shasum -a 256`. Never hash a normalised or re-serialised view.

4. **Keep provenance intact and distinguishable.** Official source, policy assumption, user-entered, and AI output must remain separable in storage, APIs, exports, and the UI. A synthetic or fixture value must never be labelled `official_source`, and recorded evidence always outranks a synthetic one.

5. **Mask personal data on every read path.** Upstream trigger rules carry named individuals' email addresses. Fixtures retain them for provenance; every API response, UI render, packet, and export must mask them. If you add a response path, add it to the redaction sweep test.

6. **Preserve the audit record.** Never add an update or delete path for `case_events`. Mutations must respect the optimistic case version and record the relevant event inside the same transaction.

7. **Consume upstream science; never invent it.** Linda Node does not compute hazard models, indices, severity classifications, or exposure scores. Where a hazard needs a severity, map the upstream `severity_level` and say so in the policy file.

8. **Treat external input as untrusted.** Validate API input, escape rendered text, and keep field reports out of system prompts. Assist calls use structured JSON only.

9. **CAP stays `status=Exercise`.** This is a safety property, not demo framing: a CAP document marked `Actual` from a non-accredited sender can be ingested by a real alert aggregator. Do not change it to make a demo look better.

10. **Never commit secrets.** `.env` files, API keys, webhook secrets, and generated runtime data stay local. `var/` is gitignored.

11. **Keep scope deliberate.** Telegram, SMS/USSD delivery, payments, beneficiary selection, and live Husika write calls are not part of this project.

---

## Changing policy content

Policies and action cards are **code-reviewed files**, not UI state. They live in `server/backend/content/` and are JSON-Schema validated at startup — an invalid file stops the process.

- A new hazard needs `content/policies/<hazard>.yaml` with a `signal_basis` of `probability` or `upstream_severity`, plus a matching entry in `library.HAZARDS`.
- A new action card needs an id matching `^card_[a-z0-9_]+_v[0-9]+$`, both budget tranches, at least one prerequisite, and a disclaimer.
- Changing a threshold changes the policy hash, which is recorded on every case assessed against it. That is intended: old cases keep the version they were decided under.

## Changing an adapter

If an upstream shape changes, update the normaliser **and** `content/schemas/sources/<adapter>.schema.json` together, then re-record the fixture. Run the live contract suite before and after:

```bash
.venv/bin/pytest -q -m contract --contract
```

## Changing the integration API

`/integration/v1/` is a frozen contract. Its response shape is pinned by `content/schemas/integration/activation.v1.schema.json` (`additionalProperties: false`) and asserted by a snapshot test. Adding or removing a field is a **breaking change** and requires `/integration/v2/`, not an edit in place.

---

## Verification

Run everything before opening a pull request:

```bash
cd server/backend
.venv/bin/ruff check app tests
.venv/bin/python -c "from app.library import validate_library; print(validate_library())"
.venv/bin/pytest -q

cd ../../client/frontend
npx tsc -b --noEmit
npm test
npm run build
```

When changing a workflow, also exercise the role-based path in a browser: a blocked critical task, a rejected stale version, the three-role approval path, and the affected export or partner endpoint.

## Pull requests

Branch from `main` with a `feat/`, `fix/`, `docs/`, or `test/` prefix. Write commit messages that explain *why* the change is needed, not just what changed.

In the description, include the problem addressed, the behaviour changed and its trust or safety impact, the tests and manual verification performed, and any source, policy, OpenAPI, or fixture changes reviewers should inspect.

## Reporting issues

Use GitHub Issues for reproducible bugs and feature proposals. Do not report security vulnerabilities publicly; follow the [security policy](SECURITY.md).

## License

By contributing, you agree that your contribution is licensed under the [MIT License](LICENSE).
