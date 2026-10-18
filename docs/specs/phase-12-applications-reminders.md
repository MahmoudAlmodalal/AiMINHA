# Phase12 — applications, immutable history and deadline alerts

## Authority and boundaries

Only `prompts/12-applications-and-reminders.md` and the current owner instruction
authorize this phase. The PRD, decision resolution, provider strategy and additive
owner decisions are present and preserved. No later phase, commit/push, deployment,
paid resource or real provider/source integration is authorized.

| Boundary | Source trace |
|---|---|
| Owned saved scholarships and per-round preparation tracker | FR-051/052/056; PRD F-07; OQ-014 |
| Explicit student-only reported submission and sourced history | FR-053–055/058; BR-019–021; AC-018/019 |
| Exact artifacts, owner approval and immutable submitted evidence | FR-044/045/048/049; BR-017/018; AC-016/017 |
| Legal deletion independent of normal history edits | BR-051/052; decision §و7; architecture R21 |
| Verified-donor deadlines and private in-app reminders | FR-057/089–093; BR-038/039; OQ-017; AC-029/030 |
| Account/lifecycle/permission isolation and truthful failure | AGENTS security invariants; FR-007/110/113–115; NFR-006–011 |

## Agreed state and artifact contract

The documented engineering matrix is:

- PREPARING → READY or WITHDRAWN.
- READY → PREPARING, SUBMITTED or WITHDRAWN.
- SUBMITTED → UNDER_REVIEW, ACCEPTED, REJECTED or WITHDRAWN.
- UNDER_REVIEW → ACCEPTED, REJECTED or WITHDRAWN.
- ACCEPTED, REJECTED and WITHDRAWN have no ordinary status exit.

The Ready back edge and direct outcomes from Submitted are pre-existing
architecture assumptions. Evidence-only corrections append a referenced self-edge;
they cannot silently reverse a terminal state. Notes/activity preserve snapshots.
Every event has a server record time, distinct observed time, actor and source.

Ready requires a known reviewed checklist and exact owned approved document
versions or accepted scanned uploads. No empty/unknown requirements set is called
complete. An explicit same-round pre-submission rebase can capture new reviewed
source facts without rewriting history or silently mapping old selections.

Submitted requires a separate explicit statement that the student submitted on the
external portal. Selected references/hashes are copied into immutable event-bound
evidence and approved document snapshots. Later document edits or restore create
new versions and cannot change those references. Ordinary file deletion protects
submitted upload evidence. Authorized legal review requests are distinct from
editing; no client can mark content erased or manufacture approval.

Official status has separate origin/source/observed/recorded evidence and never
overwrites the student-reported state. Real official ingestion remains unavailable
without lawful integration. A fixed local synthetic proof must say synthetic,
not verified official. Terminal correction/official precedence is not invented.

## Deadline and inbox contract

Use the strict existing catalog deadline parser and reviewed round identity. Current
publication, permission, freshness, exact version and active owned relationship are
checked when scheduling and again when delivering. Historical pinned application
dates are not a current countdown source. Unknown/date-only/rolling/ambiguous/stale
facts return an unavailable deadline, with no guessed end-of-day or timezone.

Immutable event versions and per-recipient/event-version/offset uniqueness prevent
duplicate delivery. Only future due times are initially scheduled. A source change
cancels pending old-version reminders; delivered/read evidence is preserved. The
finite management command is retryable and needs production scheduling separately.
No product email/WhatsApp/Web Push is implemented.
Cancelled attempts are retained. A later opt-in before due may create a fresh
attempt, while one live/delivered logical reminder remains unique. Repeated
deliveries and read acknowledgments never create duplicate inbox effects.

Source timezone fixes the verified instant; elapsed 14/7/3-day and24h offsets are
the R18 engineering assumption, not a newly approved calendar interpretation.
Storage uses UTC; user display uses a validated selected IANA zone. Asia/Hebron is
the sourced initial display assumption and can be changed explicitly. Optional
preferences do not grant access or suppress mandatory security categories.

The inbox stores typed contextual targets rather than arbitrary client URLs.
Missing/inaccessible targets cannot bypass ownership. Read acknowledgment is once
set. Source/document notices require known evidence; missing information itself
does not justify a fabricated deadline or official result.

## Scope gaps, assumptions and external gates

- Round identity is derived from distinct reviewed normalized labels because the
  catalog contains no stable source round ID. A single unlabeled round is one
  stable unknown identity; ambiguous/duplicate labels fail closed. No new year or
  round is inferred automatically.
- Reviewed document strings are DOCUMENT requirements. Typed mandatory forms or
  actions are absent and are not guessed; richer completeness stays gated.
- Legal content erasure must follow an approved scoped policy and exact storage
  cleanup; a pending request is not an erasure receipt or permission to edit.
- Live official feeds, source permission/quality, production durable scheduling,
  DB roles/RLS, performance, backups/restore, accessibility/browser and release
  evidence remain independent checks; exact outcomes/skips belong in report12.

See [ADR0016](../adr/0016-application-evidence-and-deadline-inbox.md) and the final
`tasks/phase-reports/12.md` for validation and remaining gates.
