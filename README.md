# MinhaAI

The Phase05 baseline now includes Phase06 identity and privacy flows: local email verification, verified adult sessions, versioned consent, guarded account recovery and private-resource permissions. Arabic RTL and English LTR account pages are available. Catalog data, AI, uploads, payments, ingestion and durable job execution await their named phases. Use synthetic accounts locally; real-user release approvals remain external gates.

## Local setup

Prerequisites: Python 3.12 with `venv` and pip, Node 22 with npm 10, GNU Make, Git, and Docker with Compose v2 (`up --wait` support). Linux/macOS shell commands are used. No global JavaScript packages are required. Docker downloads the local database image; package installation needs registry access. Preserve your environment's proxy and trusted CA settings.

```sh
make setup
make db-up
make migrate
make dev
```

Open [Arabic](http://127.0.0.1:3000/ar) or [English](http://127.0.0.1:3000/en). `/` redirects to `/ar`. The connection button calls `/api/v1/health` through the web origin; the API also listens on `127.0.0.1:8000`. `make dev` stops its own two processes with Ctrl+C. Use `make api` and `make web` in separate terminals if preferred. Both listeners bind to loopback.

`make setup` creates `.env` with randomly generated local Django/database credentials and mode 0600. It preserves any existing `.env`, creates `.venv`, installs the version-locked Python requirements and runs `npm ci` from the npm lockfile. `.env.example` contains placeholders only. Never commit `.env`. If you copied the example manually, generate new values locally before starting; placeholders are rejected. Existing environment variables override `.env` without being printed.

`make db-stop` preserves the database volume. Changing `.env`'s password does not change an already initialized PostgreSQL role; update it using your local database administration workflow. No target deletes data or volumes.

## PostgreSQL without Docker

An existing **local PostgreSQL 16** instance is also supported. Create an isolated database and login role through your normal local administration tools. Set `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST` and `POSTGRES_PORT` in the private `.env` to that instance, then run `make migrate` and `make dev`, skipping `make db-up`. Tests require the role to own the database and have `CREATEDB` so pytest can create/drop **its test database**. Never point tests at a production database. Credentials and privileged DB roles here are local/test conveniences; production least-privilege roles remain future work.

## Checks and generated contracts

```sh
make check
make build
make smoke
make worker-check
```

`make check` runs Ruff lint/format, mypy, frontend/client TypeScript, pytest against PostgreSQL, client unit tests, generated-contract drift/architecture compatibility, migration drift/applied-state and baseline secret checks plus Django system checks. Mypy checks annotated backend code; third-party Django/DRF internals are not stub-checked yet. No domain security or accessibility certification follows from these bootstrap tests.

`make build` produces the frontend production build. With ports 3000/8000 free, `make smoke` temporarily starts that build and Django, exercises both language pages and the real API rewrite, verifies liveness and safe 404 handling, then stops only its own processes. Liveness asserts the process can respond; it deliberately does not reveal configuration or promise database/provider readiness. `make worker-check` separately probes PostgreSQL then exits; ordinary worker execution is disabled.

If the environment cannot run PostgreSQL, `make unit` explicitly selects tests without a database and `make smoke-liveness` boots the same WSGI application without the development server's database preflight. These partial checks never substitute for `make test`, `make migrate` or the ordinary smoke gate. CI always runs the complete checks; it never silently skips PostgreSQL.

After changing annotated API serializers/views, run `make contracts` and review `packages/contracts/openapi.json` and `src/generated.ts`. `make contracts-check` regenerates in a temporary directory and fails on stale artifacts. [ADR 0009](docs/adr/0009-bootstrap-runtime-contract.md) explains how the runtime subset is checked against the future [architecture OpenAPI](docs/architecture/openapi.json). Schema generation is CLI-only; no public schema/admin endpoint exists.

Python dependency updates: use pip-tools 7.6.2 in a development environment, edit `apps/api/requirements.in`, run `pip-compile --strip-extras --no-emit-index-url --no-emit-trusted-host --output-file apps/api/requirements.txt apps/api/requirements.in`, review and rerun checks. This pins direct and transitive versions; it is not a wheel-hash lock. npm dependency changes must include a reviewed `package-lock.json`. No automatic upgrades are configured.

## Security boundaries and CI

Development uses one browser origin: Next forwards `/api/*` to Django. There is no CORS access grant. Django validates exact allowed hosts and CSRF origins and enforces CSRF even for anonymous unsafe DRF requests. Host-only HttpOnly SameSite=Lax cookies use a documented non-Secure **local HTTP exception** only with `MINHAAI_ENV=local`; other modes require HTTPS origins, Secure `__Host-` cookies and HTTPS redirects. This scaffold is not an approved production ingress. Next reads no backend `.env`; its server-only `API_INTERNAL_ORIGIN` defaults to `http://127.0.0.1:8000`. Export that process variable explicitly when changing the rewrite target, then rebuild because rewrites are fixed at build time. No provider/storage secret belongs in Next or `NEXT_PUBLIC_*` variables.

Errors use safe `application/problem+json` with server-generated correlation IDs. API logs contain only event, status and correlation ID, without URL/query, request body, cookies or exception contents. API responses are no-store. These logs are not the future append-only domain audit ledger. Next telemetry is disabled in all provided run scripts; no tracking/font service is used. New DRF endpoints deny access by default.

[CI](.github/workflows/ci.yml) runs the checks, migrations, build and HTTP smoke on an ephemeral PostgreSQL service with public test-only credentials. No repository secrets, deployment or paid resources are used. The lightweight secret guard scans tracked/proposed files and the environment template; it is not a full historical secret audit. Remote CI results are separate from local verification; local commands are reported in the [Phase 05 report](tasks/phase-reports/05.md) and [Phase 06 report](tasks/phase-reports/06.md).

## Repository and scope

- `apps/web`: Next.js App Router placeholder and connection check.
- `apps/api`: Django configuration, public health, structured errors, sessions and disabled worker command.
- `apps/worker`, `apps/extension`: documented worker boundary and inert permission-free Chrome MV3 manifest.
- `packages/contracts`: generated runtime OpenAPI/types and same-origin client.
- `infra`, `scripts`, `tests`: local database, repeatable commands and bootstrap checks.
- `docs/source`: actual PRD, owner decision resolution and provider proposal; all present and preserved.
- `docs/specs`, `docs/architecture`, `docs/adr`, `tasks`: derived specifications, design and phase evidence.

The [Phase 05 scope/traceability](docs/specs/phase-05-bootstrap.md) and [roadmap](tasks/implementation-plan.md) distinguish implemented bootstrap from future design. Legal/privacy/retention, provider/model/data approval, source/site permissions, scanner, backups/restore, hosting, measured quotas/quality and product-owner release signoff remain external gates. No deployment, AI call or paid resource is authorized. Phase06 changes remain local unless a separate push is requested.

## Phase06 local account and privacy verification

After the normal setup/database/migration commands, open `/ar/account` or
`/en/account`. Register with a synthetic `@example.invalid` address, a strong
12+ character password and an adult DOB. Default local email delivery writes
verification messages only under ignored `.local/mail/` (directory0700/files0600).
Read the latest private message locally and enter its code in the email-verification
form. Codes are never returned from registration/login APIs or logged. Do not
commit/attach these messages. Verification resend invalidates prior codes.
Local mode sends no real email. Nonlocal SMTP configuration and actual delivery
must be independently configured/verified; no email service is provisioned here.

```sh
make migrate
make check
make build
make smoke-identity
.venv/bin/python apps/api/manage.py plan_account_purges       # read-only count
# --enqueue records due exact-target tasks only; no object is physically erased.
```

The HTTP identity smoke creates an isolated synthetic local account, reads its
private local verification message, checks both account pages and actual same-origin
signup/verify/login/owned-access/403/logout, and prints no credentials. It leaves
only synthetic DB/mail evidence and stops its servers. PostgreSQL tests cover
strict18/leap dates, cross-user/admin403, CSRF, session/token revocation, immutable
audit, exact30-day UTC boundary, policy changes, support shares and concurrency.

Deletion requires a current impact review, password reauthentication and explicit
confirmation. Default30 means 720 elapsed UTC hours; configurable policy is frozen
per request and equality is too late to restore. No legal retention approval is
seeded, so deletion remains unavailable in a default checkout. Tests use synthetic
approved policy fixtures. An approved envelope is independent evidence, not a
configuration switch for ordinary Admin. Restore uses an independent one-use
email proof, never a normal deletion-pending session, and creates no signup grant
or login session. Personal-AI consent is revoked on deletion and not regranted on
restore. Actual storage erasure/backup replay remains gated; queued tasks are
`BLOCKED_STORAGE`, not success receipts.

Google is optional and unavailable without `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`
and an exact approved `GOOGLE_REDIRECT_URI` on a trusted web origin. The callback
page may be `/ar/account` or `/en/account`. Store server credentials only in private
environment configuration. Existing verified accounts can explicitly link after
recent password proof; matching email never merges users. New Google-only signup
is not enabled. Live Google/SMTP/MFA proof was not exercised; real privileged
Admin operations remain denied without a configured server MFA backend. The role
matrix, source conflicts and remaining gates are in [Phase06 scope](docs/specs/phase-06-identity-privacy.md)
and [report06](tasks/phase-reports/06.md).
