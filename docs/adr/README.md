# Phase 02 architecture decision records

ADRs are **DOCUMENTED WORKING DESIGN / ASSUMPTION**, reconciled to the supplied PRD/Phase01/UD-001/002; runtime/platform/security/legal validation and release signoff remain independent gates. Sources A/D/P/U02 are defined in `../architecture/system-overview.md`. Decisions guide bounded documented flows; no FR or implementation approval is invented.

| ADR | Decision |
|---|---|
| [0001](0001-session-cookies-and-csrf.md) | Django-owned same-origin session, secure cookie and CSRF |
| [0002](0002-typed-api-and-versioning.md) | OpenAPI 3.1 REST v1, generated types later, stable errors/idempotency |
| [0003](0003-postgres-jobs-and-reconciliation.md) | Durable PostgreSQL jobs, independent worker, fencing/reconciliation |
| [0004](0004-private-storage-and-ownership.md) | Quarantine, scan, immutable version acceptance, object-scoped capabilities |
| [0005](0005-deployment-separation.md) | Separate frontend/API/worker; hosting eligibility gate |
| [0006](0006-feature-flags-and-cost-gates.md) | Deny-first server flags plus explicit approval and budget policy |
| [0007](0007-observability-and-audit.md) | Redacted metadata telemetry and atomic append-only audit |
| [0008](0008-configurable-recovery-period.md) | Admin-configurable calendar recovery, immutable per-request deadline and prospective audited policy changes |

## Phase 05 bootstrap decision

[0009 — implemented runtime schema](0009-bootstrap-runtime-contract.md) records the owner-confirmed runtime subset and architecture compatibility checks. Prior architecture decisions remain design guidance; this phase implements only the bootstrap surface.

## Phase06 identity and privacy decision

[0010 — identity/privacy boundaries](0010-identity-privacy-boundaries.md) records
the implemented local auth/consent/ownership/lifecycle slice, current UTC boundary
instruction, retained Admin duration control and explicit external/integration gates.

## Phase07 catalog publication decision

[0011 — permission-bound catalog publication](0011-catalog-publication.md) records
manual-first immutable candidates, independently evidenced source permissions,
exact-version human approval, current-permission public reads and explicit
search/deadline limits. No live source adapter or real-source approval is inferred.

## Phase08 eligibility decision

[0012 — evidence-bound deterministic eligibility](0012-evidence-bound-eligibility.md)
records immutable student-confirmed profile facts, exact-version human-reviewed
rules, mandatory-failure precedence, unknown-safe comparisons and the initial
coverage-gated deterministic fit formula. Credential authenticity, grading
equivalence, quality calibration and performance certification remain separate.
