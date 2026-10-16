# MinhaAI implementation roadmap — phase gates

**Status legend**: TODO / IN PROGRESS / PASS / BLOCKED. PASS means the named phase gate passed for its reported checks; design passes in 00–04 do not imply runtime, external approval or launch readiness. Phase05 has implemented bootstrap artifacts but its runtime gate is BLOCKED; Phases06–17 and product implementation backlog items remain TODO.

| ID | Phase / prompt | Prerequisite | Minimum deliverable | Acceptance gate | Status |
|---|---|---|---|---|---|
| 00 | Repository discovery | Repo + uploaded decision log | Source inventory, missing inputs, scope risk report | Source status explicit; no fabricated requirements | PASS |
| 01 | Requirements decomposition | 00, authoritative PRD | Versioned feature matrix, FR acceptance scenarios, release scope | Every in-scope feature traceable, conflicts flagged | PASS |
| 02 | Architecture & contracts | 01 | ADRs, module map, APIs/jobs/permissions plans | Modularity, trust boundaries and deployment risks reviewed | PASS |
| 03 | Domain and data model | 02 | DBML/ERD, migrations plan, state machines | Ownership, uniqueness, idempotency & history modeled | PASS |
| 04 | UX/UI specification | 01–03 | Sitemap, wireframes, tokens, RTL/LTR flows | UI states for loading/error/disabled/consent | PASS |
| 05 | Workspace/bootstrap | 02–04 | Monorepo scaffolding, local Docker, CI skeleton | Bootable app/API, CI/lint checks, no secrets | BLOCKED |
| 06 | Identity, roles, privacy | 05 | Verified adult auth, roles, consent, isolation | Cross-user 403, age boundary, admin file 403 tests | TODO |
| 07 | Scholarships/catalog | 06 | Public search, admin moderation, source registry | No auto-publish, unverified-date handling | TODO |
| 08 | Eligibility & matching | 07 | Deterministic rules, coverage/confidence | Mandatory fails cannot be overridden by AI | TODO |
| 09 | Credits & operations | 06 | Grant, ledger, limits, reconciliation | Concurrency/idempotency, no double charge/grant | TODO |
| 10 | AI gateway & budgets | 08–09 | Adapters, classification, gating, mock fallback | Private-data unapproved routes fail closed | TODO |
| 11 | Private files & documents | 06, 09–10 | Scan/upload, CV/docs, versioning, export | Secure storage and charge-on-valid-save only | TODO |
| 12 | Applications & deadlines | 07, 11 | Tracking, states, history, reminders | Verified deadlines only; frozen submitted artifacts | TODO |
| 13 | Support & SLA | 06, 10 | Ticket support, SLA engine, assigned attachments | No private library access, hours/priority tests | TODO |
| 14 | Chrome extension | 06, 12 | MV3 review-only assisted autofill | No OTP/password access, no auto-submit | TODO |
| 15 | Admin & operations UI | 07–14 | Moderation, configurable limits, audit, flags | Admin privilege boundaries audited | TODO |
| 16 | Integrated testing/security | 06–15 | E2E, abuse cases, load tests, release report | Security gates and target metrics recorded | TODO |
| 17 | Deployment & go/no-go | 16 + external gates | Infra plan, rollback, runbooks, decision | Explicit legal/provider/source/hosting signoff | TODO |

## Current execution state — 2026-10-15

- **00: PASS — SOURCE_INVENTORY_COMPLETE.** Actual PRD/decision/provider sources present, byte-preserved; owner/default/assumption/external evidence separated, current repo/map/gates updated. See [report00](phase-reports/00.md).
- **01: PASS — TRACEABILITY_COMPLETE.** 125 FR +28 NFR individual matrix rows, 54 BR acceptance paths, 26 OQ dispositions, 41 source AC/153 named requirement scenarios, 19 original stories/15 dependency-checked epics. All implementation stories TODO. See [report01](phase-reports/01.md).
- **02: PASS — ARCHITECTURE_CONTRACTS_COMPLETE.** Modular/trust/deployment/job domains, six syntax-checked Mermaid sources, eight documented ADRs, 98 API paths/109 HTTP operations/127 schemas with current ownership/CSRF/quote/MFA/PKCE/idempotency/policy contracts. See [report02](phase-reports/02.md).
- **03: PASS — DATA_DESIGN_COMPLETE.** 77 tables/53 owner-scoped tables/201 RESTRICT unique-target/type-compatible FKs; five billing/six support states, immutable snapshots/history, once-only grant/settlement/cancellation and Admin-configurable per-request recovery snapshot. DBML/PostgreSQL syntax/structural checks pass; runtime triggers/RLS/concurrency/migrations NOT RUN. See [report03](phase-reports/03.md).
- **04: PASS — UX_SPECIFICATION_COMPLETE.** Current Phase04 request authorizes documentation only: 49 route/surface specifications, 12 journeys, every source SCR/FR/AC referenced, mobile/laptop wireframes, E/L/X/O/D states, bilingual behavior and accessible tokens. Thirteen wire-contract gaps have explicit unavailable/manual paths; no API or privilege widening. Static coverage/API-reference/link/scope/contrast checks only; interactive/accessibility/runtime feature acceptance NOT RUN. See [report04](phase-reports/04.md).
- Latest owner [UD-001/002](../docs/source/2026-10-15-owner-decisions.md) authorizes early completion and Admin period control. Existing source files are unchanged. A policy edit is prospective and never moves an already confirmed deletion deadline; default30/calendar/Asia-Hebron is an explicit engineering interpretation of the PRD, not a permanent720h rule or legal approval.
- **Release status: BLOCKED — EXTERNAL_GATES / PRODUCT_IMPLEMENTATION_PENDING.** Formal historical general-release signature/original interview provenance, actual legal/provider/source/site/hosting/scanner/backup/free-quota/quality evidence remain independent. No stale PRD-missing/Phase01-unexecuted blocker is current; earlier blocked reports were superseded by this authorized re-evaluation.
- **05: BLOCKED — POSTGRESQL_RUNTIME_GATE.** Bootstrap artifacts, Next production build, type/lint/schema checks, 19 database-independent API tests, five client tests and actual HTTP liveness/forwarding/CSRF/bilingual checks are implemented and verified. Full checks report two PostgreSQL setup errors; Docker is missing and native PostgreSQL16.15 cannot allocate the host's required System V shared memory (EIO even with mmap). Migration/application-database readiness and a complete clean-clone boot remain unverified. See [report05](phase-reports/05.md) and [traceability](../docs/specs/phase-05-bootstrap.md). **06–17: TODO**; all product backlog statuses and prior phase outcomes remain unchanged. No commit/push/deployment or paid resource.

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
