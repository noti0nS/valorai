# ADR 0006: Conformance Fixes for Requirements Revision 1.4

Date: 12 November 2026. Covers migration `0010_standard_categories.sql` and the changes below. Receipt OCR/AI (RF012) is explicitly out of scope and unchanged.

## Context

A review of `docs/valorai_requisitos.docx` (rev. 1.4) against the code found partial coverage of RF003, RF013, RF015, RNF05, RNF06 and RNF07.

## Decision

1. **Standard categories (RF013).** The ten categories are exactly `Alimentação, Moradia, Transporte, Lazer, Educação, Saúde, Serviços, Renda, Investimentos, Outros`. The earlier compound names (`Alimentação & Mercado`, `Moradia (Fixo)`, ...) are renamed in code (`ledger/module.py`, `shared/validation.ts`) and in stored rows by migration 0010. Categories sent by the client, by CSV/OFX rows and by category limits must now match a standard name (case-insensitive); an unknown value is rejected on create, update, `validate` and category limits, and replaced by the keyword suggestion on imports. This keeps "100% classified" true and the user free to pick any standard category.
2. **Four alert levels (RF015).** `ok` (below the warn percent, default 80), `warning`, `reached` (spent exactly equals the limit) and `exceeded` (spent above it). The comparison uses cents, not the rounded percent, so 99.6% is never "reached". Alerts stay non-blocking.
3. **Avatar WebP (RF003, RNF05).** Avatars accept JPG, PNG and WebP up to 2 MB, in backend and UI.
4. **HSTS (RNF07).** Responses carry `Strict-Transport-Security`. The TLS 1.3 minimum itself is a Cloudflare zone setting (SSL/TLS > Edge Certificates > Minimum TLS Version) and cannot be set from this repository; it must be configured at deploy time.
5. **Cross-browser projects (RNF06).** Playwright now defines Chromium, Firefox, WebKit, Edge, Pixel 7 and iPhone 14 projects. Install the browsers once with `npx playwright install chromium firefox webkit msedge`.

## Consequences

- Renaming is a data migration: custom, non-standard categories already stored are left as they are, but cannot be chosen again. In `budget_limits`, a rename that would collide with the unique key is skipped.
- Lesson text in migrations 0006/0007 mentions "Alimentação" and "Lazer" generically and is unchanged.
- Not changed, by decision: receipt upload type/size validation (RNF05's 5 MB), the heuristic receipt extraction, and the synchronous import/extraction path (RNF02). The document still describes them as AI/OCR and asynchronous; the text or the code needs a later decision.
