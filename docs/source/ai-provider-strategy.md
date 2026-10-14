# MinhaAI — AI Provider Routing & Fallback Strategy

| Document control | Value |
|---|---|
| Product | MinhaAI |
| Date | 14 October 2026 |
| Status | Proposed technical architecture **[A]** — explicitly approved for inclusion as fallback options in the working documentation; providers not approved for processing personal data yet |
| Requirements baseline | [`PRD.md`](PRD.md), Sections 1, 10–12, 17, 20, 23, 25–27 |
| Business constraint | **$0 out-of-pocket / no automatic paid upgrade** during the initial trial |

## 1. Agreed routing order

| Rank | Provider | Intended role | Production data eligibility | Free-tier caveat |
|---|---|---|---|---|
| 1 | **Cloudflare Workers AI** | Default for eligible extraction, grounded explanation, document drafting and AI support | **Conditional approval required** under PRD OQ-004; apply data minimization and consent | Free allocation is **10,000 Neurons/day**, shared across models; unavailable operations must not auto-upgrade to Paid. Not all models are available on Free. |
| 2 | **GroqCloud** | First automatic fallback when quota/rate limits or retriable outages affect the primary | **Conditional** on provider terms, jurisdiction and active data controls; enable/verify Zero Data Retention (ZDR) where required | Model-specific free request/token quotas; not a promise of unlimited capacity. |
| 3 | **Google Gemini API (unpaid tier)** | Optional fallback for **synthetic or non-sensitive** text, testing, or publicly available scholarship content only | **NOT approved for real student personal/confidential information on the unpaid tier**; provider terms expressly permit using unpaid-service inputs/outputs to improve services, and human review may occur | Free availability, model availability and rate limits can vary. |
| 4 | **OpenRouter (free models)** | Last fallback for **synthetic/non-sensitive** testing or publicly sourced content after the specific underlying processor/model is evaluated | **NOT approved for personal student data by default**; approval must consider routing and underlying provider policies | About 50 free API requests/day under the standard free plan, subject to change; free-model uptime varies. |

**Important:** This is a routing preference, not a blanket permission to send a request to every provider. For personal data, the allowed fallback chain is **Cloudflare → Groq only if each is separately approved for that category**; otherwise return a controlled unavailable response. Gemini Free and OpenRouter Free are excluded from automatic routing of sensitive data.

## 2. Routing and fallback behavior

1. **Classify each request**: `(a)` synthetic/public, `(b)` student private/confidential, or `(c)` financial/security/other prohibited automation. Restrict the payload to the minimum information required.
2. **Validate policy first**: student consent where applicable, permitted provider/data-region/model, no-training and retention controls, model suitability, and daily free-tier budget. Never send a prompt to a disallowed provider even if it has remaining quota.
3. **Select primary**: send the request to Cloudflare Workers AI only if the selected model is free-tier eligible and has sufficient remaining request/Neuron allowance.
4. **Trigger fallback only for retriable causes**: provider unavailable, timeout, capacity error, rate limit, or exhausted free allowance. Do not reroute validation failures, security refusals, consent refusals, or confirmed business-rule failures as if they were outages.
5. **Use the next *eligible* provider**, skipping any candidate that fails policy, budget or task suitability checks. Use bounded retry and backoff, and cap total attempts.
6. **Idempotency and Credits**: the user authorizes one operation with one price snapshot and correlation ID. Reserve once, avoid duplicate parallel generations, settle a single charge only after a successful accepted result, and release/reconcile on confirmed terminal failure. A timeout with uncertain provider outcome must first be reconciled; do not blindly refund or double-charge.
7. **Safe failure**: when no permitted provider is available, show `AI temporarily unavailable` and offer retry/manual alternatives where possible. Existing student data, submitted documents and application statuses remain intact. The rule-based eligibility engine remains usable without an LLM.
8. **Observability**: record provider/model ID, non-sensitive error class, request/usage counts, quota reason and correlation ID; do **not** store raw CVs, prompts containing personal details, identity documents, OTPs or passwords in telemetry.

## 3. MinhaAI workload routing

