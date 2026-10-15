# Recoverable jobs, provider budget and credit settlement

Trace U02, A credit invariants, D §ب/OQ-016/§د/§هـ and P §2/§5. Queue algorithm is ASSUMPTION; product reservation timing is an analyst default, not a proven guarantee.

## Durable queue and leases

Use PostgreSQL rows for jobs, attempts and a transactional outbox; no in-memory queue or required Redis. Proposed job states QUEUED/LEASED/RETRY_WAIT/SUCCEEDED/DEAD/RECONCILING are distinct from credit operation states RESERVED/RUNNING/RECONCILING/SETTLED/RELEASED. Schema and migrations belong to phase 03/05.

Claim transaction selects due jobs via `SELECT ... FOR UPDATE SKIP LOCKED`, checks operation/lifecycle, increments fencing token, sets worker_id/lease_until/attempt count and commits immediately. Worker then performs I/O outside locks. Proposed lease is 120 seconds, heartbeat every 30 seconds; workers with stale lease tokens cannot finalize. Adapter timeouts must be shorter than a renewed live lease; actual model-specific deadlines remain configurable and unvalidated. If heartbeat cannot confirm ownership, stop new egress. Lease loss before known unsent dispatch permits reclaim; lease loss after send marker leads to reconciliation, never automatic duplicate generation.

Persist attempt ID, provider/model, budget reservation and `DISPATCH_INTENT` before external send. Crash between intent and send is uncertain without provider evidence, just like crash after send. Provider request idempotency keys are used only where documented and verified; internal IDs alone cannot promise provider-side exactly-once. Separate jobs are used for scan/purge, publication outbox, reminders and reconciliation; each handler deduplicates resource/version key.

ASSUMPTION proposed retry policy: at most 3 total attempts per operation, sequential; known not-executed/transient failures back off 5s then 30s, obey Retry-After with scheduling instead of blocking worker. Never retry validation/consent/security/business refusal. A timeout/drop after dispatch is UnknownOutcome, not a proved failure, and is not automatically resent to another provider. Reconciliation may query a documented provider status or idempotent retrieval capability; absent that, record UNKNOWN and require scoped operator review. Failure/worker death cannot mint/refund credits or rerun output by itself. Dead jobs expose metadata and alert, not automatic balance editing.

## Transaction boundaries and output staging

1. API locks idempotency/user/limit/credit resources; obtains current immutable price, profile/scholarship/consent/config snapshots; creates operation+reservation+job+logical global slot+audit atomically. Commit before returning 202. Duplicate client key/body returns same operation; changed body is 409.
2. Worker claims with fence, classifies/minimizes input and rechecks flags, consent/approvals and budget. Only eligibility-preserving, task-suitable free models are candidates.
3. Before send, atomically claim a conservative physical provider allowance and persist attempt intent. No network within DB transaction. Credential only in worker secret environment.
4. Provider result is untrusted. Validate schema, language, grounding/fabricated-credential constraints and current consent/lifecycle. Valid bytes stage in private inaccessible storage outside transaction. Database acceptance owns an immutable result ID.
5. Final transaction checks lease/fence/current authorization and operation not final, commits accepted result pointer+one debit+job completion+audit/outbox. Conflicting finalize reads existing final result. A failure rolls back all database effects; orphan bytes purge later. No debit for response arrival alone.

## Two budgets, no free-tier overspend assumption

Student Credits are not provider currency/Neuron accounting. D defaults: 30 one-time signup grant, daily 6 spend in Asia/Hebron, prices 1 match explanation, 4 CV extraction, 6 document creation; policy version applies prospectively. Available wallet = grant/adjustments minus settled debit and active reservation. Daily usage includes active reserved spend to prevent concurrent bypass; confirmed released reservation returns corresponding allowance, not new Credits. Global logical operations includes chargeable and free AI support; each operation consumes one slot at acceptance, retries do not reset the logical counter. Proposed logical slots stay consumed for that policy day after failed attempts (conservative cap, not a guarantee of 100 successful results).

Physical provider tokens/requests/Neurons budget counts every actual attempt across all workloads/workers and fallback providers. D default global AI cap 100/day and Cloudflare guardrail 8,000 Neurons/day are upper bounds; provider/model caps may be smaller. Store provider reset zone/window separately from student local-day limits; do not assume vendor resets at Asia/Hebron midnight. Reserve worst-case known cost before send and retain uncertain usage reservations until authoritative reset/meter evidence. No reliable free-tier model or conservative bound/current meter → disable dispatch. Budget lock covers concurrent sends; worker cannot bypass via free support or a fallback. No paid model, auto-upgrade, paid API key or plan is eligible; contract/account spend cap must also enforce zero-cost boundary. Without an enforceable free-only account, gate remains closed.

Known measured usage adjusts unused allowance only with reliable evidence; telemetry not authoritative enough to unblock unknown outcomes. Reserve cap does not prove a vendor will honor quota or availability. Real quota estimation/metering and reset behavior are EXTERNAL_GATE.

## Reconciliation and timing

D defaults: ordinary reservation 15 minutes, then RECONCILING; 24-hour reconciliation target. Expiration is a signal to investigate, not evidence to release. After provider outcome is proved absent/terminal rejected and no result was accepted, one RELEASED transition returns student reservation; provider physical usage can still remain consumed. After valid authorized saved output, settle once. Unknown outcome stays RECONCILING, with safe owner status and metadata-only operational escalation; 24 hours is an alert/target, not blind automatic refund. No manual operator can reveal private contents or create an arbitrary debit through reconciliation.

Timeout, consent revocation, account deletion, crash, stage-write error, invalid grounding, concurrent finalizers and delayed provider response require separate reason codes and reconciliation evidence. A result for a RELEASED/SETTLED operation cannot create a second document/debit; late bytes purge or resolve to existing accepted version under recorded policy. Provider cannot callback with trust merely by knowing an operation ID; authenticated signed callback design is deferred until provider support is verified, otherwise poll/status reconciliation only.

## Required future proof

Implementation must test duplicate create/keys, cross-user key collision, reserve-vs-cap concurrency, worker crash at every boundary, fencing/late response, unknown timeout without resubmit, revoked consent before send/finalize, atomic document/debit, quota-exhaustion fallback and global stop. No such runtime test was executed in this documentation phase.
