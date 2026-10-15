# Current decisions and external gate register

2026-10-15. **Discovery/requirements design PASS; real-user release BLOCKED.** PRD and provider strategy are present. This register separates unexecuted external proof from completed early documentation.

| Gate | Missing decision / evidence | Enforcement until resolved | Source |
|---|---|---|---|
| G-SIGNOFF | Formal general-release PRD revision signature and original interview provenance not independently supplied | Work from attached baseline; do not claim historical signatures or general-release approval | PRD header/§27; UD-002 |
| G-LEGAL | Actual jurisdictions, privacy/terms, retention minima/maxima, deletion/backup/processor erasure basis and exception durations | No real-user activation absent approved policy; Admin recovery edits must remain within that legal envelope | PRD FR-113–121/OQ-005/006; D §ز; UD-001 |
| G-PROVIDER | Per-provider/model/purpose/data-class/region contracts, no-training/retention and quality, free-only account, conservative usage/reset evidence | Private AI off, no private fallback to Gemini unpaid/OpenRouter free; unknown meter denies send, no paid upgrade | D §أ 5/OQ-004; P §§1–6 |
| G-SOURCE | Each source's permitted fetch/publication and actual official-source list | No ingest/publish without current source evidence and human moderation | FR-015–024; D §أ 2/3 |
| G-SCANNER | Working exact-byte scanner, supported types/bounds/private immutable storage/quota enforcement/region | Upload and conversion disabled; manual entry available | FR-011/050; D OQ-013 |
| G-HOSTING | Current account terms/commercial use, permitted $0 API/worker/DB/storage, measured quota | No deployment or paid resource; independent durable worker required | D §هـ/§ز; deployment-boundaries.md |
| G-RESTORE | Independently restored backup and deletion/revocation replay, real RPO/RTO and retention expiry | No real-user release; no fabricated backup safety | FR-120; NFR-021 |
| G-PAID | Payment rail/recipient/currency/funds verification/reference normalization/refund-dispute policy | F-10 disabled in Beta; remains required before paid/general Advanced MVP | FR-080–088; D §أ 1/OQ-001/002 |
| G-PROFILE | Exact required stage fields, known GPA/proof scales, leap-day/legal age edge | Preserve Unknown, manual confirmed facts; deny ambiguous activation/mandatory eligibility rather than guess | FR-004/009/028/029; OQ-011/012 |
| G-TICKET | Rating scale/eligibility, warning thresholds/routes and staffing evidence | Undefined rating/escalation automation off; manual human queue continues; targets not promises | FR-100–105; D OQ-008–010 |
| G-EXT | Permitted portal/browser matrix, exchange-origin review, exact supported fields/test thresholds | Extension off until allowed-site/session review; no OTP/password/submit | FR-059–068; D OQ-015 |
| G-STATUS | Terminal/backward correction and future official-source precedence | Preserve both origins/history; reject unlisted transitions, no official integration enabled | FR-053/055/058; D OQ-014 |
| G-MEASURE | Load/quality/uptime/bilingual/semantic-search/accessibility metrics and pilot evidence | Numerical defaults remain proposals, no measured service guarantees | NFR-013–028; D OQ-018/021/023 |

UD-001 resolves who controls the recovery period: Admin. [ADR 0008](../adr/0008-configurable-recovery-period.md) gives the proposed exact, versioned calendar calculation and immutable per-request deadline. No stale “PRD missing” blocker remains. Externally gated features have explicit unavailable/manual paths rather than invented approvals.

No application, test harness, CI, migration, deployed worker/scanner/backup or infrastructure exists. Phases 04–17 remain future work. Passing phases 00–03 means their documentation/design gates pass; it does not pass any runtime, legal, provider, payment or deployment gate above.
