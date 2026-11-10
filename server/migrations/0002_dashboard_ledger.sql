ALTER TABLE accounts ADD COLUMN goal_target_cents INTEGER NOT NULL DEFAULT 500000;
ALTER TABLE accounts ADD COLUMN goal_current_cents INTEGER NOT NULL DEFAULT 0;
ALTER TABLE accounts ADD COLUMN goal_monthly_cents INTEGER NOT NULL DEFAULT 75000;
ALTER TABLE accounts ADD COLUMN avatar_data TEXT;

CREATE TABLE profile_changes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id TEXT NOT NULL REFERENCES accounts(id),
  changed_fields TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
CREATE INDEX profile_changes_account ON profile_changes(account_id, created_at);

CREATE TABLE transactions (
  id TEXT PRIMARY KEY,
  account_id TEXT NOT NULL REFERENCES accounts(id),
  title TEXT NOT NULL,
  amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
  kind TEXT NOT NULL CHECK(kind IN ('income', 'fixed_expense', 'variable_expense')),
  category TEXT NOT NULL,
  channel TEXT NOT NULL CHECK(channel IN ('manual', 'import', 'photo')),
  occurred_on TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'paid' CHECK(status IN ('paid', 'pending')),
  payment_method TEXT NOT NULL DEFAULT 'debit' CHECK(payment_method IN ('pix', 'credit', 'debit', 'cash', 'boleto', 'transfer')),
  merchant_doc TEXT,
  confidence INTEGER,
  validated INTEGER NOT NULL DEFAULT 1 CHECK(validated IN (0, 1)),
  external_ref TEXT,
  notes TEXT,
  created_at INTEGER NOT NULL
);
CREATE INDEX transactions_account_date ON transactions(account_id, occurred_on DESC, created_at DESC);
CREATE INDEX transactions_account_ref ON transactions(account_id, external_ref);

CREATE TABLE budget_limits (
  id TEXT PRIMARY KEY,
  account_id TEXT NOT NULL REFERENCES accounts(id),
  scope TEXT NOT NULL CHECK(scope IN ('category', 'daily', 'card_share')),
  category TEXT NOT NULL,
  limit_cents INTEGER NOT NULL CHECK(limit_cents > 0),
  warn_percent INTEGER NOT NULL DEFAULT 80 CHECK(warn_percent BETWEEN 10 AND 100),
  created_at INTEGER NOT NULL,
  UNIQUE(account_id, scope, category)
);
CREATE INDEX budget_limits_account ON budget_limits(account_id);

CREATE TABLE lesson_progress (
  account_id TEXT NOT NULL REFERENCES accounts(id),
  lesson_id TEXT NOT NULL REFERENCES lessons(id),
  progress_percent INTEGER NOT NULL DEFAULT 0 CHECK(progress_percent BETWEEN 0 AND 100),
  updated_at INTEGER NOT NULL,
  PRIMARY KEY (account_id, lesson_id)
);
