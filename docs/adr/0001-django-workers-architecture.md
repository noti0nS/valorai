# ADR 0001: Django on Python Workers

Date: 10 November 2026. This record describes the registration backend that ran in the worktree. It does not amend the meeting of 22 October 2026.

## Decision

The registration slice runs as Django inside a Python Worker. `pywrangler` (workers-py 1.17.9, passing commands to Wrangler 4.160.0) is the deploy CLI. `server/cloudflare.config.ts` stays for the previous TypeScript Worker and cannot host this Python entry.

Local command that served the suite:

`uv run pywrangler dev --ip 127.0.0.1 --port 8787`

from `server/python`, using `server/python/wrangler.jsonc`.

## Modules

- Account owns identity, status (`pending`, `demo_confirmed`, `inactive`), password checks, and deactivation. It receives a hasher and does not import bcrypt.
- Session owns the `valorai_session` cookie, the SHA-256 token hash, the 30-minute idle timeout, the 12-hour cap, and revocation.
- Confirmation owns the demo code and its counters. The storage prefix `code:` appears only in `valorai/confirmation/module.py`. No recovery module imports those counters. The prototype limits, 6 digits, 10 minutes, 5 attempts, 60 seconds between sends, and 3 sends per hour, still await RF002 approval.
- Financial profile owns income, fixed expenses, goal, and the cents conversion.

Lessons stay a seeded read. The Client remains the only role. `demo_confirmed` is not email verification: responses keep `emailVerified: false`.

## Seams and adapters

The Worker entry is one adapter. `Default.fetch` serves static assets outside `/api`, rejects a POST whose `Origin` is not the request origin, and forwards `/api` to the Durable Object named `accounts-v1` (`AuthCoordinator`). That object serves Django through `workers.wsgi.fetch`.

The in-process tests are the second adapter. They call the same Account, Session, Confirmation, and Financial profile modules without a browser. `uv run pytest` in `server/python` passed 17 tests. `npx playwright test` then passed both registration browser tests against `http://127.0.0.1:8787`.

## Database and transactions

Accounts, sessions, audit events, and lessons use the existing D1 database `valorai-prototype` (`9186a9b0-dce5-442b-96ee-a3e67b4fe2b0`) through `django_cf.db.backends.d1` and the `DB` binding. A registration stored a bcrypt hash whose prefix is `$2b$10$`, and a financial profile stored income as `350000` cents.

`django-cf` 0.2.17, the build that served these requests, sets `supports_transactions` to false and does not start a SQLite transaction. Rollback is a no-op. Deactivation therefore writes in this order, and a failure between the writes cannot be rolled back: account status, session revocation, confirmation code, audit event.

Confirmation codes, login failures, and request throttles are rows in the coordinator's own SQLite table `module_kv`, not in D1.

## Hasher

`BcryptHasher` lives with the coordinator and uses bcrypt cost 10. One hash during `POST /api/register`, which returned 201, measured `bcrypt_cost_10_ms=81.0` with `time.perf_counter` around `hashpw` inside the local Python Worker. The README recorded a Workers Free CPU budget of 10 ms per invocation on 29 October 2026. 81.0 ms does not show that this hash fits that budget, so `accounts-v1` keeps the hasher. Account does not take it over.

Django's database calls are synchronous, so the Worker sets `DJANGO_ALLOW_ASYNC_UNSAFE=1` before creating the WSGI application.

## What a later review should leave in place

Keep bcrypt at cost 10, separate confirmation limits from any future recovery limits, `demo_confirmed` distinct from email verification, the Client as the only role, and these four modules instead of one `handle()`. Keep the coordinator for hashing until a new measurement shows cost 10 finishes inside the Workers CPU budget. Do not build the ledger on this D1 backend while its transactions remain a no-op.

Turnstile runs when `ENVIRONMENT` is not `development`. The browser suite ran with the top-level Wrangler vars, where that value is `development` and Turnstile is skipped. The `production` environment in `wrangler.jsonc` sets `ENVIRONMENT` to `production` and the public site key. The Turnstile secret stays a Worker secret and is not in the repository.
