# ADR 0002: Operational Dashboard, Financial Ledger Module, and Stitch Workspace

Date: 10 November 2026. This record documents the architectural additions for the operational financial dashboard, multi-channel transaction ledger, configurable spending limits with non-blocking alerts, educational progress tracking, and RF003 profile maintenance. It follows the consolidated requirements in `docs/valorai_requisitos.docx` and `docs/Ata_de_Reuniao_ValorAl_v1.3.docx` without attributing new technical choices to the original meeting of 22 October 2026.

## Context

Following [ADR 0001](./0001-django-workers-architecture.md), the ValorAI prototype supported account registration (`RF001`), simulated email confirmation (`RF002`), initial financial profile estimation (`RF004`), logical account deactivation (`RF005`), and login/session management (`RF006`/`RF007`).

To make the post-login Dashboard operational according to the Stitch design specifications (`.stitch/DESIGN.md`, `.stitch/designs/dashboard-web.html`, `.stitch/designs/visao-geral-mobile.html`, `.stitch/designs/dashboard.html`, and `.stitch/designs/dashboard-gestao-financeira.html`) and the elicited product scope in `docs/valorai_requisitos.docx`, the architecture needed to expand across three areas:

1. **Domain & Persistence**: Support the three mandatory transaction input channels (`manual`, `import_file` for CSV/OFX, and `receipt_ai` for receipt photo OCR extraction), mandatory transaction categorization with keyword auto-classification, configurable spending limits (`daily`, `weekly`, `monthly`) with non-blocking alerts, financial goal progress/contributions, seeded lesson completion tracking, and `RF003` (`Manter Perfil Cadastral`).
2. **D1 Adapter Compatibility**: Handle nullable columns (`merchant_doc`, `confidence`, `external_ref`, `notes`, `avatar_data_url`, `target_date`) through `django-cf`'s D1 database backend (`django_cf.db.backends.d1`).
3. **Frontend Workspace Architecture**: Implement the Stitch "Warm Financial Sanctuary" asymmetric Bento grid and sub-pages (`Visão Geral`, `Transações & Extratos`, `Planejamento & Metas`, `Guias Práticos`, plus the `RF003` profile modal) inside the Astro + React island architecture.

## Decision

### 1. Fifth Domain Module: `LedgerModule` (`valorai/ledger/module.py`)

Alongside `AccountModule`, `SessionModule`, `ConfirmationModule`, and `FinanceModule`, a dedicated `LedgerModule` (`server/python/valorai/ledger/module.py`) owns post-onboarding financial operations:

- **Three Input Channels**:
  - `manual`: Direct user entry (`POST /api/transactions`, `PUT /api/transactions`, `DELETE /api/transactions`).
  - `import_file`: Statement parser (`POST /api/transactions/import`) supporting both **OFX** (`<STMTTRN>` SGML/XML blocks via `parse_ofx_content`) and **CSV** (semicolon/comma delimited with Brazilian decimal formatting via `parse_csv_content`).
  - `receipt_ai`: Receipt OCR/AI metadata extractor (`POST /api/transactions/receipt` via `extract_receipt_metadata`) that parses structured receipt payloads or derives deterministic merchant/amount/CNPJ/confidence metadata from uploaded receipt images (PNG/JPEG/WebP up to 5 MB), returning an extracted preview or persisting the confirmed transaction.
- **Mandatory Categorization & Auto-Classification**:
  - Every transaction requires a category (`Alimentação`, `Moradia`, `Transporte`, `Saúde`, `Lazer`, `Educação`, `Serviços`, `Investimentos`, `Renda`, or `Outros`).
  - `auto_classify_category` provides deterministic keyword-based classification for imported statements and OCR receipts while allowing the client to override or confirm the category.
- **Configurable Spending Limits & Non-Blocking Alerts**:
  - Users can configure active spending limits per category and period (`daily`, `weekly`, `monthly`) via `POST /api/limits` and `DELETE /api/limits`.
  - `LedgerModule.compute_limit_statuses` evaluates expenses within the active period window (`today` for daily, Monday-to-today for weekly, and `YYYY-MM-01` to `YYYY-MM-31` for monthly) and emits `ok` (<80%), `warning` (≥80%), `reached` (100%), or `exceeded` (>100%) statuses.
  - Per the requirements, reaching or exceeding a limit triggers visual alerts (`newlyTriggeredAlerts` and dashboard banners) with `nonBlocking: True` and **never blocks** saving a transaction.
