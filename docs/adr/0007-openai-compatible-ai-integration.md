# ADR 0007: OpenAI-Compatible AI Integration for Receipt Extraction and Condensed Financial Summaries

Date: 13 November 2026. Covers the new `valorai/ai/` package, `POST /api/ai/summary`, receipt extraction updates in `/api/transactions/receipt`, client-side image compression in `DashboardWorkspace.tsx`, and Wrangler configuration in `server/python/wrangler.jsonc`. Builds on [ADR 0001](0001-django-workers-architecture.md), [ADR 0002](0002-dashboard-ledger-and-stitch-workspace.md), and [ADR 0006](0006-requirements-1-4-conformance.md); does not alter D1 schema or existing audit triggers.

## Context

ValorAI targets low-cost smartphones on mobile networks and previously handled `/api/transactions/receipt` strictly with deterministic filename/text heuristics (`LedgerModule._extract_receipt_metadata`) while presenting static insight strings in the Overview tab. We needed real multimodal extraction capable of reading any Brazilian payment proof (NFC-e/SAT receipts, PIX transfers sent or received, bank slips/boletos, credit card statements, TED/DOC, and POS slips) plus a short, personalized financial summary on the Overview tab, without running heavy OCR/ML models on the user's device and without locking the codebase to a single AI vendor.

Because the Cloudflare Python Worker executes Django synchronously inside the `AuthCoordinator` Durable Object (`workers.fetch` bridged via `pyodide.ffi.run_sync`, as established in [ADR 0001](0001-django-workers-architecture.md)), domain code cannot `await` and outbound HTTP must go through an injected synchronous transport. Furthermore, Google AI Studio's Free Tier enforces per-project RPM/TPM/RPD quotas and allows prompts/images to be used for model improvement unless billing is enabled.

## Decision

1. **Provider-agnostic OpenAI-Compatible client (`valorai/ai/client.py`).**
   - `OpenAiCompatibleClient` calls `POST {AI_BASE_URL}/chat/completions` with `response_format` (`json_schema` strict mode) and `temperature: 0.1`.
   - Transport is injected via `http_post`: `server/python/valorai/worker.py` injects `worker_http_post` (`run_sync(fetch(...))`), while local tests inject fakes without touching `pyodide` or `workers`.
   - `server/python/wrangler.jsonc` configures `AI_MODE="openai_compatible"`, `AI_BASE_URL="https://generativelanguage.googleapis.com/v1beta/openai"`, `AI_MODEL="gemini-3.5-flash-lite"`, and `AI_TIER="free_prototype"` in both `vars` and `env.production.vars`. `AI_API_KEY` is supplied only via Wrangler secrets or local `.dev.vars`; when absent, `AiConfig.enabled` is `False` and the system falls back deterministically.

2. **Multimodal receipt extraction with mandatory human review (`valorai/ai/receipt.py`, `LedgerModule.handle_receipt`).**
   - `DashboardWorkspace.tsx` (`compressReceiptImage`) resizes selected images on `<canvas>` to a maximum dimension of `1280px` and JPEG quality `0.78` (stepping down to `0.62` if over `480,000` characters) before calling `POST /api/transactions/receipt`.
   - `AiReceiptExtractor.extract` instructs the VLM to handle NFC-e/SAT, PIX (distinguishing `income` vs. expense), boletos, credit card statements, TED/DOC, and POS slips, prioritizing the amount actually paid (or total invoice amount) over subtotals, available limits, or minimum payments.
   - Categories are coerced through `standard_category` (falling back to `suggest_category`) so [ADR 0006](0006-requirements-1-4-conformance.md)'s ten `STANDARD_CATEGORIES` remain enforced.
   - Extracted transactions are never auto-saved; the user must review and confirm (`confirm: true`). On HTTP `429`, `AiReceiptExtractor` trips a 60-second circuit breaker in `DurableKv` (`ai:circuit_open_until`) and falls back to `_extract_receipt_metadata` with `source: "fallback"`.

