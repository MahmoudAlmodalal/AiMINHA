# ADR 0005 — Separate frontend, API and worker runtime

Status: DOCUMENTED WORKING DESIGN / ASSUMPTION; hosting EXTERNAL_GATE. Traces U02; D §هـ/§ز; A Stack. Context: function support is not continuous worker support or commercial-use approval.

Decision: Next.js web, Django HTTP API, independent recoverable worker, durable PostgreSQL/private storage, one trusted browser origin. Same domain codebase, compatible release versions; no microservice split. AI/scanning/reconciliation are queued and never depend on frontend/serverless request lifetime. Deploy environment and secrets separately; no frontend DB/provider key.

Official docs checked 2026-10-14 confirm Vercel Hobby non-commercial personal-use restriction, finite function durations and Django function deployment. Render free docs warn against production usage and record spin-down/free database expiration. See `../architecture/deployment-boundaries.md` for evidence hashes/URLs, limitations and release gate. No current candidate is approved for $0 public SaaS plus reliable worker/backup/scanner. No paid plan is provisioned or selected to solve that gap.

Consequences: gateway/origin routing and API/worker compatibility tests required. Worker outages preserve jobs but may miss experimental targets; alert and expose unavailable/reconciling status. A bounded scheduled independent process can replace continuous worker only after cadence/recovery evidence. Rejected alternative: Django background thread/forever polling Vercel function or relying on a sleeping free service as dependable scheduler.
