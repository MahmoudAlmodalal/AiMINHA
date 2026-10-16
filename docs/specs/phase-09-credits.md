# Phase09 — credit accounting, entitlements and concurrency

The current request authorizes only Phase09 and parallel agents. It does not
authorize a commit, push, deployment, paid resource or provider call. Authoritative
source files and earlier phase outcomes remain unchanged. Runtime choices are
recorded in [ADR0013](../adr/0013-credits-and-reconciliation.md); actual checks,
defects and phase status belong to [report09](../../tasks/phase-reports/09.md).
This bounded accounting implementation is not approval to enable private AI.

## Source traces and scope

`U09.1`–`U09.5` identify the current work items. The authoritative feature baseline
is [PRD v3.0.0](../source/PRD.md). The [decision resolution](../source/MinhaAI_PRD_Decision_Resolution_AR.md)
separates the owner's decision to use configurable bounded credits (§أ7) from
analyst-proposed numeric beta defaults (§ب, OQ-002/016). The
[provider strategy](../source/ai-provider-strategy.md) does not approve a vendor,
model, data class, free-tier capacity or semantic output validator.

| Work | Implemented boundary | Source trace |
|---|---|---|
| One-time activation grant | A canonical verified adult student receives one immutable signup entitlement and journal entry, including a zero-amount consumed marker; an explicit activation hook and bounded legacy backfill share the database uniqueness boundary | U09.1; FR-005/070; BR-027; decision §أ7/§ب/OQ-002; schema R06/R11 |
| Daily/global limits and prices | Versioned prospective policy, distinct posted/reserved/available amounts, local spend reservations, immutable accepted prices and logical admissions | U09.1/2; FR-069–074/078; BR-028–031; AC-023/025; decision §ب; R07/R13 |
| Exactly-once accounting | Stable owned operation identity, reservation, fenced execution, validated saved synthetic result, one terminal witness/debit or proved release, append-only journal | U09.3; FR-074–077; BR-031–033; AC-024/041; R10/R11/R14/R22 |
| Uncertainty and recovery | A 15-minute reconciliation marker and 24-hour due marker retain uncertain holds; safe replay preserves the original operation and no provider request is resent | U09.3/4; OQ-016; provider strategy §2.6; guarded state machines |
| Negative/concurrent proof | Independent PostgreSQL connections, two students, races, policy/day changes, failure, output and ownership denials | U09.5; AC-023/024/035/041; NFR-003/015/016/024; R22 |

FR-079 manual financial adjustments, public payment/top-up flows, real AI
adapters, actual document/CV validation and final erasure settlement are outside
this bounded work list. They are not implemented by a general balance editor or
an invented approval. Existing deterministic eligibility, browsing, manual edits,
same-version re-export and extension work remain free; no funded operation is
created merely to use those features.

## Entitlement and wallet

The identity verification transaction locks the canonical account, consumes the
single-use verification proof, verifies adult eligibility, activates the account
and calls the signup grant service before commit. A grant or audit failure rolls
back activation. The grant service accepts only a current verified adult student,
uses the server's active policy and enforces the one-per-account grant in the
database. The configured zero value still creates a permanent consumed marker.
The caller cannot choose the amount or fabricate an entitlement from a price.

A migration backfills pre-existing active verified adult student accounts once
under the seeded Phase09 policy. This is a transparent engineering migration
choice; it does not reconstruct an absent historical policy or claim those
accounts already received a grant. The same uniqueness boundary protects a later
service replay. The runtime activation hook is explicit; there is no generic ORM
signal or claim that arbitrary direct SQL account activation invokes it.
Legacy inactive/deletion-pending accounts are intentionally excluded; reading a
wallet never lazily creates a grant. Restoring such an excluded legacy account
does not resolve its missing historical activation policy or mint an entitlement.

Google linking, sign-in, policy edits and account restoration do not grant again.
The canonical account remains the entitlement identity. Existing identity
uniqueness and deletion denial are retained. Lifetime identity continuity after
lawful erasure, re-registration or an approved account merge is unresolved; no
new promise of deduplication after every identifying link has been erased is
made. A future lifecycle integration must preserve lawful entitlement tombstones
or deny ambiguous re-grants.

The append-only signed journal is the accounting record. Wallet posted balance
is the sum of entries; reserved balance is the total of active holds, including
`RECONCILING`; available balance is posted minus reserved. Amounts are integer
credit units. No wallet can have negative available or reserved credit. A release
removes a hold and does not add a positive refund entry because it never posted a
debit. Credits do not expire due to elapsed time, and midnight creates no credit.
There is no general student, Admin or AI write path for balances or ledger rows.

