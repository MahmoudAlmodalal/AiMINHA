# Phase06 — identity, permissions, consent and lifecycle

Only Phase06 is authorized. The existing Next/Django/Postgres baseline and
authoritative sources are adapted in place. No catalog, credits, provider AI,
upload/scan, support workflow, extension or deployment implementation follows.

| Required work | Runtime implementation | Requirement trace |
|---|---|---|
| Signup/login/email ownership, DOB18+, leap edge | `identity` Account, password validation, digest challenges, expiry/throttling/idempotency, cookie session tracking; private local mail/optional SMTP | U06.1; PRD FR-001/002/004/006; identity contract; ADR0001 |
| Optional unique Google link | PKCE/state/nonce and verified OIDC tokens; unique provider subject; recent account proof; no email merge or new-user activation | U06.1; PRD FR-003; decision §أ5; identity contract |
| Denied default/role/ownership | Core default deny preserved; identity authentication/verified adult guards; scoped MFA Admin guard; owner-filtered queries | U06.2; AGENTS security; PRD NFR-003/007 |
| Public browse boundary | `PublicCatalogRead` permits safe methods without account; actual published scholarship data/API remains Phase07 | U06.2; decision OQ-022; no invented catalog |
| Versioned purpose-specific consent | Immutable disclosures/events, consent head revision, If-Match, stale-capture/revocation checks; no provider approval inferred | U06.3; FR-012/113; decision §أ5/OQ-004 |
| Delete/restore and queue | Policy snapshot, impact review, short-lived reauth, all-session invalidation, one-use independent recovery proof, strict UTC cutoff, serialized safe queue | U06.3; FR-116–120; UD-001; OQ-006/020; ADR0010/C06-01 |
| Admin file denial, exact ticket shares | Student-owned metadata projections; staff library403; assigned exact share+MFA+scope; revoke/reassign/lifecycle checks | U06.4; decision §أ6/OQ-007; FR-110 |
| Backend/UI/tests/audit | Identity/privacy migrations, typed runtime API/client, bilingual account forms, privacy audit with SQL guards, DB and HTTP adversarial tests | U06.5/Gate; NFR-013/015/023/024 |

Permission matrix:

| Actor | Auth/public boundaries | Personal/library | Ticket exact shared metadata | Policy service |
|---|---|---|---|---|
| Anonymous | CSRF/auth entry; future safe published browse |401 |401 | denied |
| Pending/unverified/under18/suspended/deletion-pending | Limited verification/recovery only; ordinary login denied | denied | denied | denied |
| Verified active adult Student | Session + own commands | Own only; foreign/missing403 | Share/revoke own accepted asset; no staff read authority | denied |
| Admin without current scope/MFA | Identity pre-auth/session/logout/security flows | Always403 |403 | denied |
| Admin with current server scope/MFA | Scoped operational proof only | Always403 | Only current assigned exact owner share, accepted asset, active owner | Scoped, approved-envelope, expected-version service only |

Implemented metadata endpoints do not implement file upload, object download,
ticket creation/assignment or a staff UI. Default retention has no approved legal
envelope. No fabricated privacy notice/provider/retention approval is seeded.
Google-only signup, real email/OAuth/MFA integration, object erasure/backups,
full RLS under separate production roles, browser accessibility certification
and deployment remain explicitly unverified/gated. See [ADR0010](../adr/0010-identity-privacy-boundaries.md)
and [Phase06 evidence](../../tasks/phase-reports/06.md).
