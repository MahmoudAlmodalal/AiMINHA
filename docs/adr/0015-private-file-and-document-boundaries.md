# ADR0015 — scanned private bytes and immutable document artifacts

Status: accepted for the bounded Phase11 local implementation, not release approval.

## Context

PRD FR-011–014/034–050/072–077, BR-015–018/029–033 and decision OQ-004/007/013/016
require truthful documents, private files, scanner success and a saved result before
charging. Phase10 intentionally has no live or scoped private AI pipeline. Its
synthetic accounting proof must not be relabeled as processing a student's CV.

## Decision

Use two modular services, `private_files` and `documents`, with the existing
identity/privacy and credit kernels. Extend `PrivateAsset` with exact scan/storage
evidence; do not grant administrators access to the library. Use bounded API
uploads and backend-streamed reads with expiring, session-bound grants and current
owner/assigned-share checks. Private file operations are disabled unless an
approved storage root and a working actual ClamAV engine with fresh signatures
are configured. No permissive production scanner implementation exists.

Persist immutable document versions and separate exact owner approvals. Plain
text previews are escaped; PDF and DOCX are rendered locally and pass mandatory
scan/storage admission. A repeat export of an approved saved version reuses the
existing export. An export outage cannot remove or charge again for its source.

Keep real/private extraction and generation closed, offering manual input. Add a
server-only, fixed synthetic document/proposal proof to the existing synthetic
credit kernel. Bind each job's kind/language/operation and saved artifact before
settlement. Synthetic validation accepts only fixed literal evidence. No student
fact becomes trusted automatically and no client selects provider permissions.

Provide an internal immutable submitted-version snapshot prerequisite, without
inventing a Phase12 application aggregate or public submission endpoint.

## Consequences

Scanner/storage failures deny uploads and exports, while manual documents remain
editable. Files and exports share the conservative decimal-byte storage budget.
Production storage/scanner/retention/backup and real AI approvals remain independent
external gates. The phase report must distinguish genuine scanner evidence,
mocked failure tests, local synthetic accounting and checks not performed.