Each journal entry identifies its owning/originating student, reason code, entry
identity, policy and timestamp, with metadata audit for its guarded command. It
has no dedicated authenticated worker/actor field; the local synthetic worker is
a trusted service caller. Full FR-077 worker-principal provenance is therefore
partial and must be added with the real execution/finance identity contract.

Current account permissions freeze access and prevent new spending during
deletion recovery. Restoration of a previously granted account exposes the same
wallet without a new grant.
Final deletion cancellation and resolution of uncertain in-flight work require a
separate guarded erasure integration; no physical purge or financial write-off is
inferred from this phase.

## Versioned policy and calendar semantics

| Initial setting | Default | Meaning |
|---|---|---|
| Signup grant | 30 credits | Once on qualifying activation, not on each login |
| Student spend | 6 credits per local calendar day | Settled plus reserved spend; not a daily refill |
| Global logical AI admissions | 100 per local calendar day | Upper bound, not promised provider capacity |
| Matching AI | 1 credit | Future funded AI explanation, not deterministic eligibility |
| CV extraction | 4 credits | Future approved extraction, not an upload fee |
| New document | 6 credits | Per new AI-generated document, not manual editing or same-version export |

Student calendar boundaries use the IANA `Asia/Hebron` timezone. Global logical
admissions use that same day as an explicit R13 engineering assumption because
the decision record states the global daily amount without independently naming
its reset timezone. Events remain UTC instants; a day is obtained through actual
timezone rules, never a hard-coded UTC offset or fixed 24-hour bucket.

Daily bucket identity excludes the policy version. For a new request, current
limits must permit `settled + reserved + proposed_price` and the next global
admission. A lowered limit below existing usage blocks further admissions; it
does not erase counters, release accepted holds or reprice existing operations.
Policy changes are immutable versions published prospectively under a locked
head, expected-version check, explicit reason, audit and current scoped Admin MFA.
The runtime scope is `COST_POLICY`. Keys, provider approvals, bypass flags and
student balance edits are not policy fields.

An accepted synthetic operation captures policy, exact server price, input
identity, UTC acceptance time and local spend/global days. It has no public
execution or quote flow and does not claim student displayed-price authorization.
Future real execution must add an explicit confirmed expected price/policy quote
before reservation to meet FR-072/BR-029/AC-023; a server price alone is not that
authorization.
Retry and settlement use these original values. A later policy or day cannot
refresh the price, idempotency identity or allowance. Release decrements reserved
spend in the original captured student day. A failed/released operation retains
its logical global admission, following R13's conservative design; retries of
the same logical operation do not increment it again. Provider physical usage
budgets and the separate future free support allowance are not implemented or
certified by this logical admission counter.

## Bounded synthetic execution contract

There is no public reserve, claim, output-validation or settlement endpoint, and
no live provider adapter, provider credential or external request in this phase.
The kernel accepts only a server-created `SyntheticInput` UUID. Its deterministic
output has the strict shape `{"fixture_id": "<UUID>", "result": "SYNTHETIC_OK"}`;
the fixture must be the exact owned operation input. Unknown fields, altered
identity, arbitrary text, claimed provider success or a caller's validation flag
cannot turn a result into chargeable success.

This synthetic validator proves the financial save/validation/settlement
transaction and concurrency boundaries. It does not validate a real CV,
scholarship explanation, academic claim or generated document. Storing this
payload does not create an approved student document or extraction proposal.
Future Phase10/11 services must supply their own current consent, processor,
classification, semantic validation, exact saved-domain-output and worker proof
contracts before funded real processing can be enabled. No private input is sent
to any provider and no real processing route is silently enabled by a wallet.

Stable idempotency binds the canonical owner, operation key and normalized input
body to one operation. Equal retries reauthorize and return that operation;
altered requests conflict. Another account cannot replay it, and a new session
does not authorize a second debit. No client-supplied owner, price, policy, state,
counter or output proof has authority. Safe retries return persisted state; they
do not start another uncertain execution.

## Operation states and atomic effects

| State | Accounting and permitted progress |
|---|---|
| `RESERVED` | One immutable input/price, active hold and captured day/global admission; no debit or accepted output |
| `RUNNING` | Current fenced execution owns the operation; hold remains and there is no charge yet |
| `RECONCILING` | Unknown/expired execution or acceptance needs proof; hold remains and no blind retry/release occurs |
| `SETTLED` | One validated saved result, one finalization witness and one exact debit; no active hold |
| `RELEASED` | Proven terminal no-acceptance outcome and one release witness; no accepted result, debit or active hold |

