# Phase 03 — guarded state machines

Date: 2026-10-15 UTC. **PASS — documented state/ownership design**, reconciled to the supplied PRD, Phase01/02 and UD-001/002. Engineering transition refinements remain assumptions; runtime and release gates are separate. Tables below are exhaustive allowed edges for this design; **all unlisted edges are rejected by database transition guards**, including direct staff/AI writes. Same-state retries return the prior result only through an idempotent command; they do not append another event, allocation, grant or debit. Status strings below require CHECK/enum constraints, not arbitrary VARCHAR values.

Traces and engineering-assumption convention: [schema notes](schema-notes.md). D denotes the [decision record](../source/MinhaAI_PRD_Decision_Resolution_AR.md); P the [provider strategy](../source/ai-provider-strategy.md). Exact transition matrices refine D defaults as ASSUMPTION; the supplied [PRD](../source/PRD.md) is traced for this phase with completed Phase01 traceability under UD-002. PRD formal roles are Student/Admin; human support is an Admin capability, not a third role. All dates are UTC instants unless a named business calendar/local day applies. [ERD](erd.dbml) stores heads and append-only evidence; [migration sequencing](migration-sequencing.md) lists future implementation proofs.

## AI operation billing

Trace: D §أ 7, §ب Credit result/outstanding reservation, OQ-016, §د snapshots/revocation, §و 1/2/5; P §2.6; B02. State meanings:

| State | Meaning and accounting |
|---|---|
| RESERVED | Admission committed: frozen input/price, one hold, logical/support slot and job. No debit/result. |
| RUNNING | Fenced worker owns execution; hold remains. No debit/result before atomic acceptance. |
| RECONCILING | Outcome, authorization or persistence unresolved; retain hold, stop new generation until proved safe. Age alone does not resolve it. |
| SETTLED | Exactly one validated saved accepted result and one terminal witness; one debit if price >0, none for explicitly free AI. Terminal. |
| RELEASED | Proven terminal no-acceptance outcome; one release witness, no accepted result/debit. Hold removed once. Terminal. |

| From → to | Authorized trigger | Guard / atomic effects |
|---|---|---|
| absent → RESERVED | Verified adult owner's request via domain routine | R06/R07/R10/R11/R13: current permissions/consent/approval/free route; server quote; request uniqueness; sufficient wallet + student/global/support limits; insert operation/hold/job/audit/outbox together. |
| RESERVED → RUNNING | Current fenced worker claims AI job | Current lifecycle/policy, unexpired authority and nonterminal operation; no already unresolved/successful call that would cause another generation. No debit. |
| RESERVED → RELEASED | Cancellation or admission dependency failure after reservation, proved unsent | No dispatch intent/accepted result; terminal evidence; remove active hold/day spend reservation once, keep logical/support admissions. |
| RESERVED → RECONCILING | Reservation expires or uncertain job/cancellation evidence | 15 minutes is sourced default investigation threshold; no refund or new call. |
| RUNNING → RECONCILING | Unknown send, lost fence after possible send, acceptance/storage conflict, revocation, deletion or 15-minute expiry | Record reason/evidence, retain hold and unknown physical allocation; reject stale worker writes. |
| RUNNING → SETTLED | Fenced validator/finalizer | Current lifecycle/consent/processor approval; correct immutable snapshots; accepted output + document if applicable + exact one debit/witness + counters/job/audit/outbox atomically (R14). |
| RUNNING → RELEASED | Proven terminal failure/rejected validation and no uncertain other attempt | No accepted result; terminal no-acceptance proof; remove hold once, no positive journal refund; physical consumed usage stays consumed. |
| RECONCILING → RUNNING | Scoped recovery routine with current fenced recovery job | Authoritative proof all previous attempts did not execute and a bounded retry is eligible; same snapshots/price/operation and captured logical days, current gates and new physical allowance. No retry of security/consent/content refusal. |
| RECONCILING → SETTLED | Scoped recovery validator/finalizer | Recoverable valid output, current consent/account/approval and live recovery fence; same one-result/debit transaction as RUNNING settlement. Operator may not browse private output. |
| RECONCILING → RELEASED | Recovery routine with proved terminal no-acceptance outcome | No pending uncertain generation that may still be accepted, no result/debit; bounded hold release + evidence once. |

