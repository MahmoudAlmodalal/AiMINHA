# Phase 11 — Private files, CV and document workflows

**Objective:** Perform exactly one bounded phase of the MinhaAI build.

## Work
1. Implement storage boundary with student ownership, expiring backend-authorized access, server-side limits (PDF/DOCX/PNG/JPG, 5 MB each, 10 MB/student, 750 MB global experimental), MIME/content checks and mandatory actual malware scanning before accepting a file.
2. If scanner is unavailable, fail safely and offer manual data entry. No admin library browsing; only explicitly shared, assigned ticket attachments can be read by support.
3. Implement CV information extraction and generation/editing of CV, motivation letter, personal statement, essay only for verified/admissible flows. Use explicit consent + approved AI route or disable safely.
4. Track document versions, sanitized previews, output verification, private export, immutable snapshots when submitted to an application. Re-export of same saved version does not charge again.
5. Integrate credit reservation/settlement idempotently; failed export preserves original generated artifact without duplicate charge.
6. Test ownership, MIME spoofing, scanner failure, export recovery, oversized files and fake provider claims.

**Gate:** No file accepted without scanner success; no leakage; valid document saved before credit charge.
## Required execution contract
- Read `AGENTS.md`, `tasks/implementation-plan.md`, `docs/source/MinhaAI_PRD_Decision_Resolution_AR.md`, and the authoritative source files where available.
- Execute only THIS phase. Identify source/requirement traces and unresolved external gates. Do not invent absent documents.
- Produce exact named artifacts, run relevant checks, update roadmap statuses, and write `tasks/phase-reports/11.md`. Report skipped checks truthfully.
- Do not push, deploy, create paid resources, or change other phases.

