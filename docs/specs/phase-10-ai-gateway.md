# Phase10 — AI gateway, classification and budget stop

This request authorizes one bounded Phase10 implementation with parallel agents.
It does not authorize a commit, push, deployment, paid resource or real provider
call. The local boundary is `LOCAL_MOCK_GATE_WITH_LIVE_EGRESS_DISABLED`.
Authoritative source bytes and earlier phase outcomes remain unchanged. Runtime
decisions are recorded in [ADR0014](../adr/0014-ai-gateway-and-budget-stop.md);
actual commands, results and omissions belong to
[report10](../../tasks/phase-reports/10.md).

## Sources and requirement traces

The authoritative baseline is [PRD v3.0.0](../source/PRD.md). The
[decision resolution](../source/MinhaAI_PRD_Decision_Resolution_AR.md) §أ5
records the owner's private-processing consent and independent provider approval
requirement. Its §ب/OQ-004 supplies the proposed numeric limits and categorical
routing restriction; these are not vendor, contractual or legal approvals. The
[provider strategy](../source/ai-provider-strategy.md) is a proposed routing
preference with five unresolved external decisions (§5), not permission to
process student data. Derived implementation guidance includes schema R12–15/R22,
[job boundaries](../architecture/jobs-and-reconciliation.md) and
[privacy boundaries](../architecture/privacy-boundaries.md).

`U10.1`–`U10.6` identify the current work items.

| Work | Bounded implementation | Trace |
|---|---|---|
| Adapter, configuration and fault boundaries | Server-selected provider/model configuration, pure adapter interface, local fixed synthetic mock, bounded timeout/retries and persisted circuit state; all real transports disabled | U10.1; FR-123/125; NFR-019/020/022; provider strategy §§2/4; R15 |
| Classification and approval | Explicit `PUBLIC/SYNTHETIC`, `STUDENT_PRIVATE`, `PROHIBITED`; exact provider/model/data-type/purpose/region evidence and validity/revocation metadata; no seeded live approval | U10.2/3; FR-012/113/115; NFR-010/011; decision §أ5/OQ-004; R12 |
| No surprise cost | Canonical existing logical admissions plus separate per-physical-attempt shared-account quota allocations; missing/stale metering or free-only evidence stops dispatch | U10.4; decision §أ7/§ب/§هـ; provider strategy §§1/2/5; R13 |
| Untrusted input/output isolation | Fixed instructions, bounded structured evidence input, no tools/actions, strict output schema/language/citations and exact synthetic fact checks; validation and durable save precede settlement | U10.5; FR-030/035/037/098/124; AC-013/031/041; PRD §20.3; R14/15 |
| Negative and concurrent proof | Approval, private routing, consent change, quota, outages, retry/fencing, circuit and redacted audit tests without provider I/O | U10.6; NFR-003/007/008/023/024; provider strategy AI-FB-01–06 |

This phase does not implement live CV extraction, generated student documents,
ticket support, public AI execution, displayed-price confirmation, real provider
account enrollment or general Admin approval controls. Those source requirements
remain partial or separately gated. Deterministic eligibility remains authoritative
and cannot be overridden by a model result.

## Classification and private-data denial

Classification is a server-side processing boundary. Private profile, file,
account-context or student-linked support input remains `STUDENT_PRIVATE` when
combined with public text. A caller cannot declassify it with a public label.
`PROHIBITED` never dispatches. The executable mock accepts only server-created
fixed synthetic fixtures in LOCAL mode; it cannot accept an arbitrary prompt,
real student's content or a private payload as a substitute for a live processor.

Approval metadata identifies one provider, model, data class, data type, purpose
and region, along with terms/security evidence and a bounded validity interval.
An expired, missing, revoked or mismatched record cannot authorize an attempt.
Credentials and enabled flags are not approvals. No real provider approval is
seeded, and no ordinary Admin API creates or edits this independent evidence.

Private eligibility is restricted to Cloudflare Workers AI or Groq, each
individually approved. Gemini Free and OpenRouter Free cannot receive private
input even if a configuration or purported approval requests that route.
Public/synthetic real egress also requires specific current terms approval.
The named real adapter boundaries have no HTTP transport in this phase: keys,
configuration and approval rows cannot activate a live request.

