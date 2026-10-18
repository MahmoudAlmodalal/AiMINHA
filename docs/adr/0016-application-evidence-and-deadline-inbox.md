# ADR0016 — application evidence and confirmed-deadline inbox

Status: accepted for the bounded Phase12 local implementation; external release
and lawful official-status/deletion approvals remain independent.

## Context and source traces

PRD FR-044/045/048/051–058/089–093, BR-017–021/038–039/051,
AC-016–019/029–030, decision OQ-014/017 and architecture R17/R18 require an
owned tracker, immutable submission evidence, separate official/student reports
and nonmisleading internal reminders. No external portal submission or lawful
official-status feed is currently approved.

The current catalog has reviewed deadline records but no round IDs. Its
`required_documents` field is a reviewed string list, not a typed form/action
checklist. These gaps cannot be filled by guessing academic rounds or mandatory
steps from free text.

## Decision

Use an `applications` aggregate with contiguous append-only status/activity
history and a CAS head. The student alone explicitly reports submission after
external action. Each owner/scholarship/reviewed round has one lifetime application;
a different round creates another application. Ordinary edits never reset terminal
states or mutate submitted manifests. Exact approved document versions or accepted
scanned upload identities are frozen atomically at the submission event.

Represent reviewed document strings as required DOCUMENT slots. An empty list is
unknown completeness and cannot produce Ready. Additional form/action schemas are
not invented. Changes to source requirements require explicit pre-submission
review/rebase, preserving all prior source/version and artifact history.

**ASSUMPTION:** distinct normalized reviewed round labels provide stable identity
across deadline revisions. A sole unlabeled round gets one stable single-round
key; it does not imply an invented year. Multiple blank/duplicate labels are
ambiguous and fail closed. Renamed labels do not silently map an old application
to a new round. This may require source review before creating another round.

Store official reports separately with origin, source and observation time.
No student field can certify official status. Live official ingestion stays closed
until a lawful documented integration and independent verification exist; local
synthetic evidence is labeled synthetic and never presented as verified official.
Submitted-artifact deletion requests follow a separate authorized review path;
ordinary edit/deletion cannot impersonate legal approval or thaw evidence.

Use `notifications` for immutable deadline revisions and finite recoverable
scheduling/delivery into one private in-app inbox. Only current approved published
fresh CONFIRMED donor instants with an unambiguous source zone qualify. Unknown,
rolling, date-only, stale, revoked or ambiguous facts produce no timed countdown
or reminder. Recheck source, version/head, active recipient and relationship at
delivery; superseded pending reminders cancel while delivered/read history stays.
Cancellation is terminal for an attempt. Re-enabling a preference or saving again
before a future due time may create another attempt; a partial unique constraint
allows only one scheduled/delivered attempt for a recipient/event-version/offset,
so cancelled history is preserved without preventing a valid new opt-in.

**ASSUMPTION:** offsets use the existing R18 elapsed-minute interpretation:
20,160/10,080/4,320/1,440 minutes. Subtract from the sponsor's verified absolute
instant, then display in the student's selected IANA zone. Do not invent a wall
time for a date-only deadline. Schedule future due times only; no retroactive
missed reminders or guaranteed student viewing is claimed.

## Consequences and gates

Owner-scoped reads/writes, strict DTOs, session/CSRF checks, immutable SQL evidence,
idempotency and auditable typed destinations are required. No AI, new Credits,
external submission, email/push/WhatsApp or support workflow is introduced.
Real official integration, lawful content erasure/retention, production scheduler,
RLS/performance/backup evidence and release signoff remain external gates.
