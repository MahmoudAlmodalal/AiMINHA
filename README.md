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

## Phase07 catalog and source moderation

After `make db-up migrate dev`, browse `/ar/scholarships` or `/en/scholarships`.
The public catalog starts empty: no real-source permissions or award facts are
seeded. Search uses PostgreSQL full text, public filters and bounded pages.
Unknown funding, uncertain deadlines and missing freshness policies remain
explicitly unknown. The deadline filter includes confirmed future instants through
the selected UTC calendar day; it never guesses the donor's closing time.

`/{locale}/admin/catalog` provides the source registry, manual candidate entry,
immutable version comparison and exact-version human moderation. Every admin read
and mutation requires the existing server session, `MODERATION` scope and recent
server-verified MFA; recording an approved source additionally requires
`SOURCE_APPROVAL`, checked licensing/use basis and evidence. The live MFA backend
remains a Phase06 external gate, so ordinary local accounts cannot use these
privileged operations. Tests use isolated synthetic server proofs; no browser or
API field can manufacture one.

A permitted structured import is a supplied draft payload, never an outbound
fetch. Automation is always disabled. Candidate changes withdraw public visibility
until reviewed; restoring a listing returns it to review. Source revision changes,
revocation and expiry also withdraw the public projection until valid review.
Internal notes, permission evidence and editor identities remain private to the
moderation projection. No source crawler, semantic provider, personal matching,
student report workflow or reminder scheduler is added in this phase.

Run `make check build smoke smoke-identity smoke-catalog worker-check` for the
combined local checks (ports 3000/8000 must be free for smokes). The catalog smoke
checks six bilingual routes, the actual API rewrite, public search and denied
anonymous moderation; it does not claim browser interaction or real source/legal
approval. See [Phase07 scope](docs/specs/phase-07-catalog.md),
[ADR0011](docs/adr/0011-catalog-publication.md) and
[report07](tasks/phase-reports/07.md) for evidence and remaining gates.

Local `make api`, `make dev` and smoke commands use Django's `--nothreading`
development server so it explicitly closes upstream connections. This avoids the
observed Next rewrite pooled-socket `ECONNRESET` during consecutive requests.
It is a local integration workaround, not a production server or concurrency
performance claim. Database concurrency tests still use separate connections.

## Phase08 deterministic eligibility and fit

Run `make db-up migrate dev`, then open `/ar/eligibility` or `/en/eligibility`.
The verified adult student can save a private, versioned manual profile and
explicitly confirm each known field. Blank values remain unknown; a confirmed
empty list means an explicit declaration of no entries. Self-report is not
independent credential verification. Profiles and evaluations are owner-only;
Admin moderation does not provide access to these private facts.

Select a currently published scholarship to evaluate its exact reviewed rule
basis against the current profile version. Catalog prose and search facets do
not generate rules. A separate `MODERATION`/server-MFA review API binds structured
criteria, source evidence and completeness to the exact catalog version/hash.
Without that reviewed basis, the result is insufficient information. Source
permission, publication, profile/rule versions and freshness are rechecked;
obsolete evaluations cannot appear current.

Every rule reports pass, fail or unknown with evidence. A failed mandatory
condition always makes the aggregate ineligible. The initial fit weights are
academic30%, field25%, nationality/residency20%, language15%, interest10%.
A score appears only with at least70% covered verified comparisons; missing
comparisons are not a zero score or a pass. Fit is not an acceptance probability,
and the weights are uncalibrated. GPA comparisons require the same explicitly
known scale; arithmetic within a scale never establishes institutional or
cross-scale equivalence. This phase makes no AI/provider call or Credit charge.

`make check build smoke-eligibility` validates the implementation and the actual
same-origin profile/permission flow using synthetic local security email.
Existing catalog behavior is preserved; new eligibility fixtures are authored
synthetic data and do not seed a live scholarship/rule approval. Real MFA,
source/credential approvals and production security gates remain independent.
See [Phase08 scope and warm p95 measurement plan](docs/specs/phase-08-eligibility.md),
[ADR0012](docs/adr/0012-evidence-bound-eligibility.md), and
[report08](tasks/phase-reports/08.md). The warm p95 target is <=2 seconds;
a production 20-client HTTP load result is not claimed by unit tests or smoke.

## Phase09 credits and reconciliation

Run `make db-up migrate dev`, then open `/ar/wallet` or `/en/wallet` after
verifying an adult student account. Verification grants 30 Credits once in the
activation transaction. The upgrade migration also grants existing active,
verified adult students once. Credits are internal units, with no payment or
purchase route. A new day never refills the wallet. The beta daily spend cap is 6
in `Asia/Hebron`; held and settled Credits count toward the captured day's cap.
The global cap is 100 admitted logical AI operations per Hebron day, including
failed operations. A retry of the same operation does not consume that cap again.

