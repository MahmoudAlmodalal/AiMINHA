# Phase 02 architecture decision records

All ADRs are **PROPOSED / ASSUMPTION**, pending approved PRD/phase 01 reconciliation and platform/security/legal validation. Sources A/D/P/U02 are defined in `../architecture/system-overview.md`. Decisions guide bounded documented flows; no FR or implementation approval is invented.

| ADR | Decision |
|---|---|
| [0001](0001-session-cookies-and-csrf.md) | Django-owned same-origin session, secure cookie and CSRF |
| [0002](0002-typed-api-and-versioning.md) | OpenAPI 3.1 REST v1, generated types later, stable errors/idempotency |
| [0003](0003-postgres-jobs-and-reconciliation.md) | Durable PostgreSQL jobs, independent worker, fencing/reconciliation |
| [0004](0004-private-storage-and-ownership.md) | Quarantine, scan, immutable version acceptance, object-scoped capabilities |
| [0005](0005-deployment-separation.md) | Separate frontend/API/worker; hosting eligibility gate |
| [0006](0006-feature-flags-and-cost-gates.md) | Deny-first server flags plus explicit approval and budget policy |
| [0007](0007-observability-and-audit.md) | Redacted metadata telemetry and atomic append-only audit |
