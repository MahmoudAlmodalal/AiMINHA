# Phase07 — scholarship catalog, sources, moderation and search

The current Phase07 request authorizes this catalog slice and parallel agents.
The user's later explicit instruction authorizes a Git commit/push after completion.
Deployment, paid resources and implementation of later phases remain outside scope.
Existing source files and earlier phase outcomes
remain unchanged. [ADR0011](../adr/0011-catalog-publication.md) records the runtime
choices; the [phase report](../../tasks/phase-reports/07.md) records actual checks
and remaining defects. This specification is not independent release approval.

## Requirement and source traces

`U07.1`–`U07.5` refer to the five work items in the current Phase07 request.
The authoritative feature baseline is [PRD v3.0.0](../source/PRD.md), particularly
the F-03/F-04 definitions, functional requirements, business rules and acceptance
criteria. [Decision resolution](../source/MinhaAI_PRD_Decision_Resolution_AR.md)
§أ2/3 records owner choices; §ج numerical defaults remain analyst proposals.

| Current work | Bounded runtime contract | Trace |
|---|---|---|
| Source registry | Append-only source revisions record source URL, explicit permission status, licensing/use basis, permission evidence, authenticated editor, checked date and validity. New/unverified sources grant no publication or import permission. | U07.1; FR-015/016/021; BR-009; decision §أ2/3, OQ-003; schema-notes R08 |
| Manual first; controlled proposals | Manual creation and revision append immutable candidate facts and exact source-revision/hash provenance. Approved structured import proposals are candidates only; no live adapter, URL retrieval or scraper is enabled. | U07.2; FR-016/017; BR-007/008; AC-006; AGENTS permitted-source/no-auto-publish invariant |
| Review/version/publication | Scoped human review binds an exact candidate version/hash; stale writes fail. Approval/publication and attributable audit commit together. Rejected facts are not silently edited into approval. | U07.2/4; FR-018/020/109/111; BR-007/008; AC-006/007; architecture R08/state machine |
| Public text search/filter/detail | Public reads expose an explicit allowlist of current permitted, human-approved facts. PostgreSQL full-text GIN indexing supports Arabic/English exact lexemes, bounded pagination, public fact filters, stable sort and an explicit empty result. | U07.3/4; FR-021/022/025–027; AC-012; decision OQ-022; NFR-013/016/028 |
| Dates, rounds and unknown facts | Single/multiple/rolling/unknown rounds retain source text, verification state and source timezone where known. Only verified, unambiguous instants qualify as confirmed deadlines; unknown funding/criteria/dates stay unknown. | U07.3/5; FR-022/023/027; BR-006; decision OQ-017, §د stale facts; architecture R18 |
| Negative gate evidence | Synthetic fixtures exercise blocked/unverified sources, draft invisibility, exact-version approval, source expiry/revocation, private-note exclusion and unknown-deadline behavior. Actual command outcomes belong to the phase report. | U07.5/Gate; AC-006/007; NFR-024/026; AGENTS source/privacy invariants |

## Source permission and administration

Registry `permission_status` is `UNVERIFIED`, `APPROVED`, `BLOCKED` or `REVOKED`.
Permission is not inferred from a public URL, robots text, an Admin checkbox or
the existence of scraped text. Publication and acceptance of an import proposal
need their own currently approved use basis. `allow_import` describes permission
to accept an already supplied structured proposal; `automation_enabled` remains
false throughout this phase. No user-supplied URL causes a network request.

`MODERATION` and `SOURCE_APPROVAL` are separate Admin capabilities. Both require
current server-authenticated MFA proof and active identity/session validation;
neither grants access to student private files. A moderator cannot manufacture
source approval. An authorized source approver must record actual permission
evidence; scope possession is not legal permission. No real-source approval is
seeded. Phase06 has no configured live MFA factor backend, so normal privileged
use remains gated; synthetic server-proof fixtures do not add a production bypass.

