# ValorAI

Nulfinance Inc. financial-management prototype: Astro + React 19 frontend, Django inside a Cloudflare Python Worker, D1, a singleton Durable Object coordinator, Turnstile. UI copy is Brazilian Portuguese; code, comments and commits are English.

## Sources of truth
- `README.md` (pt-BR) for commands and scope, `ARCHITECTURE.md` + `docs/adr/0001`, `docs/adr/0002` for modules, schema and decisions.
- Requirements baseline is `docs/valorai_requisitos.docx` (revision 1.3 content: RF001–RF009, financial complement, RNF, RS, traceability matrix, function points). It is the only requirements document — the Ata `v1.0`–`v1.3` DOCX/PDF and `revision_ata.md` were deleted and must not be recreated.
- `README.md` and `ARCHITECTURE.md` still cite those deleted Ata files; the citation is stale, not the document.
- `entrevista_valorai.pdf` (root) is the elicited scope. Logos: `assets/Nulfinance_Inc.svg` (company), `assets/ValorAI.svg` (product).
- No CI. Run checks locally. `.agents/skills/` + `skills-lock.json` are pinned agent skills; do not hand-edit the hashes.

## Commands (root)
- `npm ci` for the frontend; Python deps live in `server/python` and go through `uv`.
- `npm run check` = `astro check` (0 errors). It typechecks `src/` + `shared/` only; `tsconfig.json` excludes `server/` and `tests/`.
- `npm test` = 7 Zod/validation tests in `tests/*.test.ts` (Node test runner via `tsx`).
- `uv run --directory server/python pytest` = 22 backend tests in ~0.3 s against in-memory SQLite and fakes; no Worker or browser needed.
- `npm run test:e2e` = Playwright (`tests/browser`, 1 worker, `baseURL` `127.0.0.1:8787`). Prerequisites, in order: migrations applied, `npm run dev:api` running, and `npm run build` — the Worker serves `dist/`, so stale or missing `dist/` fails every test. `npx playwright install chromium` once.
- Docker: `docker compose up --build` (Worker 8787 + Astro HMR 4321 on `API_URL=http://api:8787`); `docker compose run --rm test` runs `npm test` and `pytest`.
- Node is `^22.23 || ^24.22 || ^26.12` (see `engines`). The Worker runtime is Python 3.14 (`pylock.toml` requires >=3.14.2) even though `pyproject.toml` says >=3.12.
- Migrations, from `server/python`: `uv run pywrangler d1 migrations apply valorai-prototype --local` (or `--remote`, before deploys). `npm run deploy` builds and runs `pywrangler deploy --env production`; never deploy with `ENVIRONMENT=development`.
- In `wrangler.jsonc`, `d1_databases` and `durable_objects` are not inherited by `env.production` — keep the duplicated blocks in sync when editing bindings.

