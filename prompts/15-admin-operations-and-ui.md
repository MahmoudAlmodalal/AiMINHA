# Phase 15 — Admin workflows, configuration and operations

**Objective:** Perform exactly one bounded phase of the MinhaAI build.

## Work
1. Finish admin screens for scholarship moderation, provider approval registry, AI budgets, pricing/credits policy versioning, support SLA rules, user/account audit, availability flags, source rights and operational health.
2. Admin can adjust defaults with effective dates and audit, but not retroactively alter credit policy without explicit approved migration/compensation.
3. Make support permissions independent of superuser-style private-file browsing; admin private file library remains forbidden.
4. Add system-safe disable switches (AI private, upload when scanner down, payment disabled, ingestion per source, extension per host) and observable status/error UX.
5. Add React responsive, accessible, RTL/LTR treatment and server-side permission tests for every admin endpoint.

**Gate:** A console setting cannot bypass hard security constraints; feature flags fail closed.
## Required execution contract
- Read `AGENTS.md`, `tasks/implementation-plan.md`, `docs/source/MinhaAI_PRD_Decision_Resolution_AR.md`, and the authoritative source files where available.
- Execute only THIS phase. Identify source/requirement traces and unresolved external gates. Do not invent absent documents.
- Produce exact named artifacts, run relevant checks, update roadmap statuses, and write `tasks/phase-reports/15.md`. Report skipped checks truthfully.
- Do not push, deploy, create paid resources, or change other phases.

