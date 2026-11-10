# PRD: ValorAI backend rework on Django

Planning document of 10 November 2026. It records a proposed backend rework. It does not amend the meeting record of 22 October 2026, and it does not change `docs/Ata_de_Reuniao_ValorAl_v1.3.docx`.

Prototype confirmation numbers below stay prototype settings. They are not approved RF002 limits.

### 1. Executive Summary

- **Problem Statement**: The registration API is one Cloudflare Worker. `AuthCoordinator.handle()` in `server/src/index.ts` is the router and the implementation of registration, login, session, confirmation, financial profile, and deactivation, and one Durable Object serializes every account.
- **Proposed Solution**: Keep Cloudflare Workers. Replace that Worker implementation with Django on Python Workers, and deepen Account, Confirmation, Session, and Financial profile so each module owns one concept from the registration slice.
- **Success Criteria**:
  - The existing browser suite passes against the Django Worker on the same `/api` paths and JSON fields the Astro client already uses.
  - Account, Confirmation, Session, and Financial profile each have in-process tests that fail when their own rule breaks, with no browser required for those tests.
  - A password check stores a bcrypt hash at cost 10, and one such hash completes inside the Python Workers CPU limit measured and written down during the build.
  - Confirmation counters are readable only from the Confirmation module. A recovery path, still unbuilt, has no import of those counters.
  - After the architecture is running, `docs/adr/0001-django-workers-architecture.md` exists and describes the architecture that was built.

Assumptions pending confirmation: no deadline and no budget were set. The rework stays on the current Cloudflare account and does not assume a paid plan. The academic default for a new database would be PostgreSQL; this plan keeps D1 because Workers stay and `django-cf` provides a D1 backend. Deadline, budget, and the database choice are open for correction.

### 2. User Experience & Functionality

- **User Personas**: The only persona is the Client. The prototype has no backoffice, support, or admin account. A second reader of this plan is a later reviewer of the codebase, who needs the ADR after the build.
- **User Stories**:
  - As a Client, I want to register, confirm through the demo inbox, set my financial profile, sign in, stay signed in, sign out, and deactivate, so that the current registration slice still works after the host change.
  - As a Client, I want deactivation to keep my financial profile and block login, so that logical deletion still matches the approved registration behavior.
  - As a Client, I want a confirmation code that only my pending session can read, so that the demo inbox stays tied to that account.
  - As a later reviewer, I want an ADR written after the new architecture exists, so that the modules, seams, and database choice are on record.
- **Acceptance Criteria**:
  - Registration still requires name, valid CPF, age of at least 16, mobile phone, CEP, UF, city, email, matching passwords, and demo consent. CPF and email stay unique.
  - Login accepts CPF or email. An unknown identifier and a wrong password both fail. An `inactive` account cannot sign in. Deactivation requires the current password, sets status to `inactive`, and revokes every session for that account.
  - Session cookie remains `valorai_session`, `HttpOnly`, `SameSite=Strict`, and `Secure` on HTTPS. The database stores the token hash. Idle timeout stays 30 minutes. Absolute cap stays 12 hours.
  - Confirmation stays simulated. Status `demo_confirmed` still reports `emailVerified: false`. The demo inbox returns the code only to the pending session that owns it. Prototype settings stay: 6 digits, 10 minutes, 5 attempts, 60 seconds between sends, 3 sends per hour. The ADR states that these numbers await RF002 approval.
  - Financial profile still stores income, fixed expenses, and one goal of `budget`, `debt`, `reserve`, or `invest`. Stored amounts stay integer cents. The JSON the client already reads stays decimal reais. The difference between income and fixed expenses is still not a bank balance.
  - Three lessons remain seeded reads: `first-budget`, `emergency-fund`, `due-dates`. No admin UI appears.
  - Turnstile is required in production on registration and login, and skipped only when the Worker environment is local development. The Turnstile secret stays in Worker secrets.
  - POST requests from another origin are rejected. Authenticated responses send `Cache-Control: no-store`.
  - The ADR file is added only after this behavior is running. It names each module, each seam, the database backend that ran, the transaction behavior that was observed, the password hasher that wrote hashes, the WSGI or ASGI entrypoint, and the CLI that deployed the Worker.
- **Non-Goals**:
  - Rewriting the Astro client.
  - Sending real email, or treating `demo_confirmed` as proof of an email address.
  - Building RF003 profile editing and RF008 password recovery in this phase. Recovery, when it is built later, gets its own module and its own limits.
  - Transactions, categories, limit alerts, CSV/Excel/OFX import, and receipt extraction.
  - Backoffice accounts, investor profiling, reactivation, retention periods, and definitive erasure.
  - Claiming LGPD compliance from logical deletion.
  - Replacing bcrypt with another password algorithm.
  - Promoting this PRD into the meeting record.

### 3. AI System Requirements (If Applicable)

