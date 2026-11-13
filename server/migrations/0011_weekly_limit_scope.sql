-- Adds 'weekly' to budget_limits.scope CHECK constraint (RF014).
-- SQLite validates referencing views during ALTER TABLE RENAME, so v_monthly_category_spending
-- is dropped before recreating budget_limits and restored immediately after along with triggers.

DROP VIEW IF EXISTS v_monthly_category_spending;

CREATE TABLE budget_limits_new (
  id TEXT PRIMARY KEY,
  account_id TEXT NOT NULL REFERENCES accounts(id),
  scope TEXT NOT NULL CHECK(scope IN ('category', 'daily', 'weekly', 'card_share')),
  category TEXT NOT NULL,
  limit_cents INTEGER NOT NULL CHECK(limit_cents > 0),
  warn_percent INTEGER NOT NULL DEFAULT 80 CHECK(warn_percent BETWEEN 10 AND 100),
  created_at INTEGER NOT NULL,
  UNIQUE(account_id, scope, category)
);

INSERT INTO budget_limits_new (id, account_id, scope, category, limit_cents, warn_percent, created_at)
SELECT id, account_id, scope, category, limit_cents, warn_percent, created_at FROM budget_limits;

DROP TABLE budget_limits;
ALTER TABLE budget_limits_new RENAME TO budget_limits;
CREATE INDEX budget_limits_account ON budget_limits(account_id);

CREATE VIEW IF NOT EXISTS v_monthly_category_spending AS
SELECT
  t.account_id,
  SUBSTR(t.occurred_on, 1, 7) AS year_month,
  t.category,
  COUNT(t.id) AS expense_count,
  SUM(t.amount_cents) AS spent_cents,
  bl.limit_cents,
  bl.warn_percent,
  CASE
    WHEN bl.limit_cents IS NOT NULL AND bl.limit_cents > 0
      THEN ROUND((SUM(t.amount_cents) * 100.0) / bl.limit_cents, 2)
    ELSE NULL
  END AS limit_usage_percent
FROM transactions t
LEFT JOIN budget_limits bl
  ON bl.account_id = t.account_id
  AND bl.scope = 'category'
  AND bl.category = t.category
WHERE t.kind IN ('fixed_expense', 'variable_expense')
GROUP BY
  t.account_id,
  SUBSTR(t.occurred_on, 1, 7),
  t.category,
  bl.limit_cents,
  bl.warn_percent;

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
