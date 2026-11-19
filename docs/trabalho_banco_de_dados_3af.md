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

> Nota: a definição vigente de `v_monthly_category_spending` foi recriada em `0011_weekly_limit_scope.sql` (por causa do `RENAME` de `budget_limits`); a lógica é a mesma da `0008`.

---

### 3.4. Mapeamento: onde construir views mais simples

As duas views acima concentram vários conceitos ao mesmo tempo (projeção segura, agregação por tipo, status, progresso de meta, junção com limites, percentual de uso). Isso as torna difíceis de ler, testar e reaproveitar. A proposta abaixo quebra cada uma em **views pequenas, de uma responsabilidade**, e as compõe por `JOIN`.

#### 3.4.1. Diagnóstico das views atuais

| View atual | Responsabilidades misturadas | Complexidade |
| --- | --- | --- |
| `v_account_financial_summary` | (1) projeção segura de `accounts` (sem `cpf`/`password_hash`); (2) progresso da meta (`CASE` + `ROUND` + `MIN`); (3) 4 agregados condicionais sobre `transactions` (`SUM(CASE...)`); (4) `GROUP BY` com 10 colunas só para acomodar o `LEFT JOIN` | `LEFT JOIN` + `GROUP BY` extenso + 4 `CASE` |
| `v_monthly_category_spending` | (1) classificação de "despesa" (`kind IN (...)`); (2) agrupamento por mês via `SUBSTR`; (3) agregação por categoria; (4) junção com limite; (5) percentual de uso | `LEFT JOIN` + `GROUP BY` com colunas do limite + `CASE` |

Causas recorrentes: a regra "o que é despesa" (`kind IN ('fixed_expense','variable_expense')`) aparece 4 vezes; a extração do mês (`SUBSTR(occurred_on,1,7)`) está embutida; e o `GROUP BY` carrega colunas apenas para satisfazer o `LEFT JOIN`.

#### 3.4.2. Mapa de views simples propostas

| # | View proposta | Fonte | Responsabilidade única | Substitui/alimenta | Complexidade |
| --- | --- | --- | --- | --- | --- |
| 1 | `v_account_public` | `accounts` | Projeção segura: só colunas não sensíveis | Parte (1) do resumo financeiro; reaproveitável em perfil/sessão | Nenhum `JOIN`/agregação |
| 2 | `v_account_goal_progress` | `accounts` | Progresso da meta em % | Parte (2) do resumo financeiro | Um `CASE` |
| 3 | `v_expense_transactions` | `transactions` | Define "despesa" (fixa ou variável) em um único lugar | Base de #4, #6 e #7 | Só `WHERE` |
| 4 | `v_account_transaction_totals` | `transactions` | Totais por conta: receitas, despesas, pendentes, quantidade | Parte (3) do resumo financeiro | `GROUP BY` de 1 coluna |
| 5 | `v_transactions_by_month` | `transactions` | Adiciona a coluna `year_month` | Base de #6 e #8 | Sem agregação |
| 6 | `v_monthly_category_expense` | #3 + #5 | Gasto por conta/mês/categoria, **sem** limites | Parte (2)(3) do gasto mensal | `GROUP BY` de 3 colunas |
| 7 | `v_pending_expenses` | #3 | Despesas ainda não pagas (`status = 'pending'`) | Alertas e contas a pagar | Só `WHERE` |
| 8 | `v_monthly_cashflow` | #5 | Receita x despesa por mês e saldo | Novo: gráfico/extrato mensal | `GROUP BY` de 2 colunas |
| 9 | `v_category_limits` | `budget_limits` | Limites do escopo `category` apenas | Parte (4) do gasto mensal | Só `WHERE` |
| 10 | `v_receipt_review_queue` | `transactions` | Transações de foto/importação ainda não validadas (`validated = 0`) | Novo: fila de validação de recibos | Só `WHERE` |
| 11 | `v_lesson_progress_detail` | `lessons` + `lesson_progress` | Guia + percentual por conta | Novo: tela de Guias Práticos | `JOIN` simples |

#### 3.4.3. Decomposição de `v_account_financial_summary`

Em vez de uma view com `LEFT JOIN` + `GROUP BY` de 10 colunas, o resumo passa a ser uma composição de três views simples. Quem só precisa do perfil ou só dos totais consulta a view menor.

