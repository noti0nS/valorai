# Trabalho para Compor 3AF — Estrutura de Banco de Dados (ValorAI)

**Alunos:** José Lucas da Silva e Pedro Gabriel dos Santos Barros

## 1. Introdução ao Projeto

O **ValorAI** (Nulfinance Inc.) é um protótipo de gestão financeira pessoal voltado à simplicidade e à educação financeira. O cliente se cadastra, define seu perfil financeiro (renda, despesas fixas e meta), registra transações por três canais (manual, importação de extratos CSV/OFX e comprovantes), configura limites de gasto, acompanha a meta e lê guias educativos.

O banco é o **Cloudflare D1** (dialeto **SQLite**). Os trechos abaixo são apenas os SQL de construção da estrutura, extraídos das migrations de `server/migrations/`; cargas de textos educativos foram omitidas.

## 2. Checklist de Avaliação (5 pontos)

| Critério | Pontos | Status | Seção |
| :--- | :---: | :---: | :--- |
| DDL mantendo as 4 integridades | 1,0 | Atendido | 3 |
| Criação de Trigger | 1,0 | Atendido | 4 |
| Criação de campo indexado | 1,0 | Atendido | 5 |
| Contas e Permissões (DCL) | 1,0 | Não aplicável ao SGBD (justificativa) | 6 |
| Criação de View | 1,0 | Atendido | 7 |

---

## 3. Criação das Tabelas (DDL) com as 4 Integridades

```sql
CREATE TABLE accounts (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  cpf TEXT NOT NULL UNIQUE,
  email TEXT NOT NULL UNIQUE,
  birth_date TEXT NOT NULL,
  phone TEXT NOT NULL,
  postal_code TEXT NOT NULL,
  state TEXT NOT NULL,
  city TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','demo_confirmed','inactive')),
  created_at INTEGER NOT NULL,
  income INTEGER,
  fixed_expenses INTEGER,
  goal TEXT,
  completed_at INTEGER
);

CREATE TABLE sessions (
  token_hash TEXT PRIMARY KEY,
  account_id TEXT NOT NULL REFERENCES accounts(id),
  created_at INTEGER NOT NULL,
  last_seen INTEGER NOT NULL,
  expires_at INTEGER NOT NULL
);
CREATE INDEX sessions_account ON sessions(account_id);
CREATE INDEX sessions_expiry ON sessions(expires_at);

CREATE TABLE audit_events (
  id INTEGER PRIMARY KEY,
  account_id TEXT,
  event TEXT NOT NULL,
  ip_hash TEXT NOT NULL,
  created_at INTEGER NOT NULL
);
CREATE INDEX audit_account ON audit_events(account_id, created_at);

CREATE TABLE lessons (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  body TEXT NOT NULL,
  minutes INTEGER NOT NULL
);

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
  scope TEXT NOT NULL CHECK(scope IN ('category', 'daily', 'weekly', 'card_share')),
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

ALTER TABLE transactions ADD COLUMN goal_contribution INTEGER NOT NULL DEFAULT 0 CHECK(goal_contribution IN (0, 1));
```

**Integridades aplicadas**
* **Entidade:** `PRIMARY KEY` em todas as tabelas, inclusive a chave composta `(account_id, lesson_id)` em `lesson_progress`.
* **Referencial:** `REFERENCES accounts(id)` em `sessions`, `profile_changes`, `transactions`, `budget_limits` e `lesson_progress`; `REFERENCES lessons(id)` em `lesson_progress`.
* **Domínio:** tipos explícitos, `NOT NULL`, `DEFAULT` e `CHECK` (`status`, `kind`, `channel`, `payment_method`, `scope`, `amount_cents > 0`, `limit_cents > 0`, `warn_percent BETWEEN 10 AND 100`, `progress_percent BETWEEN 0 AND 100`, `validated` e `goal_contribution IN (0, 1)`).
* **Chave / Semântica:** `UNIQUE` em `accounts(cpf)` e `accounts(email)`, `UNIQUE(account_id, scope, category)` em `budget_limits`, e regras de negócio garantidas por triggers (seção 4).

---

## 4. Criação de Triggers

Triggers de proteção de histórico (*append-only*), de meta financeira e de bloqueio de contas inativas, e de auditoria genérica por tabela.