## Backend map
- There is no URL router. Every request is one if-chain in `RegistrationApi._handle` (`server/python/valorai/http.py`); a new endpoint means a new branch there plus the `api('<path>')` helper in `RegistrationApp.tsx`.
- Only GET and POST reach the API (`admit` returns 405 otherwise); mutations are POSTs with an `action` field in the body (e.g. `delete` for transactions). `ARCHITECTURE.md` §5's `PUT`/`DELETE` and its `/api/confirm-email`, `/api/resend-confirmation`, `/api/financial-profile` paths do not exist — real paths are `/api/confirm`, `/api/resend`, `/api/finance`.
- GETs: `config`, `session`, `lessons`, `dashboard`, `demo-inbox`. POSTs: `register`, `login`, `logout`, `resend`, `confirm`, `finance`, `profile`, `transactions`, `transactions/import`, `transactions/receipt`, `limits`, `goal`, `lessons/progress`, `deactivate`.
- Domain modules (`account/`, `session/`, `confirmation/`, `finance/`, `ledger/`) never touch HTTP or the ORM; they receive repositories from `storage.py` (protocol: `query`/`execute`) plus injected clock, hasher, KV and audit.
- Repository SQL uses SQLite `?` placeholders; `DjangoDb` rewrites them to `%s` and `None` to `null` for `django-cf`. Keep `?`, do not copy `%s` in.
- `django-cf` 0.2.17 sets `supports_transactions = False`: there are no transactions, so audit events for data changes come from the generic triggers in `0009_generic_audit.sql` (rendered by `server/tools/audit_triggers.py`; never edit the SQL by hand, and extend the generator's column list when `accounts` gains an editable column). Only application-recorded events (login, lessons, goal progress, demo seeding) are written after the primary write.
- The Worker executes sync WSGI under the Durable Object: no `await` in domain code. Ephemeral state (codes, cooldowns, lockouts, throttles) goes through the synchronous `DurableKv` (`module_kv` table), not Workers KV.
- `worker.py` injects its own directory into `sys.path` and fabricates the `valorai` package because `pywrangler` treats that directory as the module root. `python_modules/` and `.venv-workers/` are generated and gitignored.

## Frontend
- `shared/validation.ts` (Zod) is the browser contract; `account/validation.py` re-implements the same rules server-side. Changing a rule means editing both and updating `tests/validation.test.ts`.
- Tokens live in `src/styles/global.css` under `:root` and `[data-theme="dark"]`; `.stitch/DESIGN.md` documents the light theme only. Theme is `data-theme` on `<html>`, persisted in `localStorage['valorai-theme']`, falling back to `prefers-color-scheme`; `ThemeToggle.tsx` also drives the Turnstile widget theme.
- `src/pages/index.astro` hydrates `RegistrationApp.tsx` (login + onboarding state machine), which renders `DashboardWorkspace.tsx` (Stitch Bento workspace, native `<dialog closedby="any">`, sub-pages Visão Geral / Transações & Extratos / Planejamento & Metas / Guias Práticos).

## Prototype boundaries
- Email confirmation is simulated: `EMAIL_MODE=demo`, status `demo_confirmed`, `emailVerified: false`; `/api/demo-inbox` reveals the code only to the pending account's own session. Confirmation limits (6 digits, 10 min, 5 attempts, 60 s resend, 3/hour) are prototype assumptions pending RF002 validation.
- Turnstile is skipped only when `ENVIRONMENT == "development"`; any other value enforces it. The secret is `TURNSTILE_SECRET_KEY` in Cloudflare, never in the repo.
- "Receipt AI" is deterministic filename/text heuristics (`_extract_receipt_metadata` in `ledger/module.py`) returning preset confidence values — no OCR or Workers AI binding. Imports parse CSV/OFX locally. Do not describe these as real AI or Open Finance.
- `seed_demo_cycle` (POST `transactions` with `action: "seed_demo"`) inserts synthetic ledger rows; never seed from read paths.

## Requirements traps
- RF describes bounded user goals and keeps its own validation rules; protection, audit and performance are transversal RNF.
- Revision 1.3 identifiers: RF001 register, RF002 confirm email, RF003 maintain profile, RF004 financial profile, RF005 deactivate, RF006 authenticate, RF007 session, RF008 recover password, RF009 change password (proposed, not approved).
- Financial capabilities (three ingestion channels, categories, limits/alerts, goals, guides) have no RF ids yet. The RF001–RF013 matrix and function-point table in the same DOCX use historical identifiers; neither maps onto the new RFs, and 88 PF is not the revised MVP size.
- MVP has only the Client role: no backoffice, support/admin accounts or temporary internal passwords. Educational content is seeded by migration, not managed in a UI.
- All three channels are essential: manual, CSV/Excel/OFX import, receipt photos. OFX was explicitly confirmed; Open Finance was not. Investments are optional and postposable — never require investor profiling.
- Every transaction needs a category. Limits alert on reach/exceed and never block a payment or a save; R$100/day is a configurable example. Avatar is JPG/PNG up to 2 MB; receipt upload limits are undecided, as are native vs. mobile-first web, alert channels and alert latency.
- Passwords use bcrypt (cost 10), not the early review's Argon2id. Confirmation and recovery codes are separate; recovery limits must not inherit confirmation limits. RF008 is still unimplemented.
- Deactivation is logical deletion: preserve financial records, block login, revoke sessions. Reactivation, retention and erasure remain open; it does not establish LGPD compliance.

## Editing documents
- DOCX is a ZIP/XML package: preserve styles, tables, media and relationships; never rebuild it from plain text.
- Extract with `pandoc "docs/valorai_requisitos.docx" -t plain`; render with LibreOffice `soffice.com` into a temporary directory (never over a deliverable) and check table and page breaks.
- Before replacing a DOCX, check for `~$*` / `.~lock.*` files and have the user close Word, or write a separately named revision. A PDF does not update when its DOCX changes.
