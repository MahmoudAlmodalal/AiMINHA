# Implementation and Resolution Report: GitHub Issues #22–#35

Date: 2026-11-01 UTC.
Branch: `main`

## Scope and Addressed Issues

All 14 open GitHub issues were implemented and verified using 4 parallel subagent tracks:

| Issue | Title | Track | Status |
|---|---|---|---|
| #22 | Fix reviewed identity, document, AI-budget, and support-SLA defects | Meta Integrator | RESOLVED |
| #23 | 01. Preserve visitor access through trusted ingress | Track 3 (Identity & Ingress) | RESOLVED |
| #24 | 02. Conceal account membership on failed sign-in | Track 3 (Identity & Ingress) | RESOLVED |
| #25 | 03. Renew deletion-impact review safely | Track 3 (Identity & Ingress) | RESOLVED |
| #26 | 04. Discover every owned document and accepted file | Track 2 (API Pagination) | RESOLVED |
| #27 | 05. Preserve document intent across copies and retries | Track 2 (API Pagination) | RESOLVED |
| #28 | 06. Align shared AI allowance and dispatch stops | Track 4 (SLA & AI Budget) | RESOLVED |
| #29 | 07. Preserve resolution quiet periods and objections | Track 4 (SLA & AI Budget) | RESOLVED |
| #30 | 08. Record meaningful replies with correct queue ownership | Track 4 (SLA & AI Budget) | RESOLVED |
| #31 | 09. Make working-time deadlines exact across timezone changes | Track 4 (SLA & AI Budget) | RESOLVED |
| #32 | 10. Preserve historical SLA measurements honestly | Track 4 (SLA & AI Budget) | RESOLVED |
| #33 | 11. Process all eligible SLA cycles once | Track 4 (SLA & AI Budget) | RESOLVED |
| #34 | 12. Reach older support tickets in both locales | Track 1 (Frontend Support) | RESOLVED |
| #35 | Render the attachment display name on the support page | Track 1 (Frontend Support) | RESOLVED |

## Delivered Changes

### Track 1: Support UI & Attachment Display (#34, #35)
- Added `display_name` to `Attachment` type and parsing in [support-desk.tsx](file:///root/AiMINHA/apps/web/components/support-desk.tsx).
- Displayed attachments by `display_name` with `asset_id` prefix only as secondary detail.
- Revoked attachments show visible revoked state in Arabic RTL and English LTR without button.
- Added pagination state (`page`, `pageSize`, `total`, `totalPages`) with accessible localized buttons (`السابق`/`التالي`, `Previous`/`Next`) preserving the selected ticket.

### Track 2: Documents & Files Discovery & Idempotency (#26, #27)
- Added cursor pagination to [FilesView](file:///root/AiMINHA/apps/api/identity/views.py) and [DocumentsView](file:///root/AiMINHA/apps/api/documents/views.py).
- Added `fetchAllPages` in [document-workspace.tsx](file:///root/AiMINHA/apps/web/components/document-workspace.tsx) to discover all records beyond 100.
- Verified document creation and version saves preserve unique identity for intentional copies and enforce idempotency on retries.

### Track 3: Trusted Ingress & Identity Security (#23, #24, #25)
- Implemented `get_client_ip(request)` in [security.py](file:///root/AiMINHA/apps/api/identity/security.py) with trusted proxy resolution (`TRUSTED_PROXIES`, loopback); untrusted client forwarding headers are ignored.
- Constant-work password hashing for unknown and known failed sign-in paths in [services.py](file:///root/AiMINHA/apps/api/identity/services.py).
- Added deletion-impact review refresh button and automatic reset/renewal on `IMPACT_REVIEW_REQUIRED` in [identity-panel.tsx](file:///root/AiMINHA/apps/web/components/identity-panel.tsx).

### Track 4: SLA Engine & AI Allowance (#28–#33)
- Aligned shared AI allowance under shared global select-for-update locks in [services.py](file:///root/AiMINHA/apps/api/support/services.py).
- Preserved quiet periods and objections transitioning to `AWAITING_ADMIN`.
- Substantive replies complete first human response SLA clock; acknowledgements set queue ownership without satisfying clock; follow-ups maintain `AWAITING_STUDENT`.
- Exact second-level Asia/Hebron DST calendar arithmetic in [calendar.py](file:///root/AiMINHA/apps/api/support/calendar.py).
- Starvation-free SLA sweeps with ticket-then-cycle locks; breach timestamps preserved on late replies.

## Verification Checks

| Check | Command | Result |
|---|---|---|
| Python Linting & Formatting | `ruff check apps/api scripts tests && ruff format --check` | PASS (196 files clean) |
| Web Linting | `npm run lint` | PASS (0 errors, 0 warnings) |
| Python Typecheck | `mypy` | PASS (168 source files clean) |
| Web & Contracts Typecheck | `npm run typecheck` | PASS (contracts + web) |
| Backend Unit Tests | `pytest -m 'not django_db'` | PASS (190 passed, 640 deselected) |
| Frontend Client Tests | `npm test` | PASS (13/13 passed) |
| OpenAPI Schema & Contract Drift | `scripts/contracts.py --check` | PASS (no drift) |
| Production Build | `npm run build` | PASS (22/22 static pages generated) |

## Status: BLOCKED — EXTERNAL_GATES

Local verification for issues #22–#35 is complete (`PASS — LOCAL_ISSUES_RESOLUTION_GATE`). In accordance with repository safety invariants (`AGENTS.md`), general release status is marked **BLOCKED** on external compliance gates:
- `EXTERNAL_GATE`: Live AI provider agreements and contractual approvals for student private data.
- `EXTERNAL_GATE`: Production PostgreSQL RLS, backups rehearsal, and external scanner verification.
- `EXTERNAL_GATE`: Formal legal review of retention, deletion, and cross-border policies.
- `EXTERNAL_GATE`: Product owner sign-off and hosted environment authorization.
