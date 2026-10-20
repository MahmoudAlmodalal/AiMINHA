# MinhaAI implementation roadmap — phase gates

**Status legend**: TODO / IN PROGRESS / PASS / BLOCKED. PASS means the named phase gate passed for its reported checks; design passes in 00–04 do not imply runtime, external approval or launch readiness. Phase05 bootstrap and Phase06 identity/privacy local gates passed; hosted CI and external integrations remain separate evidence. Phase07 catalog local gate passed; Phase08 rule-first local gate and measurement plan passed; Phase09 synthetic accounting local gate passed; Phase10 local mock/egress-denial gate passed; Phase11 local actual-scanner/manual-documents/synthetic-accounting gate passed; Phase12 local application-history/frozen-evidence/confirmed-deadline-inbox gate passed. Phase13 local support-ticket/SLA/AI-triage gate passed. Phases14–17 and unrelated product backlog items remain TODO.

| ID | Phase / prompt | Prerequisite | Minimum deliverable | Acceptance gate | Status |
|---|---|---|---|---|---|
| 00 | Repository discovery | Repo + uploaded decision log | Source inventory, missing inputs, scope risk report | Source status explicit; no fabricated requirements | PASS |
| 01 | Requirements decomposition | 00, authoritative PRD | Versioned feature matrix, FR acceptance scenarios, release scope | Every in-scope feature traceable, conflicts flagged | PASS |
| 02 | Architecture & contracts | 01 | ADRs, module map, APIs/jobs/permissions plans | Modularity, trust boundaries and deployment risks reviewed | PASS |
| 03 | Domain and data model | 02 | DBML/ERD, migrations plan, state machines | Ownership, uniqueness, idempotency & history modeled | PASS |
| 04 | UX/UI specification | 01–03 | Sitemap, wireframes, tokens, RTL/LTR flows | UI states for loading/error/disabled/consent | PASS |
| 05 | Workspace/bootstrap | 02–04 | Monorepo scaffolding, local Docker, CI skeleton | Bootable app/API, CI/lint checks, no secrets | PASS |
| 06 | Identity, roles, privacy | 05 | Verified adult auth, roles, consent, isolation | Cross-user 403, age boundary, admin file 403 tests | PASS |
| 07 | Scholarships/catalog | 06 | Public search, admin moderation, source registry | No auto-publish, unverified-date handling | PASS |
| 08 | Eligibility & matching | 07 | Deterministic rules, coverage/confidence | Mandatory fails cannot be overridden by AI | PASS |
| 09 | Credits & operations | 06 | Grant, ledger, limits, reconciliation | Concurrency/idempotency, no double charge/grant | PASS |
| 10 | AI gateway & budgets | 08–09 | Adapters, classification, gating, mock fallback | Private-data unapproved routes fail closed | PASS |
| 11 | Private files & documents | 06, 09–10 | Scan/upload, CV/docs, versioning, export | Secure storage and charge-on-valid-save only | PASS |
| 12 | Applications & deadlines | 07, 11 | Tracking, states, history, reminders | Verified deadlines only; frozen submitted artifacts | PASS |
| 13 | Support & SLA | 06, 10 | Ticket support, SLA engine, assigned attachments | No private library access, hours/priority tests | PASS |
| 14 | Chrome extension | 06, 12 | MV3 review-only assisted autofill | No OTP/password access, no auto-submit | TODO |
| 15 | Admin & operations UI | 07–14 | Moderation, configurable limits, audit, flags | Admin privilege boundaries audited | TODO |
| 16 | Integrated testing/security | 06–15 | E2E, abuse cases, load tests, release report | Security gates and target metrics recorded | TODO |
| 17 | Deployment & go/no-go | 16 + external gates | Infra plan, rollback, runbooks, decision | Explicit legal/provider/source/hosting signoff | TODO |

## Current execution state — 2026-10-16