```sql
-- 1. Projeção segura (sem JOIN, sem agregação).
CREATE VIEW IF NOT EXISTS v_account_public AS
SELECT id AS account_id, name, email, status,
       income AS declared_income_cents,
       fixed_expenses AS declared_fixed_expenses_cents,
       goal AS goal_name,
       goal_target_cents, goal_current_cents, goal_monthly_cents
FROM accounts;

-- 2. Progresso da meta (apenas um CASE).
CREATE VIEW IF NOT EXISTS v_account_goal_progress AS
SELECT id AS account_id,
       CASE WHEN goal_target_cents > 0
            THEN ROUND(MIN(100.0, goal_current_cents * 100.0 / goal_target_cents), 2)
            ELSE 0.0 END AS goal_progress_percent
FROM accounts;

-- 3. Totais de transações por conta (GROUP BY de uma única coluna).
CREATE VIEW IF NOT EXISTS v_account_transaction_totals AS
SELECT account_id,
       COUNT(*) AS transaction_count,
       SUM(CASE WHEN kind = 'income' THEN amount_cents ELSE 0 END) AS total_income_cents,
       SUM(CASE WHEN kind <> 'income' THEN amount_cents ELSE 0 END) AS total_expense_cents,
       SUM(CASE WHEN kind <> 'income' AND status = 'pending' THEN amount_cents ELSE 0 END) AS pending_expense_cents
FROM transactions
GROUP BY account_id;

-- Composição: reproduz v_account_financial_summary sem repetir regra nenhuma.
CREATE VIEW IF NOT EXISTS v_account_financial_summary AS
SELECT p.*, g.goal_progress_percent,
       COALESCE(t.transaction_count, 0)      AS transaction_count,
       COALESCE(t.total_income_cents, 0)     AS total_income_cents,
       COALESCE(t.total_expense_cents, 0)    AS total_expense_cents,
       COALESCE(t.pending_expense_cents, 0)  AS pending_expense_cents
FROM v_account_public p
JOIN v_account_goal_progress g ON g.account_id = p.account_id
LEFT JOIN v_account_transaction_totals t ON t.account_id = p.account_id;
```

Ganhos: o `GROUP BY` de 10 colunas some; `v_account_public` pode ser usada sozinha onde hoje se lê `accounts` e há risco de vazar `cpf`/`password_hash`; o `CASE` do progresso da meta é testável isoladamente.

#### 3.4.4. Decomposição de `v_monthly_category_spending`

```sql
-- 1. Definição única de "despesa".
CREATE VIEW IF NOT EXISTS v_expense_transactions AS
SELECT * FROM transactions
WHERE kind IN ('fixed_expense', 'variable_expense');

-- 2. Mês como coluna (sem agregação).
CREATE VIEW IF NOT EXISTS v_expense_by_month AS
SELECT account_id, SUBSTR(occurred_on, 1, 7) AS year_month,
       category, amount_cents, status
FROM v_expense_transactions;

-- 3. Gasto por conta/mês/categoria, sem limites.
CREATE VIEW IF NOT EXISTS v_monthly_category_expense AS
SELECT account_id, year_month, category,
       COUNT(*) AS expense_count,
       SUM(amount_cents) AS spent_cents
FROM v_expense_by_month
GROUP BY account_id, year_month, category;

-- 4. Apenas limites por categoria.
CREATE VIEW IF NOT EXISTS v_category_limits AS
SELECT account_id, category, limit_cents, warn_percent
FROM budget_limits
WHERE scope = 'category';

-- Composição: GROUP BY já resolvido; o JOIN deixa de precisar de colunas do limite no GROUP BY.
CREATE VIEW IF NOT EXISTS v_monthly_category_spending AS
SELECT s.account_id, s.year_month, s.category, s.expense_count, s.spent_cents,
       l.limit_cents, l.warn_percent,
       CASE WHEN l.limit_cents > 0
            THEN ROUND(s.spent_cents * 100.0 / l.limit_cents, 2) END AS limit_usage_percent
FROM v_monthly_category_expense s
LEFT JOIN v_category_limits l
  ON l.account_id = s.account_id AND l.category = s.category;
```

