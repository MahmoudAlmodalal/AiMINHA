# Phase08 — deterministic eligibility and evidence-backed matching

The current request authorizes only Phase08 and parallel agents. The user's
subsequent explicit `Push` instruction authorizes a Git commit and push only;
deployment, paid resources and later-phase work remain outside scope. Source
files and earlier phase outcomes remain unchanged. [ADR0012](../adr/0012-evidence-bound-eligibility.md)
records the runtime choices; [report08](../../tasks/phase-reports/08.md) records
actual commands, results and remaining defects. This is not release approval.

## Source traces and bounded scope

`U08.1`–`U08.5` refer to the five current work items. The authoritative feature
baseline is [PRD v3.0.0](../source/PRD.md). Numerical policy defaults in the
[decision resolution](../source/MinhaAI_PRD_Decision_Resolution_AR.md) remain
analyst-proposed operating defaults requiring quality calibration, rather than
owner-approved academic equivalences or measured guarantees.

| Work | Runtime boundary | Source trace |
|---|---|---|
| Typed eligibility profile | Manual nullable nationality/residency, degree, major, qualification, GPA with explicit scale, language and preferred-country facts; explicit student confirmation, immutable versions and ownership | U08.1; F-02; FR-008–010/013/014; BR-005/006; AC-005; OQ-011; schema-notes R07 |
| Three-state rules | Separate exact-version human-reviewed machine rules; per-rule PASS/FAIL/UNKNOWN; mandatory failure dominates; incomplete or unknown basis cannot imply eligibility | U08.2; F-04; FR-028/029/032/033; BR-011/012; EC-004/008/009; AC-009/010; R09 |
| Explainable initial fit | Fixed five-domain weights and >=70% evidence coverage, explicit contributions and limitations; null fit below threshold; no admission-probability label | U08.3; FR-030/031/033; BR-013/014; AC-011; OQ-012; R09 |
| Known-scale comparisons | Explicit tested within-scale GPA normalization; unknown or different schemes remain unknown; no inferred credential/CEFR equivalence | U08.4; FR-014/029; EC-004; OQ-011; G-PROFILE |
| Student API/UI and tests | Verified adult owner, current snapshots, bilingual uncertainty/evidence states and negative permissions | U08.5; FR-006/010/028–033; NFR-003/013/015/016/024/028; UX R12/R14 |
| Performance plan | Authenticated warm deterministic API plus PostgreSQL measurement, p95 target <=2 seconds | U08 gate; NFR-018; OQ-018; G-MEASURE |

Manual eligibility/profile operations are free deterministic operations under
decision §ب. They do not become quoted or funded AI matching explanations. PRD
FR-030 AI/RAG rationale and configurable Admin policy management are not completed
by this initial deterministic fit slice. AI, credits, files and extraction retain
their separately authorized phase and approval boundaries.

## Profile evidence and unknown values

Only an active server-verified adult student can access their own profile and
evaluations. A foreign private UUID and a missing private UUID share a 403 denial;
opaque IDs do not confer access. An Admin scope cannot impersonate a student or
list/read profile facts. Denial and sensitive mutations use metadata-only audit;
profile values, evidence bodies and private request payloads do not enter audit.

Profile fields have bounded typed values and null represents `Unknown`. An empty
list, when explicitly confirmed, represents a declaration of no items. A supplied
but unconfirmed fact remains untrusted for comparison. Unknown fields are not
converted to empty strings, zero GPA, false or a guessed nationality/language.
Facts confirmed by the student are explicitly labelled self-reported. This is
not government identity verification, academic authenticity or scanned proof.

Each save appends an immutable version and provenance/confirmation time, with
compare-and-swap on the profile head. Revision zero is the initial head. A stale
save does not overwrite intervening facts. The base fields are available for
manual completion without AI consent; exact conditional compulsory fields for
Bachelor/Master/PhD remain G-PROFILE. No fictional compulsory doctoral field or
extraction-result provenance is invented to fill that gap.

## Human-reviewed rule basis

The catalog's prose criteria and descriptive filter labels are not machine
rules. A current `MODERATION` Admin with server MFA reviews a separate immutable
structured rule set for the exact currently published scholarship version/hash.
Each rule binds a criterion index, typed field/operator, mandatory flag, review
state and source evidence. Student-supplied status, score, verified flag or owner
has no authority. Review and attributable audit commit together.

A `complete` basis requires the reviewer to account for every catalog criterion
index. This is a human attestation, not an automated guarantee that prose has
been semantically exhausted. A missing basis, unmapped/incomplete criteria or an
empty criterion list cannot establish eligibility. An unverified rule produces
`UNKNOWN`. Duplicate rule keys or invalid criterion indices cannot stand in for
coverage. No text parser, semantic model or catalog facet silently creates a
mandatory rule or an exemption.

