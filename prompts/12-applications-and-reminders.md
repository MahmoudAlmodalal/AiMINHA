# Phase 12 — Application tracker, status history and deadline alerts

**Objective:** Perform exactly one bounded phase of the MinhaAI build.

## Work
1. Implement Preparing→Ready→Submitted→Under Review→Accepted/Rejected plus Withdrawn with explicit transition authorization, immutable history and new application round rather than silent overwrite.
2. Record user-reported and verified-official status separately, including source and observed date; never overwrite student report without audit.
3. Attach snapshot of the document submitted; edits to master document do not mutate already-submitted artifact. Enforce permitted deletion requests separately.
4. Remind in-app 14, 7, 3 days and 24h before CONFIRMED deadlines using sponsor timezone then user display timezone. Deduplicate on event version/user.
5. Add student tracker UI, notifications, date ambiguity tests and permission checks.

**Gate:** Unknown deadline produces no misleading countdown; history and submitted evidence preserved.
## Required execution contract
- Read `AGENTS.md`, `tasks/implementation-plan.md`, `docs/source/MinhaAI_PRD_Decision_Resolution_AR.md`, and the authoritative source files where available.
- Execute only THIS phase. Identify source/requirement traces and unresolved external gates. Do not invent absent documents.
- Produce exact named artifacts, run relevant checks, update roadmap statuses, and write `tasks/phase-reports/12.md`. Report skipped checks truthfully.
- Do not push, deploy, create paid resources, or change other phases.