3. **State-guided condensed financial summary with KV caching (`valorai/ai/advisor.py`, `POST /api/ai/summary`).**
   - `compute_deterministic_context` computes deterministic state flags (`EXPENSE_RATIO_HIGH`, `LIMIT_EXCEEDED`, `NEAR_LIMIT`, `POSITIVE_SURPLUS`, `NO_LIMITS_SET`, `LOW_ACTIVITY`) and builds a PII-free condensed payload (omitting name, email, CPF, IDs, and raw transaction descriptions) plus a SHA-256 `fingerprint`.
   - `GET /api/dashboard` (`LedgerModule.present_dashboard`) never blocks on external AI HTTP: `FinancialAdvisor.get_cached_or_fallback` returns the cached AI summary from `DurableKv` (`ai:summary:{account_id}`, 6-hour TTL) or `build_deterministic_summary` along with `aiSummaryNeedsRefresh`.
   - When `aiSummaryNeedsRefresh` is true and `aiEnabled` is true, `DashboardWorkspace.tsx` triggers `POST /api/ai/summary` asynchronously, or the user can click *Atualizar* (subject to a 30-second cooldown).

4. **Free Tier prototype transparency (`GET /api/config`, UI).**
   - `GET /api/config` exposes `aiEnabled`, `aiTier`, and `aiModel`. When `aiTier === "free_prototype"`, the Overview card and receipt modal display a notice advising users not to upload sensitive real banking documents until switched to a paid tier (`AI_TIER=paid`).

## Alternatives considered

- **On-device OCR / WebGPU models (e.g., Tesseract.js):** Rejected because low-cost smartphones lack RAM/CPU headroom, bundle sizes are large, and traditional OCR struggles with Brazilian PIX screenshots and crumpled receipts.
- **Two-step OCR + regex/LLM pipeline or Google/Azure Document AI:** Rejected for the MVP because Document AI does not natively map to ValorAI's ten `STANDARD_CATEGORIES` and informal PIX screenshots, whereas a single VLM call with `json_schema` handles both image reading and schema mapping.
- **Google-specific `google-genai` SDK:** Rejected to avoid vendor lock-in and extra Worker bundle dependencies; the OpenAI-Compatible endpoint lets us swap providers via environment variables alone.
- **Client-side NFC-e QR Code reader:** Considered for zero-cost fiscal coupon parsing and deliberately excluded per product scope.

## Consequences

- **Gained:**
  - Provider-agnostic AI integration tested with 6 unit/HTTP tests in `server/python/tests/test_ai.py` (`41 passed` total in `pytest`, `0` errors in `astro check`, `7` passed in `npm test`).
  - Zero blocking of dashboard loads or transaction entry when AI quotas (`429`) or network errors occur.
  - Reduced mobile upload payloads via client-side `<canvas>` compression.
- **Costs and risks:**
  - `DurableKv` (`module_kv` table) now stores AI summary caches and circuit-breaker timestamps alongside auth/confirmation state.
  - While `AI_TIER=free_prototype` is active, Google AI Studio terms allow submitted prompts/images to be used for model improvement; moving to production with real user financial data requires switching `AI_API_KEY` to a Pay-as-you-go project and setting `AI_TIER=paid`.
  - Actual extraction accuracy against real Brazilian receipts (`>= 95%` target in `docs/PRD_ia_integracao.md`) is not yet measured in CI because `pytest` runs against mocked HTTP responses.
- **Follow-ups:**
  - `AGENTS.md` and `ARCHITECTURE.md` are stale with respect to `/api/transactions/receipt` (still described as heuristic-only) and do not yet list `POST /api/ai/summary` or `valorai/ai/`; update them when documenting the next milestone.
  - Evaluate the 50-image Golden Set against live `gemini-3.5-flash-lite` once `AI_API_KEY` is configured.
  - Phase 2 (CSV/OFX batch categorization) and Phase 3 (Cloudflare AI Gateway + R2 receipt archive + `AI_TIER=paid`) remain future work.

## What a later review should leave in place

- Keep `OpenAiCompatibleClient` behind an injected `http_post` callable so domain code remains synchronous, `pyodide`-free in unit tests, and decoupled from any single LLM vendor.
- Never allow `GET /api/dashboard` to make synchronous outbound AI HTTP calls; keep AI generation on `POST /api/ai/summary` backed by `DurableKv` fingerprint caching.
- Never auto-commit extracted receipt transactions without explicit user confirmation (`confirm: true`) and `_validate_transaction_payload` category/amount validation.
- Revisit this ADR if `AI_TIER` is switched to `paid`, if `DurableKv` caching moves to Workers KV/R2, or if receipt extraction becomes asynchronous via Cloudflare Queues.
