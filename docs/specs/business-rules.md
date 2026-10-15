# Business rules and decision dispositions

2026-10-15. **PASS — documented rules/traceability.** [PRD](../source/PRD.md) source wording is retained below. Latest [UD-001/002](../source/2026-10-15-owner-decisions.md) controls recovery configuration/work scope; owner decisions §أ 1–7 differ from analyst defaults and external approvals. [Conflict register](requirements-conflicts.md), [gates](missing-inputs.md), [scenarios](acceptance-scenarios.md).

## All 54 source rules with acceptance paths

| ID | Exact source rule | Implementation invariant / resolution | Acceptance path |
|---|---|---|---|
| BR-001 | A registration with self-declared age under 18 must not activate a student account. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-004; source BR-001 |
| BR-002 | Birth date checks are declaration-based and must not be presented as independent identity verification. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-004; source BR-002 |
| BR-003 | Each eligible account can receive the signup grant only once, including after linked OAuth login. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-005; source BR-003 |
| BR-004 | Only **Student** and **Admin** are formal MVP user roles; AI and extension are controlled system actors, not user roles. | Exactly Student/Admin; scoped MFA Admin; no private-library privilege; audit is required. | CASE-FR-007; source BR-004 |
| BR-005 | AI-extracted profile fields remain proposals until accepted/corrected by the student. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-013; source BR-005 |
| BR-006 | Missing facts are never invented or treated as confirmed. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-014; source BR-006 |
| BR-007 | No unapproved imported scholarship may be publicly listed. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-017; source BR-007 |
| BR-008 | A material source change requires documented review before altering approved published criteria. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-020; source BR-008 |
| BR-009 | Every published listing must have a traceable source and latest check state/date. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-021; source BR-009 |
| BR-010 | A student report does not automatically erase a scholarship; Admin evaluates and may suspend it for credible risk. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-024; source BR-010 |
| BR-011 | Hard eligibility criteria take precedence over Match Score. | Mandatory deterministic failure/Unknown is authoritative; score/version/contributions cannot turn it into pass or admission probability. | CASE-FR-028; source BR-011 |
| BR-012 | Unknown mandatory-criterion evidence means **Undetermined**, not satisfied. | Mandatory deterministic failure/Unknown is authoritative; score/version/contributions cannot turn it into pass or admission probability. | CASE-FR-029; source BR-012 |
| BR-013 | Match Score is explainable fit, **never** an admission-probability statement. | Mandatory deterministic failure/Unknown is authoritative; score/version/contributions cannot turn it into pass or admission probability. | CASE-FR-030; source BR-013 |
| BR-014 | Matching results retain the applicable rule/weight version. | Mandatory deterministic failure/Unknown is authoritative; score/version/contributions cannot turn it into pass or admission probability. | CASE-FR-031; source BR-014 |
| BR-015 | Supported AI draft types are CV, Motivation Letter, Personal Statement and Scholarship Essays. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-034; source BR-015 |
| BR-016 | AI cannot fabricate GPA, awards, degrees, jobs or credentials; student approves final content. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-035; source BR-016 |
| BR-017 | Versions attached to student-confirmed submitted applications cannot be modified through ordinary edits. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-048; source BR-017 |
| BR-018 | Restoring a historic document version creates a new current version instead of deleting history. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-047; source BR-018 |
| BR-019 | The student—not MinhaAI—performs the actual application submission on the external portal. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-054; source BR-019 |
| BR-020 | Autofill success must never automatically mark an application **Submitted**. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-054; source BR-020 |
| BR-021 | Student-reported statuses and any officially integrated statuses must remain source-distinguishable. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-055; source BR-021 |
| BR-022 | Extension autofill requires explicit student initiation on a permitted form. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-060; source BR-022 |
| BR-023 | Unconfirmed sensitive fields cannot be inserted as though approved. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-063; source BR-023 |
| BR-024 | No external password/OTP capture, CAPTCHA bypass or automated final submission. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-065; source BR-024 |
| BR-025 | External compatibility and remote saving are not guaranteed; failed forms must offer a manual path. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-066; source BR-025 |
| BR-026 | Core profile/basic search are free; paid AI services are governed by configured Credits. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-069; source BR-026 |
| BR-027 | Free onboarding Credits may only be granted after qualifying account activation and cannot be farmed through auth method switching. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-005; source BR-027 |
| BR-028 | Credits do not expire because of elapsed time while the account remains active; deletion is a separate cancellation event. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-078; source BR-028 |
| BR-029 | A configured paid service may start only after the student sees and confirms its Credit price. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-072; source BR-029 |
| BR-030 | Price changes do not retroactively change a previously confirmed operation. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-073; source BR-030 |
| BR-031 | Before execution, an accepted operation reserves the agreed available Credits. | Stable operation ID, same-owner snapshots, one terminal witness/result, transaction+fence, unknown outcome reconciliation, no blind retry/refund. | CASE-FR-074; source BR-031 |
| BR-032 | Each successful paid operation produces one settled debit, even under retries/concurrent callbacks. | Stable operation ID, same-owner snapshots, one terminal witness/result, transaction+fence, unknown outcome reconciliation, no blind retry/refund. | CASE-FR-075; source BR-032 |
| BR-033 | Technical failure releases/resolves the reservation without an incorrect final debit. | Stable operation ID, same-owner snapshots, one terminal witness/result, transaction+fence, unknown outcome reconciliation, no blind retry/refund. | CASE-FR-076; source BR-033 |
| BR-034 | A transfer receipt by itself is not proof of funds received; Admin verification is mandatory. | Advanced payment workflow only; disabled Beta. Independent received-funds proof, unique transfer identity, no receipt-only grant; G-PAID. | CASE-FR-083; source BR-034 |
| BR-035 | A transfer/payment reference cannot activate two purchases or duplicate Credits. | Advanced payment workflow only; disabled Beta. Independent received-funds proof, unique transfer identity, no receipt-only grant; G-PAID. | CASE-FR-085; source BR-035 |
| BR-036 | Rejection or request-for-new-proof must carry an Admin reason and user-visible state. | Advanced payment workflow only; disabled Beta. Independent received-funds proof, unique transfer identity, no receipt-only grant; G-PAID. | CASE-FR-084; source BR-036 |
| BR-037 | Credits are not ordinarily refunded as money following approved payments except where technical failure or applicable law requires a remedy; final legal policy [TBD]. | Advanced payment workflow only; disabled Beta. Independent received-funds proof, unique transfer identity, no receipt-only grant; G-PAID. | CASE-FR-088; source BR-037 |
| BR-038 | Product notices are delivered in-app only during MVP. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-093; source BR-038 |
| BR-039 | Equivalent notices for the same event and recipient should be deduplicated while preserving material subsequent changes. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-091; source BR-039 |
| BR-040 | Support tickets follow the six named states, retaining a full transition history. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-099; source BR-040 |
| BR-041 | Human handoff is triggered by request, low confidence, repeated failure, sensitive/financial issue or critical deadline. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-097; source BR-041 |
| BR-042 | AI Support must not approve money receipt or alter financial balance. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-098; source BR-042 |
| BR-043 | AI Support can respond 24/7; human agents work within the Admin-configured schedule. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-101; source BR-043 |
| BR-044 | Human **first-response** SLA is configurable by priority and measured in configured working time. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-102; source BR-044 |
| BR-045 | Resolved/closed tickets permit configured closure/reopen and support-quality rating; exact timing [TBD]. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-100; source BR-045 |
| BR-046 | Admin access requires MFA for launch and enforces least privilege over personal documents. | Exactly Student/Admin; scoped MFA Admin; no private-library privilege; audit is required. | CASE-FR-007; source BR-046 |
| BR-047 | Sensitive Admin changes and financial actions must be attributable and auditable. | Exactly Student/Admin; scoped MFA Admin; no private-library privilege; audit is required. | CASE-FR-109; source BR-047 |
| BR-048 | A confirmed account deletion request immediately disables service and freezes Credits for **30 calendar days**. | UD-001: Admin-configurable positive recovery_days, versioned calendar policy and stored immutable per-request cutoff; default 30, not a hard-coded period. See ADR 0008; legal envelope is external. | CASE-FR-117; source BR-048 |
| BR-049 | Restoring a deletion-pending account within 30 days restores uncanceled wallet balance and retained data. | UD-001: Admin-configurable positive recovery_days, versioned calendar policy and stored immutable per-request cutoff; default 30, not a hard-coded period. See ADR 0008; legal envelope is external. | CASE-FR-118; source BR-049 |
| BR-050 | After 30 days, deletion of eligible user data begins and remaining Credits are canceled. | UD-001: Admin-configurable positive recovery_days, versioned calendar policy and stored immutable per-request cutoff; default 30, not a hard-coded period. See ADR 0008; legal envelope is external. | CASE-FR-119; source BR-050 |
| BR-051 | Document-version immutability for applications cannot obstruct legally valid permanent data deletion. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-119; source BR-051 |
| BR-052 | Only valid, documented legal retention exceptions survive final deletion; backup handling follows approved policy [TBD]. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-120; source BR-052 |
| BR-053 | Work that runs asynchronously must expose nonmisleading progress and failed states. | Source rule retained; owner-bound guarded command and immutable evidence; no UI-only authorization. | CASE-FR-122; source BR-053 |
| BR-054 | Retried operations must not replay irreversible effects or money movement. | Stable operation ID, same-owner snapshots, one terminal witness/result, transaction+fence, unknown outcome reconciliation, no blind retry/refund. | CASE-FR-124; source BR-054 |