| Workload | Recommended behavior | Fallback boundary |
|---|---|---|
| Mandatory scholarship eligibility | Deterministic rule engine first | Never substitute LLM guesswork for a verified mandatory criterion. |
| Public scholarship description summarization | Cloudflare model | Groq → Gemini Free → OpenRouter Free, subject to available quota and acceptable terms. |
| Match-score rationale based on a student profile | Rules + approved AI model using minimized facts | Cloudflare → **Groq only after privacy approval**; otherwise preserve eligibility, mark AI explanation unavailable. |
| CV/profile extraction and student-specific document drafting | Approved AI model and consent; review before use | Cloudflare → **Groq only after privacy approval**; never route raw private files to Gemini Free/OpenRouter Free. |
| Support chatbot with account context | Approved AI provider with minimal necessary context | Cloudflare → **Groq only after privacy approval**; financial actions require human Admin. |
| Purely synthetic benchmark cases | Any provider with acceptable basic security posture | Compare output quality and API limits without using real student data. |

## 4. Configuration and ownership (not yet implementation)

- Use a provider-independent `AI Provider Adapter` interface behind the **Django + DRF** backend, with provider/model choices configured server-side rather than exposed as secrets to Next.js or the browser extension.
- Maintain **per-feature allowlists**, a **data-class allowlist**, rate/usage caps, health indicators, timeout/retry policy and an explicit **no-paid-API/no-auto-upgrade** control. Configuring an API key must not silently authorize that provider for private files.
- Keep model selection **replaceable**: model IDs and provider availability may change. A fallback model must satisfy task length, Arabic/English quality and basic response-shape requirements before activation.
- `AI Support`, document creation and matching must continue to follow the PRD's approved behavioral limits, human review, consent rules, version control and Credit-ledger reconciliation.
- Admin visibility should include provider failures and aggregate usage; any setting that permits sensitive data egress needs Security/Legal approval and an audit record.

## 5. Open decisions before connecting real student data

1. **OQ-004 (P0):** Which exact models, processor agreements, locations and no-training/data retention controls are approved for each category of student data?
2. What initial quotas, concurrent request limits, model fallback compatibility and daily consumption ceilings can be guaranteed under Free accounts in the actual region?
3. What measured quality threshold should be required for Arabic/English scholarship criteria, grounded explanations, CV extraction and fabricated-credential detection?
4. What timeout, retry, reconciliation and failed-generation rules qualify an AI task for safe rerouting without duplicate Credit charges?
5. How will student consent be logged if a processing region/provider differs from the one disclosed at consent time?

All five are **TBD** pending validation. They are not silently solved by naming providers.

## 6. Validation scenarios

| ID | Given | When | Then |
|---|---|---|---|
| AI-FB-01 | A public-data request and approved Groq account | Cloudflare returns rate limit | Backend retries using Groq once per configured bounded policy, preserving the request ID. |
| AI-FB-02 | A private CV and Groq not yet privacy approved | Cloudflare quota is exhausted | Backend does not send the CV to Groq, Gemini Free, or OpenRouter; displays safe error and reconciles reserved Credits. |
| AI-FB-03 | A synthetic test request | Primary and Groq are unavailable | Gemini Free may be attempted if current terms/quota allow, then approved OpenRouter free model; no paid upgrade. |
| AI-FB-04 | An AI document request with a Credit reservation | Two provider timeouts occur | At most one final Credit debit and one accepted document result; uncertain outcomes are reconciled. |
| AI-FB-05 | A known failed mandatory eligibility criterion | LLM provider is down | System still displays `Not Eligible`, not a guessed high-score approval. |
| AI-FB-06 | A provider returns a privacy/consent violation | Fallback is evaluated | Backend stops, records a safe error class, and never retries the content through another provider to bypass the restriction. |

## 7. Source references (checked 14 October 2026)

- Cloudflare Workers AI free allocation, reset, and paid-only models: https://developers.cloudflare.com/workers-ai/platform/pricing/ and https://developers.cloudflare.com/changelog/post/2026-07-28-models-require-workers-paid/
- Groq inference data retention and Zero Data Retention: https://console.groq.com/docs/your-data
- Google Gemini API additional terms — Unpaid Services: https://ai.google.dev/gemini-api/terms
- OpenRouter free-plan allowance: https://openrouter.ai/pricing/

**Status summary:** Provider fallback *options* have been added to the technical proposal. **Actual access keys, vendor eligibility, privacy approval, performance benchmarks and production deployment are not complete.**