Existing PERSONAL_AI records demonstrate purpose-specific consent/versioning,
but their generic disclosure is not a structured processor/model/region/data-type
scope bundle. An otherwise eligible private route therefore fails with
`SCOPED_PRIVATE_PIPELINE_UNAVAILABLE`, including when generic consent is GRANTED;
missing consent or a forbidden provider may be rejected by an earlier guard.
There is no private raw-content persistence or egress in this slice. This is a
fail-closed gate, not certification of a usable private-processing pipeline.

## Operation, attempts and revocation

The orchestrator operates on an existing owned Phase09 synthetic credit operation.
It uses that operation's stable identity, captured price/day/policy and canonical
global admission. It does not introduce a second logical counter or a free path
around reservations. Equal retries reuse persisted operation state. Each physical
attempt separately consumes provider allowance; retries do not create another
logical operation or another credit charge.

Before intent, the service locks/rechecks current account state, captured consent
version, approval/configuration, circuit state and quota. It persists a fenced
attempt and its conservative allocation before invoking the adapter outside
database locks. Only one unresolved attempt may exist for an operation. Current
authorization and fence are checked again before accepted-result commit.
The attempt lease cannot outlast the operation reservation, provider window,
measurement freshness cutoff or configured timeout. Deferred database guards bind
gateway/credit states: unknown attempts require reconciliation, accepted success
requires one saved result and settlement, and release forbids unresolved or
successful attempts. A release helper independently refuses an uncertain attempt.

The committed `DISPATCH_INTENT` is the revocation linearization point. Revocation
before that commit prevents dispatch. Revocation after it cannot recall bytes
already sent; a future live transport must attempt cancellation and follow the
approved processor deletion policy. A changed consent snapshot or disabled
account cannot be silently replaced at acceptance, cannot settle new output and
cannot trigger a privacy-bypassing fallback. Metadata/uncertainty remains durable
even when current student access is denied.

A proved retryable NOT_EXECUTED result may schedule another eligible attempt.
Default configuration permits two attempts per configured route, with a hard
maximum of three total physical attempts for the operation;
10-second timeout, three transport failures to open a circuit and a 30-second
cooldown are explicit engineering defaults, not measured vendor guarantees.
Half-open probes use an exclusive bounded permit. No retry policy creates an
unbounded loop or retries a schema, grounding, consent, security or business-rule
refusal.

Timeout or worker loss after intent is UNKNOWN, including a crash in the gap
between intent commit and socket send. It retains physical allowance and the
credit hold, moves the operation to RECONCILING and prevents another generation
or fallback. Neither the 15-minute investigation marker nor the experimental
24-hour review target proves that an external effect failed. There is no
automatic reconciliation exit, refund, regeneration or paid upgrade.

## Logical and physical budgets

The existing versioned Phase09 policy supplies the default 100 logical AI
operations/day and student credit limits. Logical days use Asia/Hebron, following
the previously recorded global-day engineering assumption. Changing policy,
replaying a request or releasing a failed hold cannot reset admissions. Future
zero-credit support must use the same global counter and its separately scoped
support allowance; ticket AI is not implemented here.

Each physical intent also rechecks the current logical hard stop. A zero cap or
usage above a newly lowered cap stops dispatch; a prior-day operation also stops
when the current day's admission cap is exhausted. The operation's own already
counted admission is not counted again, and equality for an accepted same-day
operation does not invent an extra admission. This stop does not reprice an
existing hold or rewrite its captured day.

Physical quota is separate from credits and logical operations. A quota window
identifies provider, shared account, unit and explicit half-open UTC interval;
all models sharing that pool compete for the same allowance. Overlapping windows
for the same pool/unit cannot create duplicate capacity. Its immutable baseline
records observed usage, measurement time, freshness cutoff, evidence reference
and confirmed free-only enforcement. A dispatch reserves a known conservative
maximum and requires:

`observed_used + tracked_consumed + tracked_held + proposed_max <= cap`.

