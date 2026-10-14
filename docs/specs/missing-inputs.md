# Phase 00 missing inputs and gates

Status: **BLOCKED: SOURCE_INCOMPLETE**. Discovery artifacts exist; requirements coverage does not.

| Priority | Missing input / evidence | Trace | Required next action |
|---|---|---|---|
| P0 | Actual approved PRD, referenced v3.0.0, with approval/version context | AGENTS.md §Source hierarchy; S2 header/OQ-024; S3 baseline | Product owner supplies `docs/source/PRD.md` and identifies authoritative version. No substitute fabricated PRD. |
| P0 | Baseline reconciliation against PRD | S2 §§أ–ج; S3 §5 | Once supplied, compare decisions/defaults and resolve conflicts explicitly before full phase 01 baseline. |
| EXTERNAL_GATE | Provider/model/data-class/region approvals, retention/no-training controls and disclosed consent changes | S2 OQ-004/005; S3 §§2,5 | Obtain individual security/contract/legal evidence before private-data AI. Keep it disabled meanwhile. |
| EXTERNAL_GATE | Hosting/commercial-use eligibility and actual $0 resource limits | S2 §هـ/§ز; roadmap release gates | Validate current terms and measured capacity; no provisioning or deployment in phase 00. |
| EXTERNAL_GATE | Privacy, terms, jurisdiction, deletion/restore and retention review | S2 OQ-005/006/020/023 | Obtain approved policies for actual users and processors. Defaults do not close legal gates. |
| EXTERNAL_GATE | Scholarship-source permissions and initial Chrome-site list | S2 OQ-003/015 | Record source/site permissions before ingestion or extension testing against those sites. |
| EXTERNAL_GATE | Working scanner, backup/restore drill, access/security/credit/extension and bilingual quality evidence | S2 OQ-013/018/021 and §§و–ز | Validate later against running code; no current proof exists. |
| Deferred paid release | Payment provider, currency, recipient, refund/dispute/settlement procedures | S2 OQ-001/002 and §د | Leave public payment/checkout disabled in Beta; settle before paid activation. |

## Repository findings, not phase 00 defects

No apps, APIs, dependencies/locks, tests, CI, migrations, environment examples, workers, extension code, storage configuration, or infrastructure exist. Bootstrap is phase 05, not authorized now. Exact package versions/package manager, supported runtime versions, provider model IDs/retry limits and deployment platform remain unspecified or unvalidated; do not invent them.

## Handoff

Provide the approved PRD, update source inventory, and reconcile source authority. Phase 01 (`prompts/01-requirements-and-backlog.md`) then derives a traceable feature matrix, business rules and backlog only under separate phase authorization. Real-user processing and release remain subject to external gates even after source completeness is resolved.