SETTLED/RELEASED have **no outgoing edges**. Same operation cannot have both outcomes because `operation_finalizations` has one PK and commit-time trigger equivalence to operation state/result/debit. RECONCILING is not a billing failure or an automatic refund. 24-hour target creates an alert, not an unconditional transition. Manually deciding “refund” cannot bypass proof; a post-settlement authorized correction uses a compensating journal entry and leaves SETTLED intact.

A worker crash after a response but before acceptance leaves no debit/result. A crash after commit replays the existing settled result. A late response after release cannot create a document or debit. Output schema success alone is insufficient: unsupported academic facts fail validation. Free re-export/manual edit uses no new AI operation; new AI content requires a new authorized operation and quote.

## Wallet lifecycle and irreversible deletion

PRD FR-076–079, BR-028/048–050 and AC-024/025/037–039: active Credits never expire merely with time. ACTIVE→deletion-pending freezes the existing wallet through account authorization; restore before approved cutoff unfreezes the same wallet without a grant. Final purge cancels all remaining posted Credits with one immutable DELETION_CANCEL journal entry only after uncertain holds are resolved, including a zero cancellation marker when balance is already zero. Its unique owner index and deferred zero-wallet invariant prevent duplicate cancellation or resurrection. DELETED has no restore/spend/grant path. Technical-failure release is still a hold removal, never this cancellation or an extra positive refund. Approved compensating reversals retain SETTLED and require separate bounded human workflow.

## Provider calls, budgets and recoverable jobs

Trace: P §§2/4/5, D §ب/§هـ; B02 proposed retry/fencing mechanism. These states are separate from billing.

| AI call edge | Evidence / rule |
|---|---|
| absent → PLANNED | Current operation/fence and retry allowance; approval/classification checked; prior calls all proved KNOWN_FAILED with retryable not-executed evidence, or this is first call. |
| PLANNED → DISPATCH_INTENT | R12 authorization linearization point; allocate all physical budgets and persist exact approval/input hash/fence before network. |
| PLANNED → KNOWN_FAILED | Proved no dispatch, e.g. pre-send current policy/budget refusal; no fallback that bypasses refusal. |
| DISPATCH_INTENT → SUCCEEDED | Authenticated response safely received; validation/persistence still pending, no billing implication. |
| DISPATCH_INTENT → KNOWN_FAILED | Authoritative terminal response/evidence. A retry additionally needs proof of non-execution and retriable reason. |
| DISPATCH_INTENT → UNKNOWN | Timeout/disconnect/crash/lease ambiguity; do not resend. |
| UNKNOWN → SUCCEEDED | Verified recoverable response/status for the same attempt. |
| UNKNOWN → KNOWN_FAILED | Authoritative terminal evidence, not a timer or guessed telemetry. |

SUCCEEDED and KNOWN_FAILED calls are immutable terminal evidence. Invalid content after SUCCEEDED releases/reconciles the **operation**; it does not rewrite transport success or reroute validation refusal. Each new permitted attempt gets a new call ID and sequential number, preserving operation ID. No simultaneous unresolved calls; a previous SUCCEEDED response also blocks another generation. No provider exactly-once guarantee is inferred from a local request UUID.

| Provider allocation edge | Required rule |
|---|---|
| absent → RESERVED | Atomic conservative maximum in each relevant actual provider window; all current caps pass. |
| RESERVED → MEASURED | Authoritative usage evidence, `0 <= measured <= reserved`; convert measured to consumed, return proven unused units. If an estimate is exceeded, stop dispatch and reconcile the metering defect; never hide actual usage. |
| RESERVED → UNKNOWN | Possible dispatch without reliable usage; retain full allowance. |
| RESERVED → RELEASED | Proof request was not sent/consumed; remove allowance once. |
| UNKNOWN → MEASURED / RELEASED | Authoritative usage/no-usage/reset evidence only; append audit. Reset does not manufacture proof of original result failure. |

MEASURED/RELEASED are terminal allocations. Student credit release is independent of provider usage. Every physical retry/fallback counts; every logical operation counts once at admission, including free support. Calendar/policy edits cannot reset either counter.

