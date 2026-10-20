# Phase13 — support tickets, AI triage and business-hours SLA

**Status:** spec for the bounded Phase13 implementation. Authority: `prompts/13` phase
instruction plus `AGENTS.md`; source traces are listed below. No later phase, commit,
push, deployment, paid resource or real provider call is authorized by this document.

| Boundary | Source trace |
|---|---|
| Owned tickets with categories, validated attachments and message history | FR-094; PRD F-12; BR-040; AC-031 |
| 24/7 AI guidance with limited authorized assistance | FR-095; OQ-019; decision §ب (AI support 5/day) |
| AI category/priority suggestion with Admin authority retained | FR-096; OQ-019 |
| Mandatory human handoff on request, failure, uncertainty, financial/security | FR-097; BR-041; EC-026; AC-032 |
| AI can never approve money or move balances | FR-098; BR-042; AC-031 |
| Six named states with an auditable transition log | FR-099; BR-040; OQ-014-style state discipline |
| Resolution confirmation, reopen and one rating with an edit window | FR-100; BR-045; OQ-010; AC-034 |
| Admin working calendar, holidays, 24/7 AI represented separately | FR-101; BR-043; OQ-008 |
| Priority-configurable first-human-response SLA on the working calendar | FR-102; BR-044; OQ-008/009; AC-033 |
| SLA warning/escalation events | FR-103; ERR-022 |
| Admin queue with ownership, due calculation and escalation markers | FR-104 |
| Aggregate support performance | FR-105 |
| Ticket attachments distinct from the private library; assigned-only support read | FR-094/110; decision §أ6/§د; OQ-007; AGENTS security invariants |
| Explicit ticket file attachments, audited on every access | phase instruction item 1; ADR0015 privacy boundary |
| Working hours Sun–Thu 09:00–17:00 Asia/Hebron with configurable holidays | OQ-008 (default, configurable) |
| First-response targets 4/8/24/48 business hours | OQ-008 (experimental targets, not a service commitment) |
| SLA starts on human request/handoff, ends on the first substantive human reply | OQ-009 |
| Resolved → Closed after 7 days, 14-day reopen window, rating once/editable 7 days | OQ-010 |
| AI support limited to 5 free messages/student/day inside the global budget | decision §ب (AI support row); OQ-019 |

## Problem Statement

A verified student who is blocked — a scholarship application will not go through, a
document cannot be produced, a deadline is unclear, a payment question needs a human —
has no support channel today. The platform advertises 24/7 AI assistance and human
support inside working hours, but there is no ticket, no thread, no queue, no service
window and no measurable response commitment. Every other domain in the product
(catalog, eligibility, credits, documents, applications) is implemented and tested;
support is the missing vertical.

At the same time, support is the domain where a careless implementation would break the
product's hardest safety rules. The private file library belongs to the student; an
administrator must never browse it (Phase06/Phase11 already enforce this). Support needs
to see *something* the student shows it — a screenshot of an error, a receipt — and the
only acceptable model is an explicit, revocable, audited share attached to one ticket,
readable only by the agent currently assigned to that ticket. Support also touches
money-adjacent questions ("why are my credits missing?"), and the AI that answers 24/7
must never be able to approve a transfer, add credits, or read a private file.

Students also need to know what "human response" means. "We answered in 3 minutes" must
be measurable against a published working calendar, must not be satisfied by an automated
reply, and must not be broken by a weekend, a public holiday or a daylight-saving change.

## Solution

A `support` module that owns the ticket aggregate end to end:

1. **Owned tickets.** A student creates a ticket with a category, a subject, a message
   and an explicit `request_human` flag. Tickets carry exactly the six documented
   states (`NEW`, `AI_HANDLING`, `AWAITING_ADMIN`, `AWAITING_STUDENT`, `RESOLVED`,
   `CLOSED`) and an append-only transition/event log. Only the owner reads their
   ticket; a support administrator reads only a ticket currently assigned to them.
