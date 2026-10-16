# Worker boundary

Phase 05 uses shared Django code in a separate process: `make worker-check` verifies a real database connection and exits. Running `python apps/api/manage.py worker` exits with an explicit disabled error. No polling loop, in-memory queue, job claims or AI/network work exists yet.

Future PostgreSQL leases, fencing, outbox and reconciliation must follow [ADR 0003](../../docs/adr/0003-postgres-jobs-and-reconciliation.md). This scaffold proves no durable workflow.
