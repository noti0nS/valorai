# ADR 0003: Database-Owned Audit Trail and Integrity Triggers

Date: 12 November 2026. This record covers migrations `0003_audit_triggers.sql`, `0004_goal_and_session_triggers.sql` and `0005_account_audit_triggers.sql` (commits `f2d5b67`, `cd71a11`, `6739260`). It builds on the write-ordering rule in [ADR 0001](./0001-django-workers-architecture.md) and [ADR 0002](./0002-dashboard-ledger-and-stitch-workspace.md) and replaces it for the events listed below.

## Context

`django-cf` 0.2.17 sets `supports_transactions = False`, so a request that changes state and then writes an audit event runs as separate statements. ADR 0001 and ADR 0002 handled that by committing primary state first and writing the audit event after. A crash or error between the two statements then lost the event, and the audit trail is a transversal RNF, not an optional log. The same gap affected two other multi-statement flows: a goal contribution inserted a transaction and then updated `accounts.goal_current_cents`, and deactivation changed the status and then revoked sessions in a separate statement.

SQLite triggers run atomically with the statement that fires them, and D1 executes them. Moving the follow-up write into a trigger removes the window without needing transactions.

## Decision

### 1. Triggers write data-change and account lifecycle audit events

| Source | Trigger event | Audit event |
| --- | --- | --- |
| `transactions` insert | `transactions_audit_insert` | `transaction_created`, `transaction_imported` (channel `import`), `receipt_transaction_saved` (channel `photo`) |
| `transactions` update | `transactions_audit_update` | `transaction_validated`, `transaction_status_toggled`, `transaction_updated` |
| `transactions` delete | `transactions_audit_delete` | `transaction_deleted` |
| `budget_limits` insert, update, delete | `budget_limits_audit_*` | `budget_limit_updated`, `budget_limit_deleted` |
| `profile_changes` insert | `profile_changes_audit_insert` | `profile_updated` |
| `accounts` insert | `accounts_audit_registered` | `registration_created` |
| `accounts.status` to `demo_confirmed` | `accounts_audit_confirmed` | `demo_confirmation_completed` |
| `accounts.status` to `inactive` | `accounts_audit_deactivated` | `account_deactivated` |
| `accounts` update of `income`, `fixed_expenses` or `goal` | `accounts_audit_finance` | `financial_profile_updated` |

Rows whose `external_ref` starts with `seed-` do not fire the insert trigger, because `seed_demo_cycle` already records its own `demo_cycle_seeded` event.

### 2. Request context lives in a one-row table

A trigger cannot see the caller's IP hash or the injected clock. Migration 0003 adds `audit_context` (`id` fixed at 1, `ip_hash`, `at`). `RegistrationApi._handle` calls `audit.bind(ip_hash, clock.now())` before each request (`valorai/http.py`), which runs `UPDATE audit_context SET ip_hash = ?, at = ? WHERE id = 1` (`SqlAudit.bind` in `valorai/storage.py`). Triggers read that row, so event times follow the injected clock and tests stay deterministic. The row starts as `('unbound', 0)`, so an event written without a bind is visibly wrong instead of silently attributed to a request.

The shared row is safe only because of the runtime already fixed in ADR 0001: one `accounts-v1` Durable Object serves synchronous WSGI, and domain code has no `await`, so requests do not interleave between `bind` and the writes that follow.

### 3. Append-only history

`audit_events` and `profile_changes` reject `UPDATE` and `DELETE` through `BEFORE` triggers that raise `ABORT`. History cannot be rewritten or removed from the application or from a manual statement on the same database.

### 4. Integrity triggers that share the same motive

- **Goal balance.** Migration 0004 adds `transactions.goal_contribution` (0 or 1). Triggers on insert, `amount_cents` update and delete adjust `accounts.goal_current_cents`, clamped at zero on decrease. A dedicated flag replaced matching on `merchant_doc`, which users can type. The flag cannot change after insert (`transactions_goal_flag_immutable`).
- **Deactivation.** `accounts_revoke_sessions` deletes the account's sessions in the same statement that sets `status = 'inactive'`, and `sessions_block_inactive` refuses any later session insert for that account. This keeps RF005 (logical deletion: preserve records, block login, revoke sessions) true even if a code path forgets a step.

### 5. What stays in the application

`login_succeeded` and `login_failed` map to no row change, so `SqlAudit.record` still writes them. Goal, lesson and `demo_cycle_seeded` events also remain application-side. `MemoryAudit.bind` is a no-op, because the in-memory stores used by fast tests have no triggers.

## Consequences

- **Gained:** an event can no longer be lost between the primary write and its audit row, and deactivation and goal balance can no longer half-complete. Tests in `server/python/tests/test_sql.py` pin the bound IP hash and clock, append-only rejection, the single deactivation event, the goal balance on insert, edit and delete, and session revocation plus the block on new sessions.
- **Costs and risks:**
  - Audit behavior is now in SQL, invisible when reading the Python modules. Every new write path to these tables must be checked against the triggers, and a change to an event name is a new migration, not an edit of an applied one.
  - `accounts_audit_finance` has no `WHEN` clause, so saving unchanged values still logs an event, and a goal change from the goal screen logs `financial_profile_updated` as well.
  - A mutating request that never calls `bind` writes events with `ip_hash` `unbound` and time 0.
  - Rows created before 0004 with `merchant_doc` `APORTE.META` remain plain expenses. They were not backfilled, because a backfill would write audit rows without a request context.
  - Existing databases fail on `/api/register` until the migrations are applied: the register path now depends on the new tables and triggers. Run `uv run pywrangler d1 migrations apply valorai-prototype --local` (or `--remote` before deploys).
- **Follow-ups:**
  - `ARCHITECTURE.md` still lists the old event names (`account.registered`, `ledger.transaction_created`, and so on) and still says audit writes follow primary writes. The names and the note are stale; this record is the current description.
  - Whether `financial_profile_updated` should skip goal-only edits, and the retention of `audit_events` after deactivation, remain open and are not settled by this decision.

## What a later review should leave in place

Keep audit events for data changes in triggers, the `audit_context` bind at the start of every request, the append-only guards, and the two integrity triggers for goal balance and deactivation. Keep login events in the application. Do not move audit writes back to separate statements while `supports_transactions` is false. Revisit this decision if a `django-cf` release provides working D1 transactions, if the coordinator stops being a single synchronous Durable Object, or if request handling becomes concurrent, because the shared `audit_context` row would then mix requests.
