-- Goal balance and deactivation enforced in the database.
-- D1 via django-cf has no transactions, so multi-statement flows can half-complete.
-- Triggers run atomically with the statement that fires them.

-- Goal contributions. A dedicated flag replaces matching on merchant_doc, which users can type.
-- Rows created before this migration (merchant_doc 'APORTE.META') stay plain expenses on purpose:
-- backfilling would write audit rows without a request context.
ALTER TABLE transactions ADD COLUMN goal_contribution INTEGER NOT NULL DEFAULT 0 CHECK(goal_contribution IN (0, 1));

CREATE TRIGGER transactions_goal_insert AFTER INSERT ON transactions
WHEN NEW.goal_contribution = 1
BEGIN
  UPDATE accounts SET goal_current_cents = goal_current_cents + NEW.amount_cents WHERE id = NEW.account_id;
END;

CREATE TRIGGER transactions_goal_amount AFTER UPDATE OF amount_cents ON transactions
WHEN NEW.goal_contribution = 1 AND OLD.amount_cents <> NEW.amount_cents
BEGIN
  UPDATE accounts
  SET goal_current_cents = MAX(0, goal_current_cents + NEW.amount_cents - OLD.amount_cents)
  WHERE id = NEW.account_id;
END;

CREATE TRIGGER transactions_goal_delete AFTER DELETE ON transactions
WHEN OLD.goal_contribution = 1
BEGIN
  UPDATE accounts SET goal_current_cents = MAX(0, goal_current_cents - OLD.amount_cents) WHERE id = OLD.account_id;
END;

-- The flag is what the balance depends on, so it cannot be flipped after insert.
CREATE TRIGGER transactions_goal_flag_immutable BEFORE UPDATE OF goal_contribution ON transactions
WHEN OLD.goal_contribution <> NEW.goal_contribution
BEGIN SELECT RAISE(ABORT, 'goal_contribution is immutable'); END;

-- Deactivation (RF005): revoke sessions with the status change and refuse new ones afterwards.
CREATE TRIGGER accounts_revoke_sessions AFTER UPDATE OF status ON accounts
WHEN NEW.status = 'inactive' AND OLD.status <> 'inactive'
BEGIN
  DELETE FROM sessions WHERE account_id = NEW.id;
END;

CREATE TRIGGER sessions_block_inactive BEFORE INSERT ON sessions
WHEN (SELECT status FROM accounts WHERE id = NEW.account_id) = 'inactive'
BEGIN SELECT RAISE(ABORT, 'account is inactive'); END;