| Job edge | Rule |
|---|---|
| absent → QUEUED | Durable typed target, request hash and unique dedupe key in initiating transaction. |
| QUEUED / RETRY_WAIT → LEASED | Due, current resource authorization, short SKIP LOCKED claim; increment fence and set lease. |
| LEASED → SUCCEEDED | Current fence; handler's entire effect/audit/outbox committed. |
| LEASED → RETRY_WAIT | Proved safe replay, bounded retry/backoff; no possibly sent AI generation. |
| LEASED → RECONCILING | Lease loss/unknown external side effect; fence old worker, no blind replay. |
| LEASED → DEAD | Known terminal non-success with appropriate operation release/reconciliation, never automatic ledger edit. |
| QUEUED / RETRY_WAIT → DEAD | Current lifecycle/dependency permanently denies handler; prove unsent AI before release, otherwise reconcile. |
| RECONCILING → RETRY_WAIT | Proven safe resumable work; AI additionally satisfies RECONCILING→RUNNING authorization when claimed. |
| RECONCILING → SUCCEEDED / DEAD | Recovery finalizer commits proved effect or terminal no-effect with current recovery fence. |

For expired LEASED jobs, the recovery routine may move to RETRY_WAIT only with proof no possible external send/effect occurred; otherwise RECONCILING. Finite lease expiry is a signal, not proof of non-execution. DEAD/SUCCEEDED are terminal. A reconciliation handler is itself a distinct scoped recovery job; it cannot reuse a dead worker token. Repeated delivery acknowledges an already committed effect without changing SUCCEEDED.

## Account, verification and consent

Trace: D OQ-006/020/022, §د DOB/revocation; A. Staff provisioning is independently scoped; it does not grant student-feature access.

| Edge | Guard / effect |
|---|---|
| absent → PENDING user | Canonical identity uniqueness, explicit DOB, no private protected work yet. Signup/identity endpoints remain unspecified. |
| PENDING → ACTIVE | Verified email + approved 18+ check; R06 unique grant/wallet/audit atomically. Google link never triggers grant again. |
| PENDING / ACTIVE → DELETION_PENDING | Authenticated confirmed deletion; one pending deletion request; revoke sessions/shares/new jobs/downloads immediately; record immutable cutoff. |
| DELETION_PENDING → ACTIVE | Previously activated account only, verified restore received strictly before stored approved `restore_until` and not PURGING; recheck access/adult policy; restore original versions, no grant. |
| DELETION_PENDING → PENDING | Previously unactivated account under same restore gate; no accidental activation or grant. |
| DELETION_PENDING → PURGING | At/after the stored approved `restore_until`, locked purge claim wins; use captured Admin policy/ADR0008, not today's setting; no future restore. |
| PURGING → DELETED | Approved erasure completed/receipts and accounting reconciled; exactly one DELETION_CANCEL entry cancels remaining balance (zero marker allowed), no active holds, wallet zero; backup erasure replay recorded. No direct DELETED→ACTIVE. |

Deletion request states mirror PENDING→RESTORED or PENDING→PURGING→PURGED; no other edge. `prior_user_state` on the deletion request preserves the pre-deletion state (never inferred from grant alone). An exactly-at-cutoff restore fails under the proposed D OQ-020 boundary. UD-001 makes duration Admin-configurable. ADR0008 defines the proposed calendar-day/zone/DST algorithm (default 30/Asia-Hebron); capture positive recovery_days, zone, algorithm, policy and restore_until once. A later Admin change never alters that request. Legal-envelope/DST runtime validation remains required; no unconditional 720-hour rule or claimed legal approval. Concurrent restore/purge lock the same user/request; a trusted pre-cutoff receipt is required, client clocks are irrelevant. Consent/lifecycle revocation is not a refund instruction for uncertain sent tasks.

Verification challenge: issued unconsumed → consumed exactly once, conditional on purpose/account/expiry; expired challenges cannot be consumed. Reissue creates a new token/challenge, not resetting a used row. Consent: absent→GRANTED version; GRANTED→new REVOKED or new GRANTED disclosure/envelope version; REVOKED→new explicitly GRANTED version. Old consent rows are immutable. Every grant/revocation CAS-updates the head/audit/outbox. Consent revocation denies new dispatch intents and acceptance; already-in-flight data follows recorded processor policy, no recall promise.