Ganhos: a regra de despesa fica em um único ponto (hoje duplicada em 4 lugares); o `scope = 'category'` do limite também; e, como a agregação acontece **antes** do `JOIN`, o `GROUP BY` deixa de incluir `limit_cents`/`warn_percent`. Isso também resolve a fragilidade apontada em `0011_weekly_limit_scope.sql`, em que o `RENAME` de `budget_limits` obrigou a recriar a view: com `v_category_limits` isolando a dependência, só uma view pequena precisa mudar quando a tabela de limites mudar.

#### 3.4.5. Views novas, simples, que atendem telas já existentes

```sql
-- Fluxo de caixa mensal (aba "Transações & Extratos" / Visão Geral).
CREATE VIEW IF NOT EXISTS v_monthly_cashflow AS
SELECT account_id, SUBSTR(occurred_on, 1, 7) AS year_month,
       SUM(CASE WHEN kind = 'income' THEN amount_cents ELSE 0 END)  AS income_cents,
       SUM(CASE WHEN kind <> 'income' THEN amount_cents ELSE 0 END) AS expense_cents,
       SUM(CASE WHEN kind = 'income' THEN amount_cents ELSE -amount_cents END) AS balance_cents
FROM transactions
GROUP BY account_id, SUBSTR(occurred_on, 1, 7);

-- Despesas pendentes (alertas / contas a pagar).
CREATE VIEW IF NOT EXISTS v_pending_expenses AS
SELECT id, account_id, title, amount_cents, category, occurred_on, payment_method
FROM v_expense_transactions
WHERE status = 'pending';

-- Fila de validação de recibos e importações (canais 'photo' e 'import').
CREATE VIEW IF NOT EXISTS v_receipt_review_queue AS
SELECT id, account_id, title, amount_cents, category, channel, confidence, occurred_on
FROM transactions
WHERE validated = 0;

-- Guias com progresso por conta (aba "Guias Práticos").
CREATE VIEW IF NOT EXISTS v_lesson_progress_detail AS
SELECT lp.account_id, l.id AS lesson_id, l.title, l.minutes,
       lp.progress_percent, lp.updated_at
FROM lesson_progress lp
JOIN lessons l ON l.id = lp.lesson_id;
```

#### 3.4.6. Onde cada view simples poderia ser consumida

| Local (código/tela) | Consulta hoje | View que simplifica |
| --- | --- | --- |
| `storage.py` — listagem do dashboard (`list_transactions`, `list_limits`) | `SELECT` direto em `transactions`/`budget_limits` com filtros repetidos | `v_expense_transactions`, `v_category_limits` |
| Dashboard — cartões de receita/despesa/saldo | Agregação feita na aplicação | `v_account_transaction_totals`, `v_monthly_cashflow` |
| Planejamento & Metas — barra de progresso | Cálculo do percentual no código | `v_account_goal_progress` |
| Planejamento & Metas — alertas de limite | Soma por categoria e comparação no código | `v_monthly_category_spending` (recomposta) |
| Transações & Extratos — revisão de recibos | Filtro `validated = 0` no código | `v_receipt_review_queue` |
| Guias Práticos | `lessons` + `lesson_progress` em duas consultas | `v_lesson_progress_detail` |
| Perfil/sessão | `SELECT * FROM accounts` (inclui `password_hash`) | `v_account_public` quando a senha não for necessária |

#### 3.4.7. Cuidados na adoção

* **Ordem de criação:** views que dependem de outras devem ser criadas depois (ex.: `v_expense_transactions` antes de `v_expense_by_month`). Em SQLite, `DROP VIEW` + `CREATE VIEW` na mesma migration é a forma segura de substituir as definições atuais.
* **Dependência de `RENAME`:** o SQLite valida views dependentes em `ALTER TABLE ... RENAME` (já ocorreu na `0011`). Mudanças futuras em `transactions`/`budget_limits` devem remover as views dependentes antes e recriá-las depois.
* **Compatibilidade:** `v_account_financial_summary` e `v_monthly_category_spending` mantêm as mesmas colunas, então o restante do documento (checklist e DDL) não muda de significado.
* **Desempenho:** views no SQLite não são materializadas; empilhar muitas camadas é aceitável no volume do protótipo, e o índice `transactions_account_date` cobre os filtros por `account_id`.
* **Status:** esta seção é uma **proposta de mapeamento**; as views das seções 3.4.3 a 3.4.5 ainda **não** estão em migration (a próxima seria `0012_simple_views.sql`).

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