Terminal states have no outgoing transition. A duplicate callback returns the
existing authorized outcome. A competing settle/release cannot create both
outcomes. A stale execution fence cannot write an output or charge. Known safe
synthetic failure may release once; a timeout, missing callback, uncertain effect
or age alone cannot prove failure. Late writes to a released operation cannot
save an accepted result or debit. There is no enabled transition out of
`RECONCILING`: an authoritative future adapter/recovery proof is required before
those exit paths can be introduced.

Acceptance validates and saves the exact owned synthetic output, appends its
debit and terminal witness, updates wallet/day counters, closes the hold and
records audit in one transaction. Any failure rolls back the whole effect.
Validation without persistence and persistence without validation cannot settle.
Database uniqueness, immutable fields, transition guards and final-state
conservation checks supplement service locking; passing an API serializer is not
the only barrier against incorrect accounting.

Current clock/deadline and worker-fence checks are trusted-service guards;
database guards establish structural identity and accounting conservation, not
independent attestation of a worker's authority or semantic truth. Deferred
conservation uses complete-table scans for this bounded implementation. Its
per-row trigger cost requires realistic volume/concurrency profiling and likely
incremental validation before production; no performance certification is inferred.

The implementation follows a consistent account/policy/budget/operation/wallet
lock order, using sorted identities where several rows participate. Independent
database connections exercise conflicting requests. External I/O never occurs
under these locks. The accounting services do not expose a generic journal
mutation API or allow synthetic results to certify real document success.

## Reconciliation markers and reliable local work

A database-scanning management command identifies outstanding reservations at
the standard 15-minute boundary and marks them `RECONCILING`. It also records a
24-hour resolution-due marker. The scan is replayable database work, with no
provider sending or external side effect; no outbox is claimed or needed for
this bounded scan.

The 15-minute value is an investigation threshold, not automatic release. The
24-hour value is an experimental resolution target/alert, not a financial
deadline, guarantee or forced state transition. Repeated scans do not release
holds, issue credit, re-run generation or generate duplicate terminal effects.
Actual human response and production scheduler reliability remain operating
gates. Unknown outcomes remain reconciling until a trusted proof permits one
terminal outcome.

## API, student presentation and authorization

The runtime exposes read-only owned wallet, ledger and operation projections.
The generated OpenAPI/types are authoritative for implemented route and field
names. Protected reads require the current active verified adult student and
return only that owner's data. A private foreign/missing identifier receives
the existing audited 403 boundary. Admin policy privileges do not confer student
wallet impersonation or private-library access. CSRF and idempotency/version
checks protect the scoped policy mutation; current MFA remains mandatory.

| Method and path, relative to `/api/v1` | Current capability |
|---|---|
| `GET /wallet` | Current student's balances, original grant marker and policy/day limits |
| `GET /wallet/entries` | Bounded paginated owned journal metadata |
| `GET /operations` | Bounded paginated owned operation states and captured prices |
| `GET /operations/{operation_id}` | Owned operation metadata; no private output body or worker token |
| `GET /admin/policies/credits` | Current policy for a current `COST_POLICY` Admin with MFA |
| `POST /admin/policies/credits` | Explicit typed prospective policy version with CSRF, idempotency and `If-Match` |

The minimal bilingual student page is `/{locale}/wallet`. This runtime name
differs from the earlier architecture's `/credits` surface and is recorded as a
bounded route disposition, without claiming the broader Admin/finance console.
It distinguishes posted, reserved and available amounts, the daily spend cap
from a refill, logical global limits from capacity, and reconciling funds from a
completed debit. It does not show a purchase, cash value, promised AI
availability or a real funded-operation launch button.

## Verification obligations and remaining gates

Report the actual commands and results in report09; this document does not claim
they passed. Meaningful proof includes: once-only and zero grants; atomic adult
verification activation; two-account ownership/conservation; competing
reservations and double requests; changed-body retries; exact accepted pricing
under policy changes; local midnight/DST and original-day release; configured
caps without counter resets; double settlement and settle/release races;
unvalidated/unsaved output rejection; rollback; stale workers; 15-minute and
24-hour equality boundaries; append-only journal and direct-database guard
denials; public API permissions, CSRF and safe projections. Static types,
migrations, generated contract validation, build and secret checks remain
required alongside relevant runtime checks.

External gates remain: actual processor/model/data/region approvals; minimized
private-data consent and revocation handling; trusted real output validators and
exact durable document/file identity; physical free-only provider metering;
production role separation/RLS and worker operations; legal financial/identity
tombstone and deletion policy; actual MFA enrollment; semantic bilingual quality;
manual adjustment approvals; legal retention and release signoff. Synthetic
proof and a local phase gate do not close those gates or certify production.
