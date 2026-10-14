# Phase 03 — Data model, ERD and state machines

**Objective:** Perform exactly one bounded phase of the MinhaAI build.

## Work
1. Generate conceptual domain model, relational ERD (DBML or Mermaid), uniqueness/index/foreign key rules, tenant ownership rules and soft delete / retention policies.
2. Cover users, profiles, verification, consents, scholarship sources/versioning/moderation, eligibility, saved opportunities, credit ledger and operations, AI calls, documents and file assets, applications/history, deadline notifications, tickets/SLA/attachments, audit and platform settings.
3. Model `RESERVED/RUNNING/RECONCILING/SETTLED/RELEASED` for AI operation billing and required atomic constraints, once-only signup grant and daily/global limits.
4. Model immutable snapshots (`profile_version`, `scholarship_version`, `consent_version`, `price_snapshot`, `operation_id`) for tasks. Explain concurrent writes and immutable application history.
5. Produce `docs/architecture/erd.dbml`, `docs/architecture/state-machines.md`, `docs/architecture/schema-notes.md` and migration sequencing. This phase DESIGNS; no speculative code.

**Gate:** No cross-user access path by design; credit double-charge/grant and state transitions mechanically prevented.
## Required execution contract
- Read `AGENTS.md`, `tasks/implementation-plan.md`, `docs/source/MinhaAI_PRD_Decision_Resolution_AR.md`, and the authoritative source files where available.
- Execute only THIS phase. Identify source/requirement traces and unresolved external gates. Do not invent absent documents.
- Produce exact named artifacts, run relevant checks, update roadmap statuses, and write `tasks/phase-reports/03.md`. Report skipped checks truthfully.
- Do not push, deploy, create paid resources, or change other phases.