- **00: PASS — SOURCE_INVENTORY_COMPLETE.** Actual PRD/decision/provider sources present, byte-preserved; owner/default/assumption/external evidence separated, current repo/map/gates updated. See [report00](phase-reports/00.md).
- **01: PASS — TRACEABILITY_COMPLETE.** 125 FR +28 NFR individual matrix rows, 54 BR acceptance paths, 26 OQ dispositions, 41 source AC/153 named requirement scenarios, 19 original stories/15 dependency-checked epics. All implementation stories TODO. See [report01](phase-reports/01.md).
- **02: PASS — ARCHITECTURE_CONTRACTS_COMPLETE.** Modular/trust/deployment/job domains, six syntax-checked Mermaid sources, eight documented ADRs, 98 API paths/109 HTTP operations/127 schemas with current ownership/CSRF/quote/MFA/PKCE/idempotency/policy contracts. See [report02](phase-reports/02.md).
- **03: PASS — DATA_DESIGN_COMPLETE.** 77 tables/53 owner-scoped tables/201 RESTRICT unique-target/type-compatible FKs; five billing/six support states, immutable snapshots/history, once-only grant/settlement/cancellation and Admin-configurable per-request recovery snapshot. DBML/PostgreSQL syntax/structural checks pass; runtime triggers/RLS/concurrency/migrations NOT RUN. See [report03](phase-reports/03.md).
- **04: PASS — UX_SPECIFICATION_COMPLETE.** Current Phase04 request authorizes documentation only: 49 route/surface specifications, 12 journeys, every source SCR/FR/AC referenced, mobile/laptop wireframes, E/L/X/O/D states, bilingual behavior and accessible tokens. Thirteen wire-contract gaps have explicit unavailable/manual paths; no API or privilege widening. Static coverage/API-reference/link/scope/contrast checks only; interactive/accessibility/runtime feature acceptance NOT RUN. See [report04](phase-reports/04.md).
- Latest owner [UD-001/002](../docs/source/2026-10-15-owner-decisions.md) authorizes early completion and Admin period control. Existing source files are unchanged. A policy edit is prospective and never moves an already confirmed deletion deadline; default30/calendar/Asia-Hebron is an explicit engineering interpretation of the PRD, not a permanent720h rule or legal approval.
- **Release status: BLOCKED — EXTERNAL_GATES / PRODUCT_IMPLEMENTATION_PENDING.** Formal historical general-release signature/original interview provenance, actual legal/provider/source/site/hosting/scanner/backup/free-quota/quality evidence remain independent. No stale PRD-missing/Phase01-unexecuted blocker is current; earlier blocked reports were superseded by this authorized re-evaluation.
- **05: PASS — LOCAL_BOOTSTRAP_GATE, 2026-10-16.** Existing bootstrap preserved and verified on a Docker-capable host using Python3.12/Node22/npm10 and PostgreSQL16.15. A clean local Git clone passed setup, database startup, sessions migration, all 21 API tests plus five client tests, lint/type/schema/migration/secret checks, production build, real HTTP smoke and worker database preflight. Development startup served both locales and the API rewrite, stopped cleanly and left Git clean. The former host-specific PostgreSQL blocker is superseded; hosted CI remains independently unverified until an authorized push/run. See [report05](phase-reports/05.md) and [traceability](../docs/specs/phase-05-bootstrap.md). **06–17: TODO**; all product backlog statuses and prior phase outcomes remain unchanged. The user explicitly requested pushing to AiMINHA; deployment and paid resources remain unauthorized.

## Release gates that code cannot waive

Phase06 current state, superseding only its TODO at the Phase05 handoff:
**06: PASS — LOCAL_IDENTITY_PRIVACY_GATE, 2026-10-16.** Canonical verified-adult
email/password accounts, optional existing-user Google linking boundary, rotating
sessions, explicit versioned consent, immutable configurable UTC recovery snapshots,
safe blocked file-purge queue and audited ownership/Admin/support denials are
implemented. Fresh PostgreSQL verification passed 69 backend tests, eight client
tests, static/types/schema/migrations/build and real bilingual identity HTTP flow.
Live SMTP/Google/MFA, legal approvals, object erasure/backups and full production
RLS remain gated. One non-reproduced HTTP500 remains a documented reliability
follow-up; it was not seen in the final fresh-database flow. See [report06](phase-reports/06.md)
and [scope](../docs/specs/phase-06-identity-privacy.md). No Phase07–17 outcome changed;
the subsequent explicit `Push` instruction authorizes committing and publishing
this bounded Phase06 change only. Deployment, paid resources and provider calls
remain unauthorized and were not performed.

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


