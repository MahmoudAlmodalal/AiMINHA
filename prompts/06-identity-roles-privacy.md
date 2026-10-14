# Phase 06 — Identity, permissions, consent and account lifecycle

**Objective:** Perform exactly one bounded phase of the MinhaAI build.

## Work
1. Implement server-verified sign-up/sign-in, email verification, explicit DOB 18+ logic (leap dates), optional Google account link with unique user identity, role permission matrix.
2. Public users may browse scholarships; protected personal features require verified adult account. Build a strict ownership/permission layer with denied default.
3. Implement consent versioning and separate personal-AI consent, account delete/restore rules including the exact 30-day UTC boundary, with safe file deletion queue and audit.
4. Never give admin direct listing/read privileges over student private files. Ticket support attachment authorization is by assignment + explicit user share only.
5. Build backend models/endpoints, minimal UI, negative permission tests and privacy-specific audit.

**Gate:** Unauthorized cross-user reads 403; admin private-file 403; age/time-boundary tests; no secrets in responses.
## Required execution contract
- Read `AGENTS.md`, `tasks/implementation-plan.md`, `docs/source/MinhaAI_PRD_Decision_Resolution_AR.md`, and the authoritative source files where available.
- Execute only THIS phase. Identify source/requirement traces and unresolved external gates. Do not invent absent documents.
- Produce exact named artifacts, run relevant checks, update roadmap statuses, and write `tasks/phase-reports/06.md`. Report skipped checks truthfully.
- Do not push, deploy, create paid resources, or change other phases.

