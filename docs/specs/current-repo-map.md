# Current repository map — 2026-10-15

Checkout `/workspace/AiMINHA`, user-confirmed remote `MahmoudAlmodalal/AiMINHA`, branch `main`. HEAD `54d98904de4306fd3486616a48a26ae9f3188f55`; current documentation edits are uncommitted. Existing work from the same session is preserved; no push/deployment/provisioning.

```text
AiMINHA/
├── AGENTS.md, README.md              original workflow/security rules
├── docs/source/                     original PRD, decisions, provider strategy, playbook
│   └── 2026-10-15-owner-decisions.md additive latest session direction
├── docs/specs/                      source inventory/authority/gates/conflicts/map
│   ├── feature-matrix.md            all 125 FR + 28 NFR
│   ├── business-rules.md            all 54 BR + OQ dispositions
│   └── acceptance-scenarios.md      source AC + explicit requirement test paths
├── docs/architecture/               C4/sequences, APIs/modules/privacy/jobs/deployment
│   ├── openapi.json                 versioned machine-readable API draft
│   └── erd.dbml, schema/state/migration design
├── docs/adr/                        architecture decisions including recovery policy
├── prompts/                        18 original prompts 00–17
├── tasks/implementation-plan.md     current phase gates and release restrictions
├── tasks/product-backlog.md         epics/original stories/dependencies/acceptance
├── tasks/phase-reports/00..03.md    bounded completion and actual verification
└── templates/                      supplied task/report formats
```

Observed absence: `apps/`, `packages/`, `tests/`, `infra/`, application entry points, runtime dependency manifests/locks, Django migrations, CI and `.env` examples. Files under `/workspace/scratch/` are validation tools only, not application scaffolding. Repository documentation is not a runnable product. Source files that the PRD references but the user did not supply are explicitly missing, never fabricated.

After the now documented scope/architecture/data contracts, separately authorized Phase 04 produces UX. Phase 05 creates the monorepo/CI/local runtime; later vertical slices implement the backlog and required tests. No bootstrap or runtime compatibility claim is made by this map.
