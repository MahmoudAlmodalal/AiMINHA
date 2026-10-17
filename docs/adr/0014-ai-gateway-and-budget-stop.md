# ADR 0014 — classified mock gateway with disabled live egress

Status: bounded Phase10 runtime decision, 2026-10-16. The local scope is
`LOCAL_MOCK_GATE_WITH_LIVE_EGRESS_DISABLED`. Actual verification belongs to
[report10](../../tasks/phase-reports/10.md). No commit, push, deployment, paid
resource or real provider call is authorized by this phase.

Authority: current Phase10 work items; AGENTS.md; PRD FR-012/030/035/037/098,
FR-113/115/123–125, AC-013/031/041, NFR-007/008/010/019/020/022–024;
decision resolution §أ5/7, §ب/OQ-004; provider strategy §§1–6; derived schema
R12–15/R22 and the job/privacy boundaries. Numeric beta settings and retry/circuit
defaults are distinct from owner decisions and external vendor evidence.

Use a provider-independent server adapter contract with explicit classification
and route metadata. Persist exact provider/model/data-type/purpose/region approval,
validity, revocation and terms/security evidence; an enabled feature or configured
key never supplies approval. No live approval is seeded or exposed through a
general Admin setting. Mixed private/public input remains STUDENT_PRIVATE and
PROHIBITED never dispatches. Private routing is categorically limited to separately
approved Cloudflare or Groq; Gemini Free/OpenRouter Free cannot receive it.
Public/synthetic live egress still requires specific reviewed terms.

Keep every named real adapter without a network transport. External account,
free-only enforcement, model suitability, terms, meter and processor approvals are
not available. The local mock accepts only server-fixed synthetic input in LOCAL
mode; it is never a private-data fallback. Generic PERSONAL_AI consent lacks the
structured provider/model/region/data-type scope needed for private processing.
An otherwise eligible private request fails SCOPED_PRIVATE_PIPELINE_UNAVAILABLE
even when the generic purpose is granted; earlier missing-consent/forbidden-route
guards may deny first. This phase proves denial rather than pretending to
implement an approved private pipeline.

Reuse the Phase09 operation, captured price and canonical logical admission.
Do not count retries as new logical operations or introduce an independent
gateway counter. Before each physical attempt, recheck current account/consent,
approval/configuration, circuit and provider budget under stable locks; persist
the fenced attempt, conservative allocation and DISPATCH_INTENT before adapter
I/O outside transactions. Recheck authorization and fence at acceptance. Only one
unresolved attempt may exist for an operation.
Each intent rechecks the current logical hard stop without another admission or
price change; zero/lowered-exceeded limits stop dispatch. Lease bounds include
operation expiry, provider-window end and meter freshness. Deferred guards require
unknown attempts to reconcile, successful attempts to have one saved settled
result, and released requests to have no unresolved or successful attempt.

Intent commit is the revocation linearization point; a database lock cannot
recall bytes already sent. Revocation before intent denies dispatch. Revocation
after intent denies accepted-result commit and follows the future processor's
approved cancellation/deletion policy. Never replace a captured consent scope
silently or bypass a refusal through fallback.

Retry only a proved retryable NOT_EXECUTED outcome and only on another eligible
route. Use at most three total attempts, default two per configured route;
10-second timeout, three
transport failures and 30-second circuit cooldown are bounded engineering
defaults. Half-open permits serialize probes. Validation, security, consent and
business refusals do not fall back. A timeout/crash after intent is UNKNOWN even
if a socket send might not have occurred: retain physical allowance and credit
hold, mark RECONCILING and block further generation. No timer or circuit reset
authorizes refund, retry or paid upgrade.

Track physical quota separately from credits and logical operations. Use an
immutable measured baseline and explicit freshness/evidence/free-only attestation
for a provider/account/unit UTC window shared by all relevant models. Deny
overlap, unknown worst-case cost, stale/missing measurement, unavailable evidence
or exhausted allowance. Reserve the known maximum before every attempt. Enforce
the experimental Cloudflare cap of at most8,000 Neurons only with trustworthy
measurement; the source's10,000 free-tier number is not an observed balance.
Provider resets are independent from Asia/Hebron student days. Conservatively
consume the bound for known NOT_EXECUTED attempts; UNKNOWN remains held, including
across new windows. No student refund replenishes provider usage. Local mock
measurements do not attest real vendor capacity.
The immutable baseline cannot be refreshed in place; an overlapping replacement
is denied. A stale window stays closed pending a future guarded meter contract,
not a reset of tracked consumption or unresolved allowances.

Treat web/upload content and model responses as untrusted data. Provide no tools
or financial/account/application actions through the adapter. Validate exact
schema, language, evidence identities and quotes; unsupported claims never count
as success. Atomically save the validated GatewayResult and settle the existing
exact synthetic financial proof. This demonstrates transaction correctness and
bounded grounding, not real document/CV validation or model quality. Mandatory
deterministic eligibility remains authoritative.

Expose only a protected capability read with safe disabled reason codes; no
public execution/configuration/approval write route or student AI launch flow.
Persist metadata-only routing audit, never raw prompts, file text, responses,
secrets or exception bodies. Existing private file/library restrictions remain.

Consequences: the local gateway, concurrency, quota, denial and synthetic
acceptance paths can be reviewed without network I/O or surprise charges. Live
provider interoperability, exact scoped consent, free-account/meter evidence,
semantic bilingual quality, price confirmation, real file/document validation,
production worker/RLS/performance and release signoff remain explicit gates.
See the [Phase10 specification](../specs/phase-10-ai-gateway.md) and C10 dispositions
in [requirements conflicts](../specs/requirements-conflicts.md).
