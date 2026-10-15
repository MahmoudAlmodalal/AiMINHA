# ADR 0006 — Server feature flags with approval and budget gates

Status: PROPOSED / ASSUMPTION. Traces D §أ 1/5/7, §ب/OQ-004/026; P §4; A. Context: flags cannot be legal or security approval and free fallback cannot create surprise cost.

Decision: versioned server policy, deny by default, applied at admission and again before external send/finalization. Effective enablement = approved release scope AND flag AND actor permission AND current consent/provider/model/data-class/region approval AND free-only capability/budget AND dependencies healthy. Unknown values/config outage deny affected feature. UI receives capability summaries, never secrets/authority.

Proposed flags: `beta_payments=false` (no public enablement absent explicit paid-release scope/signoff); `private_ai=false` until external approvals; `uploads=false` until scanner/storage approval; `ingestion=false` until permitted source registry; `extension=false` until site/auth review. Public catalog may be enabled only for approved published content. AI support follows same budgets/approval gates even if zero student price. Admin may change scoped operational caps prospectively, but not bypass approvals, enable paid models or grant themselves private file access. Security-sensitive policy changes need distinct authorized approval records; exact scope provisioning remains baseline input.

Consequences: immutable policy/price snapshots and audit required; revocation/kill switches affect new sends while uncertain existing sends reconcile. Flags never refund blindly or rewrite settled operations. Rejected alternative: frontend-only flags or API key presence implying private-data approval. Defaults are derived operational assumptions, not production settings.
