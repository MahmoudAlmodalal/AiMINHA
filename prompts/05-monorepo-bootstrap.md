# Phase 05 — Project setup, baseline CI and developer environment

**Objective:** Perform exactly one bounded phase of the MinhaAI build.

## Work
1. If repo already exists, adapt in place—NO destructive recreate. If blank, create `apps/web` (Next.js TypeScript), `apps/api` (Django DRF modular apps), `apps/worker` (or Django management command based worker), `apps/extension`, `packages/contracts` if needed, `infra/` and `tests/`.
2. Add `.env.example` with placeholders only, `.gitignore`, local Postgres Docker Compose, Makefile or scripts for dev/test/lint/migrations and README.
3. Add typed DRF OpenAPI generation and a generated/validated frontend client strategy; configure CORS/CSRF deliberately, not permissively.
4. Add minimal public health endpoint (no secrets), frontend placeholder, structured error handling, CI unit/build/static checks and local setup scripts.
5. Prove local app and API start, migrations run, lint/typecheck pass. Record any missing tool. Do not buy/deploy anything.

**Gate:** Clean clone can boot locally via documented steps and CI is informative; zero secrets committed.
## Required execution contract
- Read `AGENTS.md`, `tasks/implementation-plan.md`, `docs/source/MinhaAI_PRD_Decision_Resolution_AR.md`, and the authoritative source files where available.
- Execute only THIS phase. Identify source/requirement traces and unresolved external gates. Do not invent absent documents.
- Produce exact named artifacts, run relevant checks, update roadmap statuses, and write `tasks/phase-reports/05.md`. Report skipped checks truthfully.
- Do not push, deploy, create paid resources, or change other phases.