## Scholarship version and publication

Trace: D §أ 2/3, OQ-003, §د stale facts; A.

| Derived version state / visibility edge | Guard |
|---|---|
| absent → DRAFT version | Permitted manual/automated source, new immutable version identity; not public. |
| DRAFT → IN_REVIEW | REVIEW_REQUESTED event seals facts/criteria/provenance; subsequent fact edits require a new version. |
| IN_REVIEW → APPROVED / REJECTED | Scoped human moderation with exact content hash, source permissions and evidence; append event. |
| APPROVED → public head | Guarded publication with expected scholarship row version; audit/outbox atomically; auto-import/AI cannot invoke. |
| UNPUBLISHED → PUBLIC | Approved head plus valid publication evidence/permissions. |
| PUBLIC → REVERIFY / SUSPENDED / ARCHIVED | Uncertain material facts, permission revocation, misleading content risk or scoped archival. Timed reminders suppressed. |
| REVERIFY → PUBLIC / SUSPENDED / ARCHIVED | Reverified same facts or newly approved version; unknown deadlines never regain timed reminders. |
| SUSPENDED → REVERIFY / ARCHIVED | Evidence review, no automatic republication. |
| ARCHIVED → REVERIFY | Explicit restoration review; never silently public. |

Changing a public head always requires a newly approved exact version, even while visibility stays PUBLIC. REJECTED/APPROVED payloads do not change; APPROVED may acquire a SUSPENDED event to withdraw current visibility, never erasing past approval. No direct rejected→approved without a new review/version. Historical version access for a previously accepted task is owner-scoped, not public catalog exposure.

## Files and documents

Trace: D OQ-006/013/016, §د export/frozen documents; A; B02 quarantine/storage proposal.

| File edge | Guard / capacity effect |
|---|---|
| absent → INITIATED | Owner, healthy scanner, private bounded immutable key capability, format/size declaration and reserved owner/global capacity. |
| INITIATED → QUARANTINED | Server verifies stored exact object/version/hash and declared=actual bytes for uploads (actual<=reserved bound for system artifacts); transfer reserved to retained capacity once. |
| INITIATED → PURGE_PENDING | Expired/abandoned/mismatch; potential existing object remains counted until confirmed cleanup. |
| QUARANTINED → SCANNING | Current fenced scan job on exact immutable bytes; no read/AI/preview. |
| SCANNING → ACCEPTED | Exact version/hash CLEAN malware and MIME/content/size validation, scanner evidence; acceptance transaction. |
| SCANNING → QUARANTINED | Scanner unavailable/transient error, bounded safe rescan; unreadable. |
| QUARANTINED / SCANNING → REJECTED | Proved invalid/malicious input; no acceptance, schedule cleanup. |
| ACCEPTED → PURGE_PENDING | Authorized lifecycle/retention erasure; hide/revoke capabilities immediately; pinned lawful-history references handled under approved policy. |
| QUARANTINED / SCANNING / REJECTED → PURGE_PENDING | Expiry/rejection/deletion; deny all content access. |
| PURGE_PENDING → PURGED | Exact-object confirmed deletion/approved nonexistent receipt, decrement capacity once; no resurrection. |

An ACCEPTED asset never returns to SCANNING with different bytes. New bytes → new asset. Unknown object deletion retains capacity. Soft-deleted library/document rows are hidden, and a reversible content request may retain accepted bytes during approved grace; once PURGE_PENDING is claimed, ordinary restore cannot resurrect that object. Account restore must explicitly report already-purged content rather than fabricate it. Strict immediate URL revocation needs streaming; signed URLs expire per B02.

Documents use immutable content versions plus exact-version student approval records (PRD FR-039/040). An unapproved draft can be reviewed/edited; an explicit owner action inserts one approval bound to that version/hash. AI technical validation/settlement cannot supply this approval. Only approved versions can be exported, marked ready or submitted; an edit creates a new version needing its own approval. Manual save appends a version and CAS-moves head, free of AI charge. Restore appends a new numbered version with earlier `restored_from_version`, preserves language/content lineage and old versions, and never copies old approval implicitly (FR-047/BR-018). Generated save appends a version only in operation SETTLED transaction. Draft/submitted application status never changes a version's content. Re-export uses `(document,version,format,renderer_version)` dedupe, new accepted file if needed, no generation debit. Legal erasure is the only controlled payload destruction path, and never converts a frozen version back into an editable version.