## Phase07 execution state — 2026-10-16

**07: PASS — LOCAL_CATALOG_PUBLICATION_GATE.** Permission-bound source revisions,
manual/approved structured proposals, immutable candidate facts and exact-version
human approval/audit now back the public bilingual catalog and PostgreSQL FTS.
Current source revision/status/expiry, review and publication must agree; imports
and edits never auto-publish, restoration returns to review and internal notes
stay private. Fresh PostgreSQL migrations, 139 API tests (70 catalog) plus eight
client tests, static/types/contracts/build and actual HTTP catalog/identity checks
passed. The earlier proxy HTTP500 recurred and was narrowed to Next upstream
ECONNRESET; a documented local Connection:close development-server workaround
passed consecutive-request and identity checks. It is not production reliability
certification. No real source/MFA/legal approval, live fetch/monitor/report workflow,
semantic quality or release readiness is inferred. See [report07](phase-reports/07.md)
and [scope](../docs/specs/phase-07-catalog.md). Only Phase07's current outcome changes;
Phase08–17 and earlier outcomes are preserved. The user explicitly requested a GitHub
push after completion; deployment, paid resources and provider calls remain outside
scope.


## Phase08 execution state — 2026-10-16

**08: PASS — LOCAL_RULE_FIRST_ELIGIBILITY_GATE_WITH_MEASUREMENT_PLAN.** Typed
nullable self-confirmed owned profile versions, exact-catalog/source human-reviewed
structured rule bases, rule-first tri-state outcomes and evidence-backed fixed
30/25/20/15/10 fit with >=70% coverage are implemented. Unknown data/scales remain
unknown, hard failure dominates any score, and no probability or private AI route
is fabricated. Fresh23-migration PostgreSQL verification passed257 backend tests
(118 new eligibility cases), eight client tests, static/types/contracts/build and
actual bilingual profile/auth/catalog/eligibility HTTP flows. Receipts retain opaque
IDs only; SQL guards reject omitted/duplicate/null rule-check substitutions.
The warm p95<=2s/20-client measurement plan is recorded; actual concurrent load
measurement, academic authenticity/equivalences, weights quality, real source/MFA
and production RLS/legal/release evidence remain unverified/external. See
[report08](phase-reports/08.md), [scope](../docs/specs/phase-08-eligibility.md) and
[ADR0012](../docs/adr/0012-evidence-bound-eligibility.md). Earlier phase outcomes and
Phase09–17 are unchanged. The user's subsequent explicit `Push` instruction
authorizes committing and publishing this bounded Phase08 change. Deployment,
paid resources and provider calls remain unauthorized and were not performed.

## Phase09 execution state — 2026-10-16

**09: PASS — LOCAL_CREDIT_ACCOUNTING_GATE_WITH_SYNTHETIC_EXECUTION.** Once-only
verified adult activation grants, append-only credit journals, guarded holds,
Asia/Hebron spend/admission days, prospective scoped-MFA policies and captured
prices now pass real PostgreSQL concurrency tests. Validated saved synthetic
outputs settle once; failure releases once; uncertain/expired operations retain
holds in RECONCILING with15-minute investigation and24-hour review markers.
Fresh25-migration verification passed359 backend tests (102 new financial cases),
eight client tests, static/types/contracts/build, all five HTTP smoke flows and
worker/timeout preflights. A concurrent policy-head join defect was fixed and
its CAS regression passes. Populated legacy-active backfill was separately
verified without granting pending/suspended/Admin/minor fixtures.

The bilingual wallet is read-only. Real provider execution/domain validators,
client-confirmed price quotes, authoritative reconciliation recovery, production
scheduling/worker principals/RLS/performance, manual finance adjustments and final
erasure/legal/provider approvals remain gated. No purchase, real AI, commit,
push, deployment or paid resource was performed. See [report09](phase-reports/09.md),
[scope](../docs/specs/phase-09-credits.md) and
[ADR0013](../docs/adr/0013-credits-and-reconciliation.md). This entry supersedes
only Phase09's earlier TODO; Phases00–08 and10–17 outcomes remain unchanged.
The user's subsequent explicit `ارفع` instruction authorizes committing and
publishing this bounded Phase09 change only. Deployment and paid resources
remain unauthorized.

