# Phase 00 — Repository audit and source inventory

**Objective:** Perform exactly one bounded phase of the MinhaAI build.

## Work
1. Inspect repository root, apps, docs, git state (read-only), package managers, existing APIs/tests/env examples.
2. List every actual attached/checked-in product document, its version, and authority. Check for `PRD.md` v3.0.0 and `ai-provider-strategy.md`. They were not in the user upload; if absent, mark `BLOCKED: SOURCE_INCOMPLETE`.
3. Compare product decisions 1–7 vs analyst defaults vs external gates. Do NOT rewrite source documents.
4. Produce `docs/specs/source-inventory.md`, `docs/specs/missing-inputs.md`, `docs/specs/source-authority.md`, and a current-repo map.
5. If PRD or provider-strategy is missing, allow only safe repository organization and a provisional scaffold plan, not invented full feature requirements.

**Gate:** The inventory explicitly identifies available/missing inputs and next decisions, without creating business requirements out of thin air.
## Required execution contract
- Read `AGENTS.md`, `tasks/implementation-plan.md`, `docs/source/MinhaAI_PRD_Decision_Resolution_AR.md`, and the authoritative source files where available.
- Execute only THIS phase. Identify source/requirement traces and unresolved external gates. Do not invent absent documents.
- Produce exact named artifacts, run relevant checks, update roadmap statuses, and write `tasks/phase-reports/00.md`. Report skipped checks truthfully.
- Do not push, deploy, create paid resources, or change other phases.