## All 26 source open-question dispositions

| OQ | Current disposition / gate |
|---|---|
| OQ-001 | Advanced local payments G-PAID; wholly disabled Beta, no invented currency/account. |
| OQ-002 | Beta defaults 30 signup once, 6/day spend; 1 matching /4 extraction /6 document; no daily grant; all versioned, paid packages off. |
| OQ-003 | Permitted official hybrid sources + human review; initial catalog counts conditional, actual sources/sites G-SOURCE/G-EXT. |
| OQ-004 | PRIVATE requires explicit scoped consent plus individual processor/model/data/region approval; public/synthetic also approved; G-PROVIDER. |
| OQ-005 | Legal/privacy/terms/refund/jurisdiction approval G-LEGAL remains external. |
| OQ-006 | UD-001 Admin-configurable calendar recovery; 24h temp/72h post-window active-file/backup<=30d are qualified defaults, not legal retention signoff. |
| OQ-007 | Owner decision: no admin library browse, only explicitly shared accepted ticket asset for current assigned scoped Admin, with audit. |
| OQ-008 | Proposed Sun–Thu 09–17 Asia/Hebron; priority 4/8/24/48 business hours; staffing and warning/route values G-TICKET. |
| OQ-009 | First human response measures business time from human request; AI never satisfies/pauses; later Awaiting Student cannot alter already measured first response. |
| OQ-010 | Proposed close after7d, reopen14d, rating edit7d; exact boundaries documented, rating scale/eligibility G-TICKET. |
| OQ-011 | Base profile categories sourced; exact stage compulsory fields/scales/proofs G-PROFILE; Unknown preserved. |
| OQ-012 | Proposed 30/25/20/15/10 weight and >=70% coverage; versioned, no mandatory-fail override; confidence/quality calibration G-MEASURE. |
| OQ-013 | Proposed PDF/DOCX/PNG/JPG, 5MB/file 10MB/student 750MB global; decimal bytes assumption; scanner/private quotas G-SCANNER. |
| OQ-014 | Preparing/Ready/Submitted/Under Review/Accepted/Rejected + Withdrawn; round history and unlisted corrections gated G-STATUS. |
| OQ-015 | Chrome desktop first, permitted tested sites, no auto-submit/secret handling; three sites and >=90% are proposed validation goals, actual matrix G-EXT. |
| OQ-016 | Five billing states; reserve once, accepted valid saved result before debit; 15min→reconcile/24h target, no timed blind release. |
| OQ-017 | Confirmed donor date only, 14/7/3d+24h offset defaults, version-recipient dedupe, in-app; exact configured offset encoding documented in schema. |
| OQ-018 | Warm search/matching and uptime/RPO/RTO figures are proposed fixtures only; actual benchmarks/worker/provider evidence G-MEASURE/G-HOSTING/G-RESTORE. |
| OQ-019 | Guidance/triage only; human on request/two failures/uncertainty/financial-security/critical deadline; no financial/account action by AI. |
| OQ-020 | UD-001 + ADR0008: trusted receipt strictly before captured restore_until; equality expired; lock same lifecycle row; calendar defaults are not a permanent 720h invariant. |
| OQ-021 | Pilot/load/bilingual/security goals are proposed; safety-critical tests mandatory; real evidence and owner release decision G-SIGNOFF/G-MEASURE. |
| OQ-022 | Explicit owner decision permits public published browsing; saving/personalization requires active verified adult. |
| OQ-023 | Internal aggregate telemetry, no third-party marketing; 90d content-free security proposal, other record retention G-LEGAL. |
| OQ-024 | User confirmed AiMINHA; source at docs/source/PRD.md per AGENTS.md; no push/commit authorized. |
| OQ-025 | No approved competitor reference; optional P2 UX research later. |
| OQ-026 | No geography/language/payment/type expansion without separate change control; required current Advanced features not silently removed. |

