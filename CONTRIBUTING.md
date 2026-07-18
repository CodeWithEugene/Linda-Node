# Contributing to Linda Node

Thanks for your interest in Linda Node — a last-mile anticipatory action engine for the Greater Horn of Africa, built on ICPAC's open-source triggers pipeline.

**Start by reading the [README](README.md) in full.** It is the single source of truth: the architecture ([§5](README.md#5-system-architecture)), the complete build specification ([§7](README.md#7-implementation-guide-for-developers--ai-agents)), and the phased plan with acceptance criteria ([§10](README.md#10-development-status-build-plan--milestones)). Contributions — human or AI-agent — should build the earliest incomplete phase and respect the scope cuts listed there.

## Ground Rules

1. **Honesty over polish.** Never present unbuilt features as built — in code comments, docs, or the README. This project's credibility depends on accurately citing ICPAC's real tooling (see [§6](README.md#6-icpac-data-infrastructure-what-we-integrate-with)); verify any claim about upstream repos/scripts against the actual source before writing it down.
2. **Scope discipline.** The hackathon MVP is defined in [§10](README.md#10-development-status-build-plan--milestones). USSD/SMS, voice notes, mesh networking, extra languages, and Celery/Redis are roadmap items — don't build them now.
3. **Safety-critical invariants** (do not weaken these in any PR):
   - Trigger evaluation and the Triangulation Engine are **deterministic code** — the LLM never decides whether a trigger fired or whether a dossier may be issued.
   - Proof of Risk dossiers are decision-support documents; a **human authorizes** any financing action.
   - Community reports are untrusted input: structured-output classification only, never concatenated into system prompts, always rendered escaped.
   - Every alert must attribute its forecast to ICPAC and avoid certainty inflation.
4. **No secrets in the repo.** `.env` is gitignored; keep it that way. Keys belong in your environment or the deploy platform's secret store.
5. **Files under 500 lines.** Split modules before they sprawl.

## Development Setup

Follow [README §7.2](README.md#72-environment--setup): clone, copy `.env.example` → `.env`, install backend (`pip install -e .` in `backend/`) and frontend (`npm install` in `frontend/`), and use ngrok for local Telegram webhooks. Enable `postgis` and `vector` extensions in your Supabase project.

## Workflow

1. **Branch** from `main`: `feat/<short-name>`, `fix/<short-name>`, or `docs/<short-name>`.
2. **Commit style:** [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `test:`, `chore:`).
3. **Test:** `pytest` in `backend/` must pass; add tests for new ingestion parsers, spatial queries, and triangulation logic (fixtures with sample NetCDF/CSV live in `backend/tests/`).
4. **Verify before PR:** run the relevant flow end-to-end (e.g., seed demo data with `scripts/seed_demo.py`, exercise the bot from a real Telegram client) — not just the test suite.
5. **PR description:** what changed, why, which README phase/section it implements, and how you verified it.

## Code Style

- **Python:** type-hinted, `ruff` + `black` formatted, async-first (FastAPI/aiogram). Pydantic models for all I/O boundaries; validate input at system boundaries.
- **TypeScript:** strict mode, functional React components, no `any` at API boundaries.
- **Prompts:** all LLM prompts live in `backend/app/agents/prompts.py`, versioned as named constants — never inline prompt strings in handlers.
- **SQL/PostGIS:** migrations as SQL files; every geometry column gets a GiST index.

## Reporting Issues

- **Bugs / feature requests:** open a GitHub issue with reproduction steps or a concrete use case.
- **Security vulnerabilities:** do **not** open an issue — follow [SECURITY.md](SECURITY.md).

## License

By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE).