## Phase10 execution state — 2026-10-17

**10: PASS — LOCAL_MOCK_GATE_WITH_LIVE_EGRESS_DISABLED.** Explicit provenance
classification, exact scoped approval metadata, immutable quota baselines,
physical reservations, bounded attempts/leases, circuit/half-open controls and
strict evidence-based synthetic output now orchestrate the existing credit
kernel. Current global stops are rechecked without recounting logical admissions.
Unknown effects retain provider and financial holds; SQL and services prevent
uncertain release, duplicate dispatch and settlement on unsupported/unsaved output.

Fresh27-migration PostgreSQL verification passed523 backend tests (164 new gateway
cases), eight client tests, static/types/contracts/build, all five HTTP flows and
worker/credit/AI timeout inspection. The capability API confirms closed client
execution. Real transports and private processing remain disabled even with a
configured key or generic consent; precise private consent, vendor terms/free-only
guarantees/meters, actual domain validation, live worker operations/RLS/load and
release approvals remain external gates. Immutable meter baselines have no live
refresh path and go unavailable when stale.

See [report10](phase-reports/10.md), [scope](../docs/specs/phase-10-ai-gateway.md)
and [ADR0014](../docs/adr/0014-ai-gateway-and-budget-stop.md). No commit or push was
performed during local implementation; the user's subsequent explicit `Push`
instruction authorizes committing and publishing this bounded Phase10 change.
No deployment, paid resource or real provider request was performed. Only
Phase10's earlier TODO is superseded; Phase00–09 and11–17 outcomes remain unchanged.

## Phase11 execution state — 2026-10-17

**11: PASS — LOCAL_ACTUAL_SCANNER_MANUAL_DOCUMENTS_SYNTHETIC_ACCOUNTING_GATE.**
Private bounded uploads and exports reserve quarantine capacity, require actual
ClamAV success plus strict MIME/content checks, and bind immutable object/scan
identities before acceptance. Owner/session-scoped expiring byte grants recheck
current account or assigned explicit ticket shares. Admin library reads remain
denied and audited. Fenced five-minute attempt recovery retains capacity until
physical cleanup is proven; no active writer is purged.

The bilingual document workspace supports four manual types, selected language,
escaped previews, immutable versions, exact approvals, comparison/restore-as-new
and deterministic private PDF/DOCX retry. Failed export preserves the saved source;
same-version re-export is free. Local fixed synthetic generation/extraction adds a
saved artifact/proposal witness before the existing once-only credit settlement.
Unsupported provider claims never save or charge; uncertain outcomes keep holds.

Local PostgreSQL verification passed633 backend tests including the actual scanner
opt-in and eight client tests, static/type/schema/migration/secret checks, production
build, all previous HTTP smokes and the new bilingual actual-scanner export-recovery
HTTP flow. No real private AI processing or displayed-price authorization is claimed:
private generation/extraction stays unavailable pending precise consent, approved
processor/model/region, real transport and domain-quality evidence. Manual input
remains available.

The filesystem adapter/fence is single-host local infrastructure. Approved durable
encrypted storage, scanner operations/scheduling, production DB roles/RLS, legal
erasure/backups, visual/export-quality and release signoff remain external gates.
Derivative exports are protected from ordinary byte deletion while retained. The
internal submission snapshot primitive awaits Phase12's authoritative application
binding; ticket lifecycle remains Phase13. See [report11](phase-reports/11.md),
[scope](../docs/specs/phase-11-private-files-documents.md) and
[ADR0015](../docs/adr/0015-private-file-and-document-boundaries.md).
No commit, push, deployment, paid resource or real provider request was performed.
Only Phase11's current outcome changes; earlier phases and Phases12–17 are preserved.
The owner's subsequent explicit `Push` instruction authorizes committing and
publishing this bounded Phase11 change only. Deployment and paid resources remain
outside this authorization; Phase12 requires a new instruction.

## Phase12 execution state — 2026-10-17

