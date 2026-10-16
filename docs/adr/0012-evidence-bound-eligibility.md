# ADR 0012 — deterministic eligibility with evidence-bound fit

Status: bounded Phase08 runtime decision, 2026-10-16. Verification results belong
to [report08](../../tasks/phase-reports/08.md), not this decision record.
Authority: current Phase08 request; AGENTS.md deterministic/privacy invariants;
PRD F-02/F-04, FR-008–010/013/014/028–033, BR-011–014, AC-005/009–011;
decision resolution OQ-011/012/018/022; architecture schema-notes R07/R09.

Store typed manual student profile facts in immutable owned versions. Null means
unknown; an explicitly confirmed empty list means the student has declared no
items. Explicit owner review records which supplied facts are confirmed and the
review time. Confirmation is a student declaration, not institutional credential
verification. No source-file, extraction or AI provenance can be fabricated through
the manual profile contract. Unknown and unconfirmed facts cannot satisfy a rule.
Only the verified active adult owner can read or edit the profile or evaluation;
Admin moderation does not grant profile access.

Scholarship publication does not turn prose criteria or catalog filter labels
into machine-readable verified requirements. A scoped `MODERATION` Admin with
current server MFA reviews a separate immutable structured rule set against the
exact published scholarship version/content hash and source. Every structured
rule refers to its source criterion index and evidence text; verified status is
an attributable human assertion. The `complete` assertion requires coverage of
every criterion index. An empty criterion basis cannot prove eligibility. Human
review is not a claim that extraction or semantic validation has occurred.

Rule-set approval requires current permitted publication and `CURRENT` source
freshness. An absent freshness window/check remains `UNKNOWN` and cannot certify
current rules. Evaluation rechecks source permission, exact publication and current
rule/profile heads. Source staleness or unknown freshness removes verified-rule
coverage and explains the uncertainty. An old evaluation cannot be presented as
current after its bound inputs change; read-time freshness/version validation
rejects obsolete snapshots. Immutable retained history does not confer a current
decision or access right.

Evaluate every structured rule as `PASS`, `FAIL` or `UNKNOWN`. A verified known
mandatory failure yields `INELIGIBLE` even when other requirements are unknown,
the completeness assertion is false, or the fit score is high. Otherwise an
unknown mandatory result, missing/incomplete basis or empty criterion basis
yields `INSUFFICIENT_INFORMATION`; a basis whose comparisons are all unknown also
stays insufficient. `ELIGIBLE` requires a complete reviewed basis, at least one
known comparison and all mandatory rules satisfied. A fit result cannot modify
that decision.
The runtime name `INSUFFICIENT_INFORMATION` expresses PRD `Undetermined` and the
earlier architecture's `UNKNOWN`; individual rules still use `UNKNOWN`.

The initial deterministic fit policy fixes academic/field/nationality-residency/
language/interest weights to 3000/2500/2000/1500/1000 basis points. A domain is
covered only when it contains at least one reviewed rule and all its comparisons
are known. Known failure is covered evidence with zero fit; an unknown domain
has null score/contribution. Domain fit is the arithmetic mean of binary rule
matches. Coverage is the sum of covered domain weights. At coverage at least
7000 basis points, fit is the weighted mean over those covered domains; below
that threshold it is null with insufficient-coverage reasons. Use decimal
arithmetic and half-up rounding to integer basis points. These coverage and
normalization details are explicit engineering assumptions because OQ-012 does
not define them. Multiple rules in one domain cannot increase its total weight.

This is an initial evidence-backed deterministic fit indicator, not the PRD's
future AI/RAG explanation, a calibrated ranking model or an acceptance
probability. Return each rule's decision, evidence, missing input, domain
contributions, exact snapshots and engine/weight versions. Confidence is
`UNCALIBRATED`; no numeric confidence is invented. Unknown evidence is not
silently counted as either a failure or a pass.

The explicit GPA schemes are `PERCENT_100`, `GPA_4_0` and `GPA_5_0`. Within the
declared scheme, normalization is `value / maximum` with finite bounded decimal
values. It does not establish equivalence between institutions or schemes.
Compare only matching known schemes; different known schemes, `UNKNOWN` or a
missing scale yield an unknown rule. No guessed scale, percentage-to-GPA admission
conversion or unsupported grading equivalence is allowed. Language comparison
supports explicitly declared CEFR A1–C2 levels only; it does not convert IELTS,
TOEFL or other credentials or authenticate language proof. Field/country labels
use explicit values rather than inferred synonyms or nationality equivalences.

The initial flat mandatory rule list is conjunctive. Cross-field alternatives,
exclusions, age/date conditions and institution-specific credentials outside the
typed operators remain unsupported/unknown; human review cannot silently rewrite
an OR condition as two mandatory AND conditions. Syntax-only code validation is
not an approved geopolitical or academic dictionary.

The runtime schema supplies typed owned profile/evaluation APIs and a scoped
rule-review API. Profile writes use CSRF, actor-scoped idempotency and quoted
revision `If-Match`, including revision zero for initial creation. Evaluations pin
the exact current profile and published scholarship version IDs and capture the
applicable rule set, policy and time. Evaluation reads are owned and reauthorize
the current snapshots. Rule replacement is human-reviewed and compare-and-swap;
student requests cannot set verified rules, owner, status, score or policy.

No AI provider, credit operation, upload, application tracking, reminder,
scraper or paid resource is added. Admin weight/rule-policy management beyond
this fixed versioned policy remains partial FR-031 coverage; no general Admin
console or live MFA integration is inferred. Real academic dictionaries,
credential authentication, grading equivalences, policy calibration, source
permissions and production DB-role/RLS/legal/release evidence remain independent
gates. The warm p95 <=2s target requires the explicit measurement plan in the
[Phase08 specification](../specs/phase-08-eligibility.md), not an invented SLO.
