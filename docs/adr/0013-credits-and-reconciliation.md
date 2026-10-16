# ADR 0013 — guarded credits with synthetic execution and uncertain holds

Status: bounded Phase09 runtime decision, 2026-10-16. Actual verification belongs
to [report09](../../tasks/phase-reports/09.md). This phase permits no commit, push,
deployment, paid resource or provider call.

Authority: current Phase09 request; AGENTS.md credit/privacy invariants; PRD
FR-005/069–078, BR-027–033, AC-023–025/035/041; decision resolution §أ7/§ب and
OQ-002/016; provider strategy §2.6; architecture schema R06/R10–14/R22 and
guarded state machines. Numeric beta settings remain operational defaults,
distinct from owner decisions and measured/provider/legal approval.

Use one immutable signup entitlement per canonical verified adult student,
including a consumed marker when its configured amount is zero. An explicit
call from the identity verification transaction records the grant and wallet
before activation commits. A bounded data migration backfills qualifying legacy
active accounts under the initial policy. Do not use a general ORM signal, grant
on login/Google link/restore or fabricate an earlier historical policy. Arbitrary
direct SQL activation is not claimed to invoke the explicit hook. Legal
post-erasure identity continuity and account merging remain unresolved gates.
Inactive/deletion-pending legacy accounts are not backfilled, and wallet reads
do not create grants. Restoring an excluded legacy account does not invent its
historical activation policy; previously granted accounts retain the same wallet.

Keep an append-only signed journal and guarded wallet projection. Posted balance
equals journal total; reserved balance equals active operation holds, including
reconciliation. Available balance is posted minus reserved and cannot be
negative. A release removes reserved credit without a positive journal refund.
Elapsed time and midnight do not expire or refill credits. Admin policy access
is not authority to edit a student's balance or journal.

Journal owner/reason/policy/time and command audit identify the originating
student and synthetic action. There is no dedicated authenticated worker/actor
field or independently authenticated worker principal. Full FR-077 actor
provenance remains partial pending the real execution/finance contract.

Seed a versioned prospective policy with 30 once-only signup credits, 6 credits
of student daily spend, 100 daily logical AI admissions and internal prices of
1/4/6 for matching AI/CV extraction/new document. Free deterministic browsing,
eligibility, manual edits, same-version re-export and extension use create no
funded AI operation. `COST_POLICY` Admin changes require current server MFA,
expected version, reason and atomic audit; old versions remain immutable.

Use IANA Asia/Hebron local calendar days and UTC event times. Using this same
calendar for global logical admissions is an explicit R13 engineering assumption
where the source names only a global daily amount. Bucket keys exclude policy
version. New admissions check current caps against settled plus reserved spend;
lowered caps block further use without rewriting accepted charges or counters.
Captured input, price, policy and day remain fixed through retry/finalization.
Release affects the original student spend day; global logical admissions stay
consumed after failure. Midnight or a policy edit cannot mint credit or reset
usage. Physical provider quotas and support-specific allowances are separate
future contracts.

The internal synthetic kernel captures the server price and policy without a
public quote/execution flow. It does not prove displayed-price authorization.
Before real funded execution, FR-072/BR-029/AC-023 require an explicit client
confirmation of the expected quoted price/policy; a server snapshot alone is
insufficient.

Bind canonical owner plus stable operation idempotency key and normalized request
body to one operation. Reauthorize every retry and read. Equal retries return the
original state/identity; altered bodies conflict and a new session cannot cause a
duplicate charge. Lock lifecycle/policy/budget/operation/wallet rows in one
consistent order and enforce uniqueness, immutable accounting identity,
transitions and final-state conservation in PostgreSQL as well as services.

Use `RESERVED → RUNNING → SETTLED` for successful validated persistence, with
`RECONCILING` for uncertain execution/acceptance and `RELEASED` only for a proved
terminal no-acceptance outcome. Active holds include reconciliation. One terminal
witness serializes settlement versus release. Save the validated owned result,
one exact debit, finalization, counters and audit atomically. Unsaved or
unvalidated output cannot be charged; stale worker fences cannot finalize.
Terminal states have no outgoing edge. A timer is never evidence of failure.

Do not enable real private processing to demonstrate the ledger. The internal
kernel accepts only server-created synthetic fixture UUIDs and the strict
deterministic `{"fixture_id": "<UUID>", "result": "SYNTHETIC_OK"}` payload.
There is no public reserve/claim/settle endpoint, provider dispatch, arbitrary
output acceptance or real document/CV validator. A synthetic saved result proves
the financial transaction, not academic truth, a durable document or approved
processor handling. Phase10/11 must supply exact consent, approval, classification,
semantic/domain-output and trusted execution proofs before real work is enabled.

A replayable database-scanning command marks outstanding operations reconciling
at 15 minutes and records a 24-hour resolution-due alert. Neither marker releases
funds or resends a provider request. No outbox/external side effect is introduced
for this local scan. Production scheduling and human resolution capacity are not
certified by these markers. Safe retry preserves the same operation; it does not
blindly re-execute an uncertain generation.

Expose only owned read projections and the scoped immutable policy surface. The
minimal bilingual student route is `/{locale}/wallet`, an explicit disposition
of the earlier `/credits` design label. Existing default-deny permissions,
current verified adult checks, private-ID 403 and audit remain intact. No general
finance editor, payment, arbitrary adjustment, final erasure cancellation or
private-library privilege is added. Those workflows and actual MFA/provider/free
quota/retention/RLS/release evidence remain separately gated.

Worker fences and current time/deadline authorization are enforced by the trusted
service; SQL guards establish immutable structure and conservation rather than
independent execution proof. Complete-table deferred scans deliberately favor
reviewable local correctness. Their per-row overhead needs production-scale
profiling and incremental enforcement work before broader use.

See the [Phase09 specification](../specs/phase-09-credits.md) for detailed traces,
state/accounting semantics and required negative/concurrent proof. Earlier source
and phase outcomes remain unchanged.