## Recovery policy contract — UD-001

Scoped MFA Admin may publish a new immutable retention policy with positive integer `recovery_days`, calendar-day calculation, IANA zone, effective timestamp and reason. Default is 30 calendar days/Asia/Hebron from the PRD/decision context, expressly an initial configurable setting. The Admin cannot edit an existing policy version or an already confirmed deletion deadline. Legal min/max/envelope are independently approved; no production setting is admitted without that envelope. No paid resource or legal permission follows from an Admin toggle.

At deletion confirmation, capture policy ID/version, recovery_days, recovery_timezone, confirmed_at, computed restore_until and prior account state in the same locked transaction; disable access/freeze wallet. Compute same local wall time recovery_days later using that IANA zone, convert to UTC, shift a nonexistent target to the next valid instant and choose the later instant for an ambiguous fold (proposed engineering resolution). Restore trusted receipt < restore_until; equality fails. Purge may claim only at/after cutoff under the same lifecycle lock. Restore unfreezes original balance; final cancellation unique after unresolved holds reconciled. Config changes apply only to later deletion confirmations. [ADR 0008](../adr/0008-configurable-recovery-period.md) is the exact design contract; real retention/legal approval remains G-LEGAL.

## Engineering assumptions versus product authority

Page limits/ETags/session durations/lease/retry settings, decimal MB, detailed state edges, donor reminder offset encoding, proof routine interfaces and token exchange are engineering decisions, not original interview approvals. They are fully stated in architecture/schema contracts and test paths, fail closed where required evidence is absent, and remain reviewable. No source TBD becomes a measured fact. No runtime acceptance case has run in this documentation-only phase.
