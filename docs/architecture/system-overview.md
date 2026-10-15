# MinhaAI system overview — phase 02

Status: **PASS — architecture/documentation gate**, reconciled with the supplied PRD, Phase 01 traceability and latest owner directions. This is a working engineering design, not a running system, legal approval or general-release go-ahead. Phases 00–03 documentation are authorized together by UD-002; no UX/bootstrap/runtime implementation or deployment follows automatically.

## Authority and navigation

| Trace | Authority |
|---|---|
| U02 | Current user request and `prompts/02-architecture-and-boundaries.md`: architectural deliverables and boundaries |
| A | `AGENTS.md`, especially Source hierarchy, Stack and Security invariants |
| D | `../source/MinhaAI_PRD_Decision_Resolution_AR.md`, 2026-10-14: §أ owner decisions 1–7; §ب analyst defaults; §ج OQ-001–026; §§د–ز risks/stack/tests/external gates |
| P | `../source/ai-provider-strategy.md`, 2026-10-14, proposed [A], §§1–6 |
| PRD / UD | Supplied PRD v3.0.0; Phase 01 matrix/rules/scenarios/backlog; latest owner UD-001 Admin-configurable recovery and UD-002 bounded 00–03 completion. Historical release signature remains G-SIGNOFF; original interview files not fabricated. |

Every design choice beyond those sources is an **ASSUMPTION (proposed engineering decision)**, not an invented FR; actual PRD IDs are mapped in docs/specs/feature-matrix.md. ADRs carry their rationale and source traces. Exact routes, schema names, retry defaults and origin topology are documented engineering contracts reconciled to the working baseline; implementation/legal review remains separate. Numerical product limits are sourced defaults, never measured capacity. Supplied PRD/decision/provider source bytes remain unchanged; latest owner directions are an additive source record.

- [API contract and authorization](api-contracts.md), with [OpenAPI draft](openapi.json).
- [Domain public contracts](domain-contracts.md), [command catalog](command-catalog.md), [identity/extension protocols](identity-and-extension-contracts.md).
- [Privacy and data flow](privacy-boundaries.md).
- [Jobs, credits and reconciliation](jobs-and-reconciliation.md).
- [Deployment and checked platform evidence](deployment-boundaries.md).
- [ADRs](../adr/README.md).

## Proposed runtime decomposition

One Django/DRF modular monolith owns business rules and PostgreSQL transactions. Next.js provides Arabic RTL/English LTR presentation and public scholarship rendering. An independent process running the same domain code consumes recoverable PostgreSQL jobs; it has no public listener. PostgreSQL holds domain records, sessions, credit ledger/reservations, queue/outbox, operation metadata and audit records. Private object storage holds quarantined and accepted file bytes; no public buckets or direct admin library access. An optional Chrome MV3 client provides review-before-fill only; absent from required core deployment and gated by permitted sites.

ASSUMPTION: browser requests use one HTTPS origin with `/api/*` routed to Django; web pages route to Next.js. A trusted ingress enforces Host/origin and preserves multiple Set-Cookie headers; it strips spoofed forwarding headers. Django owns sessions/CSRF. Next.js does not own authorization or acquire provider/storage credentials. Public pages alone can be shared-cacheable; every authenticated response uses `Cache-Control: private, no-store`. No private data in static builds, CDN caches or analytics.

The API returns 202 after durable operation/job creation, then the UI polls an owned operation. AI generation, scanning, ingestion, export and reconciliation do not run as long-lived request handlers or post-response best-effort callbacks. API and worker scale independently, but remain one domain deployment unit with compatible contracts and migrations. No speculative Redis, vector DB or microservices.

## C4 and flow diagrams

The C4 diagrams use native Mermaid C4 syntax. Relationships show proposed runtime permissions, not currently deployed access.

