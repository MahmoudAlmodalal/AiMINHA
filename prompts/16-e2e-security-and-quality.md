# Phase 16 — Full testing, integration and security review

**Objective:** Perform exactly one bounded phase of the MinhaAI build.

## Work
1. Assemble fixed test fixtures and a bilingual set of 100 representative scenarios. Use synthetic data for private data tests. Log observed output quality without claiming factual accuracy from generation alone.
2. Run API unit/integration, cross-tenant authorization, credit concurrency, provider routing, browser extension anti-submit, file upload scanner-down, privacy consent and account restore boundary, support SLA, timezone/date and migration tests.
3. Run Playwright E2E for guest, student, admin, support and Chrome extension review; keyboard/RTL responsive coverage including 1366x768 and 1440x900.
4. Measure search warm p95 <=3s at 20 concurrent and eligibility p95 <=2s if environment permits; report uncertainty, environment and actual samples.
5. Dependency vulnerability/secret scan, API permission fuzzing, backup restore rehearsal (on safe test resources), provider budget interruption simulations and production configs review.
6. Write `docs/specs/release-verification.md` with evidence links, blocker severity, test pass/fail/not run, and GO/NO-GO recommendation.

**Gate:** Known critical vulnerabilities=0; all security-critical checks pass; no unsupported claim of 24/7 or tested recovery without real drill.
## Required execution contract
- Read `AGENTS.md`, `tasks/implementation-plan.md`, `docs/source/MinhaAI_PRD_Decision_Resolution_AR.md`, and the authoritative source files where available.
- Execute only THIS phase. Identify source/requirement traces and unresolved external gates. Do not invent absent documents.
- Produce exact named artifacts, run relevant checks, update roadmap statuses, and write `tasks/phase-reports/16.md`. Report skipped checks truthfully.
- Do not push, deploy, create paid resources, or change other phases.