Current internal prices are matching AI 1, CV extraction 4 and new document 6.
Browsing, rules-based eligibility, manual edits, same-version re-export and the
extension are free entitlements; naming them does not enable unfinished phases.
Only Admins with `COST_POLICY` and fresh server-verified MFA can publish a new
policy through `/api/v1/admin/policies/credits`, with CSRF, `If-Match` and
`Idempotency-Key`. Accepted operations keep their captured price and policy;
changing a policy never resets day counters or tops up an existing grant.
Real MFA enrollment remains a separate external integration gate.

The atomic service kernel holds funds before work and debits only when an exact
validated output is saved in the settlement transaction. It has a local-only,
server-created synthetic fixture adapter for financial tests. There is no public
reserve/run/settle endpoint or provider call. Real matching/CV/document adapters,
input classification and provider approval remain gated by Phases10–11.

`make credits-timeouts` inspects expired reservations without changes.
`.venv/bin/python apps/api/manage.py mark_credit_timeouts --apply`
marks overdue 15-minute reservations `RECONCILING`. It is safe to repeat or resume
the DB scan after a crash. Run it from your own local scheduler when exercising
timeouts; no production scheduler is installed. An uncertain outcome retains its
hold, including after the experimental 24-hour review target. That target is an
overdue indication, never an automatic debit, release or resend. Resolving real
provider uncertainty needs the later authoritative adapter; it is unavailable here.

Run `make check build smoke-credits credits-timeouts` for local validation.
Concurrent financial tests use separate PostgreSQL connections. SQL guards
verify journal/hold/day/output conservation at commit; their full-journal scans
are a bounded correctness baseline and require profiling before production load.
See [Phase09 scope](docs/specs/phase-09-credits.md),
[ADR0013](docs/adr/0013-credits-and-reconciliation.md) and
[report09](tasks/phase-reports/09.md) for evidence and remaining gates.

## Phase10 AI gateway and budget stop

The backend now has a provider-independent gateway with explicit input
classification, exact provider/model/data-type/purpose/region approval evidence,
bounded attempts, a circuit breaker, physical quota reservations and grounded
output validation. Public text mixed with student data is private; passwords,
OTPs and prohibited actions are never eligible. A provider name, API key or
remaining quota does not constitute approval. Existing generic PERSONAL_AI
consent is insufficient for a provider-specific private processing bundle.

All real transports remain disabled. Cloudflare, Groq, Gemini Free and
OpenRouter Free adapters return an unavailable result without opening a socket.
Private data cannot route to Gemini Free, OpenRouter Free or the mock. No real
approval, free-account guarantee or usage measurement is seeded. The only
executable adapter is a local server-owned synthetic mock, available to internal
tests without a public execution endpoint. `GET /api/v1/ai/capabilities` reports
the closed client gates to verified adult students and exposes no credentials.

The mock orchestrates one existing credit operation, preserving its original
price, key and canonical global logical admission (default 100 per Hebron day).
Before each physical attempt, current global stops and a fresh, evidenced,
free-only quota window must permit its worst-case allocation. Windows are keyed
by provider/account/unit across models and configs, with explicit UTC boundaries.
Cloudflare bookkeeping requires Neurons and a maximum experimental ceiling of
8,000. This ceiling does not establish actual free capacity. A missing, stale,
unknown or exhausted meter stops dispatch. Immutable baseline snapshots cannot
be reset or replaced by an overlapping window; live meter ingestion is a future
approval gate. Unknown calls remain reserved across subsequent windows.

Each committed dispatch intent precedes adapter invocation outside database
transactions. Attempts default to 10-second leases and at most 2 per config, with
a hard total of 3 per operation. These are engineering defaults. Known
not-executed failures may retry within that bound; their physical upper bound is
conservatively retired, never treated as measured zero usage. Timeout/unknown
effects retain physical and financial holds and cannot trigger fallback or a
blind refund. Three failures open the circuit for 30 seconds; only one half-open
probe may run. No paid upgrade or alternate private processor is available.

Output is a strict local quotation schema, requiring exact known evidence and
citation IDs with no tools/actions. Unsupported claims are not chargeable
success. A successful result, saved gateway output and the existing synthetic
credit settlement proof commit atomically. This is not a real CV/document
validator, processor consent flow or Arabic/English quality certification.

Run `make db-up migrate check build smoke-credits ai-timeouts` locally. The credit
HTTP smoke also checks closed AI capabilities. `make ai-timeouts` inspects only;
`.venv/bin/python apps/api/manage.py mark_ai_timeouts --apply` marks expired
dispatch intents uncertain without sending, retrying or releasing funds. Run
the credit timeout marker as well for work that never reached dispatch.
No production scheduler, live transport, private processing or provider billing
test is installed or claimed. See [scope](docs/specs/phase-10-ai-gateway.md),
[ADR0014](docs/adr/0014-ai-gateway-and-budget-stop.md) and
[report10](tasks/phase-reports/10.md) for traces and actual validation.
