# MinhaAI implementation roadmap — phase gates

**Status legend**: TODO / IN PROGRESS / PASS / BLOCKED. Initial status: TODO, except source completeness is BLOCKED until actual PRD and AI strategy are present.

| ID | Phase / prompt | Prerequisite | Minimum deliverable | Acceptance gate |
|---|---|---|---|---|
| 00 | Repository discovery | Repo + uploaded decision log | Source inventory, missing inputs, scope risk report | Source status explicit; no fabricated requirements |
| 01 | Requirements decomposition | 00, authoritative PRD | Versioned feature matrix, FR acceptance scenarios, release scope | Every in-scope feature traceable, conflicts flagged |
| 02 | Architecture & contracts | 01 | ADRs, module map, APIs/jobs/permissions plans | Modularity, trust boundaries and deployment risks reviewed |
| 03 | Domain and data model | 02 | DBML/ERD, migrations plan, state machines | Ownership, uniqueness, idempotency & history modeled |
| 04 | UX/UI specification | 01–03 | Sitemap, wireframes, tokens, RTL/LTR flows | UI states for loading/error/disabled/consent |
| 05 | Workspace/bootstrap | 02–04 | Monorepo scaffolding, local Docker, CI skeleton | Bootable app/API, CI/lint checks, no secrets |
| 06 | Identity, roles, privacy | 05 | Verified adult auth, roles, consent, isolation | Cross-user 403, age boundary, admin file 403 tests |
| 07 | Scholarships/catalog | 06 | Public search, admin moderation, source registry | No auto-publish, unverified-date handling |
| 08 | Eligibility & matching | 07 | Deterministic rules, coverage/confidence | Mandatory fails cannot be overridden by AI |
| 09 | Credits & operations | 06 | Grant, ledger, limits, reconciliation | Concurrency/idempotency, no double charge/grant |
| 10 | AI gateway & budgets | 08–09 | Adapters, classification, gating, mock fallback | Private-data unapproved routes fail closed |
| 11 | Private files & documents | 06, 09–10 | Scan/upload, CV/docs, versioning, export | Secure storage and charge-on-valid-save only |
| 12 | Applications & deadlines | 07, 11 | Tracking, states, history, reminders | Verified deadlines only; frozen submitted artifacts |
| 13 | Support & SLA | 06, 10 | Ticket support, SLA engine, assigned attachments | No private library access, hours/priority tests |
| 14 | Chrome extension | 06, 12 | MV3 review-only assisted autofill | No OTP/password access, no auto-submit |
| 15 | Admin & operations UI | 07–14 | Moderation, configurable limits, audit, flags | Admin privilege boundaries audited |
| 16 | Integrated testing/security | 06–15 | E2E, abuse cases, load tests, release report | Security gates and target metrics recorded |
| 17 | Deployment & go/no-go | 16 + external gates | Infra plan, rollback, runbooks, decision | Explicit legal/provider/source/hosting signoff |

## Current execution state — 2026-10-14

- **00: BLOCKED — SOURCE_INCOMPLETE.** Named discovery deliverables and repository map produced; inventory gate (explicit source status, no fabricated requirements) satisfied. Full completion is withheld because `docs/source/PRD.md` is missing. Provider strategy is present from an earlier user attachment. See `phase-reports/00.md`.
- Source completeness: **BLOCKED** pending actual approved PRD and baseline reconciliation.
- Phases 01–17 remain **TODO**, not executed; phase 01 cannot establish its complete baseline without the PRD.
- No bootstrap, dependency installation, commit, push, deployment, or resource provisioning performed in this run.

## Release gates that code cannot waive

- `EXTERNAL_GATE`: hosting terms support the intended use; Vercel Hobby non-commercial constraint must be checked before a commercial/public SaaS deployment.
- `EXTERNAL_GATE`: AI providers/models/data classes individually approved for private data; otherwise keep private AI disabled.
- `EXTERNAL_GATE`: legal privacy, retention/deletion/restore policies approved for actual users/jurisdictions.
- `EXTERNAL_GATE`: each scholarship source and extension site permitted and recorded.
- `EXTERNAL_GATE`: working file scanning, verified backups and restore rehearsal, and required auth/permission/security tests.
- `EXTERNAL_GATE`: product owner reviews and approves actual release readiness.

## Suggested parallelism AFTER architecture

- Agent A: catalog + deterministic matching, Agent B: credits + AI adapters, Agent C: UI components + translated flows, Agent D: test fixtures + integration tests.
- Avoid agents editing the same files or migrations simultaneously; single integrator owns merges and phase pass criteria.
- Never parallelize unagreed contracts, schema migrations, security policies, and credit settlement logic.
