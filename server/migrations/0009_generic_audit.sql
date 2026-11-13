-- Generic audit triggers, rendered by server/tools/audit_triggers.py. Do not edit by hand.
-- One trigger shape per table and operation replaces the per-event triggers of 0003 and 0005.
-- event is '<table>.<insert|update|delete>'; entity_id is the id of the changed row.

ALTER TABLE audit_events ADD COLUMN entity_id TEXT;

DROP TRIGGER IF EXISTS transactions_audit_insert;
DROP TRIGGER IF EXISTS transactions_audit_update;
DROP TRIGGER IF EXISTS transactions_audit_delete;
DROP TRIGGER IF EXISTS budget_limits_audit_insert;
DROP TRIGGER IF EXISTS budget_limits_audit_update;
DROP TRIGGER IF EXISTS budget_limits_audit_delete;
DROP TRIGGER IF EXISTS profile_changes_audit_insert;
DROP TRIGGER IF EXISTS accounts_audit_registered;
DROP TRIGGER IF EXISTS accounts_audit_confirmed;
DROP TRIGGER IF EXISTS accounts_audit_deactivated;
DROP TRIGGER IF EXISTS accounts_audit_finance;

CREATE TRIGGER transactions_audit_i AFTER INSERT ON transactions
WHEN NEW.external_ref IS NULL OR NEW.external_ref NOT LIKE 'seed-%'
BEGIN
  INSERT INTO audit_events(account_id, event, entity_id, ip_hash, created_at)
  SELECT NEW.account_id, 'transactions.insert', NEW.id, ip_hash, at FROM audit_context WHERE id = 1;
END;

CREATE TRIGGER transactions_audit_u AFTER UPDATE ON transactions
BEGIN
  INSERT INTO audit_events(account_id, event, entity_id, ip_hash, created_at)
  SELECT NEW.account_id, 'transactions.update', NEW.id, ip_hash, at FROM audit_context WHERE id = 1;
END;

CREATE TRIGGER transactions_audit_d AFTER DELETE ON transactions
BEGIN
  INSERT INTO audit_events(account_id, event, entity_id, ip_hash, created_at)
  SELECT OLD.account_id, 'transactions.delete', OLD.id, ip_hash, at FROM audit_context WHERE id = 1;
END;

CREATE TRIGGER budget_limits_audit_i AFTER INSERT ON budget_limits
BEGIN
  INSERT INTO audit_events(account_id, event, entity_id, ip_hash, created_at)
  SELECT NEW.account_id, 'budget_limits.insert', NEW.id, ip_hash, at FROM audit_context WHERE id = 1;
END;

CREATE TRIGGER budget_limits_audit_u AFTER UPDATE ON budget_limits
BEGIN
  INSERT INTO audit_events(account_id, event, entity_id, ip_hash, created_at)
  SELECT NEW.account_id, 'budget_limits.update', NEW.id, ip_hash, at FROM audit_context WHERE id = 1;
END;

CREATE TRIGGER budget_limits_audit_d AFTER DELETE ON budget_limits
BEGIN
  INSERT INTO audit_events(account_id, event, entity_id, ip_hash, created_at)
  SELECT OLD.account_id, 'budget_limits.delete', OLD.id, ip_hash, at FROM audit_context WHERE id = 1;
END;

CREATE TRIGGER accounts_audit_i AFTER INSERT ON accounts
BEGIN
  INSERT INTO audit_events(account_id, event, entity_id, ip_hash, created_at)
  SELECT NEW.id, 'accounts.insert', NEW.id, ip_hash, at FROM audit_context WHERE id = 1;
END;

CREATE TRIGGER accounts_audit_u AFTER UPDATE OF name, birth_date, phone, postal_code, state, city, avatar_data, income, fixed_expenses, goal, completed_at, goal_target_cents, goal_monthly_cents ON accounts
BEGIN
  INSERT INTO audit_events(account_id, event, entity_id, ip_hash, created_at)
  SELECT NEW.id, 'accounts.update', NEW.id, ip_hash, at FROM audit_context WHERE id = 1;
END;

-- Account status changes keep a readable event for RF002 and RF005: accounts.status.demo_confirmed, .inactive.
CREATE TRIGGER accounts_audit_status AFTER UPDATE OF status ON accounts
WHEN NEW.status <> OLD.status
BEGIN
  INSERT INTO audit_events(account_id, event, entity_id, ip_hash, created_at)
  SELECT NEW.id, 'accounts.status.' || NEW.status, NEW.id, ip_hash, at FROM audit_context WHERE id = 1;
END;