## Applications and corrections

Trace: D OQ-014 and §و 7. These are **student-reported tracking states**, never platform or extension submission of an external form.

| From | Allowed next states | Guard |
|---|---|---|
| absent | PREPARING | New owned scholarship/round, sequence 1 and initial snapshots atomically. |
| PREPARING | READY, WITHDRAWN | Ready requires policy-defined completeness and valid owned document versions; exact checklist MISSING, so cannot assert ready without it. |
| READY | PREPARING, SUBMITTED, WITHDRAWN | Back to Preparing is proposed pre-submission correction. Submitted requires explicit student report and immutable manifest snapshot. |
| SUBMITTED | UNDER_REVIEW, ACCEPTED, REJECTED, WITHDRAWN | Direct outcome permits student to report a known decision without inventing intermediate official evidence; an ASSUMPTION for review. Frozen submission unchanged. |
| UNDER_REVIEW | ACCEPTED, REJECTED, WITHDRAWN | Student evidence/source attribution; no AI promotion. |
| ACCEPTED | none | New round → new application; evidence corrections below. |
| REJECTED | none | Same. |
| WITHDRAWN | none | Same. |

Checklist states MISSING→IN_PROGRESS→COMPLETE (and pre-submission corrections back to incomplete) are proposed guarded readiness states. COMPLETE requires known versioned requirement evidence and an approved document version/accepted upload or explicit owner action confirmation as appropriate; unknown requirements remain incomplete. Freeze selected manifests on submission.

Each edge is append event + head/state CAS under lock, with prior state, actor/source/evidence and pinned profile/scholarship versions. `READY→PREPARING` cannot occur after submission; normal back edges from Submitted/terminal are denied. No reset/reuse of a round by soft deleting its application.

Notes/checklist-only activity may append a self-edge with preserved notes snapshot and a fixed activity reason; it cannot change status or frozen artifacts. Evidence-only correction appends a self-edge event with an earlier `correction_of_sequence`, nonempty evidence and reason; all previous events and manifests remain. A correction that also changes status must satisfy the ordinary matrix. A requested terminal/backward status correction is unresolved product policy and is rejected until specified. Distinct future official reports must retain their own source and the student's earlier assertion, never overwrite it. No future integration is enabled here.

Submitted content is `application_event_documents` for the pinned submission event: each slot has exactly one approved document-version reference or exact accepted upload reference, with matching hash. It never resolves through current document head or an editable draft manifest. Concurrent document editing creates a new version; it cannot change submitted hashes. A submitted-manifest correction appends another evidenced manifest and preserves the original; no UPDATE/DELETE by student/staff. Approved lawful erasure remains possible under R21.

## Deadline notification

Trace: D OQ-017, §و 6; schema R18.

Confirmed deadline revision creation requires donor source zone and verified unambiguous instant. Unknown/unverified date → no timed schedule. New confirmed/unknown/cancelled version replaces event head and cancels pending old-version reminders. A historical CONFIRMED row remains immutable; its superseded status is derived from current head.

| Edge | Guard |
|---|---|
| absent → SCHEDULED | Current confirmed published event, active adult recipient and owned save/application relationship; supported offset; future due time; unique owner/event-version/offset. |
| SCHEDULED → DELIVERED | Recheck current event/permissions/recipient/relationship, commit one internal inbox effect and delivered marker with job/outbox. |
| SCHEDULED → CANCELLED | New/unknown date version, withdrawn permission, loss of relationship or lifecycle denial; no fabricated date. |

DELIVERED/CANCELLED are terminal; `read_at` on the single linked `in_app_notifications` row is a once-set acknowledgment, not another delivery. Source/checklist/document/Credit/support events use the same inbox with stable event/version/category dedupe and exactly one typed authorized destination; optional preferences never suppress mandatory account/security events (FR-089–093). Retry same scheduled version resolves to existing notification. Exact DST offset interpretation is proposed in R18 and needs product confirmation; source instant is never guessed.