| Principal | Public approved catalog | Source evidence/revision | Candidate/review/publication |
|---|---|---|---|
| Anonymous or Student | Read current public projection | Denied | Denied |
| Admin without current required MFA/scope | Read current public projection | Denied | Denied |
| Admin with `MODERATION` and current MFA | Read current public projection | Scoped read and unapproved preparation only | Scoped manual proposal/review and guarded exact-version decisions |
| Admin with both `MODERATION` and `SOURCE_APPROVAL` and current MFA | Read current public projection | Record evidenced approved permission revision | Scoped review only; no student-file rights |
| Import/system proposal | No publication right | No approval right | Approved structured proposals enter `DRAFT` only |

Registry internals, license evidence, internal notes and moderation reasons are
protected projections. Public attribution exposes only deliberate public fields,
including the attributable source URL and verification state/date. Source text
and candidate contents are untrusted data, rendered as text rather than HTML or
executable instructions.

## Typed runtime API boundary

All paths below are relative to `/api/v1`. Public routes require no account;
protected routes require current `MODERATION`/MFA, with `SOURCE_APPROVAL` also
required to record approved source permission. Unsafe routes retain CSRF and
`Idempotency-Key`. Source/listing updates require the quoted current revision in
`If-Match`; moderation binds the exact `version_id`. Unknown input properties
cannot grant identity, publication, approval or arbitrary ORM access.

| Method/path | Contract |
|---|---|
| `GET /scholarships` | Public current approved projections; validated `q`, `education_level`, `discipline`, `country`, `language`, `funding`, `deadline_before`, `sort`, `page`, `page_size`, `mode`. Sort is `recent`, `deadline` or `relevance`; implemented mode is `TEXT`. |
| `GET /scholarships/{scholarship_id}` | Public current approved detail; internal notes/evidence/actors excluded. |
| `GET /admin/sources` | Protected source registry/current revision and evidence sufficient for review. |
| `POST /admin/sources` | Create attributable initial source revision; no inferred permission. |
| `POST /admin/sources/{source_id}/versions` | Append source permission/check policy revision with expected current revision. |
| `GET /admin/scholarships` | Protected candidate moderation queue. |
| `POST /admin/scholarships` | Create manual or approved structured-import DRAFT candidate. |
| `GET /admin/scholarships/{scholarship_id}` | Protected version/fact/provenance/history projection for informed exact-version review. |
| `POST /admin/scholarships/{scholarship_id}/versions` | Append immutable replacement candidate and enter REVERIFY. |
| `POST /admin/scholarships/{scholarship_id}/moderation` | Attributable `APPROVE`, `REJECT`, `REVERIFY`, `SUSPEND`, `ARCHIVE` or `RESTORE` command, guarded by current revision and exact selected candidate. |

The generated [runtime OpenAPI](../../packages/contracts/openapi.json) and frontend
types validate these implemented contracts. The earlier architecture OpenAPI is
a broader design record. Runtime field names, offset pages and consolidated
approval/publication are explicit dispositions, not silent claims that every
design route has been implemented.

## Immutable candidates and current publication

An edit appends a full candidate version with provenance and a content hash.
The published pointer is distinct from the latest draft. A review decision binds
the exact version being shown; a concurrent correction or source revision cannot
be silently lost through last-write-wins. Database guards supplement service
authorization and block mutation of immutable evidence and invalid publication.
Audit failure rolls back the sensitive mutation.

The conservative Phase07 update policy removes the current public projection
and marks the listing `REVERIFY` when a replacement candidate is appended.
Previously approved history remains available to authorized review; it is not
returned as current public data while the change awaits human review. This is an
engineering safety choice, stricter than retaining old facts for nonmaterial edits.

