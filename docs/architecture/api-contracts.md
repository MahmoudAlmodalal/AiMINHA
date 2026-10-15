# API contracts and authorization — proposed v1

Status: ASSUMPTION engineering contracts, not complete FR baseline. Traces A, D OQ-003/004/007/013/016/022, P §2, U02. Machine-readable bounded flow schemas: [openapi.json](openapi.json), OpenAPI 3.1.0, draft API version 0.1.0. No generated clients, app routes or runnable API are implemented. Domain modules not represented in this bounded draft remain explicitly undeclared, not freely inventable.

## Protocol

JSON UTF-8 under `/api/v1`, opaque UUID IDs, ISO dates/RFC3339 UTC instants, integer Credits (never floats). Request schemas reject unknown fields, including owner_id/price/provider/roles. Server authorizes every object independently of ID opacity. Validations reject client-owned roles and authoritative version/provider labels. Error bodies use `application/problem+json`: type/title/status/code/detail/correlation_id, optional field_errors {field,code}, and optional retry_after_seconds. Detail is safe/localizable, contains no input body, file content or internals; frontend uses stable codes. Errors preserve no private context.

Statuses: 400 invalid JSON/schema/filter/cursor; 401 no authenticated session; 403 role/CSRF/adult/consent/approval forbidden; 404 inaccessible/missing resource (except explicit admin private-library denial is 403+audit); 409 stale resource/version/idempotency or insufficient Credits; 413 body/file bound; 415 unsupported content; 422 accepted syntax but invalid domain evidence/content; 429 local/global quota with Retry-After; 503 unavailable approved route/scanner/budget meter/feature gate. A 503 never selects a paid provider. Owner operation poll returns 200 with state and reason_code even if deferred/reconciling. Shared Problem response schema in OpenAPI deliberately permits these varying HTTP statuses.

All protected endpoints require active session; student endpoints also verified email, adult eligibility and lifecycle permission. All unsafe methods, including login, require Django CSRF cookie + `X-CSRFToken` and matching trusted Origin/Referer. Session expired → 401, CSRF invalid → 403, no side effect. GET/HEAD have no domain mutations except CSRF token issuance. Same-origin credentials; no wildcard credentialed CORS. Session is host-only Secure HttpOnly SameSite=Lax; CSRF token bootstrapped through `/session/csrf`, not URL. Login rotates session and CSRF; logout flushes session; neither is accepted without CSRF. Real OAuth signup/linking protocols are MISSING, not enabled by this draft.

## Pagination, filtering, concurrency

ASSUMPTION list page limit 20 default, 100 maximum; opaque authenticated cursor bound to filter/sort hash and direction, without PII; response {items,next_cursor}, stable ordering `published_at desc,id desc` or explicit allowed `deadline asc,id asc`. No arbitrary ORM sort/filter fields. Public scholarship filters: q (max 200 chars), country (ISO alpha-2), study_level (opaque taxonomy ID, max 64 chars), deadline_before (UTC instant), sort. Taxonomy values await PRD; validate against configured catalog, never invent enums. Unconfirmed deadlines exclude timed comparisons, not silently treated as far-future. Unknown query keys yield 400. Deleted/changed catalog can alter subsequent pages; cursor is not a database snapshot promise. Owned/admin routes always scope before pagination.

Mutating versioned resources use `If-Match` with server-issued opaque ETag: missing → 428, mismatch → 412 (more specific than generic 409 stale version). Draft schemas requiring snapshots use body version fields with 409 on stale snapshot. Server-side prices require known policy; unknown quote rejects rather than generates free AI. Publish records a new immutable approved version and audit; a race never loses intervening corrections.

`Idempotency-Key` required for operation creation, upload initiation/completion and publication; 16–128 characters from `[A-Za-z0-9._~-]`, scoped by authenticated actor + route + target. Canonical validated body and relevant If-Match hashed; same key/same hash returns original response+resource (202 replay does not enqueue again); changed hash → 409 IDEMPOTENCY_CONFLICT. DB uniqueness and concurrent key locking required. Failures before any side effect need not bind the key; after durable mutation it must stay bound. Reauthorize replays; never replay private output to a now unauthorized actor. Tombstone/operation uniqueness retained for lifecycle of irreversible actions; retention policy cannot enable old-key double debit. Temporary upload key expiry returns existing expired session, not a new storage grant. Transport retry does not settle a second credit.

