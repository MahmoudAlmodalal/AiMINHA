# Phase 00 source authority and constraints

Authority follows `AGENTS.md` §Source hierarchy; user instructions limit execution to phase 00, uncommitted and without push/deployment. Repository identity is user-supplied `MahmoudAlmodalal/AiMINHA`, not an invented project location. That identifies the repo, not approval of an absent PRD.

1. **MISSING:** Actual approved `docs/source/PRD.md` is the feature baseline once supplied. Referenced v3.0.0 cannot be verified.
2. Decision record §أ explicitly attributes decisions 1–7 to the product owner. Preserve those decisions and distinguish analyst operational defaults (§ب) and qualified OQ outcomes (§ج).
3. Provider strategy is a technical proposal with approved inclusion as fallback options. It does not authorize student-private processing. Its §5 open questions remain pending validation.
4. Workflow/playbooks specify how to work; they do not fill missing feature requirements. Derived artifacts must trace to source sections or carry MISSING/ASSUMPTION/EXTERNAL_GATE labels.

## Owner decisions versus defaults and gates

| Owner decision (S2 §أ) | Related defaults (not measured facts) | External gate / boundary |
|---|---|---|
| 1 Public Free Beta, bounded free Credits, payments off | §ب: 100 active-user design target; public browsing; §ج OQ-022 verified adult personalization | §ز legal/hosting/readiness review; paid payment details OQ-001 remain deferred |
| 2 Hybrid ingestion, admin publication approval | OQ-003: initial catalog/source counts conditional on legality | Each source's permitted use; no automatic publication |
| 3 Official university/government/institution/organization coverage | OQ-003 suggested catalog start | Source permission and provenance; no unauthorized copying |
| 4 Chrome first, field review, no auto-submit | OQ-015: three initial sites, >=90% supported test fields | Actual permitted sites and tests missing; no password/OTP capture |
| 5 Explicit consent plus provider/model/data-type approval, fail closed | OQ-004 data classes; S3 §§1–4 conditional Cloudflare → Groq | Individual security/contract/region/model approvals; Gemini unpaid/OpenRouter free exclude private student data |
| 6 No admin browsing private student libraries; explicit ticket attachments only | OQ-007 and §د ticket boundaries; AGENTS.md assigned-agent access and audit | Access-control tests absent; attachment AI needs dedicated consent |
| 7 One signup grant, per-student daily spend cap, global cap, admin-configurable | §ب: 30 grant, 6/day spend (not replenishment), 100 AI operations/day, 8,000-Neuron guardrail; 15-minute reservation/24-hour reconciliation target | Resource measurement and transactional tests absent; defaults are not proven capacity |

## Other constraints with traces

- S2 OQ-012; S3 §3: deterministic eligibility; AI cannot override a verified mandatory failure. Initial weights/coverage threshold are calibration defaults, not admission probabilities.
- S2 OQ-016 and §د; S3 §2.6: stable operation identity, snapshots, validated saved output before one debit, reconciliation for uncertain outcomes.
- S2 OQ-013; AGENTS.md §Security: ownership, allowed format/size, MIME/content checks and working malware scanning; manual alternative when unavailable.
- S2 OQ-006/020/023: deletion/restore timing and telemetry retention have legal/provider qualifications; UTC storage and explicit timezone display. No retention policy signoff inferred.
- S2 §§د–هـ; S3 §2.8: untrusted retrieved content, no client/extension secrets, no private-content telemetry, no automatic paid upgrades.
- S2 §هـ and AGENTS.md §Stack: Next.js/TypeScript, Django/DRF, PostgreSQL, private storage, recoverable worker and Chrome MV3 are directed/proposed stack, not observed application implementation.
- S2 OQ-018/021 and §ز: performance, bilingual quality, backup/restore and release targets require real evidence and owner signoff.

## Unresolved reconciliation

See `requirements-conflicts.md`. Do not infer a complete FR set from OQs, declare external approvals complete, or treat a key/provider name as permission to send student data.
