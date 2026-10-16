# Phase 05 — bounded bootstrap

Status: **BLOCKED — POSTGRESQL_RUNTIME_GATE**, 2026-10-15. Bootstrap artifacts are implemented; the acceptance gate remains open. The owner's current Phase 05 request and subsequent “contnue” authorize this implementation. Earlier phase documentation remains a design baseline, not implemented product behavior.

Plan before code: add npm workspaces (`apps/web`, `packages/contracts`), Django/DRF (`apps/api`) with a disabled worker command and inert MV3 extension, local PostgreSQL Compose, placeholder environment template and local secret generation, Make targets, README and baseline CI. Implement only public liveness and safe structured errors. Generate the runtime OpenAPI and TypeScript client, validate drift against the architecture contract, then run PostgreSQL migrations, API tests, lint/type checks, builds and HTTP smoke checks. Update only Phase 05 roadmap state and `tasks/phase-reports/05.md`.

Touched paths: root development configuration/README; `apps/`, `packages/contracts/`, `infra/`, `scripts/`, `tests/`, `.github/workflows/`; this specification, a bootstrap ADR if needed, and Phase 05 tracking/report. Tests cover public liveness, error redaction, CSRF/origin and host restrictions, contract compatibility, database migrations and HTTP startup. No domain models, identities, student data, provider integration or durable job claims.

| Rule | Trace |
|---|---|
| Next.js App Router/TypeScript, Django/DRF modular monolith, PostgreSQL | AGENTS.md Stack; decision resolution §هـ; PRD NFR-022 |
| One browser origin, credentialed CORS disabled, exact CSRF origins | ADR 0001; architecture/api-contracts.md Protocol; PRD NFR-002/004 |
| HTTP cookies allowed only in explicit local mode | ASSUMPTION development exception to ADR 0001; never production configuration |
| Generated runtime schema covers implemented endpoints only | ADR 0002; Phase 05 work item 3; architecture OpenAPI remains the future product baseline |
| Public liveness is a bootstrap addition, not dependency readiness | Phase 05 work item 4; ASSUMPTION path `/api/v1/health` |
| Safe problem+json and correlation IDs; metadata-only logging | architecture/api-contracts.md Protocol; ADR 0007; PRD NFR-023 |
| Placeholder uses Arabic/English language and direction, existing design tokens | PRD NFR-013–015; specs/design-system.md Foundations |
| No identity/auth models until Phase 06; only Django sessions migration | Phase boundary; architecture/migration-sequencing.md M01; avoids prematurely fixing a user model |
| Worker and extension are inert; no payments, AI, uploads or imports | Phase 05 boundary; ADR 0003; decision resolution §أ 1/2/4/5; PRD FR-050/065 |

EXTERNAL_GATE: actual hosting, provider/model/data/region, legal/privacy/retention, source/site permissions, scanning, backups/restore, measured quality/free quotas and release signoff remain unresolved. This phase uses local generated credentials and no real student data. Missing Docker or other tooling must be reported; no SQLite substitution may claim PostgreSQL proof.

Acceptance evidence: 19 database-independent API/security/contract tests and five client tests pass; lint, mypy, frontend/client type checks, schema generation/drift and the Next production build pass. Real HTTP liveness proves API forwarding, CSRF denial, both language directions and safe 404 handling. Full checks fail at two PostgreSQL tests. Docker is absent; native PostgreSQL 16.15 initialization fails on host System V shared memory with `shmget` EIO, including an mmap retry. Migrations and the worker database preflight remain unverified. See [exact commands and handoff](../../tasks/phase-reports/05.md). No full clean-clone/database boot or remote CI success is claimed.
