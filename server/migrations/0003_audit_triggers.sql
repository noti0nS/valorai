-- Database-owned audit trail.
-- D1 via django-cf has no transactions, so an app-level audit write after the primary write can be lost.
-- A trigger runs atomically with the statement that fires it.

-- Request context (IP hash and clock) bound by the app before each mutation; triggers cannot see either.
CREATE TABLE audit_context (
  id INTEGER PRIMARY KEY CHECK(id = 1),
  ip_hash TEXT NOT NULL,
  at INTEGER NOT NULL
);
INSERT INTO audit_context(id, ip_hash, at) VALUES (1, 'unbound', 0);

-- Append-only guards (RNF audit): history cannot be rewritten or removed.
CREATE TRIGGER audit_events_no_update BEFORE UPDATE ON audit_events
BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END;
CREATE TRIGGER audit_events_no_delete BEFORE DELETE ON audit_events
BEGIN SELECT RAISE(ABORT, 'audit_events is append-only'); END;
CREATE TRIGGER profile_changes_no_update BEFORE UPDATE ON profile_changes
BEGIN SELECT RAISE(ABORT, 'profile_changes is append-only'); END;
CREATE TRIGGER profile_changes_no_delete BEFORE DELETE ON profile_changes
BEGIN SELECT RAISE(ABORT, 'profile_changes is append-only'); END;

-- Transactions. Rows seeded by the demo cycle ('seed-' refs) are covered by its own demo_cycle_seeded event.
CREATE TRIGGER transactions_audit_insert AFTER INSERT ON transactions
WHEN NEW.external_ref IS NULL OR NEW.external_ref NOT LIKE 'seed-%'
BEGIN
  INSERT INTO audit_events(account_id, event, ip_hash, created_at)
  SELECT NEW.account_id,
         CASE NEW.channel
           WHEN 'import' THEN 'transaction_imported'
           WHEN 'photo' THEN 'receipt_transaction_saved'
           ELSE 'transaction_created'
         END,
         ip_hash, at
  FROM audit_context WHERE id = 1;
END;

CREATE TRIGGER transactions_audit_update AFTER UPDATE ON transactions
BEGIN
  INSERT INTO audit_events(account_id, event, ip_hash, created_at)
  SELECT NEW.account_id,
         CASE
           WHEN OLD.validated <> NEW.validated THEN 'transaction_validated'
           WHEN OLD.status <> NEW.status AND OLD.title = NEW.title AND OLD.amount_cents = NEW.amount_cents
             THEN 'transaction_status_toggled'
           ELSE 'transaction_updated'
         END,
         ip_hash, at
  FROM audit_context WHERE id = 1;
END;

CREATE TRIGGER transactions_audit_delete AFTER DELETE ON transactions
BEGIN
  INSERT INTO audit_events(account_id, event, ip_hash, created_at)
  SELECT OLD.account_id, 'transaction_deleted', ip_hash, at FROM audit_context WHERE id = 1;
END;

-- Limits. The upsert fires INSERT on first write and UPDATE on conflict.
CREATE TRIGGER budget_limits_audit_insert AFTER INSERT ON budget_limits
BEGIN
  INSERT INTO audit_events(account_id, event, ip_hash, created_at)
  SELECT NEW.account_id, 'budget_limit_updated', ip_hash, at FROM audit_context WHERE id = 1;
END;
CREATE TRIGGER budget_limits_audit_update AFTER UPDATE ON budget_limits
BEGIN
  INSERT INTO audit_events(account_id, event, ip_hash, created_at)
  SELECT NEW.account_id, 'budget_limit_updated', ip_hash, at FROM audit_context WHERE id = 1;
END;
CREATE TRIGGER budget_limits_audit_delete AFTER DELETE ON budget_limits
BEGIN
  INSERT INTO audit_events(account_id, event, ip_hash, created_at)
  SELECT OLD.account_id, 'budget_limit_deleted', ip_hash, at FROM audit_context WHERE id = 1;
END;

-- Profile edits: profile_changes is only written when a field really changed.
CREATE TRIGGER profile_changes_audit_insert AFTER INSERT ON profile_changes
BEGIN
  INSERT INTO audit_events(account_id, event, ip_hash, created_at)
  SELECT NEW.account_id, 'profile_updated', ip_hash, at FROM audit_context WHERE id = 1;
END;

-- Deactivation (RF005).
CREATE TRIGGER accounts_audit_deactivated AFTER UPDATE OF status ON accounts
WHEN NEW.status = 'inactive' AND OLD.status <> 'inactive'
BEGIN
  INSERT INTO audit_events(account_id, event, ip_hash, created_at)
  SELECT NEW.id, 'account_deactivated', ip_hash, at FROM audit_context WHERE id = 1;
END;