2. **Explicit ticket attachments.** The student attaches an already accepted private
   file to a specific ticket. That creates an explicit, revocable share bound to that
   ticket. It is not a library permission: the file stays out of the library view, the
   share is read only by the currently assigned agent, and every metadata read and
   every byte read is audited. An admin without a current assignment is denied.
3. **Business-hours SLA engine.** A pure, DST-correct calendar module measures the
   first-human-response obligation: the clock starts when the student asks for a human
   or the case is handed to a human, pauses outside the configured working calendar
   (weekends, holidays, closed hours), and ends on the first *substantive human* reply.
   An AI reply never satisfies it. Waiting for the student afterwards never reopens it.
   Reopening a ticket starts a new measured cycle. Targets are configurable per
   priority (defaults 4/8/24/48 business hours) and are bound to the calendar policy
   version in force when the clock started.
4. **AI triage with mandatory handoff.** The AI assistant works only from an allowed
   context (this ticket's subject, category and messages). It may suggest a category
   and a priority and may answer guidance questions, but it always hands off to a human
   on student request, after two consecutive failures, on low confidence, on
   financial/security topics and on critical deadline pressure. A financial or security
   subject is decided on its own terms, never by the category ranking. It has no route to
   credits, accounts, payment approval or private file contents.
5. **Bounded experiment.** AI support is limited to five free messages per student per
   day; a published calendar can lower that number but never raise it above five. The
   same global AI allowance covers credit-backed AI operations and support AI replies.
   When either limit is reached, the request falls back to a human ticket instead of
   pretending to be AI.
6. **Resolution, reopening and rating.** `RESOLVED` becomes `CLOSED` automatically after
   the configured quiet period (7 days) without an objection; a student confirmation
   never shortens that period. A student may object while the ticket is resolved, reopen
   a closed ticket within the configured window (14 days) and may rate the support
   experience exactly once, editable inside the configured rating window (7 days).

Students get a bilingual (Arabic RTL / English LTR) support page that lists their
tickets, opens one, shows the thread, the attachments they chose to share, the measured
first-response expectation in working time, and the rating control. Administrators get
API access to the queue, assignment, replies, classification and the SLA calendar
policy. The Admin console UI stays in Phase15.

## User Stories

1. As a verified adult student, I want to open a support ticket, so that I have a durable place to ask for help.
2. As a verified adult student, I want to choose a support category when opening a ticket, so that my case reaches the right desk.
3. As a verified adult student, I want to write a subject and a description, so that the support team understands my problem.
4. As a verified adult student, I want to ask for a human immediately when I open a ticket, so that I am not left waiting on an automated answer.
5. As a verified adult student, I want to list all of my tickets, so that I can return to an earlier case.
6. As a verified adult student, I want to see a ticket's current state, so that I know whether someone is working on it.
7. As a verified adult student, I want to read the full message history of my ticket, so that I do not have to repeat myself.
8. As a verified adult student, I want to add a message to an open ticket, so that I can answer a question from support.
9. As a verified adult student, I want to see the attachments I explicitly shared on a ticket, so that I know what support can see.
10. As a verified adult student, I want to attach one of my own uploaded files to a ticket, so that support can look at the exact file I mean.
11. As a verified adult student, I want to attach a file only after an explicit confirmation, so that I never share something by accident.
12. As a verified adult student, I want to revoke a shared attachment, so that I can withdraw it from support.
13. As a verified adult student, I want to see the expected first human response time in working hours, so that I know when to expect an answer.
14. As a verified adult student, I want to see the published working calendar (days, hours, holidays), so that the expectation is transparent.
15. As a verified adult student, I want the expected response time to ignore nights, weekends and holidays, so that the promise matches the staffed hours.
16. As a verified adult student, I want an automated answer never to count as the human response, so that the measured commitment is honest.
17. As a verified adult student, I want the response clock to start when I ask for a human, so that the wait is measured from my request.
18. As a verified adult student, I want to keep waiting on the same clock while support asks me a question, so that the first-response metric is not distorted afterwards.
19. As a verified adult student, I want to reopen a recently closed ticket, so that an unresolved problem is not lost.
20. As a verified adult student, I want to be blocked from reopening a ticket outside the permitted window, so that the rule is consistent.
21. As a verified adult student, I want to confirm that my issue is resolved, so that the case can close.
22. As a verified adult student, I want to rate the support quality once, so that the team gets usable feedback.
23. As a verified adult student, I want to correct my rating shortly after giving it, so that an accidental tap does not become the record.
24. As a verified adult student, I want to be told when a rating can no longer be changed, so that the boundary is not a surprise.
25. As a verified adult student, I want to ask the AI assistant a guidance question at any hour, so that I am not blocked by office hours.
26. As a verified adult student, I want the AI to suggest a category for my case, so that it is routed faster.
27. As a verified adult student, I want the AI to suggest a priority, so that an urgent issue is not under-triaged.
28. As a verified adult student, I want the AI to never approve a payment or change my balance, so that my money stays under my control.
29. As a verified adult student, I want the AI to hand me to a human when I ask, so that I am never trapped with a bot.
30. As a verified adult student, I want the AI to hand off when it is unsure or has failed twice, so that a weak answer does not stay the answer.
31. As a verified adult student, I want the AI to hand off on financial or security questions, so that a specialist reviews them.
32. As a verified adult student, I want the AI to hand off when a scholarship deadline is critical, so that time-critical cases reach a person.
33. As a verified adult student, I want my AI support usage counted per day, so that the limit is visible.
34. As a verified adult student, I want to fall back to a human ticket when my daily AI allowance is used up, so that I still get help.
35. As a verified adult student, I want to see the reason my request went to a human, so that the outcome is explainable.
36. As a student, I want other students to be unable to see my ticket, so that my case stays private.
37. As a student, I want a ticket that is not mine to be indistinguishable from a missing ticket, so that IDs cannot be probed.
38. As a student, I want an administrator to be unable to browse my private file library, so that my documents stay mine.
39. As a student, I want an administrator to see only the attachments I explicitly sent on the ticket assigned to them, so that support is narrow and accountable.
40. As a student, I want every support read of my attachment to be recorded, so that access is accountable.
41. As a student, I want a support agent to lose access the moment the ticket is reassigned, so that the access window is exact.
42. As a student, I want attachment sharing to be revocable, so that a later decision by me is respected.
43. As a support administrator, I want a queue of tickets with state, category, priority and due calculation, so that I can work the queue.
44. As a support administrator, I want to see only tickets assigned to me before assignment, so that the queue is not a browsing surface.
45. As a support administrator, I want to assign a ticket to an agent, so that ownership is explicit.
46. As a support administrator, I want to reply to a student in the thread, so that the conversation stays in one place.
47. As a support administrator, I want my substantive reply to stop the first-response clock, so that the commitment is met explicitly.
48. As a support administrator, I want to see escalation markers and warning state on a ticket, so that I can prioritise at-risk cases.
49. As a support administrator, I want to set the effective category and priority, so that final triage decisions stay human.
50. As a support administrator, I want the priority change to be recorded with a reason, so that the SLA basis is auditable.
51. As a support administrator, I want the AI suggestion shown beside my decision, so that the machine proposal is reviewable.
52. As a support administrator, I want to configure working days, working hours and holidays, so that the calendar matches my staffing.
53. As a support administrator, I want to configure the first-response target per priority, so that targets match reality.
54. As a support administrator, I want a policy change to apply prospectively and not silently rewrite an in-flight commitment, so that history stays truthful.
55. As a support administrator, I want automatic closure of resolved tickets after a quiet period, so that the queue stays current.
56. As a support administrator, I want automatic SLA warnings and breaches to be recorded, so that misses are visible rather than silent.
57. As a support administrator, I want aggregate volumes, response times, violations and ratings, so that I can report on support quality.
58. As an operator, I want every support action audited with actor and reason, so that the domain is reviewable.
59. As an operator, I want AI support usage bounded by a global budget as well as a per-student limit, so that one heavy user cannot exhaust capacity.
60. As an operator, I want the AI support experiment to run without credits being spent, so that the beta stays free for students.
61. As an operator, I want support AI to see only the allowed context of the current ticket, so that no unrelated private data can leak into a reply.
62. As an operator, I want ticket attachments kept distinct from the private library, so that one compromise does not expose the other.
63. As an operator, I want the SLA arithmetic unit-testable over weekends, holidays and daylight-saving transitions, so that the commitment is verifiable.
64. As an operator, I want the ticket aggregate versioned with compare-and-swap writes, so that concurrent replies cannot lose history.
65. As an operator, I want the transition log append-only, so that no state change can be rewritten.
66. As an operator, I want a worker command to detect SLA warnings/breaches and auto-closure idempotently, so that a crash cannot double-apply or skip.
67. As an operator, I want the support policy versioned and auditable, so that operational settings have a history.
68. As an operator, I want honest failure when the AI route is unavailable, so that the product never fabricates support.
69. As an operator, I want a written path for the AI to be unavailable that still serves the student, so that the system degrades to human support.
70. As a student, I want the support page in Arabic with right-to-left layout, so that the product is usable in my language.
71. As a student, I want the support page in English with left-to-right layout, so that the product is usable in my language.
72. As a student, I want the support page to show a clear message when the service is unavailable, so that I never see a blank failure.
73. As a student, I want the support page to distinguish an AI answer from a human answer in the thread, so that I know what I received.
74. As a student, I want the ticket list to show my open and closed cases separately, so that I can find a live case quickly.
75. As a student, I want my rating control to disappear once the rating window closes, so that the UI matches the rule.
76. As a student, I want to see the measured first-response outcome after a human replied, so that the commitment is auditable from my side.
77. As a support administrator, I want the ticket history to include who acted and why, so that a dispute can be reconstructed.
78. As a support administrator, I want a reopened ticket to start a fresh measured cycle, so that the metric reflects current work.
79. As a support administrator, I want the AI answer stored in the same thread, so that the student sees one conversation.
80. As an operator, I want support data included in the account-deletion review scope, so that retention obligations remain achievable.

## Implementation Decisions

### Module and ownership

- A new Django app `support` owns tickets, messages, events, ratings, the SLA calendar
  policy and the AI-support usage counters. It never reaches into another module's
  internals: it calls documented service functions and reads documented models.
- The ticket identity is the existing `privacy.TicketAccess` authorization projection
  (one row per ticket, owner = student, optional assigned admin). The support ticket
  aggregate is a one-to-one extension keyed by that identifier, so the existing
  attachment/share machinery (`privacy.share_asset`, `revoke_share`, `ticket_asset`)
  keeps working with no change to its own invariants.
- Support never creates, owns or grants library access. It only shares and revokes
  shares of assets the student already owns.

### Aggregate and state machine

- `Ticket` fields: owner, category, subject, state, priority (effective), suggested
  category/priority with confidence and reason, assigned admin, `row_version`
  (compare-and-swap), `head_sequence`, created/updated/resolved/closed instants,
  reopen-until and rating-window instants, `human_requested_at`,
  `first_human_response_at`, the bound SLA policy version, bound target minutes, bound
  due instant, `sla_cycle_no`, warning/breach markers, and the consecutive AI failure
  counter.
- `TicketMessage`: ticket, contiguous sequence, author kind (`STUDENT`, `ADMIN`,
  `AI`), body, `substantive` flag, created instant.
- `TicketEvent`: append-only, ticket-scoped sequence, from/to state, kind, actor,
  reason code, observed and recorded instants. Terminal states cannot be silently
  rewritten; a reopen is a new event, never a deletion.
- `TicketRating`: one row per ticket (unique constraint), value, created/updated
  instants and the editable-until instant.
- States and permitted edges:
  - `NEW → AI_HANDLING` (student asked the AI) and `NEW → AWAITING_ADMIN` (human requested).
  - `AI_HANDLING → AWAITING_ADMIN` (handoff), `AI_HANDLING → AWAITING_STUDENT`.
  - `AWAITING_ADMIN → AWAITING_STUDENT` (agent asked the student), `AWAITING_ADMIN → RESOLVED`.
  - `AWAITING_STUDENT → AWAITING_ADMIN` (student replied), `AWAITING_STUDENT → RESOLVED`.
  - `RESOLVED → AWAITING_ADMIN` (student objection inside the quiet period).
  - `RESOLVED → CLOSED` (the configured quiet period elapses without an objection).
  - `CLOSED → AWAITING_ADMIN` (reopen inside the window) only.
- `CLOSED` is terminal otherwise; an ordinary transition cannot delete history.
- A resolution leaves the ticket `RESOLVED`. Only the bounded worker closes it after
  the configured quiet period elapses without an objection; a student confirmation
  never shortens that period. The quiet period is measured from the resolution.
- A student may object while the ticket is `RESOLVED` (inside the quiet period) or
  while it is `CLOSED` (inside the reopening window). Both start a fresh measured
  cycle with clean lifecycle timestamps.

### Business-hours calendar

- A pure module owns the arithmetic: elapsed working seconds between two instants and
  the instant reached after N working seconds, given a policy (IANA timezone,
  working weekdays, opening/closing local time, holiday dates, per-priority targets).
- Business time is defined in the policy's local wall clock. Each working day's window
  is converted to absolute instants in that zone and intersected with the measured
  interval, so daylight-saving transitions change the absolute instants correctly
  without changing the staffed window. Non-working weekdays and holidays contribute
  nothing, and the clock never runs backwards across a transition.
- Durations are computed in whole seconds, so a target is added exactly: one working
  minute added at 16:59:30 lands at 09:00:30 the next working morning. Only the value
  shown to a person is rounded to minutes.
- The two directions are inverses for the same policy: adding the measured seconds
  reproduces the same instant, and a round trip through the add direction reproduces
  the same elapsed time.
- A published policy is immutable and versioned. It applies from its effective date:
  a policy published for next month changes next month, not today's tickets. The
  version in force when a cycle starts is the version that stays bound to it, so no
  commitment is silently rewritten.

### First-response SLA

- The clock starts at `human_requested_at`: the student set `request_human`, the AI
  handed the case to a human, or an administrator accepted the assignment. The start
  is recorded once per measured cycle and never moved afterwards.
- The clock ends at the first *substantive* `ADMIN` message. Substance is classified
  server-side: a note that only acknowledges receipt is not substantive, and an agent
  cannot declare a one-word acknowledgement to be an answer. An `AI` message, an
  acknowledgement, a system event or a student message never ends it. After it ends,
  the metric is met: time spent waiting for the student afterwards cannot change it.
- The due instant is `add_business_seconds(policy, start, target * 60)` where the
  target is the effective priority's target at the moment the clock started.
- A reply that arrives after the due instant records the breach at that moment, even
  if the bounded worker has not run since; the ticket read and the aggregate counts
  include it.
- A reopen starts a new cycle (`sla_cycle_no` increments) with a fresh start, target
  and due instant. The finished cycle stays readable in the cycle history and in the
  aggregate metrics; it is never overwritten.
- Warning and breach markers are derived, not stored as truth: a warning is recorded
  when elapsed business minutes reach the configured warning ratio of the target, and
  a breach when the due instant passes without a first human response. Each is recorded
  at most once per cycle, and each writes a ticket event and an audit record.
- An agent or the student can read the current measured state: cycle number, start,
  due instant, bound policy version, bound target minutes and the first human response
  instant.

### AI triage

- The allowed context is exactly: the ticket's subject, its category and the messages
  of that ticket. Attachment names, sizes and contents, other tickets, profile fields,
  account state, credit balances and payment data are excluded by construction — the
  context builder cannot request them.
- The triage engine is a deterministic, server-local classifier (no provider call, no
  network, no raw prompt persistence). It returns a suggested category, a suggested
  priority, a confidence value and the handoff reasons that apply. Provider-backed
  triage is out of scope for this phase: no approved `STUDENT_PRIVATE` route exists,
  so any attempt to reach one fails closed and hands off.
- Handoff to a human (`AWAITING_ADMIN`) is mandatory when any of these hold: the
  student requested a human; the engine could not classify the case (low confidence);
  two consecutive failures occurred; the text matches a financial or security topic;
  the text indicates a critical imminent deadline.
- The AI suggestion never changes the effective category or priority. Only an
  administrator with the support scope sets those, with a recorded reason.
- The AI reply is stored in the thread as an `AI` message with its own marker, so the
  student always sees who answered.
- The AI has no write path to credits, accounts, payment approval or file contents
  anywhere in the module. Nothing in the triage path can move a balance, and the
  per-student allowance is free.

### Limits and fallback

- The per-student daily AI allowance defaults to five messages and is configurable
  (lowering allowed; raising is an explicit policy change). The counter is a
  per-owner/per-business-day row in the support module, using the Asia/Hebron business
  day already used by credits.
- The shared global AI budget is the credits module's global daily admission counter
  and cap. A support AI message consumes one unit of that global counter, so support
  traffic competes with the rest of the product's AI traffic instead of running beside
  it for free.
- When the per-student allowance or the global budget is exhausted, the request is not
  silently downgraded: the ticket is placed in `AWAITING_ADMIN` with an explicit
  reason and the student is told that human support is handling it. No unsupported AI
  usage is attempted.
- Two consecutive engine failures on a ticket also hand off and increment the failure
  streak; a subsequent success resets it.

### Attachments and access

- Sharing an attachment is an explicit, confirmed student action on one ticket: the
  student must own the ticket and the asset, and the asset must be an accepted,
  scanned private file. The share is revocable and versioned.
- Reading an attachment requires: an authenticated administrator, the support scope,
  a current MFA proof, a *current* assignment of that administrator to that ticket, and
  a non-revoked share. Every metadata read, grant issue and byte read is audited.
- An administrator without a current assignment is denied and the denial is audited.
  The private library itself remains unreachable from the support module.

### API surface

Student routes (verified adult, owner-scoped):

- `GET /tickets`, `POST /tickets`
- `GET /tickets/{ticket_id}`
- `GET /tickets/{ticket_id}/messages`, `POST /tickets/{ticket_id}/messages`
- `POST /tickets/{ticket_id}/ai-replies`
- `POST /tickets/{ticket_id}/transitions` (request human / confirm resolution / reopen)
- `GET /tickets/{ticket_id}/history`
- `GET /tickets/{ticket_id}/sla`
- `GET /tickets/{ticket_id}/attachments`
- `PUT /tickets/{ticket_id}/rating`

Administrator routes (MFA + support scope):

- `GET /admin/tickets`
- `POST /admin/tickets/{ticket_id}/assignments`
- `GET /admin/tickets/{ticket_id}/messages`, `POST /admin/tickets/{ticket_id}/messages`
- `POST /admin/tickets/{ticket_id}/transitions`
- `PUT /admin/tickets/{ticket_id}/classification`
- `GET /admin/tickets/{ticket_id}/attachments`
- `GET /admin/tickets/{ticket_id}/sla`
- `GET /admin/support/metrics`
- `POST /admin/policies/sla`

Every assigned-ticket action requires a current administrator role, the support scope
and a live MFA proof. The guard runs before an idempotent command, so a replay after
a reassignment or a withdrawn scope is refused instead of returning a cached ticket.
The queue exposes metadata only; the thread, the attachment list and the attachment
bytes need the current assignment.

The existing share/revoke attachment routes keep their path and semantics and are now
reachable for real tickets because creating a ticket creates its authorization row.

### Worker and scheduled work

- A management command sweeps tickets: it records SLA warnings/breaches that are due
  and closes resolved tickets whose quiet period has elapsed. The sweep is idempotent
  and bounded, uses a cursor, and never deletes history.

### Frontend

- A bilingual `/[locale]/support` page: ticket list, ticket creation, thread view with
  author markers (student / AI / human), attachment list with an explicit share
  confirmation, the measured first-response expectation, and the rating control inside
  its window. Loading, empty, denied and unavailable states exist, and the page is
  keyboard reachable with visible focus.

### Compatibility with the documented baseline

- The Phase02 OpenAPI baseline already names the ticket, SLA and support-policy
  operations. The runtime implements that surface with the same paths and semantics.
  Where the baseline names a field the runtime already fixed differently (for example
  the attachment share body), the runtime's existing, tested contract wins and the
  difference is recorded rather than silently diverging.

## Testing Decisions

- A good test asserts observable behaviour through the highest available seam: the HTTP
  API for the domain (as the existing application, credit, private-file and inbox tests
  do), and the pure calendar functions for the time arithmetic, because weekend,
  holiday and daylight-saving cases are exact and cheap to assert as unit tests. No
  test asserts internal helper structure, private attributes or ORM shapes.
- The calendar module is tested for: a request before closing time on a working day; a
  request after hours; a Friday/Saturday request rolling to Sunday; a public holiday
  inside the interval; a target spanning several working days; the spring-forward and
  autumn-back transitions in Asia/Hebron (the local due wall time and the UTC offset
  are both asserted); and the round-trip property between the two directions.
- The SLA domain is tested for: the clock starting only on a human request or handoff;
  an AI reply not satisfying the obligation; a non-substantive administrator message
  not satisfying it; the first substantive administrator message satisfying it;
  waiting for the student afterwards not changing the result; a reopen starting a new
  cycle; and the bound target not being rewritten when the priority later changes.
- The permissions are tested for: a student reading another student's ticket; an
  administrator reading an unassigned ticket; an administrator reading the private
  library; a revoked share; a reassigned ticket; and the audit rows written for each
  allowed and denied access.
- The AI triage is tested for: the allowed context excluding attachment content; the
  handoff on student request, on two consecutive failures, on low confidence, on
  financial text and on security text; the daily allowance boundary at five messages;
  the global budget fallback; the effective priority remaining administrator-controlled;
  and the credit balance being untouched by every AI path.
- The lifecycle is tested for: each permitted transition, each forbidden transition, the
  append-only event log, automatic closure after the quiet period, reopening inside and
  outside the window, and the rating window (rate once, edit inside the window, refused
  outside it).
- Prior art: `tests/api/test_applications.py` for aggregate lifecycle and append-only
  history, `tests/api/test_private_files.py` for ownership and audited access,
  `tests/api/test_notifications.py` for bounded worker sweeps, and
  `tests/api/test_credits.py` for concurrency and idempotency.
- The client test suite keeps its current shape; the support page is verified by
  lint, type-check and build, and the runtime contract check must be regenerated and
  pass.

## Out of Scope

- Real AI provider execution for support, any private-data AI approval, and any
  transport outside the local deterministic triage.
- Payment, checkout, packages, credit purchases and any credit movement caused by
  support activity.
- The administrator console UI for the support queue (Phase15) and the whole of the
  operations dashboard beyond the aggregate support metrics endpoint.
- Product email, push and WhatsApp notifications for support events.
- Actual staffing commitments: the 4/8/24/48 business-hour targets remain experimental
  targets and are not advertised as a service level.
- Browser extension work, legal retention/erasure policy for support data beyond the
  existing account-deletion review scope, and any production scheduler, RLS, backup or
  load evidence.
- Chrome extension integration, portal form support and any automatic application
  submission.

## Further Notes

- The AI-support experiment is bounded on purpose: five free messages per student per
  day inside the global budget, with a human fallback. Its measured effect on support
  load and on resolution quality is a Phase16/17 evidence question, not a Phase13
  claim.
- The daily allowance, the working calendar, the targets, the quiet period, the reopen
  window and the rating window are all configuration in one versioned, auditable policy
  object. The shipped defaults are the sourced ones (Sun–Thu 09:00–17:00
  Asia/Hebron, 4/8/24/48 business hours, 7 days to close, 14 days to reopen, 7 days to
  edit a rating); they are engineering defaults, not a published service level.
- The AI triage in this phase is a deterministic local classifier. That is an
  engineering choice forced by the current provider-approval state, and it is recorded
  as such: the product behaves as designed, and no model output is invented.
- Retained decisions: [ADR0017](../adr/0017-support-sla-and-ai-triage.md). Validation
  evidence and the exact list of skipped checks belong to `tasks/phase-reports/13.md`.
