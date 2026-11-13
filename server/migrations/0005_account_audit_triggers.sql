-- Account lifecycle audit events written by the database, like 0003 does for ledger changes.
-- login_succeeded and login_failed stay in the app: neither maps to a row change.

CREATE TRIGGER accounts_audit_registered AFTER INSERT ON accounts
BEGIN
  INSERT INTO audit_events(account_id, event, ip_hash, created_at)
  SELECT NEW.id, 'registration_created', ip_hash, at FROM audit_context WHERE id = 1;
END;

CREATE TRIGGER accounts_audit_confirmed AFTER UPDATE OF status ON accounts
WHEN NEW.status = 'demo_confirmed' AND OLD.status <> 'demo_confirmed'
BEGIN
  INSERT INTO audit_events(account_id, event, ip_hash, created_at)
  SELECT NEW.id, 'demo_confirmation_completed', ip_hash, at FROM audit_context WHERE id = 1;
END;

-- Fires whenever the financial profile is written (no WHEN clause: saving unchanged values is still a save).
-- A goal change made from the goal screen also writes these columns, so it logs this event as well.
CREATE TRIGGER accounts_audit_finance AFTER UPDATE OF income, fixed_expenses, goal ON accounts
BEGIN
  INSERT INTO audit_events(account_id, event, ip_hash, created_at)
  SELECT NEW.id, 'financial_profile_updated', ip_hash, at FROM audit_context WHERE id = 1;
END;