Unknown/stale baseline, missing evidence, absent free-only enforcement, unknown
worst-case usage, exhausted cap or inconsistent window disables that route.
Provider resets are independent of the student's local day; no Hebron-midnight
assumption is applied to vendor quotas. The baseline cannot be refreshed or
overwritten in place, and a replacement overlapping window is denied. Once its
measurement becomes stale, that window remains unavailable; a future live meter
needs a separately guarded append/reconciliation contract rather than a counter
reset. This phase has no actual vendor meter, free-account attestation or
reset-verification adapter.

Cloudflare's experimental Neurons ceiling is at most 8,000 for the configured
window, below the source's proposed 10,000 free allocation. Neither number is an
observed usable balance or proof that a selected model is free. A known
NOT_EXECUTED attempt conservatively retires its worst-case allocation into
tracked consumption; retry does not receive a free fresh allowance. A measured
accepted attempt records authoritative bounded usage. UNKNOWN retains its whole
allocation; creating a new window never clears an unresolved old allocation.
Student credit release cannot replenish provider usage.

The mock uses bounded local synthetic measurements to exercise these accounting
rules. Such evidence is not contractual approval or trustworthy metering for a
real Cloudflare/Groq/Gemini/OpenRouter account. Real adapters stay disabled, with
no paid model, paid key, automatic upgrade or account-spend assumption.

## Prompt and result boundary

Untrusted scholarship/web text is data inside a bounded JSON envelope beneath
fixed system instructions. It grants no tool, URL-fetching, file, account,
application, publication or financial authority. The adapter interface exposes
no tool execution capability, and output schemas reject unexpected action/tool
fields. A prompt asking to ignore policy cannot alter gateway authorization.

Model output is untrusted even after a transport success. Validation checks the
exact schema, requested language, citation identities and quotes against trusted
synthetic evidence; unsupported or substituted facts are rejected. A citation URL
or a model's `verified` assertion alone does not establish truth. This bounded
exact-evidence validator does not certify real CV/document semantics, academic
credentials, arbitrary paraphrases or bilingual generation quality.

Only a validated saved GatewayResult and the exact existing Phase09 synthetic
financial proof may settle, in one atomic acceptance transaction. A schema-valid
but unsupported claim, unsaved result, revoked consent, stale worker or partial
transaction is not a chargeable success. Replayed callbacks cannot create a
second accepted result or debit. No generated result can override a deterministic
mandatory eligibility failure or claim an acceptance probability.

## API and audit

The only added client route is protected `GET /api/v1/ai/capabilities`, with
current verified adult ownership/session checks. It reports live execution and
client mock execution unavailable with safe reason codes. It returns no prompt,
student content, credential, private approval evidence or raw provider response.
There is no public execution, provider selection or approval/configuration write
endpoint, and no AI launch/purchase control is implied by this capability read.
The generated runtime schema is authoritative for exact fields.

Routing audit retains request-to-operation correlation, selected provider/model,
classification, approval identity, captured consent version, quota decision and
coarse outcome/error codes. It excludes raw prompts, file text, user output,
secrets and raw exception/provider-error strings. Admin aggregate visibility does
not confer private library or arbitrary student-output access.

## Proof obligations and unresolved gates

Report actual checks in report10. Relevant proof includes missing/revoked/expired
approvals, prohibited/private mock denial, categorical private fallback denial,
generic-consent insufficiency and withdrawal, unknown/stale budgets, shared-pool
concurrency, logical cap preservation, physical retry accounting, bounded retries,
unknown timeout without reroute/refund, circuit half-open exclusivity, changed
approval before acceptance, prompt-injection/tool fields, unsupported citations,
atomic validated save/settlement, duplicate callbacks and metadata-only logs.

External gates remain: exact processor/model/data/region/retention/no-training
agreements; scoped informed consent and withdrawal/deletion handling; enforceable
free-only accounts and trustworthy live quota bounds/meters/reset evidence; real
transport/API compatibility; Arabic/English model quality and factual validators;
real document/file scanning and durable output identity; explicit displayed-price
confirmation before real funded execution; production worker identity/scheduling,
DB-role/RLS isolation, realistic quota/ledger performance and release/legal signoff.
No mock result or local gate closes these dependencies.
