# ADR0017 — support ticket lifecycle, business-hours SLA and AI triage

Status: accepted for the bounded Phase13 local implementation; external release,
provider approval, staffing and privacy approvals remain independent.

## Context and source traces

PRD FR-094–FR-105, FR-110, BR-040–BR-045, AC-031–AC-034, EC-025/026 and
ERR-021/022 require an owned ticket with a six-state lifecycle, an auditable
transition log, configurable working hours and holidays, a priority-configurable
**first human response** SLA measured on that calendar, AI triage with mandatory
handoff, resolution/reopen/rating rules and a support queue that never grants
routine access to the private file library. Decision OQ-008 (Sun–Thu 09:00–17:00
Asia/Hebron, critical 4 / high 8 / normal 24 / low 48 business hours), OQ-009 (the
clock starts on the human request or handoff, ends on the first substantive human
reply, and AI never satisfies it), OQ-010 (resolved becomes closed after 7 days,
14-day reopening window, one rating editable for 7 days) and the beta default of
five free AI support messages per student per day inside the global AI budget
shape the behaviour. Phase06/Phase11 already provide the ticket authorization
projection (`privacy.TicketAccess`) and the explicit, revocable, audited ticket
share (`privacy.TicketShare`).

No approved `STUDENT_PRIVATE` AI route exists (Phase10 outcome), and the credits
ledger conserves its global admitted-operation counter against credit operations,
so a support AI operation cannot be recorded as a credit operation.

## Decision

Use a `support` module owning the ticket aggregate. The ticket identity is the
existing `privacy.TicketAccess` authorization projection; the support ticket is a
one-to-one extension keyed by that identifier, so attachment sharing and revocation
keep the Phase06/Phase11 invariants unchanged and no library permission is created.

Keep the six documented states (`NEW`, `AI_HANDLING`, `AWAITING_ADMIN`,
`AWAITING_STUDENT`, `RESOLVED`, `CLOSED`) with an append-only event log that
records the actor, the reason, the observed instant and the recorded instant.
Transitions are explicit commands with compare-and-swap revisions; an ordinary
transition never rewrites history, and a reopen is a new event.

Measure the first-human-response obligation on the administrator's working
calendar. Business time is defined in the calendar's local wall clock; each
working day's window is resolved to absolute instants in that zone, so a
daylight-saving transition changes the absolute instants without changing the
staffed window. Weekends, holidays and closed hours contribute nothing, and the
arithmetic is exact in seconds, so a target is added exactly and only the value
shown to a person is rounded to minutes. The clock starts once per cycle — at the
student request, the AI handoff or the agent assignment — and ends at the first
substantive administrator message. Substance is classified by a server-side rule
that treats a receipt acknowledgement as an acknowledgement, so an agent cannot
declare a one-word note to be the answer. An AI message never satisfies it, and
time spent waiting for the student afterwards cannot change a metric that was
already met. A reply after the deadline records the breach immediately. The due
instant, the bound target minutes and the bound calendar version are frozen at the
start of the cycle, so a later policy or priority change never silently rewrites
an in-flight commitment. A reopen starts a new cycle and keeps the finished cycle
readable in the cycle history and in the aggregate metrics.

**ASSUMPTION:** the working calendar, the per-priority targets, the quiet period,
the reopening window, the rating window and the AI allowance live in one
versioned, auditable policy object. The shipped values are the sourced defaults
(Sun–Thu 09:00–17:00 Asia/Hebron, 4/8/24/48 business hours, 7/14/7 days, five AI
messages per student per day). They are engineering defaults, not a published
service level, and the targets are experimental. A published policy applies from
its effective date.

A resolution leaves the ticket `RESOLVED`. Only the bounded worker closes it
after the configured quiet period elapses without an objection; a student
confirmation never shortens that period. A student may object while the ticket is
resolved, reopen a closed ticket inside the reopening window, and may rate the
support experience exactly once, editable inside the rating window. An expired
rating keeps its own deadline across a later re-resolution.

Keep the AI triage inside a strict allowed context: the current ticket's subject,
category and messages. Attachment bytes, attachment metadata, other tickets,
profile data, account state and credit balances cannot enter the context, so no
private data can reach a provider even if a route is approved later. The triage
engine is a deterministic server-local classifier. It suggests a category and a
priority and it always records its handoff reasons: a student request, low
confidence, two consecutive uncertain answers for that student, a financial topic,
a security topic or a critical deadline. A financial or security subject is
decided on its own terms, never by the category ranking, and a student reporting
that the advice did not help counts as a failed answer that hands off at two. The
suggestion never changes the effective category or priority; an administrator
decides, with a recorded reason. The AI has no write path to credits, accounts,
payment approval or file contents.

**ASSUMPTION:** because no approved private route exists, provider-backed triage
is not implemented in this phase and the local engine is the honest, testable
behaviour. It is recorded as an engineering choice forced by the approval state,
not as a model capability.

Bound the experiment: five free AI messages per student per Asia/Hebron business
day — a published calendar can lower that number but never raise it above five —
and one global AI allowance that the credit-backed admission path and the support
reply path both draw on. The financial admitted-operation counter is never touched
by support usage, because the ledger's conservation guard equates it with credit
operations; support AI therefore cannot be laundered through the financial ledger,
and a support AI message never debits or reserves a credit. When either allowance
is exhausted the request is handed to a human with an explicit reason instead of
pretending to be an AI answer.

Keep agent access narrow. The queue exposes metadata only — no student identity,
subject or message content. The thread, the ticket metadata, the explicit
attachment list and the shared attachment bytes are readable only by the
administrator currently assigned to that ticket, with the support scope and a
current MFA proof; every denial and every read is audited. The guard runs before
an idempotent command, so a replay after a reassignment or a withdrawn scope is
refused instead of returning a cached ticket. The private library itself stays
unreachable from support.

## Consequences and gates

Owner-scoped reads and writes, strict DTOs, session/CSRF checks, immutable event
evidence, idempotent commands, audited attachment access and a bounded, idempotent
worker sweep (SLA warning, SLA breach, quiet-period closure) are required.

Real provider-backed triage, staffing evidence behind the 4/8/24/48 targets, a
production scheduler, database-role/RLS and load evidence, legal retention and
erasure review for support data, the administrator console, and release signoff
remain external gates. The account-deletion review scope still covers the ticket
records; no separate erasure receipt is claimed.