**12: PASS — LOCAL_APPLICATION_HISTORY_FROZEN_EVIDENCE_CONFIRMED_DEADLINE_INBOX_GATE.**
Owned saved scholarships and distinct reviewed-round applications now have explicit
authorized transitions, immutable student-reported history, separate official-status
evidence and exact submitted document/upload manifests. Later master edits and new
rounds preserve submitted evidence. Source rebases are explicit and Preparing-only;
legal deletion review is separate from ordinary edits and is not an erasure receipt.

The bilingual tracker and private read/unread inbox use current confirmed source
deadlines, sponsor-zone instants and validated user display zones. Unknown, rolling,
ambiguous, stale and revoked deadlines produce no live countdown or timed schedule.
Four reminder offsets have recipient/event-version dedupe, transactional delivery
rechecks and a finite recoverable worker. Cancelled attempts remain historical and
can be rescheduled before due without duplicate delivery.

Local PostgreSQL verification passed 711 backend tests (78 new cases), including
the actual scanner opt-in, and eight client tests. Static/type/contracts/migration/
secret checks, production build, all prior HTTP flows and the new real-clock 24h
reminder/submission-history HTTP flow passed. The documents smoke initially failed
registration in the combined run; its isolated actual-scanner rerun passed. Exact
failures, harness corrections and skipped checks are recorded in
[report12](phase-reports/12.md), with source traces in
[scope](../docs/specs/phase-12-applications-reminders.md) and
[ADR0016](../docs/adr/0016-application-evidence-and-deadline-inbox.md).

Real official feeds, richer portal requirements, production periodic scheduling,
DB-role/RLS/load evidence, legal erasure/retention/backup approvals and full browser/
visual/accessibility interaction checks remain external or unverified. Reviewed
round labels and elapsed-minute reminder offsets remain explicit assumptions.
No commit, push, deployment, paid resource or real provider call was performed.
Only Phase12's current outcome changes; earlier phases and Phases13–17 are preserved.
The owner's subsequent explicit `Push` instruction authorizes committing and
publishing this bounded Phase12 change only. Deployment and paid resources remain
outside this authorization; no new phase is started.

## Phase13 execution state — 2026-10-20

**13: PASS — LOCAL_SUPPORT_TICKET_SLA_AI_TRIAGE_GATE.** Owned tickets carry the
six documented states with an append-only, SQL-guarded transition log. The first
human response is measured on an administrator working calendar (default
Sun–Thu 09:00–17:00 Asia/Hebron with holidays, 4/8/24/48 business-hour targets);
the clock starts on the human request or handoff, ends on the first substantive
human reply, is never satisfied by an automated answer and is not distorted by
waiting for the student. Resolution, seven-day quiet-period closure, fourteen-day
reopening and one rating editable for seven days are implemented.

Ticket attachments are explicit, revocable shares of a student-owned asset,
readable only by the currently assigned agent with an audit trail; the private
library stays unreachable from support. AI triage works only from the allowed
context of the current ticket, suggests a category and priority without changing
the administrator's decision, and hands off to a human on request, uncertainty,
two consecutive failures, financial/security topics or critical deadline. The
experiment is bounded to five free AI messages per student per day inside the
shared global AI budget, and no AI path can move a credit balance.

Local PostgreSQL verification passed 756 backend tests (50 new support cases)
with five pre-existing actual-scanner skips because ClamAV is unavailable here,
plus eight client tests. Static/type/contracts/migration/secret checks, the
production build, the base and identity HTTP smokes and a new real-HTTP support
smoke passed. The deterministic local triage is an engineering choice forced by
the current provider-approval state and is not a model capability. Provider-backed
triage, staffing evidence behind the experimental targets, a production scheduler,
DB-role/RLS/load evidence, legal erasure/retention review for support data, the
Phase15 administrator console and release signoff remain external gates. See
[report13](phase-reports/13.md), [scope](../docs/specs/phase-13-support-sla.md)
and [ADR0017](../docs/adr/0017-support-sla-and-ai-triage.md). Only Phase13's
current outcome changes; earlier phases and Phases14–17 are preserved. No commit,
push, deployment, paid resource or real provider call was performed; the working
tree holds this bounded Phase13 change only and the branch remains at the Phase12
baseline.
