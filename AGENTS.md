# ValorAI

## Repository state and sources
- This repository contains the requirements/branding materials and an Astro + React registration prototype, implemented on 29/10/2026. The prototype API is Django on a Python Worker with D1, a Durable Object coordinator, and Turnstile. See `README.md`, the root `package.json`, and `server/python` for actual setup/build/test/deploy commands; there is no CI workflow.
- Read `docs/Ata_de_Reuniao_ValorAl_v1.3.docx` for the latest consolidated requirements and `entrevista_valorai.pdf` for the elicited product scope.
- `docs/Ata_de_Reuniao_ValorAl.docx` contains version 1.2 despite its unversioned name. The original PDF, `_original.docx`, `_v1.1.docx`, and `docs/revision_ata.md` are historical; the Markdown review is not a current requirements specification.
- Logos are `assets/Nulfinance_Inc.svg` (company) and `assets/ValorAI.svg` (product).

## Prototype development
- Node 24.22+ in the 24.x line is supported by the current Cloudflare CLI; use `npm ci` at the root. The API dependencies are installed with `uv` from `server/python`. Check `engines` for other supported Node lines.
- Use `pywrangler` and `server/python/wrangler.jsonc`. Root `npm run build` builds Astro. Root `npm run dev:api` serves that output with the Python Worker. Root `npm run deploy` builds and deploys with `pywrangler --env production`.
- Local Worker development listens on `127.0.0.1:8787` and serves root `dist/`; rebuild the frontend before browser tests. Astro's dev server proxies `/api` to that Worker.
- Email confirmation is intentionally simulated, as authorized for this prototype. `/api/demo-inbox` is restricted to the account's pending session, and confirmed accounts are `demo_confirmed`, never email-verified.
- Confirmation limits in code are prototype assumptions pending requirements validation. Turnstile is enforced in production and bypassed only in local development mode. Store its secret in Cloudflare, never in source files.
- The implementation is a registration slice, not the whole MVP. RF003/RF008, financial transactions/imports/receipt extraction, and unresolved requirements are not completed by this prototype.

## Requirements traps
- Keep the RF/RNF convention: RF describe bounded user goals; their validation rules stay attached to them; technical protection and quality constraints are transversal RNF.
- Version 1.3 RF001–RF008 mean registration, email confirmation, profile maintenance, financial profile, deactivation, login, sessions, and recovery. RF009 (authenticated password change) is proposed, not approved.
- These are working identifiers, not a finalized global catalog. The old RF001–RF013 matrix and the 88-function-point estimate use historical identifiers; do not equate them with the new RF or treat 88 PF as the revised MVP size. Financial capabilities still need RF allocation and traceability remapping.
- MVP has only the Client role: no backoffice, support/admin accounts, or temporary internal passwords. Educational content is seeded into the database, not managed through an admin UI.
- All three input channels are essential: manual, CSV/Excel/OFX import, and receipt photos with AI extraction. OFX was explicitly confirmed after the interview. Investments are optional/postponable; do not require investor profiling.
- Every transaction needs a category. Limits trigger alerts when reached or exceeded; examples such as R$100/day are configurable examples, not fixed defaults. Alerts do not imply blocking payments or saving transactions.
- JPG/PNG up to 2 MB applies to avatars only; receipt upload limits remain undecided. Native mobile versus mobile-first responsive web, alert channels, and measurable alert latency are also undecided.
- Passwords use bcrypt, not the early review's Argon2id suggestion. Email confirmation and password recovery use separate codes; recovery limits must not silently become confirmation limits.
- Account deactivation is logical deletion: preserve financial records, block login, revoke sessions. Reactivation, retention, and definitive erasure remain unresolved; logical deletion does not establish LGPD compliance.

## Editing and checking documents
- Preserve previous versions and identify later revisions explicitly; never attribute new decisions to the original meeting of 22/10/2026. Keep pending proposals distinguishable from approved scope.
- Editing a DOCX does not update its PDF counterpart. Do not present historical PDFs or the external traceability matrix as synchronized exports.
- Before replacing a DOCX, check for Office/LibreOffice lock files and have the user save/close it, or create a separately named revision. `.gitignore` excludes lock files and temporary documents.
- DOCX is a ZIP/XML package: preserve styles, tables, media, and relationships when editing; do not replace it with a plain-text reconstruction.
- Validate DOCX ZIP/XML integrity and render to PDF for visual inspection, especially table/page breaks. Keep verification exports outside `docs` unless requested as deliverables.
- On this Windows environment, `pandoc "docs/Ata_de_Reuniao_ValorAl_v1.3.docx" -t plain` extracts readable text. LibreOffice's `soffice.com` supports synchronous headless PDF conversion; export to a separate temporary directory to avoid overwriting historical PDFs.