```sql
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

CREATE TRIGGER transactions_goal_flag_immutable BEFORE UPDATE OF goal_contribution ON transactions
WHEN OLD.goal_contribution <> NEW.goal_contribution
BEGIN SELECT RAISE(ABORT, 'goal_contribution is immutable'); END;

CREATE TRIGGER accounts_revoke_sessions AFTER UPDATE OF status ON accounts
WHEN NEW.status = 'inactive' AND OLD.status <> 'inactive'
BEGIN
  DELETE FROM sessions WHERE account_id = NEW.id;
END;

CREATE TRIGGER sessions_block_inactive BEFORE INSERT ON sessions
WHEN (SELECT status FROM accounts WHERE id = NEW.account_id) = 'inactive'
BEGIN SELECT RAISE(ABORT, 'account is inactive'); END;

-- Auditoria genérica (um formato por tabela e operação; exemplo em transactions e accounts).
ALTER TABLE audit_events ADD COLUMN entity_id TEXT;

CREATE TRIGGER transactions_audit_i AFTER INSERT ON transactions
WHEN NEW.external_ref IS NULL OR NEW.external_ref NOT LIKE 'seed-%'
BEGIN
  INSERT INTO audit_events(account_id, event, entity_id, ip_hash, created_at)
  SELECT NEW.account_id, 'transactions.insert', NEW.id, ip_hash, at FROM audit_context WHERE id = 1;
END;

CREATE TRIGGER transactions_audit_d AFTER DELETE ON transactions
BEGIN
  INSERT INTO audit_events(account_id, event, entity_id, ip_hash, created_at)
  SELECT OLD.account_id, 'transactions.delete', OLD.id, ip_hash, at FROM audit_context WHERE id = 1;
END;

CREATE TRIGGER accounts_audit_status AFTER UPDATE OF status ON accounts
WHEN NEW.status <> OLD.status
BEGIN
  INSERT INTO audit_events(account_id, event, entity_id, ip_hash, created_at)
  SELECT NEW.id, 'accounts.status.' || NEW.status, NEW.id, ip_hash, at FROM audit_context WHERE id = 1;
END;
```

---

## 5. Criação de Campos Indexados

```sql
CREATE INDEX sessions_account ON sessions(account_id);
CREATE INDEX sessions_expiry ON sessions(expires_at);
CREATE INDEX audit_account ON audit_events(account_id, created_at);
CREATE INDEX profile_changes_account ON profile_changes(account_id, created_at);
CREATE INDEX transactions_account_date ON transactions(account_id, occurred_on DESC, created_at DESC);
CREATE INDEX transactions_account_ref ON transactions(account_id, external_ref);
CREATE INDEX budget_limits_account ON budget_limits(account_id);
```

Além desses, as restrições `UNIQUE` criam índices implícitos em `accounts(cpf)`, `accounts(email)` e `budget_limits(account_id, scope, category)`.

---

## 6. Contas e Permissões (DCL) — Motivação para Não Implementação

O **Cloudflare D1** é baseado em **SQLite**, que **não possui gerenciamento de contas de banco nem comandos DCL** (`CREATE USER`, `CREATE ROLE`, `GRANT`, `REVOKE`); executá-los em uma migration resulta em erro de sintaxe. O controle de acesso ocorre em duas camadas externas ao SQL:

1. **Infraestrutura (Cloudflare Workers):** somente o Worker autorizado pelo *binding* configurado em `server/python/wrangler.jsonc` acessa a instância do D1.
2. **Aplicação:** autenticação com hash `bcrypt` em `accounts`, sessões com expiração em `sessions`, isolamento por `account_id` em todas as consultas e a view `v_account_public` (seção 7), que expõe os dados da conta sem `cpf` nem `password_hash`.

---

## 7. Criação de Views

As views são pequenas, de uma responsabilidade cada, e as duas analíticas são compostas a partir delas (`server/migrations/0012_simple_views.sql`).

| View | Responsabilidade |
| :--- | :--- |
| `v_account_public` | Projeção segura de `accounts` (sem `cpf` e `password_hash`) |
| `v_account_goal_progress` | Percentual de progresso da meta |
| `v_account_transaction_totals` | Receitas, despesas, pendentes e quantidade por conta |
| `v_account_financial_summary` | Composição das três acima |
| `v_expense_transactions` | Define "despesa" (fixa ou variável) em um único lugar |
| `v_expense_by_month` | Despesas com a coluna `year_month` |
| `v_monthly_category_expense` | Gasto por conta, mês e categoria |
| `v_category_limits` | Limites do escopo `category` |
| `v_monthly_category_spending` | Gasto mensal por categoria x limite (composição) |
| `v_monthly_cashflow` | Receita, despesa e saldo por mês |
| `v_pending_expenses` | Despesas ainda pendentes |
| `v_receipt_review_queue` | Transações de foto/importação ainda não validadas |
| `v_lesson_progress_detail` | Guias com o progresso de cada conta |

```sql
DROP VIEW IF EXISTS v_account_financial_summary;
DROP VIEW IF EXISTS v_monthly_category_spending;

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
```

---

## 8. Registro de Uso de IA

### Triggers de auditoria
* **Modelo:** Claude Code
* **Prompt:** *"remova a responsabilide de auditoria da api e implemente-as no formato de triggers no próprio banco de dados; logo em seguida, remova as chamadas da api aos triggers"*

### Avaliação da estrutura, views e documentação (3AF)
* **Modelo:** Gemini
* **Prompts:**
  1. *"Esse trabalho, o ValorAI, ele também precisa seguir alguns requisitos do trabalho de banco de dados que foram estabelecidos. Segue abaixo os requisitos e eu quero que você avalie a implementação."*
  2. *"Implemente o ponto da view."*
  3. *"Gere em docs/ um documento markdown referente a essa tarefa, preenchendo a checklist, informando o codigo das migrations e a motivacao de nao ter feito o account management."*

### Simplificação das views e adequação do documento
* **Modelo:** Claude Code
* **Prompts:**
  1. *"O arquivo docs/trabalho_banco_de_dados_3af.md possui a descrição de views muito complexas. Faça um mapeamento de onde podemos construir views mais simples e colocar no documento"*
  2. *"O documento tem que ser escrito pra comportar os seguintes requerimentos, não eh um histórico"* (seguido das regras da 3AF)
