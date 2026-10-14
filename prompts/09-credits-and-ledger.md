# Phase 09 — Credit accounting, entitlements and concurrency

**Objective:** Perform exactly one bounded phase of the MinhaAI build.

## Work
1. Implement once-only signup grant default 30 on verified adult activation; daily spend cap default 6 in Asia/Hebron (not daily refill), global 100 AI operations/day; admin-configurable versioned policy.
2. Default beta internal prices: matching AI=1, CV extraction=4, new document=6. Browsing, rules-based eligibility, manual edits, same-version re-export, extension free.
3. Build atomic ledger/operation service with stable idempotency key, unique grant constraints, reserve→run→settle validated saved output, fail release once; uncertain result moves to RECONCILING, not blind release.
4. Standard 15-minute reserve/reconciliation marker and 24-hour experimental resolution target. Support safe retries without duplicate charges and outbox/reliable work if used.
5. Write negative and concurrent DB tests for 2 students, double requests, worker timeout, race conditions, policy version changes and double-settlement.

**Gate:** No double grant/debit, no negative balance, no charge for unverified/unsaved AI output.
## Required execution contract
- Read `AGENTS.md`, `tasks/implementation-plan.md`, `docs/source/MinhaAI_PRD_Decision_Resolution_AR.md`, and the authoritative source files where available.
- Execute only THIS phase. Identify source/requirement traces and unresolved external gates. Do not invent absent documents.
- Produce exact named artifacts, run relevant checks, update roadmap statuses, and write `tasks/phase-reports/09.md`. Report skipped checks truthfully.
- Do not push, deploy, create paid resources, or change other phases.

