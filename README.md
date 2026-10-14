# MinhaAI — AI Agent Build Pack

This pack is a **sequenced development workflow**, not a finished application or a replacement for the product PRD. It includes 18 phase prompts, a task board, project rules, templates, and the user-supplied decision log.

## Quick start

1. Create or open the **actual MinhaAI repository**. Do not assume the repo name/URL.
2. Copy `AGENTS.md`, `prompts/`, `tasks/`, `templates/`, and `docs/source/` into the repository.
3. Add the **actual**, authoritative `PRD.md` (v3.0.0, if current) and `ai-provider-strategy.md` to `docs/source/`. Those documents were **not included** in the provided upload. Do not invent their contents.
4. Run `prompts/00-repository-discovery.md` in your coding agent. Inspect the outputs and unblock missing source files.
5. Execute `prompts/01-...` through `prompts/17-...` in order. Use a new agent session per phase, and point the agent at the previous reports / handoff.
6. Allow the next phase only when its acceptance criteria and tests pass; leave unverified tasks marked BLOCKED.

### Paste in your coding agent

```text
Open AGENTS.md, tasks/implementation-plan.md and prompts/00-repository-discovery.md.
Execute ONLY phase 00 in this repository. Do not implement future phases.
Create its deliverables and write tasks/phase-reports/00.md with changes, commands/results,
open questions, risks and a proposed next action. Do not push or deploy.
```

For the next phase replace `00-repository-discovery` with the correct prompt file. Always include `AGENTS.md` as the shared policy and `tasks/implementation-plan.md` as the roadmap.

## Implementation principles

- **Vertical slices**: database/domain logic → API → permissions → UI → tests for each feature, rather than implementing everything at once.
- **Single-source-of-truth**: source PRD and the decision log; derived specs must explicitly trace to them. A decision explicitly approved by the product owner is not silently reversed by an agent.
- **Fail closed** for private AI, unsupported file scans, missing permissions and unknown source legality.
- **Zero surprise cost**: no paid plan/API/upgrade/deployment without separate explicit authorization.
- **Review and verification**: an agent saying “done” is not evidence; test outputs and actual checks are required.

## Source completeness

The provided uploaded file is `docs/source/MinhaAI_PRD_Decision_Resolution_AR.md`, dated October 14, 2026. It references `PRD.md` 3.0.0 and `ai-provider-strategy.md`, which are currently **missing**. Phase 00 must not declare requirements coverage complete until the authoritative documents are present.

## What does NOT mean launch-ready?

A completed codebase is **not** approval to handle real students' personal data. Before public beta: hosting terms; legal/privacy review; AI-provider eligibility and approvals; approved scholarship sources and extension sites; malware scanning; backup restore drill; security tests and owner signoff must be independently verified.
