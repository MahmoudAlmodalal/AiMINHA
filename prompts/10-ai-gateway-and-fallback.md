# Phase 10 — AI gateway, classification, provider adapters and budget stop

**Objective:** Perform exactly one bounded phase of the MinhaAI build.

## Work
1. Implement adapter boundary with provider config, cost counters, per-operation timeouts, circuit breaker, limited retries, mock provider for local synthetic tests.
2. Require input classification `PUBLIC/SYNTHETIC`, `STUDENT_PRIVATE`, `PROHIBITED`; log provider approval by specific model/data class plus explicit consent version before processing private student content.
3. Only allow Cloudflare Workers AI or Groq for specific private input AFTER individually approved; never silently route student-private payload to Gemini Free or OpenRouter Free. Public/synthetic route also subject to terms review.
4. Estimate and enforce default 100 AI ops/day plus an 8,000 Neurons experimental Cloudflare ceiling ONLY when trustworthy usage measurement exists; no paid auto-upgrade; hard stop/feature disable on exhausted or unknown capacity.
5. Add prompt-injection isolation, no tool actions from web text, output schema validation, citations/factual validation where required, and not-a-chargeable-success behavior on unsupported claims.
6. Test provider outage, missing approvals, consent withdrawal, budget exhaustion, retries and routing logs (no sensitive raw prompts).

**Gate:** Private-data fail-closed proven; $0-surprise policy enforced in app; unapproved fallback cannot execute.
## Required execution contract
- Read `AGENTS.md`, `tasks/implementation-plan.md`, `docs/source/MinhaAI_PRD_Decision_Resolution_AR.md`, and the authoritative source files where available.
- Execute only THIS phase. Identify source/requirement traces and unresolved external gates. Do not invent absent documents.
- Produce exact named artifacts, run relevant checks, update roadmap statuses, and write `tasks/phase-reports/10.md`. Report skipped checks truthfully.
- Do not push, deploy, create paid resources, or change other phases.

