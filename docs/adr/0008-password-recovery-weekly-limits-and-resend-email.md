# ADR 0008: Password Recovery, Authenticated Password Change, Weekly Budget Limits, and Resend Email Delivery

Date: 13 November 2026. Covers `RF008` password recovery, `RF009` authenticated password change, the `weekly` budget limit scope (`0011_weekly_limit_scope.sql`), and optional transactional email delivery via `ResendMailer` (`valorai/mailer.py`). Builds on [ADR 0001](0001-django-workers-architecture.md), [ADR 0002](0002-dashboard-ledger-and-stitch-workspace.md), [ADR 0005](0005-generic-audit-triggers.md), and [ADR 0006](0006-requirements-1-4-conformance.md); does not alter `accounts` editable-profile triggers or `AI` modules.

## Context

A requirements audit against `docs/valorai_requisitos.docx` (revision 1.5) identified three functional gaps in the prototype:
1. **Password lifecycle (`RF008`, `RF009`):** Unauthenticated password recovery (`RF008`) and authenticated password change (`RF009`) were not yet implemented, and recovery limits must remain segregated from `RF002` email confirmation limits.
2. **Weekly spending limit (`RF014`):** `budget_limits.scope` only allowed `category`, `daily`, and `card_share` in both `LimitScope` (`records.py`) and the `CHECK` constraint in `0002_dashboard_ledger.sql`.
3. **Real email delivery for production:** `EMAIL_MODE="demo"` kept codes inside `/api/demo-inbox` and `/api/recovery/demo-inbox`. With the `noti0ns.dev` zone active on Cloudflare, transactional emails can be sent from `mail.noti0ns.dev` via HTTP without adding SMTP libraries to the synchronous Durable Object runtime.

## Decision

1. **Segregated password recovery (`RF008`) and authenticated password change (`RF009`).**
   - `ConfirmationModule` (`server/python/valorai/confirmation/module.py`) stores recovery challenges in `DurableKv` under a separate `recovery:` prefix with `RF008` limits: 15-minute expiry (`RECOVERY_SECONDS = 900`), 5 incorrect attempts before invalidation (`RECOVERY_MAX_ATTEMPTS = 5`), 60-second resend cooldown, and 5 issuances per hour (`RECOVERY_MAX_SENDS = 5`).
   - `AccountModule` (`server/python/valorai/account/module.py`) adds `find_active_by_email`, `recover_password`, and `change_password`, delegating password hashing to the injected `BcryptHasher` (cost 10) and persisting hashes via `update_password` (`storage.py`). Both flows call `SessionModule.revoke_all` and record application audit events (`password_recovered`, `password_changed`).
   - `RegistrationApi` (`http.py`) exposes `POST /api/recovery/request` (returning a uniform response regardless of account existence), `POST /api/recovery/demo-inbox` (active only when `EMAIL_MODE == "demo"`), `POST /api/recovery/reset`, and `POST /api/password` (returning a fresh session cookie for the current device after revoking all prior sessions).

2. **Weekly budget limit scope (`RF014`, `0011_weekly_limit_scope.sql`).**
   - `LimitScope` (`records.py`) adds `WEEKLY = "weekly"`.
   - Migration `0011_weekly_limit_scope.sql` drops `v_monthly_category_spending` (required by SQLite before renaming a referenced table), recreates `budget_limits` with `CHECK(scope IN ('category', 'daily', 'weekly', 'card_share'))`, and restores the view and `budget_limits_audit_i`/`_u`/`_d` triggers from `0009_generic_audit.sql`.
   - `LedgerModule._evaluate_limits` sums non-income expenses within the current Monday–Sunday ISO week (`today_date - timedelta(days=today_date.weekday())` through `+6` days). `DashboardWorkspace.tsx` exposes the `"Teto de consumo semanal"` option.

3. **Transactional email via Resend HTTP API (`valorai/mailer.py`, `worker.py`).**
   - `ResendMailer.send_code` posts JSON to `https://api.resend.com/emails` using the synchronous `worker_http_post` transport already injected for AI calls (`run_sync(fetch(...))`).
   - `GET /api/config` returns the active `emailMode` instead of a hardcoded `"demo"`. When `EMAIL_MODE == "resend"`, `/api/register`, `/api/resend`, and `/api/recovery/request` dispatch real emails from `ValorAI <noreply@mail.noti0ns.dev>` (`EMAIL_FROM`), while `/api/demo-inbox` and `/api/recovery/demo-inbox` return `404`.
   - `server/python/wrangler.jsonc` keeps `EMAIL_MODE="demo"` in local `vars` and sets `EMAIL_MODE="resend"` in `env.production.vars`, with `RESEND_API_KEY` stored exclusively as a Wrangler secret.

## Alternatives considered

- **Adding `password_hash` to `accounts_audit_u` trigger:** Rejected so `accounts_audit_u` remains scoped to profile/finance columns and `AccountModule` records distinct `password_recovered` / `password_changed` events explicitly.
- **SMTP client or Google Apps Script webhook:** Rejected because `noti0ns.dev` is already managed on Cloudflare DNS and Resend provides a single-call HTTPS API with verified DKIM/SPF on `mail.noti0ns.dev` without introducing SMTP socket dependencies into `workers-py`.

## Consequences

- **Gained:**
  - Full `RF008` and `RF009` password lifecycle with session revocation, verified by `test_rf008_password_recovery_demo_flow_and_session_revocation` and `test_rf009_authenticated_password_change_revokes_other_sessions` in `server/python/tests/test_http.py`.
  - Weekly limit evaluation verified by `test_weekly_limit_evaluates_current_week_expenses` in `server/python/tests/test_ledger.py` and schema compatibility across all 11 migrations in `tests/test_sql.py` (`46 passed` in `pytest`, `7` passed in `npm test`, `0` errors in `astro check`).
  - Real email delivery in production via `mail.noti0ns.dev` (`ResendMailer` tested via `test_resend_mailer_sends_confirmation_and_recovery_codes`) while preserving zero-dependency `demo` mode for local development and tests.
- **Costs and risks:**
  - Production deployments with `EMAIL_MODE="resend"` depend on `RESEND_API_KEY` remaining configured as a Worker secret and Resend's free-tier quota (3,000 emails/month, 100/day).
  - `0011_weekly_limit_scope.sql` duplicates the `v_monthly_category_spending` and `budget_limits_audit_*` definitions from `0008` and `0009`; future edits to those definitions must keep `0011` in mind.
- **Follow-ups:**
  - `RF003` address subfields (*Bairro, Rua, Número, Complemento*) remain outside the current schema (`accounts` stores `postal_code`, `state`, `city` only) and should be either added or formally scoped out in a future requirements revision.

## What a later review should leave in place

- Keep `recovery:` and `code:` prefixes private to `ConfirmationModule` (`test_confirmation_storage_prefix_is_private`).
- Keep `EMAIL_MODE="demo"` in local test fixtures and `vars`, enabling `EMAIL_MODE="resend"` only when `RESEND_API_KEY` is provided.
- Never allow `/api/recovery/request` to return different HTTP statuses or payloads for existing vs. non-existing email addresses.