Receipt extraction is part of the product purpose and is outside this rework. This phase calls no model.

- **Tool Requirements**: None in this phase. Workers AI, R2, and Queues stay unused. A later receipt module chooses its own tool. Receipt upload size is still undecided, so no byte limit is set here.
- **Evaluation Strategy**: No model output is produced in this phase, so there is no accuracy target. The later phase defines a labeled receipt set and a field-level accuracy number before extraction is accepted. That number is TBD.

### 4. Technical Specifications

- **Architecture Overview**: The Astro client stays. Static assets stay on Workers Static Assets. `/api/*` is served by Django through the Python Workers WSGI adapter, because the `django-cf` D1 backend is synchronous.

  Four modules own the registration slice:

  - Account owns identity, password verification, status (`pending`, `demo_confirmed`, `inactive`), and deactivation.
  - Session owns the cookie, the token hash, idle timeout, absolute cap, and revocation.
  - Confirmation owns the demo code, its counters, and the demo inbox read.
  - Financial profile owns income, fixed expenses, goal, and the cents conversion.

  The Worker entrypoint is an adapter in front of those modules. Tests use a second, in-process adapter. Those two adapters make the seam real. Lessons stay a seeded read and are not a deepened module.

  The browser keeps its current Zod checks. The Django modules decide. Both must agree on the acceptance criteria above.

  The global Durable Object `accounts-v1` stays until a measurement shows bcrypt cost 10 completes inside the Python Workers CPU budget. Until that measurement is written down, Account does not take over hashing from the coordinator.

- **Integration Points**:
  - D1 database already provisioned for this prototype, via `django-cf` engine `django_cf.db.backends.d1` and the existing `DB` binding. `django-cf` documents that `transaction.atomic` is a no-op on D1 and on Durable Object storage, and that rollback does not run. Deactivation writes status, session revocation, and code removal in a documented order and records that partial failure cannot roll back.
  - Turnstile siteverify, with the secret read from the Worker environment.
  - ViaCEP and IBGE stay in the browser. The server still checks CEP length, UF, and city presence.
  - The repository CLI is `cf`, with `server/cloudflare.config.ts`. The Django Workers guide demonstrates `pywrangler`. The build uses one of them. The ADR records which one deployed the Worker.
  - Python Workers require the `python_workers` compatibility flag. Dependencies are managed in the Python Worker project that replaces `server/src/index.ts`.

- **Security & Privacy**:
  - Passwords stay bcrypt at cost 10. The native `bcrypt` package must load under Pyodide. If it does not load, the rework stops on hashing and does not store a different algorithm.
  - Session tokens are stored as hashes. Confirmation codes stay out of D1 and out of logs.
  - Logs omit payloads, passwords, codes, and SQL errors, matching the current Worker.
  - Demo data is synthetic. This plan does not define retention or erasure.

### 5. Risks & Roadmap

- **Phased Rollout**:
  - MVP: Django on Python Workers serves the current registration slice. Account, Session, Confirmation, and Financial profile exist as modules. The browser suite passes. In-process tests cover the acceptance criteria. The bcrypt measurement is written down. The ADR is written from that running architecture.
  - v1.1: RF003 profile maintenance, and RF008 recovery in its own module with limits that are not the confirmation limits.
  - v2.0: The client ledger. Manual entry, CSV/Excel/OFX import, and receipt extraction are three adapters of one ledger module. Categories are required. Alerts fire when a limit is reached and do not block a save. This phase starts only after the store used by the ledger can commit and roll back a multi-row write. `django-cf` on D1 does not provide that.

  ADR gate, required: the MVP is unfinished until `docs/adr/0001-django-workers-architecture.md` is in the repository. The ADR is written after the architecture runs, from the modules, seams, adapters, hasher, database, and CLI that actually shipped. It tells a later review to leave these choices in place: bcrypt at cost 10, separate confirmation and recovery limits, `demo_confirmed` distinct from email verification, the Client as the only role, and the four modules above instead of a single `handle()`.

- **Technical Risks**:
  - `django-cf` transaction support is a no-op. A deactivation that fails midway can leave status, sessions, and the demo code out of agreement. The MVP records that residual risk in the ADR. The ledger waits for a store with real commits.
  - Pyodide may reject the native bcrypt package. Hashing then has no approved algorithm inside the Worker.
  - The README recorded, on 29 October 2026, a Workers Free CPU budget of 10 ms per invocation and a single coordinator chosen because bcrypt cost 10 needs that coordinator. Python Workers need their own measurement. The free plan can still stop the Worker if the hash exceeds the budget.
  - Removing `accounts-v1` before that measurement drops the only serialization point for authentication writes.
  - The browser Zod schemas and the Django validators can drift. The browser suite is the check that the client still matches the server.
  - `cf` and `pywrangler` are both plausible build tools. Using both in one project splits the deploy path.
