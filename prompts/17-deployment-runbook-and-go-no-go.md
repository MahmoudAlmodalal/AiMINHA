# Phase 17 — Deployment plan and controlled release

**Objective:** Perform exactly one bounded phase of the MinhaAI build.

## Work
1. Based on verified actual platform terms, propose a zero-spend environment for private testing and permitted public launch. Do not assume Vercel Hobby permits a commercial SaaS; confirm before public use.
2. Separate stateless Next.js frontend, Django API, database/storage and durable background worker; document secrets/allowed origins, migrations, job reconciliation, observability, throttling, no-paid-upgrade budget controls.
3. Write `infra/deployment-runbook.md`, `infra/incident-runbook.md`, `infra/backup-and-restore.md`, `infra/cost-guardrails.md`, and a rollback sequence.
4. Reconcile legal privacy/retention, vendor per-data-type approvals, source/extension permissions, working malware scanning, verified backups and product owner acceptance; mark every external gate with evidence or BLOCKED.
5. If not approved, deploy local/private synthetic-data demonstration only; do not launch public real-user processing, create billable resources or push without explicit approval.

**Gate:** Owner and required external checks clear; otherwise release status NO-GO with explicit next actions.
## Required execution contract
- Read `AGENTS.md`, `tasks/implementation-plan.md`, `docs/source/MinhaAI_PRD_Decision_Resolution_AR.md`, and the authoritative source files where available.
- Execute only THIS phase. Identify source/requirement traces and unresolved external gates. Do not invent absent documents.
- Produce exact named artifacts, run relevant checks, update roadmap statuses, and write `tasks/phase-reports/17.md`. Report skipped checks truthfully.
- Do not push, deploy, create paid resources, or change other phases.