The initial operators are explicit set membership/intersection, same-scheme GPA
minimum and same-language CEFR minimum. Flat mandatory rules are conjunctive.
Compound alternatives across fields, exclusions, age/date conditions and
institution-specific credential rules must remain `UNSUPPORTED`/`UNKNOWN` when
they cannot be represented faithfully. For example, nationality A **or** residency
A cannot be approximated as two mandatory conditions. Country/language code
format validation is not an authoritative geopolitical or credential dictionary.

Rule approval also requires current source permission, exact publication and
`CURRENT` source freshness. The existing source-specific check/window controls
freshness; absent policy/check is `UNKNOWN`, not an invented default period.
Evaluation rechecks the current publication, source and rule basis. Stale or
unknown source freshness prevents those rules from supplying verified coverage
and makes the limitation visible. Versioned history does not bypass a current
revocation or withdrawn listing.

| Known rule outcomes / basis | Aggregate result |
|---|---|
| At least one verified mandatory FAIL, including with unknowns or incomplete basis | `INELIGIBLE` |
| No known mandatory FAIL, but unknown mandatory evidence, missing/incomplete basis, no criteria or all comparisons unknown | `INSUFFICIENT_INFORMATION` |
| Complete reviewed nonempty basis, at least one known comparison and every mandatory rule PASS | `ELIGIBLE` |

`INSUFFICIENT_INFORMATION` corresponds to the PRD's `Undetermined`. Missing
evidence is a usable partial result with a reason and safe next step, rather
than a fabricated pass or a terminal platform error. Nonmandatory failures can
reduce fit without altering hard eligibility. AI cannot write or override a
deterministic result, and this phase makes no provider request.

## Fit coverage and arithmetic

| Domain | Weight |
|---|---|
| Academic | 30% |
| Field | 25% |
| Nationality/residency | 20% |
| Language | 15% |
| Interest, using explicitly declared preferred countries | 10% |

The engine maps each typed field to one fixed domain; a request cannot inflate
weight by choosing a different domain. A domain is covered only when at least
one verified comparison exists and every comparison in that domain is known.
Covered FAIL is evidence with zero fit. Uncovered domains have null fit and
contribution, rather than a zero indicating disqualification.

For each covered domain, fit is the arithmetic mean of binary rule results
(PASS=1, FAIL=0). Coverage is the sum of covered domain weights. When coverage is
at least 70%, overall fit is the weighted mean of covered domain fit divided by
covered weight. Below 70% overall fit is null and the result explains insufficient
verified coverage. Decimal arithmetic rounds half-up to integer basis points;
10000 basis points denotes 100%. A domain with more rules cannot increase its
configured total weight. Display contributions as domain-weight contributions;
the final score's covered-weight normalization is explicit.

This particular coverage/within-domain formula, binary fit and preferred-country
interest proxy are engineering assumptions. Sources specify the initial weights
and threshold, but do not define these formula details or establish calibrated
quality. Record engine/weight versions, exact inputs and time. Confidence is
`UNCALIBRATED`; no numeric confidence, acceptance probability, admissions
guarantee or credential-authenticity inference is shown. A high fit cannot
change `INELIGIBLE` to `ELIGIBLE`.

## Explicit GPA and language policy

Supported declared GPA schemes are `PERCENT_100` (0–100), `GPA_4_0` (0–4) and
`GPA_5_0` (0–5). Normalization is the finite bounded decimal value divided by the
scheme maximum. Same-scheme thresholds can be compared after this explicit
normalization. This does not authorize cross-scheme or cross-institution
equivalence. Different known schemes, unknown scale, missing value or unconfirmed
fact return an unknown GPA rule. Do not infer a scheme from the numeric value.

Language rules can compare the same explicitly named language with a declared
CEFR A1/A2/B1/B2/C1/C2 level. Missing levels remain unknown. No IELTS/TOEFL score
conversion, language-proof authenticity or credential equivalence is inferred.
Exact label comparison does not invent field synonyms, country aliases or
nationality/residency substitutions. These conservative supported-policy bounds
are partial G-PROFILE coverage, not a universal academic taxonomy.

## Runtime API and student UI

All routes are relative to `/api/v1`. The generated runtime OpenAPI/types define
the final implemented field names; the earlier architecture schema remains a
broader design record. Strict serializers reject unknown input fields.

| Method/path | Boundary |
|---|---|
| `GET /profile` | Current verified adult owner's typed facts/version; private no-store response |
| `PUT /profile` | Explicit reviewed manual facts; CSRF, idempotency and quoted current-revision `If-Match`; immutable replacement version |
| `POST /eligibility/evaluations` | Owned current `profile_version_id`, exact currently published `scholarship_id`/`scholarship_version_id`; CSRF/idempotency; server-derived immutable result |
| `GET /eligibility/evaluations/{evaluation_id}` | Owner-only result; recheck current account, profile/rule/publication/source state before treating it as current |
| `GET /admin/scholarships/{scholarship_id}/eligibility-rules` | Current MFA/MODERATION-protected rule review projection; no student profile facts |
| `POST /admin/scholarships/{scholarship_id}/eligibility-rules` | Exact-version structured human review with source evidence, CSRF/idempotency and expected-version checks |

