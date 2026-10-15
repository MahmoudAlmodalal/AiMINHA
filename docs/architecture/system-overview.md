# MinhaAI system overview — phase 02

Status: **PROVISIONAL / BLOCKED: SOURCE_INCOMPLETE, PHASE_01_MISSING**. This is an implementable architecture proposal for the documented flows, not a complete product baseline or running system. User authorization permits phase 02 despite the unsatisfied roadmap dependency; it does not close that dependency. No code, migrations, deployment or later-phase deliverables are created.

## Authority and navigation

| Trace | Authority |
|---|---|
| U02 | Current user request and `prompts/02-architecture-and-boundaries.md`: architectural deliverables and boundaries |
| A | `AGENTS.md`, especially Source hierarchy, Stack and Security invariants |
| D | `../source/MinhaAI_PRD_Decision_Resolution_AR.md`, 2026-10-14: §أ owner decisions 1–7; §ب analyst defaults; §ج OQ-001–026; §§د–ز risks/stack/tests/external gates |
| P | `../source/ai-provider-strategy.md`, 2026-10-14, proposed [A], §§1–6 |
| MISSING | Approved PRD v3.0.0, phase 01 feature matrix/business rules/backlog |

Every design choice beyond those sources is an **ASSUMPTION (proposed engineering decision)**, not an invented FR. ADRs carry their rationale and source traces. Exact routes, schema names, retry defaults and origin topology are proposed contracts subject to baseline reconciliation. Numerical product limits are sourced defaults, never measured capacity. No source document was changed.

- [API contract and authorization](api-contracts.md), with [OpenAPI draft](openapi.json).
- [Domain public contracts](domain-contracts.md).
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

A daily cap does not mint Credits. Boundary calculation uses the actual next local midnight converted to UTC (23/25-hour days possible), locks one user/day policy bucket; new policies apply prospectively, never erase recorded consumption. UTC account restore predicate is strictly `request_at < deleted_at + 30*24h`, no calendar-month approximation; concurrent deletion/restore serializes on lifecycle state. Deadline stores source zone, source text, confirmed instant/version; unknown or ambiguous source time produces no timed reminder until verified. Display according to user locale/timezone; fallback Palestine display timezone is `Asia/Hebron`. Schedule reminders on versioned confirmed events and deduplicate by event version/user/offset. SLA uses a versioned Asia/Hebron business-hours/holiday calendar, measuring first substantive human response, not chatbot activity. No first-response pause caused by later student waiting.

## Readiness and handoff

Architecture packet covers documented authorization/cost/data flows; complete slice coverage is blocked until PRD and phase 01 exist. Deployment hostname/provider, actual provider models, legal approvals, source/site registries, scan engine, quota meter, retention and consent-region policy, OAuth/extension credential exchange and measured capacity remain gates. Phase 03 may refine schema/state machines only after reconciling these proposals with the approved baseline and receiving separate phase authorization. No ERD, migrations, app bootstrap or UX phase work is performed here.
