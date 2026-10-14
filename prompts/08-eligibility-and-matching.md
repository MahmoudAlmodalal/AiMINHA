# Phase 08 — Deterministic eligibility and evidence-backed matching

**Objective:** Perform exactly one bounded phase of the MinhaAI build.

## Work
1. Implement typed student eligibility profile fields (nationality/residency, degree level, major, qualification, GPA+scale, language, preferred countries); `Unknown` is not false.
2. Rule engine emits three states: eligible / ineligible / insufficient information; mandatory disqualification cannot be overridden by AI.
3. Add initial weighted fit score only for verified evidence and coverage >=70%: academic 30%, field 25%, nationality/residency 20%, language 15%, interest 10%; else explain insufficient coverage. Do not call it acceptance probability.
4. Keep normalized scale conversions explicit/tested rather than guessing unknown GPA scales. Return per-rule evidence/explanations.
5. Build API and student UI with sensitivity to uncertainty, unit tests for all rule branches and permission checks.

**Gate:** Rule-first decisions correct; no fabricated acceptance probabilities; p95 measurement plan for target <=2s warm.
## Required execution contract
- Read `AGENTS.md`, `tasks/implementation-plan.md`, `docs/source/MinhaAI_PRD_Decision_Resolution_AR.md`, and the authoritative source files where available.
- Execute only THIS phase. Identify source/requirement traces and unresolved external gates. Do not invent absent documents.
- Produce exact named artifacts, run relevant checks, update roadmap statuses, and write `tasks/phase-reports/08.md`. Report skipped checks truthfully.
- Do not push, deploy, create paid resources, or change other phases.

