# Trabalho para Compor 3AF — Estrutura de Banco de Dados (ValorAI)

**Alunos:** José Lucas da Silva e Pedro Gabriel dos Santos Barros

## 1. Introdução ao Projeto

O **ValorAI** (Nulfinance Inc.) é um protótipo de gestão financeira pessoal desenvolvido com foco em simplicidade e educação financeira. A aplicação permite o cadastro e onboarding do cliente, definição de perfil financeiro (renda, despesas fixas e meta), registro e categorização de transações por três canais (manual, importação de extratos CSV/OFX e leitura de comprovantes), configuração de limites de gastos, acompanhamento de metas e leitura de guias educativos.

A persistência de dados utiliza **Cloudflare D1** (compatível com **SQLite**), estruturada por meio de migrations SQL versionadas em `server/migrations/`.

---

## 2. Checklist de Avaliação (3AF — 5 Pontos)

| Critério | Pontuação | Status | Onde está implementado |
| :--- | :---: | :---: | :--- |
| **DDL mantendo as 4 integridades** (Entidade, Referencial, Domínio e Chave/Semântica) | 1,0 | [x] Atendido | `0001_initial.sql`, `0002_dashboard_ledger.sql`, `0003_audit_triggers.sql`, `0004_goal_and_session_triggers.sql` |
| **Criação de Trigger no banco** | 1,0 | [x] Atendido | `0003_audit_triggers.sql`, `0004_goal_and_session_triggers.sql`, `0005_account_audit_triggers.sql` (21 triggers). A migração `0009_generic_audit.sql` substituiu depois os triggers de auditoria de dados de 0003 e 0005 por triggers genéricos gerados de um único modelo (`server/tools/audit_triggers.py`); o esquema completo passa a ter 19 triggers. As seções abaixo descrevem as migrações 0003 e 0005 como foram aplicadas originalmente |
| **Criação de campo indexado** | 1,0 | [x] Atendido | `0001_initial.sql`, `0002_dashboard_ledger.sql` (7 índices explícitos `CREATE INDEX`) |
| **Criação de Contas e Permissões (DCL)** | 1,0 | [ ] Não aplicável ao SGBD | Limitação nativa do SQLite / Cloudflare D1 (justificativa na Seção 4) |
| **Criação de View** | 1,0 | [x] Atendido | `0008_views.sql` (2 views analíticas e de projeção segura) |

---

## 3. Trechos de Código SQL das Migrations

> Conforme orientado na entrega, os trechos abaixo contêm apenas as estruturas DDL, índices, triggers e views (omitindo blocos extensos de carga inicial de textos educativos em `0001`, `0006` e `0007`).

### 3.1. Criação das Tabelas (DDL com as 4 Integridades) e Índices

#### `server/migrations/0001_initial.sql`

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
```

#### `server/migrations/0002_dashboard_ledger.sql`

```sql
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
```

**Resumo das 4 integridades aplicadas:**
* **Entidade:** `PRIMARY KEY` em todas as tabelas (incluindo chave composta `(account_id, lesson_id)` em `lesson_progress`).
* **Referencial:** `REFERENCES accounts(id)` em `sessions`, `profile_changes`, `transactions`, `budget_limits` e `lesson_progress`; `REFERENCES lessons(id)` em `lesson_progress`.
* **Domínio:** Tipagem explícita, `NOT NULL`, `DEFAULT` e restrições `CHECK` (`status`, `amount_cents > 0`, `kind`, `channel`, `payment_method`, `validated IN (0, 1)`, `scope`, `limit_cents > 0`, `warn_percent BETWEEN 10 AND 100`, `progress_percent BETWEEN 0 AND 100`, `goal_contribution IN (0, 1)`).
* **Chave / Semântica:** `UNIQUE` em `accounts(cpf)`, `accounts(email)` e `UNIQUE(account_id, scope, category)` em `budget_limits`, além de regras de imutabilidade e *append-only* garantidas via triggers.

---

### 3.2. Triggers

#### `server/migrations/0003_audit_triggers.sql`

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

CREATE TRIGGER profile_changes_audit_insert AFTER INSERT ON profile_changes
BEGIN
  INSERT INTO audit_events(account_id, event, ip_hash, created_at)
  SELECT NEW.account_id, 'profile_updated', ip_hash, at FROM audit_context WHERE id = 1;
END;

CREATE TRIGGER accounts_audit_deactivated AFTER UPDATE OF status ON accounts
WHEN NEW.status = 'inactive' AND OLD.status <> 'inactive'
BEGIN
  INSERT INTO audit_events(account_id, event, ip_hash, created_at)
  SELECT NEW.id, 'account_deactivated', ip_hash, at FROM audit_context WHERE id = 1;
END;
```

#### `server/migrations/0004_goal_and_session_triggers.sql`

```sql
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
```

#### `server/migrations/0005_account_audit_triggers.sql`

```sql
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

CREATE TRIGGER accounts_audit_finance AFTER UPDATE OF income, fixed_expenses, goal ON accounts
BEGIN
  INSERT INTO audit_events(account_id, event, ip_hash, created_at)
  SELECT NEW.id, 'financial_profile_updated', ip_hash, at FROM audit_context WHERE id = 1;
END;
```

---

### 3.3. Views

#### `server/migrations/0008_views.sql`

```sql
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
```

---

## 4. Motivação para Não Implementação de Contas e Permissões (DCL)

O projeto **ValorAI** utiliza o **Cloudflare D1**, um banco de dados relacional *serverless* baseado no motor **SQLite**. Diferente de SGBDs cliente-servidor tradicionais (como PostgreSQL, MySQL ou SQL Server), o **SQLite / Cloudflare D1 não possui suporte a gerenciamento de contas de banco ou comandos DCL** (`CREATE USER`, `CREATE ROLE`, `GRANT`, `REVOKE`). Qualquer tentativa de executar esses comandos em uma migration do D1 resulta em erro de sintaxe.

Na arquitetura do ValorAI, o controle de acesso ocorre em duas camadas externas ao dialeto SQL:
1. **Camada de Infraestrutura (Cloudflare Workers):** apenas o Worker autorizado pelo *binding* configurado em `server/python/wrangler.jsonc` possui acesso direto à instância do D1, protegido por tokens e políticas da conta Cloudflare.
2. **Camada de Aplicação:** o acesso dos usuários finais é controlado por autenticação com hash `bcrypt` na tabela `accounts`, sessões com expiração na tabela `sessions` e isolamento por `account_id` em todas as consultas.

---

## 5. Registro de Uso de IA (Transparência da Entrega)

### Geração das Triggers de Auditoria
* **Ferramenta / Modelo utilizado:** Claude Code
* **Prompt utilizado:**
  * *"remova a responsabilide de auditoria da api e implemente-as no formato de triggers no próprio banco de dados; logo em seguida, remova as chamadas da api aos triggers"*

### Avaliação da Estrutura, Criação das Views e Documentação
* **Modelo utilizado:** Gemini
* **Prompts utilizados:**
  1. *"Esse trabalho, o ValorAI, ele também precisa seguir alguns requisitos do trabalho de banco de dados que foram estabelecidos. Segue abaixo os requisitos e eu quero que você avalie a implementação."* (seguido das instruções da 3AF)
  2. *"Implemente o ponto da view."*
  3. *"Gere em docs/ um documento markdown referente a essa tarefa, preenchendo a checklist, informando o codigo das migrations e a motivacao de nao ter feito o account management."*
