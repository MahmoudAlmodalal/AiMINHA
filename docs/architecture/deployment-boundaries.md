# Deployment separation and checked platform evidence

Trace U02; A Stack; D §هـ/§ز; P §4. Status: PROVISIONAL; **EXTERNAL_GATE: no approved public SaaS hosting topology**. No deployment or paid service was created. Public deployment requires a fresh terms check and recorded owner/legal/security approval; this research is a technical eligibility check, not legal clearance.

## Proposed topology

Next.js frontend and trusted HTTPS ingress serve one browser origin; `/api/v1/*` forwards to separate Django web service. Independent worker runs the same backend/domain build with polling/scheduler heartbeat; never Vercel request lifecycle. PostgreSQL and private storage sit behind service credentials/appropriate network controls in approved region. API process owns HTTP authentication/domain commands; worker holds task-scoped AI/scanner access and its own secrets. Browser/extension/Next.js client bundle never holds these secrets. Server Next.js public catalog fetch uses public projection only. Same-origin gateway must preserve CSRF Origin/Host, Set-Cookie, request-size caps and no-store; test before choosing provider.

The gateway/Next.js forwarding hop remains bounded; generation/scanning returns durable 202 and polls. Do not use serverless post-response callbacks, cron-only best effort or an always-on function loop as durable processing. Scheduled independent worker runs are acceptable only if measured wake/cadence, lease recovery, cleanup and reconciliation meet targets. Without a $0 permitted reliable worker, leave deployment blocked; no automatic upgrade or paid fallback.

Deploy web/API/worker separately but on compatible API/domain versions. Expand/contract migrations and drain/fence old workers before breaking schema. Regional DB/storage/provider placement requires approved disclosure and data-processing terms. Disposable local disks never host authoritative files, credits, queue or backup. Backup must be independent and restore rehearsed; free database expiration/sleep is not an availability plan.

## Official pages checked on 2026-10-14 UTC

HTTP retrieval via Python stdlib succeeded (200 for all eight pages); exact excerpts below reflect retrieved current docs. Raw request hashes describe the response, not legal approval or immutability of vendor policy. Scratch evidence is outside the repo and not a required deploy artifact.

| Page | Observed statement | Architecture implication |
|---|---|---|
| [Vercel Hobby](https://vercel.com/docs/plans/hobby) | “the Hobby plan restricts users to non-commercial, personal use only” | Do not assume free/public Beta makes MinhaAI SaaS eligible. Hobby cannot be approved for intended commercial SaaS from this evidence. Free frontend hosting remains unresolved. |
| [Vercel fair use](https://vercel.com/docs/limits/fair-use-guidelines) | “All commercial usage of the platform requires either a Pro or Enterprise plan”; financial gain includes paid production work | Needs commercial-use classification and terms review before public deployment. No paid alternative authorized. |
| [Vercel function limitations](https://vercel.com/docs/functions/limitations) | Hobby duration “300s default and maximum”; other plans bounded/configurable | Request runtime does not promise independent durable jobs. Model/scanner/reconciliation stays in recoverable worker. |
| [Vercel Django](https://vercel.com/docs/frameworks/full-stack/django) (redirected from `/frameworks/backend/django`) | “When you deploy a Django app to Vercel, it becomes a single ... Vercel Function” | Technical Django support is real, but is not an always-on worker or approval to deploy the business on Hobby. |
| [Render free](https://render.com/docs/free) | “Do not use them for production applications”; web service spins down after 15 minutes idle; 750 free instance hours/workspace/month; Free Postgres expires 30 days after creation | Candidate local/synthetic preview only until actual production suitability reviewed. Not accepted as persistent free SaaS DB/queue or dependable worker. |
| [Render background workers](https://render.com/docs/background-workers) | Workers “run continuously” and “don't receive any incoming network traffic”; tasks offloaded from critical request path | Correct runtime type conceptually. No free background-worker entitlement or commercial eligibility was established by this page. Hosting approval stays open. |

Official legal terms were also retrieved:

- [Vercel Terms](https://vercel.com/legal/terms): “only use the Services under a Hobby plan for your personal or non-commercial use”; data-processing terms incorporate the DPA. Together with fair-use definitions, this does not establish MinhaAI SaaS eligibility on Hobby. DPA acceptance, region and actual account classification remain unapproved.
- [Render Terms](https://render.com/terms): agreement incorporates acceptable-use policy, DPA and privacy policy; fees/charges can change under its pricing terms. This is not a verified $0 commercial worker/storage entitlement. Do not add billable services or treat those terms as complete student-data approval.

The Hobby/free-service statements are actual retrieved constraints, not assumptions from pack text. Region, full legal terms, account-level plan eligibility, file scanning support, reliable quota reset/meter and backup capabilities were not proven. Do not cite these checks as a launch go-ahead.

## Deployment gate checklist

Owner records approved commercial-use eligibility of each provider/account, $0 caps with no paid model/upgrade, exact regions/processors and consent disclosures, secrets ingress/worker isolation, origin-cookie-CSRF tests, source/site approvals, scanner fail-closed, backup/restore proof, API/worker lease recovery, capacity/availability measurements and security/release signoff. Missing evidence blocks affected feature or release. Payment remains disabled regardless of hosting choice.

## Retrieval evidence

- `render-free`: HTTP 200, SHA-256 `d6549a2b1862a4cc6fa690120e69221c25f347348a83198ae8705f52c347ef6b`; final URL https://render.com/docs/free
- `render-workers`: HTTP 200, SHA-256 `d3c15fc60854ff27023f81b540a2ce22cc55b7c2e60aa4ef5cfb0ec44c04a5c5`; final URL https://render.com/docs/background-workers
- `vercel-django`: HTTP 200, SHA-256 `cd2f213bcdd54769ee6e0de9395b78b3228b4ab61fd9716ac2bddbd89af6f63b`; final URL https://vercel.com/docs/frameworks/full-stack/django
- `vercel-functions`: HTTP 200, SHA-256 `09c7a62065c8a549c6b4934c524911b4a6759fcbf51516eaa7afade8622990f2`; final URL https://vercel.com/docs/functions/limitations
- `vercel-hobby`: HTTP 200, SHA-256 `e1d5c1bd45337664ea4e34037161e6041bb686a07451d3298ab7dca47e2a3822`; final URL https://vercel.com/docs/plans/hobby
- `vercel-fair-use`: HTTP 200, SHA-256 `82b0bc63ac13e45114eef965f58bcf1a3e1fb0e10c35db07e4b7d7eb5a5e0473`; final URL https://vercel.com/docs/limits/fair-use-guidelines
- `vercel-terms`: HTTP 200, SHA-256 `a881c57f7dfaf0a0a7a0673c2a6a55ac68505217bd2c66e7ff568148239b814c`; final URL https://vercel.com/legal/terms
- `render-terms`: HTTP 200, SHA-256 `3e03a4604019e61b15e06a2a4c8303f877cb7e44b0a930ac0a610698e520b99e`; final URL https://render.com/terms