| Diagram | Source |
|---|---|
| Context | [c4-context.mmd](diagrams/c4-context.mmd) |
| Container | [c4-container.mmd](diagrams/c4-container.mmd) |
| Django components | [c4-component.mmd](diagrams/c4-component.mmd) |
| Credit-backed AI | [credit-ai-generation.mmd](diagrams/credit-ai-generation.mmd) |
| Quarantined file upload | [file-upload.mmd](diagrams/file-upload.mmd) |
| Admin scholarship moderation | [admin-moderation.mmd](diagrams/admin-moderation.mmd) |

## Required invariant boundaries

- D §أ 1/7, OQ-002/016; P §2: payment/checkout off, one signup grant, server-priced operation, transactional reservation once and debit only on accepted saved output. Provider cost budget is separate from student Credits; no $0 escape through fallback/retry.
- D §أ 5/OQ-004; P §§1–4: classification and consent/provider/model/region approvals before each egress. Private data only to individually approved Cloudflare or Groq; never to Gemini unpaid/OpenRouter free. Policy/security/consent refusal never becomes fallback permission.
- D §أ 6/OQ-007/013; A: owner-scoped private storage, pre-acceptance scanner, admin library 403+audit, assigned support access only to explicitly attached ticket files. No private library route in generic Django admin.
- D §أ 2–4/OQ-003/015: approved source permissions and explicit moderation; no auto-publication. Extension never reads password/OTP or submits.
- D OQ-012/019: deterministic mandatory eligibility failures remain authoritative; support AI cannot move money, change account state or access arbitrary files.
- D OQ-022/023; A: protected student features require verified adult accounts; logs contain metadata, never raw private content.

## Time and locale contract

Trace D OQ-006/008/017/020; ASSUMPTION API representation. Store instants as PostgreSQL timezone-aware timestamps in UTC; JSON RFC3339 `Z`, stable UTC audit timestamps. Store birth date as ISO date, not an instant. IANA `Asia/Hebron` determines daily spend/support business calendar and adult-age evaluation (proposed consistent evaluation timezone); record policy version and evaluated local date. Use timezone database rules, not fixed offsets. Leap-day age rule is MISSING pending legal/product confirmation; protected activation fails closed for an unresolved boundary case rather than inventing a legal rule.

A daily cap does not mint Credits. Boundary calculation uses the actual next local midnight converted to UTC (23/25-hour days possible), locks one user/day policy bucket; new policies apply prospectively, never erase recorded consumption. Recovery follows UD-001/[ADR0008](../adr/0008-configurable-recovery-period.md): Admin-configurable calendar days/zone, default 30/Asia-Hebron from the PRD, immutable policy/days/zone/algorithm/UTC restore_until captured per deletion request. Restore trusted receipt strictly < stored cutoff; equality expires. Admin edits affect later requests only; no hard-coded 720-hour rule. Calendar DST gap/fold resolution is explicitly proposed in ADR0008 and legal envelope remains gated. Restore/purge serialize on lifecycle state. Deadline stores source zone, source text, confirmed instant/version; unknown or ambiguous source time produces no timed reminder until verified. Display according to user locale/timezone; fallback Palestine display timezone is `Asia/Hebron`. Schedule reminders on versioned confirmed events and deduplicate by event version/user/offset. SLA uses a versioned Asia/Hebron business-hours/holiday calendar, measuring first substantive human response, not chatbot activity. No first-response pause caused by later student waiting.

## Readiness and handoff

Feature-level and all-FR/BR/NFR traces exist in Phase 01; selected Beta contracts define owner/scoped Admin/worker/extension authorization, price/counter/transaction semantics, typed DTOs and fail-closed dependencies. Seven original ADRs plus recovery ADR0008, six Mermaid sources and OpenAPI are structurally checked. Graph/schema design is in Phase 03, not live migrations.

Deployment hosts/provider models/legal/source/site/scanner/backup/free quota and measured security/quality remain [external gates](../specs/missing-inputs.md). The PRD's historical signature is a release gate, not file absence; UD-002 authorizes working documentation, not retroactive provenance or release. Next Phase04 UX/05 bootstrap/implementation require separate authorization. No app code, paid resource, push or deployment in this run.
