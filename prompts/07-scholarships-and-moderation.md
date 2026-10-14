# Phase 07 — Scholarship catalog, permitted sources, moderation and search

**Objective:** Perform exactly one bounded phase of the MinhaAI build.

## Work
1. Implement source registry with explicit `permission_status`, licensing/use basis, source URL, editor and date checked. Default deny unverified automation.
2. Add manual entry first; optional ingestion only when a source is individually approved. Imported data remains DRAFT until human approval; updates create versions/audit.
3. Public search/filter with PostgreSQL full text indexes, pagination, robust date parsing, deadline timezone and stale/unknown indications; no unsupported facts.
4. Add admin moderation queue and review workflow (approve/reject/reverify), public list/detail and search test fixtures from synthetic or explicitly permitted sources.
5. Test no automatic publishing, unknown deadlines do not invent reminders, no public leak of internal notes.

**Gate:** 100% published scholarships trace to an approved version; blocked sources never scraped.
## Required execution contract
- Read `AGENTS.md`, `tasks/implementation-plan.md`, `docs/source/MinhaAI_PRD_Decision_Resolution_AR.md`, and the authoritative source files where available.
- Execute only THIS phase. Identify source/requirement traces and unresolved external gates. Do not invent absent documents.
- Produce exact named artifacts, run relevant checks, update roadmap statuses, and write `tasks/phase-reports/07.md`. Report skipped checks truthfully.
- Do not push, deploy, create paid resources, or change other phases.

