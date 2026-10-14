# Phase 00 current repository map

Local checkout: `/workspace/AiMINHA`. Origin: `https://github.com/MahmoudAlmodalal/AiMINHA.git`. Branch: `main`, tracking `origin/main`. Inspected HEAD: `de578430c59531bac01586ae632708e418cdf4d8` (`first commit`), containing only the original README. Phase 00 changes are local and uncommitted; no remote re-fetch was needed for document discovery.

```text
AiMINHA/
├── AGENTS.md                         imported rules
├── README.md                         build-pack README replaces title
├── MASTER_PLAYBOOK_AR.md              packaged playbook
├── docs/
│   ├── source/
│   │   ├── MinhaAI_PRD_Decision_Resolution_AR.md
│   │   ├── ai-provider-strategy.md
│   │   └── MinhaAI_AI_Agent_Master_Playbook_AR.md
│   └── specs/
│       ├── source-inventory.md
│       ├── missing-inputs.md
│       ├── source-authority.md
│       ├── requirements-conflicts.md
│       └── current-repo-map.md
├── prompts/                          18 imported prompts, 00–17
├── tasks/
│   ├── implementation-plan.md        phase 00 status recorded
│   └── phase-reports/00.md            updated discovery report
└── templates/                        task and phase-report templates
```

`docs/source/PRD.md` is absent. No `apps/`, `packages/`, `tests/`, `infra/`, `.github/`, dependency manifests/locks, `.env` examples, application entry points, migrations or API contracts exist. No runtime/toolchain compatibility, test health or deployed system can be asserted.

## Provisional scaffold plan — not implemented

Trace: AGENTS.md §Stack; S2 §هـ; master playbook proposed repository layout; roadmap phases 01–05.

After the approved PRD is supplied, phase 01 derives scope, phases 02–03 establish architecture/contracts/data ownership, and phase 04 establishes UX. Only phase 05 creates `apps/web`, `apps/api`, `apps/worker`, `apps/extension` and justified contracts/local infrastructure. Package-manager choices, dependency versions and infrastructure provider selections must be made there with evidence. This plan does not create app directories, install packages, or enable any private-data/paid workflow.