The student flow supports Arabic RTL and English LTR, manual known facts,
explicit review, safe stale-version conflict handling and per-rule uncertainty.
Status uses readable text; fit, evidence coverage and uncalibrated confidence
are distinct. Profile values stay in current page memory and private no-store
responses, with no browser persistent private cache or third-party analytics.
The UI explains server denials and absent reviewed rules without creating mock
scholarships or simulated eligibility. Full Admin policy/UI work remains separate.

Idempotency receipts retain opaque version/evaluation/rule-set references rather
than private DTO bodies. Replays reconstruct an authorized DTO and recheck the
current head, source permission and applicable freshness; an old receipt cannot
reveal a superseded profile or revive an obsolete rule decision. Evaluations
record the combined policy version and explicit engine/weight versions.

Database guards reinforce ownership, immutable snapshots, complete pinned check
identity and rule-first aggregate status. Typed comparison correctness and exact
fit arithmetic remain responsibilities of the deterministic application engine;
these guards are not a second independent SQL implementation or certification
of all grading/academic semantics. Production role/RLS separation remains gated.

## Warm p95 measurement plan

OQ-018 proposes <=2 seconds p95 for warm matching rules; it is a test target, not
a service promise. A defensible run must:

1. Record revision, runtime/DB versions, CPU/memory, server configuration, dataset,
   fixture size, rules per listing, profile/evaluation payload bounds and query
   counts. Use synthetic accounts/facts and permitted synthetic scholarship bases.
2. Measure the authenticated HTTP API plus session/permission, PostgreSQL and
   deterministic result/persistence path, with current CSRF/idempotency semantics.
   Distinguish that end-to-end path from a pure-engine microbenchmark.
3. Warm processes and DB connections explicitly; exclude and report warmup
   samples. Keep cold starts, stale/version conflicts, denied requests and
   source-unavailable cases as separately reported cohorts.
4. Use 20 concurrent authenticated clients and representative complete, partial,
   failed-mandatory and near-maximum-rule profiles. Use fresh idempotency keys for
   independent evaluations; a replay-only run cannot measure normal computation.
5. Record sample count, duration, successful latency distributions, nearest-rank
   p50/p95/p99, throughput, failures/timeouts and their rate. Do not discard slow
   or failed samples to manufacture the target; a latency pass with material
   errors is not a capacity pass.
6. Repeat the declared workload with bounded measurement overhead. Report whether
   the synthetic local target passed, failed or was not run. Keep free-host cold
   start and realistic production/load certification separate. A single-process
   development smoke or pure-engine timing does not prove this concurrent target.

A concrete baseline run should use an isolated synthetic database and20 separate
verified adult sessions on an approved production-like HTTP server configuration
(the local single-thread development workaround is not that configuration).
Declare cohorts with5,25 and50 rules, complete/partial profiles and known mandatory
failures. Warm with100 requests (five per session), then record1000 fresh-key
evaluations (50 per session) over at least five minutes at a maximum of20 in flight.
For N recorded normal-path latencies, nearest-rank p95 is sorted[ceil(0.95*N)-1];
report cohort counts and end-to-end failures as well as the combined distribution.
The provisional pass requires p95<=2000ms with zero unexpected5xx/timeouts;
intentional permission/stale-input cohorts have separate expected outcomes and
must not be used to disguise normal-path errors. Archive minimized timings and
configuration, not profile bodies, cookies or request credentials.

Any executable local benchmark is optional supporting evidence; exact performed
commands and limitations belong to the phase report. There is no claim that a
realistic production 20-client workload or semantic-quality pilot has passed
without recorded evidence.

## Remaining external and later-phase gates

- `G-PROFILE`: academic-stage compulsory dictionaries, institution-specific scale
  equivalences, approved proof/taxonomy policies and independent credential
  authentication remain unresolved. Preserve manual/unknown paths.
- `G-MEASURE`: real evidence quality, weights/coverage calibration, fairness,
  uncertainty comprehension, assistive technology and realistic warm/concurrent
  performance remain independently evaluated targets.
- `G-SOURCE`: no real source permission or current human machine-rule attestation
  is fabricated by synthetic fixtures. Real MFA and production DB-role/RLS
  separation retain their previous gates.
- AI/RAG rationale and private-data processors require later-phase contracts and
  approvals; no egress, quotes, credit ledger, scan/upload, reminders, saved-item
  workflow or application-state personalization is implemented here.
- `G-LEGAL`, hosting, backups and release signoff remain open. The subsequent
  explicit `Push` authorizes Git publication only; deployment and paid resources
  remain unauthorized.