Every public list/detail query rechecks the exact sealed source revision against
the current source head, current source permission and its expiry,
current publication state and exact approved version. An old approval or a saved
URL cannot expose a now blocked/revoked/expired source. Reject, suspend, archive
and restoration history remain attributable; restoration requires review rather
than automatic republication. No import or proposed update publishes itself.

## Search and deadline semantics

PostgreSQL `simple` text search is a bounded exact-lexeme baseline for Arabic and
English. It does not claim linguistic stemming, typo correction, semantic search
quality or a measured load target. `SEMANTIC` is explicitly unavailable without
an approved expansion/quality policy. No provider receives public query text.
Personal eligibility and application-state filters depend on Phases08/12 and are
unavailable in this slice; they never become anonymous personalized lookups.

Filters and sort keys are allowlisted and validated; unknown parameters fail
instead of being ignored or passed to arbitrary ORM expressions. Pagination is
bounded and uses a stable secondary identity ordering. Page continuation does
not promise a snapshot across later publication/revocation changes. Unknown or
unverified deadlines do not participate in confirmed-instant comparisons.
Country, discipline and language labels use case-insensitive exact matching, not
inferred taxonomy translation. `deadline_before` includes future confirmed
instants through the selected UTC calendar day. Public reads are bounded to 120
requests per server-observed IP per 15 minutes as an engineering rate limit.

A confirmed deadline needs the original source text, valid IANA donor timezone,
verified status and an ISO datetime that resolves unambiguously to a real instant.
Date-only values, invalid dates, missing/unknown zones, DST gaps and unresolved
folds cannot acquire a fabricated UTC midnight or end-of-day. An explicit offset
on a donor-local value must agree with the named zone. A `Z` suffix explicitly
means an absolute UTC instant; the IANA zone determines its donor-local display.
This canonical response format can be submitted unchanged in a later candidate.
An unknown deadline has no confirmed instant or
reminder eligibility. Rolling/unknown rounds carry those labels rather than a
guessed closing date.

PRD KPI-001 leaves the freshness window/target **TBD**. Neither OQ-022 nor another
owner decision sets a seven-day freshness guarantee. The source's explicit
`freshness_days` is nullable; null means `UNKNOWN`. An approved reviewer can record
a source-specific window from 1 to 365 days (bounded engineering policy range);
only a recorded check within that explicit window means `CURRENT`, otherwise
`STALE`. Show the actual check date. Source expiry and explicit `REVERIFY` are
separate current-permission/publication checks. The UI must not infer fresh facts
from publication time or treat all fields as confirmed because a listing has a
verification label. This metadata creates no reminder schedule.

## Deliberate limits and external gates

- `G-SOURCE`: no actual official-source list, per-source fetch/publication license
  evidence or approved live adapters are supplied. OQ-003's proposed 30 listings
  from ten sources is conditional on lawful availability; synthetic fixtures do
  not satisfy that real-world coverage target.
- `G-MEASURE`: Arabic morphology/semantic quality, realistic 20-concurrent search
  p95 targets, assistive-technology/mobile review and launch usability evidence
  remain independent of passing unit/build/static checks.
- Admin MFA integration and production DB-role/RLS separation retain the Phase06
  external/security gates. Test fixtures cannot approve those integrations.
- FR-019 has a bounded duplicate flag for matching title/provider or exact
  submission URL, without merging or claiming exhaustive fuzzy detection. This
  slice does not implement FR-020 live background monitoring or FR-024 student
  report/case workflow. The source
  registry and immutable review path provide their future boundary. This is partial
  PRD coverage, not completion of all F-03/F-04 requirements.
- Deterministic eligibility/fit belongs to Phase08; saved/application state and
  timed notification scheduling/delivery belong to Phase12. No reminder, inbox,
  provider, credit, upload, private-file or extension workflow is added here.
- `G-LEGAL`, `G-SIGNOFF`, hosting and release approvals stay open. This phase does
  not authorize actual scraping, deployment or paid services. The user's later
  explicit instruction authorizes a Git commit/push after completion only.
