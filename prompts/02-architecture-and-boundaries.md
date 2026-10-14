# Phase 02 — Architecture and API contracts

**Objective:** Perform exactly one bounded phase of the MinhaAI build.

## Work
1. Architect a modular monolith with Next.js frontend, Django DRF backend, PostgreSQL, private storage, a recoverable PostgreSQL job queue and independent worker, optional Chrome MV3 extension.
2. Produce `docs/architecture/system-overview.md` and Mermaid diagrams: C4 context/container/component + sequence for credit-backed AI generation + file upload + admin moderation.
3. Write ADRs for auth/session/cookie & CSRF strategy, typed API contracts/versioning, asynchronous jobs & reconciliation, object storage and ownership, deployment separation, feature flags, observation & audit.
4. Define privacy trust boundaries, domain module public contracts, API pagination/filtering/errors/idempotency, and timezone behavior.
5. Explain Vercel frontend vs Django worker hosting and verify platform terms before any public SaaS deployment. No fragile in-request long worker assumption.

**Gate:** A different engineer can implement domain slices from contracts without inventing authorization, cost or data flow.
## Required execution contract
- Read `AGENTS.md`, `tasks/implementation-plan.md`, `docs/source/MinhaAI_PRD_Decision_Resolution_AR.md`, and the authoritative source files where available.
- Execute only THIS phase. Identify source/requirement traces and unresolved external gates. Do not invent absent documents.
- Produce exact named artifacts, run relevant checks, update roadmap statuses, and write `tasks/phase-reports/02.md`. Report skipped checks truthfully.
- Do not push, deploy, create paid resources, or change other phases.

