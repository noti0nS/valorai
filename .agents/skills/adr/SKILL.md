---
name: adr
description: 'Use this skill when the user asks to write, create, draft or update an Architecture Decision Record (ADR), or to document an architectural decision in docs/adr. Also use it when the user wants a decision from recent commits, migrations or code changes recorded as an ADR. It inspects the existing ADRs, picks the next number, gathers evidence from the code and git history, and writes a file that matches the repository style. Do not use it for requirements (docs/valorai_requisitos.docx), READMEs or commit messages.'
license: MIT
allowed-tools: shell(git:*), shell(ls:*)
---

# Architecture Decision Records (ADR)

Write ADRs for this repository in the same shape as `docs/adr/0001-django-workers-architecture.md` and `docs/adr/0002-dashboard-ledger-and-stitch-workspace.md`. An ADR records a decision that already shaped the code, with the evidence a later reader needs to trust it or reverse it.

## Workflow

1. **Read the existing ADRs.** `ls docs/adr`, then read the latest one in full. Take the next number, zero-padded to four digits. Never renumber or reuse a number.
2. **Gather evidence before writing.** Use `git log --stat` and `git show` on the commits involved, read the migrations in `server/migrations/`, the modules they touch, and the tests that pin the behavior. Quote real names: tables, triggers, functions, files, event names, commit hashes. If a fact cannot be verified in the repository, leave it out or label it as an assumption.
3. **Check the sources of truth.** `AGENTS.md`, `README.md` and `ARCHITECTURE.md` may be stale. If the decision contradicts them, say so in a "Consequences" or "Follow-ups" section and do not silently edit them unless asked.
4. **Write the file** to `docs/adr/NNNN-kebab-case-title.md`, in English (code, comments and docs are English; only UI copy is pt-BR).
5. **Report** the path and anything the ADR found stale or unresolved. Do not commit unless asked.

## Template

```markdown
# ADR NNNN: <Title in the form of the decision>

Date: <D Month YYYY>. <One or two sentences: what this record covers and which ADR or migration it builds on. Say what it does not amend.>

## Context

<The problem and the constraint that forced a decision. Cite the limit, requirement or failure, for example "django-cf 0.2.17 sets supports_transactions = False". Reference earlier ADRs with relative links.>

## Decision

<What was chosen, split into numbered or titled parts. Name the exact artifacts: migrations, triggers, tables, modules, endpoints. State what stays in the application and what moved, and why.>

## Alternatives considered

<Only the real ones that were weighed, each with the reason it lost. Omit the section if none are known.>

## Consequences

- **Gained:** <guarantees that now hold, and the test that pins each>
- **Costs and risks:** <new coupling, hidden state, limits, behavior that surprises>
- **Follow-ups:** <stale docs, open questions, work deliberately not done>

## What a later review should leave in place

<The invariants that must survive a refactor, and the observable conditions under which the decision should be revisited.>
```

## Rules

- **One decision per ADR.** Related migrations that implement the same decision belong in one record.
- **Facts, not advocacy.** Describe what the code does today. Do not describe intended behavior as shipped.
- **Name the trade-offs.** An ADR with no cost listed is incomplete.
- **Dates** use the long form already used in the repository ("12 November 2026"). Use the current date.
- **Status.** ADRs here have no status field. If a decision is replaced, add a line at the top of the old ADR pointing to the new one and say what changed. Do not delete old ADRs.
- **Requirements vocabulary.** Use the revision 1.3 identifiers (RF001–RF009) and treat protection, audit and performance as transversal RNF. Do not cite the deleted Ata files as sources for new decisions.
- **No invented measurements.** Report only numbers you measured or that a test asserts.