## Tickets, SLA, ratings and attachment sharing

Trace: D OQ-007–010/019; §أ 6; A. The six states are required by PRD FR-099/BR-040; edge details remain a proposed workflow reviewed against D OQ-008–010.

| From | Allowed next states | Guard |
|---|---|---|
| absent | NEW | Active verified adult owner creates ticket/category and initial event. |
| NEW | AI_HANDLING, AWAITING_ADMIN, RESOLVED | AI path only if current consent/approval/budgets allow; explicit human request/refusal/unavailability goes to Admin queue. Resolution requires owner acknowledgment or assigned Admin. |
| AI_HANDLING | AWAITING_ADMIN, RESOLVED | Human handoff on request/low confidence/repeated failures/financial-security/critical-deadline issue; no AI financial action. Resolution needs owner confirmation. |
| AWAITING_ADMIN | AWAITING_STUDENT, RESOLVED | Assigned MFA-verified scoped Admin reply/action or owner's acknowledged resolution. AI/auto-ack cannot stop human SLA. |
| AWAITING_STUDENT | AWAITING_ADMIN, RESOLVED | Owner reply resumes human queue, or owner/assigned Admin resolves; current SLA not paused by status. |
| RESOLVED | AWAITING_ADMIN, CLOSED | Owner objection resumes human help; otherwise close only after >=7×24h with no objection under the sourced default policy. |
| CLOSED | AWAITING_ADMIN | Owner reopening request strictly before closed_at+14×24h under sourced default; proposed new SLA cycle at human request. |

An assigned Admin classification-only change is an explicit same-state history event with reason/before-after audit, not a hidden status transition or replay; existing SLA policy remains pinned. All other edges denied; after reopen deadline create a linked new ticket workflow only once separately specified (not fabricated here). Close/reopen timers compare trusted UTC instants. Concurrent objection and automatic closure serialize on ticket/head; a valid objection wins if committed before close, otherwise current reopen rule applies.

SLA cycle: absent → ACTIVE at request/transfer to humans; ACTIVE → FIRST_HUMAN_RESPONDED at first assigned substantive human message. Once stopped, immutable. Calendar-only business-time integration (Sun–Thu 09–17 Asia/Hebron with versioned holidays); AI, auto-ack, off-hours, later waiting-for-student and status changes do not satisfy first response or introduce a manual pause. Human hours and critical/high/normal/low targets are D defaults, not an operational promise. WARNING/BREACH/ESCALATION SLA events are append-only and deduplicated per cycle/type/configured threshold; absent warning offsets/route policy disables that automation rather than inventing numbers (FR-103). AI escalation triggers request/two consecutive failures/uncertainty/financial-security topic or a critical approaching verified deadline (threshold/routing policy still TBD), with no direct account/credit changes.

Attachment share: absent → ACTIVE only by owner explicit action on accepted owned asset/ticket; ACTIVE → REVOKED by owner/lifecycle/approved retention. REVOKED is terminal for that share row; explicit owner re-share inserts a fresh row/evidence through an audited guarded command. A partial UNIQUE prevents two active shares of the same ticket/asset while preserving revoked rows. Assignment: absent → ACTIVE by scoped assignment command; ACTIVE → ENDED; reassignment ends old row and inserts new under ticket lock. Every read rechecks current assignment/share/scope and writes audit; no library permission flows through this graph.

Rating: absent → RECORDED once; RECORDED → updated value only before original first_rated_at+7×24h with audit. Editing does not restart window. Scale/eligible ticket state are MISSING: rating creation disabled until resolved; do not invent five-star semantics.

## Concurrency and commit rules

Schema R10–R15/R22 are mandatory companions to these matrices: conditional updates alone are insufficient. Frozen fields cannot be edited to create an apparently legal transition. Domain writers have no general table DML; guarded commands + immediate transition checks and deferred final-state constraints enforce edges. Lock order, idempotency, stable operation IDs, partial UNIQUE indexes, fencing and terminal witness equivalence mechanically prevent duplicate effects in the proposed implementation. They are **not implemented/passed runtime tests in this phase**. Required adversarial proof schedules appear in [migration sequencing](migration-sequencing.md).
