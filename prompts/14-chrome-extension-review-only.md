# Phase 14 — Chrome extension with review-before-fill

**Objective:** Perform exactly one bounded phase of the MinhaAI build.

## Work
1. Build MV3 extension with minimal scoped host permissions, safe authentication handoff, explicit student initiation and limited field mapping. No secrets/AI keys in extension.
2. Only support specific sites after source/site authorization and fixture validation. Best effort for other allowed sites; no form submission or unsupported claims.
3. Detect sensitive inputs (password/OTP/security questions/payment) and never read, persist, transmit or fill those fields. Explicit user review for every proposed field; no click on Submit.
4. Provide clear preview/change/cancel UI, per-field provenance, error reporting without sending third-party page data to unapproved providers.
5. Test with synthetic HTML fixtures and documented 3 authorized pilot sites when approvals exist; target >=90% supported fields, zero OTP/password capture and zero submit actions.

**Gate:** Extension cannot auto-submit even on malformed or malicious pages; site permissions externally recorded.
## Required execution contract
- Read `AGENTS.md`, `tasks/implementation-plan.md`, `docs/source/MinhaAI_PRD_Decision_Resolution_AR.md`, and the authoritative source files where available.
- Execute only THIS phase. Identify source/requirement traces and unresolved external gates. Do not invent absent documents.
- Produce exact named artifacts, run relevant checks, update roadmap statuses, and write `tasks/phase-reports/14.md`. Report skipped checks truthfully.
- Do not push, deploy, create paid resources, or change other phases.

