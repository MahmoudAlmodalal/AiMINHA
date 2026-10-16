# ADR 0011 — permission-bound catalog publication

Status: Phase07 runtime decision for local/synthetic verification, 2026-10-16.
Authority: current Phase07 request; AGENTS source/no-auto-publication invariants;
PRD FR-015–027/109/111, BR-007–010, AC-006–008/012; decision resolution §أ2/3,
OQ-003/OQ-017/OQ-022 and §د; architecture domain contracts/schema-notes R08.
Actual verification evidence is in [report07](../../tasks/phase-reports/07.md).

Use append-only source revisions and scholarship candidate versions. A source
revision records explicit permission state, public source URL, licensing/use basis,
permission evidence, checker and date/validity. Missing or unverified permission
denies publication and import. `MODERATION` cannot approve its own legal basis;
recording an `APPROVED` source revision requires separately scoped `SOURCE_APPROVAL` with current
server MFA and recorded evidence. Neither scope confers access to student files.

Manual entry is the first supported path. `allow_import` permits an already
supplied structured proposal from an individually approved source; every accepted
proposal starts as `DRAFT`. No HTTP fetching, crawler or monitor is enabled and
`automation_enabled` is always false. No real-source permissions or public facts
are fabricated to populate the catalog. Network access is not implied by a source
URL. A future adapter needs its own source/URL/redirect/network validation and
operational approval; it cannot bypass the same draft and review boundary.

Candidate facts, rounds and provenance are immutable and hashed. Human review
binds the exact candidate version/hash and current source revision. Publish uses
expected aggregate version and rechecks permissions under locks; approval/audit
and pointer change are atomic. Database guards reinforce immutable evidence and
publication consistency. Ordinary draft writers, imports and UI fields cannot
assert an approved or published state.

Appending a replacement candidate conservatively withdraws public visibility to
`REVERIFY` pending review, even for an edit not yet classified as material. This
ASSUMPTION favors preventing reliance on uncertain facts over retaining visibility
of the prior approved snapshot. Historic approvals remain immutable. Restoration
returns to review rather than silently republishing a previous version.

Public list/detail reads project explicit public fields and recheck the current
source state/expiry and exact source-revision binding as well as current
exact-version human approval and visibility. A replacement permission snapshot
withdraws old public facts until a replacement candidate is reviewed.
No historic approval permits continued public exposure after source permission
is blocked, revoked or expires. Internal notes, permission evidence, editor
identities and moderation reasons never enter the public projection or its index.

Use PostgreSQL full-text search with a GIN index and the `simple` configuration for
bounded Arabic/English exact lexemes, validated public filters and stable bounded
pagination. This does not claim linguistic stemming or semantic quality. Semantic
mode fails explicitly unavailable without an approved policy; no AI egress occurs.
Personal eligibility/application-state filters await Phases08/12.

Only source-verified, timezone-valid and unambiguous datetimes become confirmed
deadline instants. Preserve original source text and known IANA timezone; date-only,
unknown-zone, invalid and unresolved DST inputs are rejected as confirmed facts
and must be entered explicitly as unknown instead of acquiring
a guessed instant. Explicit `Z` values represent absolute UTC instants with the
source IANA zone retained for display; donor-local offsets must agree with that
zone. Exact date/funding/criteria uncertainty stays visible. No
notification rows or timed deliveries are implemented by this phase. PRD KPI-001's
freshness window is TBD; an unspecified policy is unknown freshness, not an
invented seven-day rule. Source revisions may record an explicit `freshness_days`
window (nullable by default, bounded to 1–365 as an engineering range). The actual
check and that policy determine CURRENT/STALE; null means UNKNOWN. Source expiry
is an independent permission check.

Runtime pagination uses bounded `page`/`page_size` with stable secondary identity
ordering, rather than implementing the design's opaque cursor. Changes between
requests can shift offset pages; no database snapshot or duplicate-free traversal
across concurrent updates is promised. Runtime public filter names and sort enums
are explicit in the generated schema. Approval/publication is one guarded
moderation command: exact-version human APPROVE inserts evidence and atomically
moves the public pointer only when all current permission/CAS checks pass. There
is no separate less-restricted publish route. These bounded runtime choices are
recorded as C07-07/08 without modifying the earlier design sources.

Add typed protected registry/candidate/evidence reads sufficient for informed
moderation; this fills the catalog fact/diff portion of UX-API-02; a full source-history browsing API is not added. Generated
runtime OpenAPI remains the implementation contract. Historical architecture
OpenAPI and Phase04 specifications remain preserved design records. See the
[Phase07 scope](../specs/phase-07-catalog.md) and [conflict register](../specs/requirements-conflicts.md).

No live MFA, real source/legal approval, production RLS certification, load/semantic
quality, monitoring, duplicate merge, student report workflow or general release
readiness is inferred. Those independent gates and later phases remain explicit.


A Phase07 integration run reproduced the earlier intermittent HTML500 at the Next
rewrite boundary with upstream ECONNRESET, without a Django application exception.
Local Make/dev/smoke commands use Django --nothreading so responses explicitly
close upstream connections; the catalog smoke verifies that header and50 serial
requests. This bounded local workaround does not configure a production server,
certify concurrent HTTP performance or claim a complete upstream defect diagnosis.
See report07 for the failed first run and successful subsequent checks.
