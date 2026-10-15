# ADR 0003 — PostgreSQL jobs and reconciliation

Status: PROPOSED / ASSUMPTION. Traces U02; D §ب/OQ-016/§هـ; P §2.6/§5. Context: AI and file scans outlive requests; free-host restarts and provider timeouts can duplicate side effects.

Decision: PostgreSQL queue and transactional outbox, independent worker using shared domain code; `SKIP LOCKED` claims, finite heartbeat lease and monotonically fenced finalization. I/O outside transactions; persisted send intent/attempt and conservative provider budget before network. At-least-once delivery with durable operation uniqueness, not a promise of exactly-once external execution. Uncertain outcome → RECONCILING without blind reroute/refund. Saved validated output plus one credit settlement commits atomically. Detailed crash/retry/budget semantics in `../architecture/jobs-and-reconciliation.md`.

Proposed queue retry/lease defaults are engineering assumptions; D's 15-minute reservation and 24-hour reconciliation are qualified operational defaults, not timers proving failure. Expired lease cannot authorize duplicate provider call after dispatch intent. Require reliable documented provider status/idempotency or operator metadata review to resolve unknown outcomes. Unknown physical usage stays reserved through reset evidence; credit release never replenishes consumed provider budget.

Consequences: queue growth/lease lag needs alerts, polling capacity and DB indexing later. Release migrations must be worker-compatible. Rejected alternatives: in-request loops, post-response callbacks or memory queues as durable jobs; unnecessary Redis/Celery dependency before evidence. No scheduler/worker hosting approved yet.
