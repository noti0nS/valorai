# ADR 0005: Generic Audit Triggers Rendered From One Template

Date: 12 November 2026. This record covers migration `0009_generic_audit.sql`, its generator `server/tools/audit_triggers.py` and the per-request reset of `audit_context`. It replaces section 1 of [ADR 0003](./0003-database-owned-audit-trail.md) (the per-event triggers) and keeps the rest of that decision: database-owned audit, the `audit_context` bind, append-only guards, the goal and deactivation integrity triggers, and login events in the application.

## Context

ADR 0003 moved data-change audit into SQLite triggers because `django-cf` 0.2.17 sets `supports_transactions = False`. It did so with a different trigger per event: eleven audit triggers across migrations 0003 and 0005, each with its own event name, and `CASE` and `WHEN` logic that classified changes (`transaction_imported`, `transaction_validated`, `transaction_status_toggled`, `financial_profile_updated` and so on). A review of that design found three costs:

- The classification logic lives in SQL, invisible from the Python modules, and every new write path had to be checked against it.
- Events carried no row identity. `transaction_deleted` did not say which transaction was deleted.
- Some triggers fired for the wrong reason: `accounts_audit_finance` logged saves of unchanged values, and a goal contribution produced both `transaction_created` and an application-side event.

The project is at an early stage, so an incompatible change to the event vocabulary and a `DROP TRIGGER` migration are acceptable. SQLite has no table wildcard in `CREATE TRIGGER` and no table-name variable, so a single trigger cannot cover several tables.

## Decision

### 1. One trigger shape per table and operation

Migration 0009 drops the eleven triggers of 0003 and 0005 and creates, for each audited table, the same three-line trigger body:

| Table | Triggers | Event |
| --- | --- | --- |
| `transactions` | `transactions_audit_i`, `_u`, `_d` | `transactions.insert`, `.update`, `.delete` |
| `budget_limits` | `budget_limits_audit_i`, `_u`, `_d` | `budget_limits.insert`, `.update`, `.delete` |
| `accounts` | `accounts_audit_i`, `_u` | `accounts.insert`, `accounts.update` |

Each trigger copies `ip_hash` and `at` from `audit_context` and writes the owning account and the row id. `audit_events` gains a nullable `entity_id` column for the row id. The event name is `<table>.<operation>`, so the vocabulary is derived from the schema and a new table needs no new names.

Two details are not uniform, and both are explicit in the generator:

- `transactions_audit_i` keeps `WHEN external_ref NOT LIKE 'seed-%'`, because `seed_demo_cycle` records its own `demo_cycle_seeded` event.
- `accounts_audit_u` fires only on `UPDATE OF` the profile and finance columns (`name`, `birth_date`, `phone`, `postal_code`, `state`, `city`, `avatar_data`, `income`, `fixed_expenses`, `goal`, `completed_at`, `goal_target_cents`, `goal_monthly_cents`). It leaves out `goal_current_cents`, which the goal-balance triggers of migration 0004 move as a consequence of a transaction already audited, and `status`.

### 2. One extra trigger for account status

`accounts_audit_status` fires on a real change of `accounts.status` and writes `accounts.status.<new status>`: `accounts.status.demo_confirmed` (RF002) and `accounts.status.inactive` (RF005). Without it, confirmation and deactivation would be indistinguishable from any other account edit. `profile_changes_audit_insert` is dropped: the profile edit already fires `accounts_audit_u`, and the `profile_changes` rows (append-only) still hold which fields changed.

### 3. A generator, not hand-written SQL

D1 migrations are plain SQL, so the repetition is produced by `server/tools/audit_triggers.py` (`python server/tools/audit_triggers.py > server/migrations/0009_generic_audit.sql`). The table list and the account-column expression live in its `AUDITED` dictionary. The committed migration must equal `render()`, pinned by `test_generated_migration_matches_the_generator`. Adding an audited table later means a new migration generated from the same template, not an edit of 0009.

### 4. The request context is reset after each request

`RegistrationApi.handle` now calls `audit.unbind()` in a `finally` block. `SqlAudit.unbind` sets `audit_context` back to `('unbound', 0)` and only executes when a `bind` happened, so GET requests cost no extra statement. ADR 0003 claimed that a write without a bind would be visibly wrong, but only the first request after migration behaved that way: later stray writes silently reused the previous request's IP hash and time. `MemoryAudit.unbind` is a no-op.

### 5. What stays unchanged

Login events (`login_succeeded`, `login_failed`) and the goal, lesson and `demo_cycle_seeded` events remain in `SqlAudit.record`. Append-only guards, the goal-balance triggers and the deactivation triggers (`accounts_revoke_sessions`, `sessions_block_inactive`) are not touched.

## Alternatives considered

- **Keep the semantic event names and only add `entity_id`.** This preserves `transaction_imported` and `transaction_validated`, but keeps the classification logic in SQL that the review flagged. Rejected in favor of fewer, uniform triggers.
- **Record before and after values in a JSON `detail` column.** It would answer what changed, but needs per-table column lists inside the triggers, which is the per-table logic this decision removes. `entity_id` gives the pointer to the row, and the transaction row itself holds the channel and status. Left for a later decision if the requirements ask for it.
- **Audit from the application with a decorator or ORM signal.** Rejected for the reason in ADR 0003: without transactions, a statement after the primary write can be lost.

## Consequences

- **Gained:** the audit trigger set shrinks from eleven special-purpose triggers to eight uniform ones plus one status trigger, all rendered from one template. Every data event now names the row it touched (`test_triggers_record_data_changes_with_the_bound_request_context` asserts the id on a delete). A write outside a request is recorded as `unbound` with time 0 (`test_context_is_reset_after_a_request_so_stray_writes_are_visibly_unbound`). A goal contribution no longer logs an account edit (`test_goal_contribution_balance_is_kept_by_triggers`).
- **Costs and risks:**
  - Business meaning is lost from the event name. Whether a transaction was imported, validated or only toggled must be read from the transaction row, which can change again, so the trail no longer records that distinction.
  - Update triggers have no `WHEN`, so a save of unchanged values still writes an event, as in ADR 0003.
  - Audit rows written before migration 0009 keep the old names, so queries over the whole history must handle both vocabularies. `entity_id` is `NULL` for them and for application-recorded events.
  - `accounts_audit_u` depends on a column list. A new editable column on `accounts` stays unaudited until the list in the generator is extended and a new migration is rendered.
  - The shared `audit_context` row still assumes the single synchronous Durable Object described in ADR 0003.
- **Follow-ups:**
  - `ARCHITECTURE.md` and `docs/trabalho_banco_de_dados_3af.md` still describe the old event names. They were not edited here.
  - The `AGENTS.md` note that primary state is committed before audit writes is now true only for the application-recorded events.
  - `ip_hash` is an unsalted SHA-256 of the client IP, which can be brute-forced over the IPv4 space. Not changed by this decision.
  - Retention of `audit_events` after deactivation remains open.

## What a later review should leave in place

Keep audit events for data changes in triggers generated from the one template, the `entity_id` on every data event, the `audit_context` bind at the start of a POST and the reset after every request, the append-only guards, and the generator-versus-migration test. Do not edit `0009_generic_audit.sql` by hand. Revisit if the requirements need the business distinction between import, validation and edit in the trail (add a `detail` column then), if `django-cf` gains working D1 transactions, or if request handling stops being synchronous on a single coordinator.
