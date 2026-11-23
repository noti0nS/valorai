-- Splits the two analytical views into small single-purpose views composed by JOIN.
-- The public columns of v_account_financial_summary and v_monthly_category_spending are unchanged.
-- Views are dropped first because SQLite validates dependent views on ALTER TABLE ... RENAME.

DROP VIEW IF EXISTS v_account_financial_summary;
DROP VIEW IF EXISTS v_monthly_category_spending;

-- Safe projection of accounts: no cpf, no password_hash.
CREATE VIEW v_account_public AS
SELECT id AS account_id, name, email, status,
       income AS declared_income_cents,
       fixed_expenses AS declared_fixed_expenses_cents,
       goal AS goal_name,
       goal_target_cents, goal_current_cents, goal_monthly_cents
FROM accounts;

CREATE VIEW v_account_goal_progress AS
SELECT id AS account_id,
       CASE WHEN goal_target_cents > 0
            THEN ROUND(MIN(100.0, goal_current_cents * 100.0 / goal_target_cents), 2)
            ELSE 0.0 END AS goal_progress_percent
FROM accounts;

CREATE VIEW v_account_transaction_totals AS
SELECT account_id,
       COUNT(*) AS transaction_count,
       SUM(CASE WHEN kind = 'income' THEN amount_cents ELSE 0 END) AS total_income_cents,
       SUM(CASE WHEN kind <> 'income' THEN amount_cents ELSE 0 END) AS total_expense_cents,
       SUM(CASE WHEN kind <> 'income' AND status = 'pending' THEN amount_cents ELSE 0 END) AS pending_expense_cents
FROM transactions
GROUP BY account_id;

CREATE VIEW v_account_financial_summary AS
SELECT p.*, g.goal_progress_percent,
       COALESCE(t.transaction_count, 0)     AS transaction_count,
       COALESCE(t.total_income_cents, 0)    AS total_income_cents,
       COALESCE(t.total_expense_cents, 0)   AS total_expense_cents,
       COALESCE(t.pending_expense_cents, 0) AS pending_expense_cents
FROM v_account_public p
JOIN v_account_goal_progress g ON g.account_id = p.account_id
LEFT JOIN v_account_transaction_totals t ON t.account_id = p.account_id;

CREATE VIEW v_expense_transactions AS
SELECT * FROM transactions
WHERE kind IN ('fixed_expense', 'variable_expense');

CREATE VIEW v_expense_by_month AS
SELECT account_id, SUBSTR(occurred_on, 1, 7) AS year_month, category, amount_cents, status
FROM v_expense_transactions;

CREATE VIEW v_monthly_category_expense AS
SELECT account_id, year_month, category,
       COUNT(*) AS expense_count,
       SUM(amount_cents) AS spent_cents
FROM v_expense_by_month
GROUP BY account_id, year_month, category;

CREATE VIEW v_category_limits AS
SELECT account_id, category, limit_cents, warn_percent
FROM budget_limits
WHERE scope = 'category';

CREATE VIEW v_monthly_category_spending AS
SELECT s.account_id, s.year_month, s.category, s.expense_count, s.spent_cents,
       l.limit_cents, l.warn_percent,
       CASE WHEN l.limit_cents > 0
            THEN ROUND(s.spent_cents * 100.0 / l.limit_cents, 2) END AS limit_usage_percent
FROM v_monthly_category_expense s
LEFT JOIN v_category_limits l
  ON l.account_id = s.account_id AND l.category = s.category;

CREATE VIEW v_monthly_cashflow AS
SELECT account_id, SUBSTR(occurred_on, 1, 7) AS year_month,
       SUM(CASE WHEN kind = 'income' THEN amount_cents ELSE 0 END)  AS income_cents,
       SUM(CASE WHEN kind <> 'income' THEN amount_cents ELSE 0 END) AS expense_cents,
       SUM(CASE WHEN kind = 'income' THEN amount_cents ELSE -amount_cents END) AS balance_cents
FROM transactions
GROUP BY account_id, SUBSTR(occurred_on, 1, 7);

CREATE VIEW v_pending_expenses AS
SELECT id, account_id, title, amount_cents, category, occurred_on, payment_method
FROM v_expense_transactions
WHERE status = 'pending';

CREATE VIEW v_receipt_review_queue AS
SELECT id, account_id, title, amount_cents, category, channel, confidence, occurred_on
FROM transactions
WHERE validated = 0;

CREATE VIEW v_lesson_progress_detail AS
SELECT lp.account_id, l.id AS lesson_id, l.title, l.minutes, lp.progress_percent, lp.updated_at
FROM lesson_progress lp
JOIN lessons l ON l.id = lp.lesson_id;