- **Goal Contributions & Educational Progress**:
  - `POST /api/goal` updates the user's primary financial goal (`objective`, `name`, `targetAmount`, `currentAmount`, `targetDate`) or records incremental contributions (`addContribution`).
  - `POST /api/lessons/progress` persists per-account reading progress (`progress_pct`, `completed`) for the seeded educational guides without introducing any administrative backoffice (`Client` remains the sole system role).

### 2. `RF003` Profile Maintenance in `AccountModule`

`AccountModule.update_profile` (`PUT /api/profile`) and `validate_profile_update` (`server/python/valorai/account/validation.py`) implement `RF003` (`Manter Perfil Cadastral`):
- Editable fields: `fullName`, `birthDate` (preserving the 16-year minimum age rule), `phone`, `cep`, `state`, `city`, `neighborhood`, `street`, `number`, `complement`, and optional `avatarDataUrl` (PNG/JPEG up to 2 MB).
- Immutable identity fields: `email` and `cpf` cannot be altered through profile maintenance.
- Every profile update records an `account.profile_updated` audit event.

### 3. D1 Schema Migration (`0002_dashboard_ledger.sql`) and `DjangoDb` Placeholder Translation

- **Migration `0002_dashboard_ledger.sql`** adds `financial_transactions`, `spending_limits`, and `lesson_progress` tables with indexes on `(account_id, occurred_on DESC)` and `(account_id, category, occurred_on)`.
- **Non-Transactional Write Ordering**: Because `django-cf` 0.2.17 sets `supports_transactions = False`, `LedgerModule` orders writes so primary records (`financial_transactions`, `spending_limits`, `financial_goals`, `lesson_progress`) are written before `audit_events`. Account deactivation (`RF005`) continues to preserve all financial ledger records while revoking sessions and blocking login.
- **`DjangoDb` Null-Parameter Adaptation**: `django_cf.db.backends.d1.base.DatabaseWrapper.process_query` strips `None` values from `params` while replacing `%s` placeholders with `null` one by one. Because the repository's SQL queries use SQLite `?` placeholders, passing `None` parameters with `?` caused parameter count mismatches in D1. `DjangoDb.query` and `DjangoDb.execute` in `server/python/valorai/storage.py` now translate `?` to `%s` before invoking `cursor.execute`, allowing `SqliteDb` (used in fast unit tests) and `DjangoDb` (used in the Python Worker with D1) to share identical SQL statements.

### 4. Stitch Workspace Frontend (`src/components/DashboardWorkspace.tsx`)

The authenticated view in `src/components/RegistrationApp.tsx` delegates to `src/components/DashboardWorkspace.tsx`, styled via `src/styles/global.css` following the Stitch design system:
- **Navigation**: Sticky glassmorphic top navbar (`Visão Geral`, `Transações & Extratos`, `Planejamento`, `Guias`, user profile pill, and `Sair`), responsive mobile navigation drawer, and sub-page tab bar.
- **3-Column Asymmetric Bento Grid (`Visão Geral`)**:
  - Hero Dark Emerald Balance Card (`#14281D`) displaying projected free balance (`Saldo livre projetado`), monthly income, monthly expenses, and income commitment percentage.
  - Primary Financial Goal Card with native `<progress>` bar and `+ Registrar aporte` modal trigger.
  - Spending Limit & Non-Blocking Alert Card (`Limites e Alertas`).
  - Category Allocation horizontal bars (`Distribuição de Gastos`) alongside AI Receipt OCR and OFX/CSV quick-upload cards.
  - Recent Transactions Ledger (`Últimos Lançamentos`) with channel badges (`Manual`, `Extrato OFX/CSV`, `IA • Cupom`) and seeded Educational Guides (`Educação Financeira`).
- **Declarative Native Dialogs**: All interactive modals (Manual Transaction, Receipt AI OCR with editable review step, OFX/CSV Import, Goal Contribution, Guide Reader, and `RF003` Profile Maintenance) use native HTML `<dialog closedby="any">` elements for accessible keyboard/backdrop light-dismiss.

## Verification

- **Python Unit Tests**: `uv run pytest` in `server/python` passed 22 tests across `test_account.py`, `test_confirmation.py`, `test_finance.py`, `test_http.py`, `test_ledger.py`, `test_session.py`, and `test_sql.py`.
- **Frontend Unit & Type Tests**: `npm test` passed 7 validation suites (`tests/validation.test.ts`), and `npm run check` (`astro check`) reported 0 errors, 0 warnings, and 0 hints.
- **End-to-End Browser Suite**: `npm run test:e2e` passed all 3 Playwright suites (`tests/browser/dashboard.spec.ts` and both tests in `tests/browser/registration.spec.ts`) against the local Python Worker (`127.0.0.1:8787`).