## Bounded endpoint catalog

| Method/path after `/api/v1` | Request → result | Actor / checks / side effect |
|---|---|---|
| GET `/session/csrf` | none → {csrf_token} | Public, safe no-store; sets CSRF cookie. Token never logged. |
| POST `/session/login` | email,password → SessionView | CSRF+origin; credential checks, login throttling; server chooses no roles from client. Rotates session/token. Signup/OAuth deliberately absent. |
| GET `/session` | none → SessionView | Authenticated; actor state and CSRF refreshed through dedicated route after login. |
| POST `/session/logout` | no body → 204 | Authenticated+CSRF, session flush. |
| GET `/scholarships` | allowlisted query → ScholarshipPage | Public, published records only, no candidate/private metadata. |
| POST `/operations/document-generations` | kind, profile_version, optional scholarship_id/version, consent_version → OperationView (202) | Verified active adult; own snapshots; type-specific consent/policy/approved free route; reserve once, atomic enqueue. Kind enum CV/MOTIVATION_LETTER/PERSONAL_STATEMENT/ESSAY traces D §ب, not full PRD scope. |
| GET `/operations/{operation_id}` | none → OperationView | Verified active adult owner; no cross-user/admin library output; result reference only after SETTLED. |
| POST `/files/uploads` | filename,declared_content_type,declared_size → UploadSession (201) | Verified adult owner; scanner/caps active; reserve storage; quarantine-only capability and expiry, no public URL. Filename private, never telemetry. |
| POST `/files/{file_id}/complete` | object_version,checksum_sha256 → FileView (202) | Verified adult owner; capability/object identity and server-measured size/hash; atomic scan enqueue; remains QUARANTINED until scan completes. |
| GET `/files/{file_id}` | none → FileView | Verified adult owner only; metadata, status; admin library 403+audit. |
| POST `/files/{file_id}/download-capabilities` | optional ticket_id → DownloadCapability (201) | CSRF; owner verified adult or assigned support agent with explicit ticket attachment and accepted file; admin library access forbidden; no caching. Ticket ID supplies context, not permission. |
| POST `/admin/scholarships/{scholarship_id}/publish` | source_permission_ref,review_evidence_ref → ScholarshipView | Moderator scope, CSRF, ETag + idempotency, permission evidence and complete validated facts; transaction publish+audit+outbox. Does not authorize ingestion. |

This API draft omits signup, consent grant/revoke UI endpoints, profile editing, document read/export, moderation candidate editing, applications, matching, support/SLA, operational policy admin, payment and extension token issuance. Their domain boundaries are defined, but exact exposed payloads/actors and release scope require the missing baseline. No engineer may infer blanket permission from an omitted route.

## Result access and client behavior

Operation {id,state,kind,created_at,price_credits,policy_version,result_id?,reason_code?}; result_id nullable, only available on SETTLED. File {id,state,declared_size,created_at}; no direct storage key in normal file read. UploadSession and DownloadCapability contain expiring bearer URLs only in authorized no-store responses; OpenAPI marks them sensitive. No polling provider direct from browser. Duplicate transport retries reuse key; poll with bounded backoff, stop on final status, RECONCILING explains unresolved state. Workers returning valid-looking but ungrounded output yield rejected/reconciling status, not billable success.

## Required implementation acceptance

Schema conformance plus object-level authorization and CSRF are separate tests. Prove public catalog excludes candidates; unauthorized owned ID → 404; admin library → 403+audit; assigned attachment only; cookie/CSRF/origin failure has no mutation; tampered price/owner/provider rejected; repeated identical key returns same reservation; different payload same key conflicts; caps include concurrent reservations; wrong-version file scan/publish cannot accept; timezone day boundary and current consent checked at dispatch/finalization. These are test obligations, not passed tests.
