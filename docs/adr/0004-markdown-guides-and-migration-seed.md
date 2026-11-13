# ADR 0004: Client-Side Markdown Rendering and Migration-Seeded Financial Guides

Date: 12 November 2026. This record covers migration `0006_rich_markdown_lessons.sql` and the frontend Markdown renderer in `src/components/MarkdownContent.tsx`. It builds on the migration-seeded content model in [ADR 0002](./0002-dashboard-ledger-and-stitch-workspace.md) and does not amend the SQLite/D1 schema or the audit trail in [ADR 0003](./0003-database-owned-audit-trail.md).

## Context

`0001_initial.sql` seeded `lessons` with three short plain-text rows (`first-budget`, `emergency-fund`, `due-dates`), and `RegistrationApp.tsx` rendered `lesson.body` inside a single `<p>{lesson.body}</p>` element. That format could not present structured tables, checklists, or callouts needed for practical personal-finance guides, while the MVP scope keeps `Client` as the only role with no administrative UI to author or edit educational content.

Because `lesson_progress.lesson_id` (`0002_dashboard_ledger.sql`) references `lessons(id)` and `LedgerModule.seed_demo_cycle` (`valorai/ledger/module.py`) writes progress for `emergency-fund` and `first-budget`, expanding the library could not drop or rename existing IDs.

## Decision

### 1. Migration `0006_rich_markdown_lessons.sql` upserts nine Markdown guides

`server/migrations/0006_rich_markdown_lessons.sql` uses `INSERT INTO lessons (id, title, description, body, minutes) VALUES (...) ON CONFLICT(id) DO UPDATE SET ...` to rewrite the three existing guides in Markdown and add six new guides (`annual-expenses`, `credit-card-control`, `debt-exit`, `first-investments`, `invisible-spending`, `irregular-income`), bringing the seeded catalog to nine guides. No schema change was made to `lessons` or `lesson_progress`, and `SqlLessons.list` (`valorai/storage.py`) continues to return rows ordered by `id`.

### 2. Zero-dependency JSX Markdown renderer in the frontend

`src/components/MarkdownContent.tsx` parses `lesson.body` directly into React elements without `dangerouslySetInnerHTML` and without adding a third-party Markdown package:

- **Supported blocks:** headings (`#`–`####`, shifted down one level to `<h3>`–`<h5>` inside the modal whose title is `<h2>`), unordered and ordered lists, blockquotes (`>`), pipe tables wrapped in `.md-table-wrap`, horizontal rules (`---` / `***`), and paragraphs.
- **Supported inline tokens:** inline code (`` `...` ``), bold (`**...**`), italic (`*...*`), and links (`[label](url)` restricted to `http://` or `https://`; other schemes render as plain text).
- **Modal presentation:** `LightDismissModal` (`src/components/DashboardWorkspace.tsx`) and `Modal` (`src/components/RegistrationApp.tsx`) accept `wide?: boolean`, which applies `.modal.modal-wide` (`min(740px, calc(100% - 32px))`) and `.lesson-markdown` styles in `src/styles/global.css`.

## Alternatives considered

- **Adding `react-markdown` or `marked` + HTML sanitizer:** rejected to avoid new npm dependencies and HTML-string sanitization surface when a small, deterministic JSX parser covers the exact Markdown subset used by the seeded migrations.
- **Storing pre-rendered HTML in `lessons.body`:** rejected because `lessons` is read by `GET /api/lessons` and `GET /api/dashboard` as structured data; keeping Markdown in `body` avoids coupling database rows to DOM markup and classes.

## Consequences

- **Gained:** richer educational guides with tables, checklists, and educational disclaimers without XSS risk from raw HTML injection and without breaking existing `lesson_progress` foreign keys. `server/python/tests/test_sql.py` pins the sorted list of all nine lesson IDs and verifies that every `lessons.body` row contains Markdown headings (`## `).
- **Costs and risks:**
  - `MarkdownContent.tsx` implements a constrained Markdown subset (for example, it does not support fenced code blocks, nested lists, or raw HTML). Future guides in migrations must stay within that subset.
  - Because `DashboardWorkspace.tsx` slices `allLessons.slice(0, 3)` in the `Visão Geral` side card and `SqlLessons.list()` orders alphabetically by `id`, the overview card now shows `annual-expenses`, `credit-card-control`, and `debt-exit` instead of the original three guides.
  - Existing local and remote D1 databases show the old plain-text three-guide catalog until `0006_rich_markdown_lessons.sql` is applied.
- **Follow-ups:**
  - `README.md` still states "Três guias educativos pré-carregados por migração" and lists only `0001_initial.sql` and `0002_dashboard_ledger.sql` under `server/migrations/`; both notes are stale.
  - `ARCHITECTURE.md` still refers to the table as `educational_lessons` instead of `lessons`.
  - No dedicated frontend unit test yet exercises `MarkdownContent.tsx` edge cases directly; `npm run check` and `npm run build` verify compilation only.

## What a later review should leave in place

Keep guide content seeded via idempotent `ON CONFLICT(id) DO UPDATE` migrations while `Client` remains the only role, preserve the existing IDs referenced by `lesson_progress` and `seed_demo_cycle`, and keep Markdown rendering free of unsanitized HTML injection. Revisit the custom parser in `src/components/MarkdownContent.tsx` if guides later require fenced code blocks, nested lists, or user-authored Markdown.
