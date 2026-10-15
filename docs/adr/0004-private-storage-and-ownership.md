# ADR 0004 — Private object storage and ownership

Status: DOCUMENTED WORKING DESIGN / ASSUMPTION; reconciled PRD/Phase01/UD-001/002. Traces A; D §أ 6/OQ-007/013 and §د. Context: uploads are untrusted and staff role must not expose student libraries.

Decision: private quarantine and accepted namespaces; immutable object version/hash bind scan to accepted bytes. Server controls keys, capacity reservations and owner relation. Bounded short upload capability; current scanner and quotas required even to initiate. Completion verifies bytes then queues scan; library accepts only exact clean validated version. Scanner outage/rejection never exposes file to converter/AI/preview. Detailed flow in `../architecture/privacy-boundaries.md`.

Owner download or assigned support agent with explicit ticket attachment receives short no-store capability only after current authorization. Staff library requests return 403+audit. Other cross-owner IDs return 404+metadata deny audit. No public buckets, predictable keys, direct generic admin model access or shared file URLs. Legal retention/deletion and quarantine expiration are policy-dependent; proposed temporary 24-hour purge follows D OQ-006 but requires confirmed object deletion to release storage quota.

Consequences: signed URLs have a bearer lifetime and cannot promise instant revocation; choose API streaming if strict immediate revocation required. Storage API must enforce scope/byte bounds/version semantics; if not, bounded streaming quarantine replaces presigning. Provider/region/scanner privacy approval and restore evidence remain EXTERNAL_GATE. Rejected alternatives: public media bucket or local ephemeral application filesystem.
