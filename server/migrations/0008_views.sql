-- Analytical and security-scoped views for ValorAI (Cloudflare D1 / SQLite).

-- 1. Account financial summary without exposing sensitive credentials (password_hash, cpf).
CREATE VIEW IF NOT EXISTS v_account_financial_summary AS
SELECT
  a.id AS account_id,
  a.name,
  a.email,
  a.status,
  a.income AS declared_income_cents,
  a.fixed_expenses AS declared_fixed_expenses_cents,
  a.goal AS goal_name,
  a.goal_target_cents,
  a.goal_current_cents,
  a.goal_monthly_cents,
  CASE
    WHEN a.goal_target_cents > 0
      THEN ROUND(MIN(100.0, (a.goal_current_cents * 100.0) / a.goal_target_cents), 2)
    ELSE 0.0
  END AS goal_progress_percent,
  COUNT(t.id) AS transaction_count,
  COALESCE(SUM(CASE WHEN t.kind = 'income' THEN t.amount_cents ELSE 0 END), 0) AS total_income_cents,
  COALESCE(SUM(CASE WHEN t.kind IN ('fixed_expense', 'variable_expense') THEN t.amount_cents ELSE 0 END), 0) AS total_expense_cents,
  COALESCE(SUM(CASE WHEN t.kind IN ('fixed_expense', 'variable_expense') AND t.status = 'pending' THEN t.amount_cents ELSE 0 END), 0) AS pending_expense_cents
FROM accounts a
LEFT JOIN transactions t ON t.account_id = a.id
GROUP BY
  a.id,
  a.name,
  a.email,
  a.status,
  a.income,
  a.fixed_expenses,
  a.goal,
  a.goal_target_cents,
  a.goal_current_cents,
  a.goal_monthly_cents;

-- 2. Monthly spending by category paired with configured category budget limits.
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
