# MinhaAI screen inventory and wireframes — Phase 04

2026-10-15. **ASSUMPTION UX specification, not implemented screens.** Read with [flows](user-flows.md), [tokens and interaction rules](design-system.md), [PRD](../source/PRD.md) §§11–15/18–20/23, [D owner/default decisions](../source/MinhaAI_PRD_Decision_Resolution_AR.md), [UD-001](../source/2026-10-15-owner-decisions.md), [OpenAPI](../architecture/openapi.json) and [API semantics](../architecture/api-contracts.md). API references below are exact method/path pairs relative to `/api/v1`; a documented endpoint is not a running service or legal clearance. No API/schema change is made here.

## Universal route contract

All web paths have proposed `/{locale}` prefix (`ar|en`). UUID route IDs are opaque references, always authorized server-side. Guest G, active verified adult owner S, MFA Admin with exact scope A, and currently assigned support-scoped MFA Admin T are actor abbreviations. T is an Admin scope. Every private route also needs active lifecycle, no-store delivery, scoped retrieval before rendering, and current permission on each command/download.

Every route inherits these states; route-specific **E/L/X/O/D** below supplies empty/loading/error/offline/disabled detail. **E** never uses a fabricated record or zero for unknown. **L** uses text plus skeleton, `aria-busy`, preserves heading/navigation, and announces completion once. **X** uses safe localized Problem codes, inline field errors plus focused summary, correlation ID for help; no stack traces or private payloads. 401/403/404/409/412/428/429/503 behavior follows flows' recovery contract. **O** disables mutations and says whether last result is stale or outcome unknown; private data is not persisted for offline use. **D** keeps a readable adjacent reason and an actionable alternative; no hover-only tooltip. Not-applicable states are explicitly described, not omitted. Capabilities unknown/unavailable means gated actions disabled; public content and navigation remain readable where available.

All routes use logical inline-start labels/alignment and DOM order that follows visible reading order in Arabic RTL and English LTR. The **Bidi** entry names route-specific exceptions. Email, URL, IDs, code and ISO examples isolate LTR; names/body text use `dir=auto`. UI locale never changes a document's selected language. Layout defaults: mobile 320–767px one column, laptop ≥1024px rail/content or two columns; 768–1023px adapts without hiding tasks. Each **Wireframe M / L** describes reading order, not pixels. All dialogs have labelled title, focus trap/return and keyboard dismiss except while a critical mutation result is unknown (retain a safe close/navigation option).

## Unavailable contract and external dependencies

The following MISSING findings are additive UX dependencies. Existing architecture is retained; no broad permission or invented endpoint fills a gap. Affected sections render a disabled shell, and only documented readable portions remain active. Deferred capability is not marked implemented by this phase.

| ID | Observed contract gap / affected routes | Required UX restriction until separately resolved |
|---|---|---|
| UX-API-01 | ScholarshipPage supplies title/version/deadline/verification but no source URL, last-check time, provider/funding. R01/R02/R15 | Enrich visible cards only through authorized `GET /scholarships/{scholarship_id}`; show loading/unknown source metadata until it succeeds, never infer freshness from publication time. Detail provides facts.official_url and last_verified_at. No card's verified label implies unknown facts are verified. |
| UX-API-02 | Admin sources have POST but no source registry/history GET; scholarship/report/audit lists return CommandPage IDs/state/row_version/correlation only. No candidate content/diff/report evidence/audit-event read. R34–R36/R44 | Metadata-only queues. Evidence-dependent review/approve/publish/report decisions, source editing/history and detailed audit viewer disabled; no fetching a student's library or unpublished data through public API. New candidate entry may prepare manual input but source selection/permission evidence must be verifiable before sending. |
| UX-API-03 | OperationView.kind enum includes only four document types despite extraction/match/support endpoints; extraction proposals and AI match result have no typed readable result endpoint. No operation-list lookup recovers a lost request identity after full reload. R13/R14/R17/R18/R26 | Extraction, AI match and AI support initiation disabled until type/result contracts agree. Existing deterministic checks, manual profile and human messages remain usable within other gates. Never interpret result_id as an undocumented GET route. Lost key with no returned operation ID means outcome unknown/help, never another paid start with a new key. |
| UX-API-04 | EligibilityView has checks/coverage/score/policy ID but no contribution breakdown, confidence/limitations or evaluation time. R14 | Show deterministic status/evidence/coverage/pinned versions. Withhold fit score and advanced rationale until a complete explainable projection is available; do not derive confidence from coverage or access Admin-only policies. |
| UX-API-05 | No scoped Admin wallet/ledger/adjustment-case read or reconciling-operation list. R40 | Disable financial case decisions/adjustments/reconciliation; do not reuse owner wallet/operation endpoints with another student's ID or accept an unverified pasted balance. |
| UX-API-06 | TicketView lacks subject/assignment/closed_at/attachment list; no Admin history/attachment-list endpoint or SLA closure/rating policy read/write. R25/R26/R41/R42/R43 | List uses ID/category/state/priority only. Unassigned users cannot load threads; assignment response is not attachment inventory. Shared file visibility/revocation only for IDs established in current authorized share workflow; after reload show unavailable list. Reopen is a server-validated request, no invented countdown. Rating, configurable closure UI and rich assignment history disabled. |
| UX-API-07 | Deletion requires reauthentication_token but no issuance endpoint, deletion-impact/current student recovery-policy/deletion-status read or pre-confirm cutoff. R29/R30 | Account deletion confirmation disabled until approved informed-impact and recent-proof protocol can be completed. Recovery can submit purpose proof to existing endpoint, but cannot fetch disabled-account profile/wallet to show pending status. No fabricated recovery deadline before authoritative DeletionView. |
| UX-API-08 | Google LINK requires recent proof/link challenge in prose but wire lacks that proof workflow; verification consume exists without resend endpoint. R05/R07/R08/R28 | Initial Google signup/sign-in only once deployed approved config supports it; existing-account linking and verification resend disabled with recovery/manual sign-in alternatives. MFA enrollment requires independent bootstrap; never offer self-serve bypass. |
| UX-API-09 | NotificationView lacks notification body/preview and preference GET. R11/R24 | Render known category + timestamp + typed destination, no invented source-change text. Optional preference controls start unknown until confirmed change; do not claim current selection, unread total or full counts from one page. |
| UX-API-10 | Extension release has no request parameters beyond token scope despite portal/selection context in prose; pairing carries portal/application. R31/R32 | Bind release to pairing's exact portal/application, no client-side widening or switching. Sensitive subset server consent and origin enforcement require security review G-EXT; disable pairing/fill until proved. No status-write or private-file permission. |
| UX-API-11 | No general manual document-create/clone/variant endpoint, rich uploaded-file organization, explicit frozen marker, or full aggregate personal statistics. R11/R19–R23 | Edit existing owned docs; no new blank/clone/variant promise. Show version references from owned checklist/history only, no assumed freeze badge; server rejects locked action. No denominator/progress percentage or all-account counts from a paginated subset. |
| UX-API-12 | No payment/package wire surface or public approved legal-content service. R46–R49 | Beta payments are unavailable. Legal pages require independently approved versioned static content; absent content says unavailable and real-user activation remains blocked. No invented legal policy or payment instructions. |
| UX-API-13 | ScholarshipDetailView has a nullable UTC confirmed_deadline but no donor timezone or structured round/key list. R03/R15/R22/R23 | Show a known instant explicitly as UTC; donor-zone display, multiple/rolling round labels and round selection stay unavailable unless supplied by an authorized reviewed projection. Do not invent a round_key to create an application; existing owned records retain their stored round. |

External gates apply independently: G-LEGAL/G-RESTORE/G-SIGNOFF block real-user release; G-SOURCE gates source use; G-PROVIDER gates every classified AI route including free ones; G-SCANNER gates upload/preview/conversion; G-EXT gates site/Chrome support; G-PROFILE preserves unknown scales/required fields; G-TICKET gates undefined rating/warnings/staffing claims; G-STATUS gates unlisted transitions/official feeds; G-MEASURE/G-HOSTING gate capacity/deployment claims; G-PAID stays closed in Beta. Missing field dictionaries/localized taxonomies must disable affected selectors rather than invent values. [Gate evidence register](missing-inputs.md) remains authoritative for those external proofs.

## Public and identity routes

### R01 — `/` — public scholarships landing

- **Purpose / trace:** G; explain discovery, preparation and no admission guarantee; SCR-001/007; FR-021/069/121; AC-012. **Fields:** locale, public scholarship titles/source/freshness via bounded detail enrichment. **Validation:** approved public content only, capabilities from server. **CTA / hint:** “Browse scholarships”; signup explains adult verified account for saved/private work.
- **API:** `GET /capabilities`; `GET /scholarships`; `GET /scholarships/{scholarship_id}`. **E/L/X/O/D:** E no published opportunities → browse/check later; L public cards; X catalog retry; O already-rendered public data marked stale; D gated AI/payments labelled unavailable, never advertised as active. UX-API-01.
- **Wireframe M / L:** M heading/disclaimer → browse CTA → featured cards → how it works → policies. L compact header, introductory text beside public cards, same order. **Bidi:** mirror sections and directional icons; isolate provider URLs/names appropriately.

### R02 — `/scholarships` — browse and filter

- **Purpose / trace:** G public; S for personal filters. SCR-007; FR-025–027/032; AC-012. **Fields:** query ≤200 chars; level, discipline, country, funding, language, verified deadline-before, sort, TEXT/SEMANTIC; S-only eligibility/application state. **Validation:** exact OpenAPI filter keys/enums; taxonomy IDs from approved dictionary; convert explicit timezone date selection to UTC; unknown deadlines excluded from timed comparisons. No relevance sort enum exists: expose published-date/deadline only and explain unavailable relevance sorting.
- **API:** `GET /scholarships`; `GET /scholarships/{scholarship_id}`; `GET /capabilities`. **CTA / hint:** Apply filters, clear, next page; “Unknown deadline is not included in date filtering.” **E/L/X/O/D:** E no matches → remove individual filters; L keep query/results dimmed; X invalid filter inline/retry; O no new fetch; D personalized filters for G and unapproved SEMANTIC have visible reason. UX-API-01; no hidden LLM egress.
- **Wireframe M / L:** M search → active chips → filter sheet with count-free Apply → sort → cards → next. L filter column + result column; no hidden mobile filters. **Bidi:** logical chip/remove order, LTR URL queries internal only, Arabic query preserved; no forced transliteration.

### R03 — `/scholarships/{id}` — opportunity details

- **Purpose / trace:** G; S owns save action. SCR-008; FR-021–023/027/051; AC-007/012. **Fields:** provider, official URL/source, verification status/time, funding scope/unknowns, levels/criteria/documents, confirmed deadline or unknown. **Validation:** published projection only; no invented rounds/timezone if not returned; external URL safety and source permission. **CTA / hint:** Open official source, S save / G sign in to save; check current requirements with provider.
- **API:** `GET /scholarships/{scholarship_id}`; `PUT /saved-opportunities/{scholarship_id}`. **E/L/X/O/D:** E inaccessible/withdrawn → catalog; L sections; X safe 404/retry; O source remains external only if safe, no save; D missing/unsafe submission URL, stale deadline reminders and unpublished versions unavailable with reason.
- **Wireframe M / L:** M title/freshness → funding/deadline → eligibility → requirements → source/CTAs. L main facts plus side summary/action card. **Bidi:** official URL LTR, criteria auto direction; dates always include known zone.

### R04 — `/scholarships/{id}/report` — information report

- **Purpose / trace:** S; SCR-008; FR-024; AC-008. **Fields:** category, evidence text ≤8000, exact viewed scholarship version. **Validation:** approved category dictionary and bounded plain text; no unsupported attachment field. **CTA / hint:** Send report; report requests review, not automatic removal.
- **API:** `POST /scholarships/{scholarship_id}/reports`. **E/L/X/O/D:** E blank form; L retain typed evidence while sending; X field errors/outcome unknown retry with same key; O submit off; D G → sign in, duplicate submission pending → wait. Success shows returned case ID/state only.
- **Wireframe M / L:** M scholarship context → category/evidence → send; L narrow form beside source summary. **Bidi:** evidence `dir=auto`, version/ID isolated LTR.

### R05 — `/sign-up` — declared adult registration

- **Purpose / trace:** G; SCR-002; FR-001–005; AC-001/002. **Fields:** email, password, explicit DOB, locale; Google choice. **Validation:** real nonfuture date, server 18+ policy incl leap-day uncertainty, email ≤254, password server policy (no invented minimum); no role/grant field. **CTA / hint:** Create account; self-declared DOB is not official identity verification; verified eligible activation grants once.
- **API:** `POST /auth/registrations`; `POST /auth/google/authorizations`. **E/L/X/O/D:** E blank; L disable duplicate submit; X non-enumerating identity failure, specific invalid/minor DOB; O no activation; D G-LEGAL/auth config/age ambiguity blocks activation, Google unavailable fallback email. UX-API-08.
- **Wireframe M / L:** M method → labelled fields → age/privacy explanation → submit → sign in; L one readable-width panel. **Bidi:** email/password LTR controls; DOB labelled day/month/year independent of direction, locale-formatted help.

### R06 — `/sign-in` — session entry

- **Purpose / trace:** G; SCR-002; FR-001/006/007; AC-003. **Fields:** email/password; Google, recovery links. **Validation:** credentials handled server-side, no client-selected role; safe return path. **CTA / hint:** Sign in; unverified/deletion-pending status uses safe verification/recovery branch, not ordinary protected access.
- **API:** `GET /session/csrf`; `POST /session/login`; `GET /session`; `POST /auth/google/authorizations`. **E/L/X/O/D:** E blank; L signing in; X generic credentials/CSRF retry bootstrap; O sign-in off; D throttled → retry interval, unavailable provider → email. Login never proves Admin scopes without MFA.
- **Wireframe M / L:** M/laptop compact form with recovery beneath password. **Bidi:** email/password LTR; error summary follows UI direction.

### R07 — `/auth/google/callback` — OAuth completion

- **Purpose / trace:** preactivation owned identity or sign-in; SCR-002; FR-003–005; AC-001/002. **Fields:** server code/state exchange, DOB/locale only if new Google account. **Validation:** state/nonce/PKCE/provider claims server-verified; explicit adult check; never merge by equal email. **CTA / hint:** Complete registration or return to sign-in; existing account uses verified login/recovery.
- **API:** `POST /auth/google/callbacks`; `POST /auth/google/activation`. **E/L/X/O/D:** E invalid/missing callback → restart; L exchange once; X safe identity collision; O no replay by a new identity/key; D LINK proof workflow unavailable UX-API-08. Callback secrets scrubbed from visible URL/logs after handling.
- **Wireframe M / L:** M/laptop status panel then short DOB form if needed. **Bidi:** code/state never rendered; dates follow R05.

### R08 — `/verify-email` — verification

- **Purpose / trace:** purpose-bound challenge; SCR-003; FR-002/005; AC-002. **Fields:** one-use challenge, verification outcome. **Validation:** account/purpose/expiry/rate checks; token never shown in analytics. **CTA / hint:** Verify → sign in; grant only on eligible activation, never on page view.
- **API:** `POST /auth/email-verifications`. **E/L/X/O/D:** E missing challenge → instructions; L verifying; X expired/used generic recovery instructions; O verify off; D resend unavailable UX-API-08, no fake resend button success.
- **Wireframe M / L:** M/laptop single status card + sign-in link. **Bidi:** masked address isolated LTR only if safely available; localized outcome.

### R09 — `/password-recovery` — request and reset password

- **Purpose / trace:** G/purpose proof; SCR-003; FR-006. **Fields:** email then challenge/new password. **Validation:** format and configured password policy, expiring single-use purpose proof, reset invalidates sessions. **CTA / hint:** Send recovery instructions; Save password. Same acknowledgment regardless of account existence.
- **API:** `POST /auth/password-reset-requests`; `POST /auth/password-resets`. **E/L/X/O/D:** E request form; L processing; X invalid/expired proof restart; O no submit; D Retry-After countdown text when throttled, never imply delivery confirmed.
- **Wireframe M / L:** M/laptop two distinct steps with explicit completion. **Bidi:** email/password LTR, no raw challenge in rendered body.

### R10 — `/admin/mfa` — Admin second factor

- **Purpose / trace:** Admin pre-MFA only; SCR-002/025; FR-007; AC-003. **Fields:** challenge and one of server available TOTP/WebAuthn proofs. **Validation:** current challenge, expiry, replay/rate limits; no assumed factor method. **CTA / hint:** Verify; enroll/recover through approved security workflow only.
- **API:** `POST /admin/mfa/challenges`; `POST /admin/mfa/verifications`. **E/L/X/O/D:** E no available methods → security setup required; L verification; X rejected/expired proof; O no access; D no factor backend → protected Admin disabled, no bypass/enrollment shortcut.
- **Wireframe M / L:** M/laptop narrow challenge with supported method control and sign-out. **Bidi:** numeric factor LTR with a single labelled input, WebAuthn platform dialog respects locale.

## Student workspace routes

### R11 — `/home` — personal overview

- **Purpose / trace:** S; SCR-004; FR-014/056/071/089. **Fields:** profile missing_fields, wallet available/reserved, loaded application summaries and notices. **Validation:** owned projections only; pages are not all-account totals. **CTA / hint:** Complete known profile fields, browse, resume application.
- **API:** `GET /profile`; `GET /wallet`; `GET /applications`; `GET /notifications`. **E/L/X/O/D:** E first-use links; L each panel independent; X per-panel retry, no 0 balance on failure; O private values stale in memory only; D absent metrics/previews UX-API-09/11.
- **Wireframe M / L:** M next task → credits → current applications → notices; L same content in bounded columns. **Bidi:** count and credit units explicit, application IDs isolated.

### R12 — `/profile` — manual personal/academic facts

- **Purpose / trace:** S; SCR-005; FR-008–010/013/014; AC-004/005. **Fields:** name/contact, nationality/residency, Bachelor/Master/PhD, field/institution/qualification, GPA+scale, languages+proof, interests/preferred countries; confirmed flag per fact. **Validation:** approved stage/key/type dictionary; known scale normalization only, optional unknown stays null; no invented required PhD fields. ETag conflict does not overwrite.
- **API:** `GET /profile`; `PUT /profile`. **CTA / hint:** Review and save facts; manual entry is free. **E/L/X/O/D:** E unknown fields with examples, not fabricated values; L load/save separate; X field errors/stale comparison; O unsaved current-memory draft labelled unsaved; D undefined stage inputs/unsupported scale G-PROFILE explain limitation, save other known fields where server permits.
- **Wireframe M / L:** M stage → short labelled sections → review confirmation → save; L section navigation + form. **Bidi:** names `auto`, GPA number/scale pair LTR with localized labels; country names translated, IDs stable.

### R13 — `/profile/extraction` — upload and proposal review

- **Purpose / trace:** S; SCR-006; FR-011–014/050; AC-004/005. **Fields:** file type/size, accepted asset ID, disclosure, quote, proposed field/source/uncertainty/accept/edit/reject. **Validation:** exact accepted scan before preview/AI; current configured limits ≤5,000,000 bytes per upload draft contract; student confirmation never implicit. UX-API-03 blocks extraction/result review; no fabricated proposals.
- **API:** `POST /files/uploads`; `POST /files/{file_id}/complete`; `GET /files/{file_id}`; `POST /quotes`; `POST /operations/cv-extractions`. **CTA / hint:** Conditional extract, always Continue manually. **E/L/X/O/D:** E no file; L upload/quarantine/scan distinct from acceptance; X rejected/scanner outage/manual path; O stop upload and check exact session on reconnect; D missing scan/provider/typed result blocks affected action before send.
- **Wireframe M / L:** M upload bounds → consent/quote → proposals one field at a time → confirm; L source/proposals side by side only after accepted authorized preview. **Bidi:** file/source snippets auto, type and byte figures isolated.

### R14 — `/scholarships/{id}/eligibility` — reasons and optional fit

- **Purpose / trace:** S; SCR-010; FR-028–033; AC-009–011. **Fields:** profile/listing versions, criterion PASS/FAIL/UNKNOWN+evidence, aggregate Eligible/Ineligible/Undetermined, coverage, policy ID. **Validation:** missing mandatory evidence never passes; hard fail dominates; no probability. Optional quoted AI explanation blocked UX-API-03/04.
- **API:** `POST /eligibility-evaluations`; `POST /quotes`; `POST /operations/match-explanations`. **CTA / hint:** Check eligibility (free), complete missing facts, verify source; fit button says unavailable. **E/L/X/O/D:** E not evaluated; L rules checking; X stale snapshots refresh for review; O previous result explicitly stale; D confidence/contributions/time/score withheld until supported, not inferred from policy ID or coverage.
- **Wireframe M / L:** M outcome → blockers/unknowns → evidence list → optional fit section; L reasons beside profile/source actions. **Bidi:** status is text+icon; evidence auto; percentages isolated and labelled coverage only.

### R15 — `/saved` — saved opportunities

- **Purpose / trace:** S; SCR-009; FR-051/057. **Fields:** owned saved listing page and authorized detail enrichment; save state. **Validation:** exact known scholarship ID; withdrawn detail denied normally. **CTA / hint:** View, unsave, prepare via R23; saving is not applying.
- **API:** `GET /saved-opportunities`; `PUT /saved-opportunities/{scholarship_id}`; `GET /scholarships/{scholarship_id}`. **E/L/X/O/D:** E browse scholarships; L cards; X withdrawn source warning, unsave conflict retry safely; O no toggle; D create application absent usable round/version → explain, no invented round. UX-API-01.
- **Wireframe M / L:** M saved cards/source change warnings; L compact grid. **Bidi:** mirror card actions; source/date isolation as R03.

### R16 — `/credits` — wallet and ledger

- **Purpose / trace:** S; SCR-017; FR-069–079; AC-023–025. **Fields:** available/reserved/posted/frozen, entry kind/signed amount/reason/time, known operation link only if retained authoritatively. **Validation:** integer Credits; never daily allowance as balance or cash. **CTA / hint:** View history, check operation, human support; purchase unavailable Beta.
- **API:** `GET /wallet`; `GET /wallet/entries`. **E/L/X/O/D:** E no posted entries (holds may still exist); L balance unknown until response; X retry no inferred balance; O read values marked stale/no spend; D purchase off, unknown daily remaining/per-operation history unavailable rather than computed from incomplete page.
- **Wireframe M / L:** M available → reserved explanation → ledger cards; L wallet strip above scrollable semantic ledger. **Bidi:** signed amounts LTR with Credits unit; debit sign remains visible, timestamps explicit zone. D proposed 30 once/6 daily spend are policy examples, not live values or recurring grants.

### R17 — `/documents/new` — AI document request

- **Purpose / trace:** S; SCR-013; FR-034–038/041; AC-013/015/023. **Fields:** CV/Motivation Letter/Personal Statement/Essay; output ar/en; profile/listing snapshot; disclosure and exact quote/expiry. **Validation:** no unconfirmed credentials, scholarship/version pair, manifest bound to inputs; changed input/expired quote needs new confirmation. No essay-prompt/word-limit wire field is invented.
- **API:** `GET /profile`; `GET /consents/disclosures`; `POST /quotes`; `POST /operations/document-generations`. **CTA / hint:** Confirm N Credits and generate; AI draft requires review. **E/L/X/O/D:** E select type/facts; L quote then operation admission; X unsupported content/balance errors preserve choices; O confirm off/outcome unknown polls existing operation; D no consent/approved provider/caps → manual editing of an existing doc, no blank-create API UX-API-11.
- **Wireframe M / L:** M type/language → facts → disclosure → quote → confirmation; L steps plus review summary. **Bidi:** output selection independent; preview language direction independent of UI.

### R18 — `/operations/{id}` — authoritative progress

- **Purpose / trace:** S; SCR-013/006; FR-041/074–077/122–125; AC-024/040/041. **Fields:** operation ID, kind, state, accepted price/policy/time, reason, result_id on SETTLED only. **Validation:** own ID; no fake percent/ETA; exact same key for transport retry, no blind new paid run.
- **API:** `GET /operations/{operation_id}`. **CTA / hint:** Refresh, open authorized document result, contact support with ID. **E/L/X/O/D:** E inaccessible operation safe 404; L first load then textual state; X poll outage distinct from failed job; O outcome unknown, do not restart; D repeat generate off while unresolved. Non-document kinds blocked UX-API-03.
- **Wireframe M / L:** M/laptop status timeline → hold/debit disclosure → next action. **Bidi:** ID isolated LTR; RESERVED/RUNNING/RECONCILING/SETTLED/RELEASED translated as specified in design system.

### R19 — `/documents` — private library

- **Purpose / trace:** S; SCR-015; FR-043/044/049/050/116; AC-016/036. **Fields:** generated metadata/current version/language/approval and owned uploaded assets with accepted/scan state, optional filename. **Validation:** owner only; no preview/download before ACCEPTED; per-document delete effect approved by legal policy. **CTA / hint:** Open, rename, controlled delete, upload if enabled; generated/uploaded sections both discoverable.
- **API:** `GET /documents`; `GET /files`; `PATCH /documents/{document_id}`; `DELETE /documents/{document_id}`; `DELETE /files/{file_id}`; `POST /files/{file_id}/download-capabilities`. **E/L/X/O/D:** E generate or manual profile; L list metadata; X access denial no file leak; O no private offline storage; D scan/retention missing disables upload/delete, no clone/group/blank-create promise UX-API-11.
- **Wireframe M / L:** M filter visible page locally, document cards → uploads; L metadata table with overflow region. **Bidi:** titles auto, format/version LTR; do not expose storage keys.

### R20 — `/documents/{id}` — manual editor and preview

- **Purpose / trace:** S; SCR-014; FR-035–042/046/048; AC-013–016. **Fields:** supported structured text blocks, language, version/hash, approved flag; marks requiring review only if authoritative, otherwise no invented AI assurance. **Validation:** schema-safe formatting; save creates new unapproved version; approval exact hash/version; frozen write denied server-side. **CTA / hint:** Save revision, I reviewed this version, Export PDF/DOCX; no chat-based editing.
- **API:** `GET /documents/{document_id}`; `GET /documents/{document_id}/versions/{version_id}`; `POST /documents/{document_id}/versions`; `POST /documents/{document_id}/approvals`; `POST /documents/{document_id}/exports`; `GET /jobs/{job_id}`. **E/L/X/O/D:** E no accessible content → library; L body/export job distinct; X save conflict/locked version → new revision, export failure retains text; O current-memory unsaved warning/no persistence; D export until approved and scanner enabled. Export result file retrieved only via authorized capability when job gives output_file_asset_id.
- **Wireframe M / L:** M toolbar → document → review → export; L editor/preview tabs or split, never fixed-width paper overflow for editing. **Bidi:** body follows document language; toolbar follows interface language; keyboard formatting named.

### R21 — `/documents/{id}/versions` — compare and restore

- **Purpose / trace:** S; SCR-016; FR-046–048; AC-016/017. **Fields:** version list, selected pair, text/body diff, approval, known linked-version context. **Validation:** same owner/document; restore appends new version requiring new approval; no historical overwrite. **CTA / hint:** Compare, Restore as new revision; submitted snapshots stay unchanged.
- **API:** `GET /documents/{document_id}/versions`; `GET /documents/{document_id}/versions/{version_id}`; `POST /documents/{document_id}/restorations`. **E/L/X/O/D:** E one version → no comparison yet; L selected bodies; X stale head reload before restore; O restore off; D no reliable frozen marker UX-API-11, do not assert unlinked/unused from absence.
- **Wireframe M / L:** M version selectors → stacked additions/deletions labelled; L synchronized side-by-side with semantic text alternative. **Bidi:** each document panel uses its own language; addition/deletion uses text/icon, not color alone.

### R22 — `/applications` — personal tracker

- **Purpose / trace:** S; SCR-011; FR-051/053/056; AC-018/019. **Fields:** scholarship ID/round/state/notes for loaded owned records; referenced public title where accessible. **Validation:** application origin not official; no counts over unloaded pages. **CTA / hint:** Open record, prepare saved opportunity; fill success is not submission.
- **API:** `GET /applications`; `POST /applications`; `GET /scholarships/{scholarship_id}`. **E/L/X/O/D:** E browse/save; L list; X inaccessible source still show owned record safely; O no state changes; D missing current round/version stops creation; no drag-to-Submitted.
- **Wireframe M / L:** M list grouped by labelled state; L optional columns with keyboard move action using allowed transition controls, list always available. **Bidi:** state progression follows logical reading order, round keys isolated; no probability meter.

### R23 — `/applications/{id}` — checklist and confirmed submission

- **Purpose / trace:** S; SCR-012; FR-044/045/048/052–058; AC-016/018/019. **Fields:** requirement state/verification, exact approved document version OR accepted upload, notes ≤20000, history origin/time, allowed status, explicit external-submission checkbox. **Validation:** exclusive artifact choice/owner/version, unknown checklist not Ready, pinned submission immutable; unlisted transitions and official feed disabled G-STATUS.
- **API:** `GET /applications/{application_id}`; `GET /applications/{application_id}/requirements`; `GET /applications/{application_id}/history`; `PUT /applications/{application_id}/notes`; `PUT /applications/{application_id}/requirements/{requirement_key}/artifact`; `PUT /applications/{application_id}/requirements/{requirement_key}/completion`; `POST /applications/{application_id}/transitions`. **CTA / hint:** Save notes/attach, mark Ready, open official portal, separately “I submitted on the official site”. **E/L/X/O/D:** E requirements unknown → explain; L checklist/history independently; X concurrent state/version refresh; O confirm off, unknown response recover same key; D submitted replacement/terminal rollback forbidden, preserve history.
- **Wireframe M / L:** M state/round → checklist → notes → external-action explanation → history; L checklist beside action/history panel. **Bidi:** source labels Student-reported/Official remain explicit; version/instant isolated.

### R24 — `/notifications` — inbox and optional preferences

- **Purpose / trace:** S; SCR-020; FR-089–093; AC-029/030. **Fields:** category, event version, timestamp, read state, typed destination; optional category enabled decision. **Validation:** known category/destination mapping only; mandatory security cannot be disabled; no remote product channels. **CTA / hint:** Open destination, mark read, set known optional category preference.
- **API:** `GET /notifications`; `POST /notifications/{notification_id}/read`; `PUT /notification-preferences/{category}`. **E/L/X/O/D:** E no notices; L list; X unavailable destination → return safely, keep notice; O no mark read or settings write; D missing body/current preferences UX-API-09, unknown destination not clickable. Do not claim a change was read before acknowledgment.
- **Wireframe M / L:** M chronological category cards → preferences section; L inbox + preferences panel. **Bidi:** category and time start at logical start; mixed destination names auto.

### R25 — `/support` — own ticket inbox and new ticket

- **Purpose / trace:** S; SCR-021; FR-094–097; AC-031/032. **Fields:** category, subject, message, request_human; own list ID/state/category/priority. **Validation:** configured category, bounded subject/message per wire; warn not to paste portal secrets; AI is optional and requires separate approved consent. **CTA / hint:** Create ticket / Request a human; free human path remains available.
- **API:** `GET /tickets`; `POST /tickets`. **E/L/X/O/D:** E no tickets → new ticket; L own list; X create outcome unknown recover same key; O submit off/current-memory draft only; D AI off UX-API-03/G-PROVIDER, subject preview unavailable UX-API-06. Never promise 24/7 human staffing.
- **Wireframe M / L:** M new-ticket button → existing list → creation form; L list and bounded form. **Bidi:** subject/message auto; labels and support-hours disclosures follow locale.

### R26 — `/support/{id}` — own conversation and sharing

- **Purpose / trace:** S; SCR-022; FR-094–103/110; AC-031–034/036. **Fields:** own messages with AI/human labels, state/history/SLA, message/request_human, explicit selected accepted-file share, revoke established share, resolution/reopen. **Validation:** owner ticket/asset, independent attachment AI processing consent, allowed transitions, rating only with approved policy. No library-wide share checkbox.
- **API:** `GET /tickets/{ticket_id}`; `GET /tickets/{ticket_id}/messages`; `GET /tickets/{ticket_id}/history`; `GET /tickets/{ticket_id}/sla`; `POST /tickets/{ticket_id}/messages`; `POST /tickets/{ticket_id}/transitions`; `POST /tickets/{ticket_id}/attachments`; `DELETE /tickets/{ticket_id}/attachments/{attachment_id}`. **CTA / hint:** Send, request human, explicitly share selected file, resolve/request reopen. **E/L/X/O/D:** E no messages; L history/SLA; X share or expired reopen explains actual refusal; O sends off/no duplicate replay; D AI/rating/attachment inventory limitations UX-API-03/06; no invented first-response due when null.
- **Wireframe M / L:** M state/due label → thread → composer → selected shares; L thread plus status/share panel. **Bidi:** each message auto direction, chronology stays top-to-bottom; distinguish author labels in text.

### R27 — `/consents` — scoped processing decisions

- **Purpose / trace:** S; SCR-006/023; FR-012/113–115; AC-004/005. **Fields:** available disclosure ID/version/purpose/full text, granted/revoked record/time. **Validation:** explicit independent grant, no prechecked box, current disclosure/ETag; approved text must identify data/purpose/processor scope/retention/withdrawal consequences, absent details disable grant. No model-training opt-in UI absent separate approved workflow.
- **API:** `GET /consents`; `GET /consents/disclosures`; `POST /consents`. **CTA / hint:** Allow this purpose, decline/continue manually, withdraw. **E/L/X/O/D:** E no approved disclosures → manual only; L loading text; X changed version requires reread; O decisions off; D processor unavailable blocks AI even after grant; withdrawal cannot recall data already sent.
- **Wireframe M / L:** M purpose cards → plain disclosure → distinct decision actions; L bounded reading panel beside current status. **Bidi:** Arabic/English full text without truncation; processor names isolated, no implied provider approval from a name.

### R28 — `/account` — identity and privacy controls

- **Purpose / trace:** S; SCR-023; FR-003/006/113/116–121. **Fields:** safe session verification/adult flags, consent links, locale, deletion entry. **Validation:** no email/DOB edit endpoint assumed, locale navigation only; protected data owner only. **CTA / hint:** Sign out, manage consent, review deletion; linking unavailable UX-API-08.
- **API:** `GET /session`; `POST /session/logout`. **E/L/X/O/D:** E expired session → sign in; L session load; X logout failure clear visible private content and explain session may remain until verified revocation; O sign-out pending server confirmation, no offline persistence; D Google linking/unprovided identity edits unavailable.
- **Wireframe M / L:** M account/security → consent → deletion separated with impact link; L settings navigation + panel. **Bidi:** identifiers LTR, destructive action placement follows logical order, never hidden offscreen.

### R29 — `/account/deletion` — informed deletion confirmation

- **Purpose / trace:** S + recent proof; SCR-023; FR-116–120; AC-037–039 modified by UD-001. **Fields:** approved impact, legal/backup exceptions, captured days/zone/cutoff when authoritative, confirm_impact, recent proof. **Validation:** current approved policy/legal envelope and trustworthy preflight required; UX-API-07 currently disables confirmation. Never hard-code 30 or 720h in operative promise.
- **API:** `POST /account/deletions`. **CTA / hint:** Review impact; conditional Confirm deletion; cancel returns to account. **E/L/X/O/D:** E impact unavailable → explain; L preflight unavailable shell, not fake fetch; X no false success/confirmed cutoff if response lost; O no confirmation; D missing informed-impact/proof workflow → unavailable with manual privacy-help instructions, no automatic ticket attachment.
- **Wireframe M / L:** M consequences → actual deadline and exceptions → explicit confirmation → destructive CTA; L readable single column. **Bidi:** deadline includes zone and full date/time in both languages; confirmation checkbox order logical.

### R30 — `/account/restore` — purpose-bound account recovery

- **Purpose / trace:** G request/recovery proof; SCR-003/023; FR-118–120; AC-038/039, UD-001. **Fields:** email request then single-use challenge; no standard private account reads. **Validation:** proof bound to exact deletion; server receipt strictly before stored restore_until; equality/purging denies; restoration no new grant.
- **API:** `POST /account/recovery-requests`; `POST /account/restorations`. **CTA / hint:** Request recovery, restore then sign in; actual cutoff only from authoritative disclosure already obtained, no client recomputation. **E/L/X/O/D:** E generic request form; L verifying; X expired/no longer recoverable safe explanation; O no restore and client click time is not receipt; D pending status/details unavailable UX-API-07, no private disabled-account dashboard.
- **Wireframe M / L:** M/laptop narrow instructions/proof status/next action. **Bidi:** email LTR; zoned deadline if legitimately available, no ambiguous relative-only timer.

### R31 — `/extension/connect` — approve pairing

- **Purpose / trace:** S + recent ownership proof; SCR-024; FR-059/060; AC-020/021. **Fields:** approved extension ID/origin, portal ID, optional owned selected application, S256 challenge, bounded scopes. **Validation:** exact allowed origin/portal/resource; one-use code/short expiry; UX-API-07/10 and G-EXT must be resolved before activation.
- **API:** `POST /extension/pairings`. **CTA / hint:** Approve this connection; cancel; no passwords/files/wallet/status writes granted. **E/L/X/O/D:** E no valid pairing request → extension instructions; L approval; X expired/mismatched request restart; O approve off; D mobile/unknown extension or portal → web/manual fallback.
- **Wireframe M / L:** M informational fallback; L permissions review then approve/cancel. **Bidi:** exact extension/site identifiers isolated LTR, translated scope labels; code not displayed or logged.

### R32 — `extension:popup/review` — Chrome field review

- **Purpose / trace:** scoped extension owner; SCR-024; FR-059–068; AC-018/020–022. **Fields:** permitted site status, selected confirmed field/value, separate sensitive selection, missing/failed/inserted counts. **Validation:** current portal/application bound to pairing, sender/tab/origin validation, no password/OTP/CAPTCHA enumeration, no submission command. Unknown values remain blank; no value telemetry.
- **API:** `POST /extension/token`; `GET /extension/confirmed-data`. **CTA / hint:** Review → Fill selected → review externally; manual copy only for permitted known nonsensitive values. **E/L/X/O/D:** E no supported fields → manual instructions; L recognized field analysis without protected-field reads; X partial result lists failures, bounded safe retry only; O no data fetch/fill replay; D denied portal/token expiry/mobile/UX-API-10 → no fill. Tested versus permitted best effort labelled distinctly.
- **Wireframe M / L:** M unsupported-browser web explanation; L popup site/session → scrollable labelled field review → sensitive confirmation → selected fill → results, wider on-page panel only with permission. **Bidi:** popup UI mirrors, each value auto; external portal direction unchanged. No Submit button.

## Admin and support-agent routes

### R33 — `/admin` — aggregate overview

- **Purpose / trace:** A aggregate_metrics scope; SCR-025; FR-105/108/112. **Fields:** metric/count/window start/end only; no private text, individual drilldown or invented cost dollars. **Validation:** approved aggregate projection; no default 0 on missing metrics. **CTA / hint:** Open authorized queue; counts are measured window values only.
- **API:** `GET /admin/metrics`. **E/L/X/O/D:** E no measurements; L panels; X scope/gate safe denial; O stale aggregates; D unmeasured/G-MEASURE unavailable labelled, no made-up p95/SLA success.
- **Wireframe M / L:** M period text → cards → scoped destinations; L grid/tables with textual equivalents. **Bidi:** metric labels localized, numeric values/instants isolated.

### R34 — `/admin/sources` — source registry shell

- **Purpose / trace:** A moderation; SCR-026; FR-015/016/020. **Fields:** canonical domain, source type, permission evidence ref; proposed history/registry unavailable UX-API-02. **Validation:** permitted method/evidence independently verified; no arbitrary scrape URL. **CTA / hint:** source registration unavailable until evidence can be reviewed; no command from unverified pasted evidence ID.
- **API:** `POST /admin/sources`. **E/L/X/O/D:** E no readable registry → unavailable, not empty registry; L no invented registry fetch; X registration command failure preserves input if later enabled; O no submit; D registry/edit/ingest controls off pending read/evidence contracts and G-SOURCE.
- **Wireframe M / L:** M unavailable reason then field preview; L registry placeholder beside disabled registration form. **Bidi:** domain/evidence IDs LTR; reasons localized.

### R35 — `/admin/scholarships` — moderation queue and review

- **Purpose / trace:** A moderation; SCR-027; FR-016–020/111; AC-006/007/035. **Fields:** current readable candidate ID/state/version; intended title/provider/source/funding/criteria/requirements/evidence/diff, reason and exact selected version require missing review projection. **Validation:** source approval, duplicate review and content evidence before decision; no automatic merge/publish.
- **API:** `GET /admin/scholarships`; `POST /admin/scholarships`; `POST /admin/scholarships/{scholarship_id}/versions`; `POST /admin/scholarships/{scholarship_id}/moderation`; `POST /admin/scholarships/{scholarship_id}/publish`. **CTA / hint:** View metadata; approve/reject/suspend/restore/publish disabled UX-API-02 until informed review is possible. **E/L/X/O/D:** E no loaded candidates; L queue; X conflict reload; O no decisions; D missing facts/diff/evidence/G-SOURCE explicitly blocks decisions even for scoped Admin.
- **Wireframe M / L:** M queue → selected review with before/after stacked → reasons → actions; L queue + paired review/evidence panel. **Bidi:** source facts auto; before/after explicitly named, no color-only diff.

### R36 — `/admin/reports` — student source reports

- **Purpose / trace:** A moderation; SCR-028; FR-024/109/111; AC-008/035. **Fields:** case ID/state/version available; actual report evidence and decision context unavailable UX-API-02. **Validation:** cannot decide from case ID alone or open reporter library. **CTA / hint:** Metadata refresh; accept/reject/correct/suspend controls disabled pending evidence projection.
- **API:** `GET /admin/scholarship-reports`; `POST /admin/scholarship-reports/{report_id}/decisions`. **E/L/X/O/D:** E no loaded reports; L list; X safe scope errors; O no decision; D evidence absent → review unavailable, no auto-dismissal/removal.
- **Wireframe M / L:** M cases → selected evidence placeholder → decision rationale; L queue + case pane. **Bidi:** report evidence auto when authorized; opaque IDs LTR.

### R37 — `/admin/matching` — versioned matching policy

- **Purpose / trace:** A matching_policy; SCR-029; FR-031/107; AC-009/035. **Fields:** five weights academic/field/nationality-residency/language/interests, minimum coverage, effective_at, reason; current version. **Validation:** nonnegative integer basis points sum 10000; known policy, ETag; hard mandatory rules unchangeable by score weights; no uncontracted rule editor.
- **API:** `GET /admin/policies/{policy_kind}/current`; `POST /admin/policies/eligibility`. **CTA / hint:** Review and publish policy; D 30/25/20/15/10 and 70% are proposed defaults, not measured quality. **E/L/X/O/D:** E no current policy → setup unavailable; L snapshot; X sum/version errors; O publish off; D G-PROFILE/missing approval denies relevant changes.
- **Wireframe M / L:** M current version → weight inputs → coverage → prospective change summary/reason; L current/proposed comparison. **Bidi:** percent input LTR with localized labels, no mirrored math.

### R38 — `/admin/users` — limited account administration

- **Purpose / trace:** A identity for list; security/approver scopes for actions; SCR-030; FR-006/106/109/110; AC-003/036. **Fields:** id/formal role/state/verified/adult/MFA flags; scoped session revocation reason or principal/scope/evidence for independently authorized grant. **Validation:** no document/profile listing, no invented email search parameter; no scope widening from client role text. Scope grant off absent verifiable approval evidence.
- **API:** `GET /admin/users`; `POST /admin/users/{user_id}/session-revocations`; `POST /admin/scope-grants`. **CTA / hint:** Revoke sessions with reason where authorized; private library always prohibited. **E/L/X/O/D:** E no metadata; L page; X scope/MFA denial; O no actions; D library/profile impersonation and unsupported account edits unavailable, direct private-library attempts 403+audit.
- **Wireframe M / L:** M metadata cards + specific actions; L scrollable limited table. **Bidi:** role/status text localized; user IDs LTR, no sensitive details in accessible labels.

### R39 — `/admin/credits/policies` — grant, limits and prices

- **Purpose / trace:** A cost_policy; SCR-031; FR-005/069/070/073; AC-002/023/035. **Fields:** one-time grant, daily student spend/global AI/support message caps, per-service integer Credit price/chargeable, effective_at/reason, current policy. **Validation:** strict kinds/nonnegative integers; funded service >0, free support 0; prospective edits, no bucket reset or regrant; ETag/current policy required.
- **API:** `GET /admin/policies/{policy_kind}/current`; `POST /admin/policies/limits`; `POST /admin/policies/prices`. **CTA / hint:** Review/publish limits or prices separately; daily spend is not daily grant. **E/L/X/O/D:** E no current policy → setup reason; L snapshot; X validation/conflict; O publish off; D package editor/payment flags absent and Beta off; cannot approve processors by toggling settings.
- **Wireframe M / L:** M limits → service prices → effects/reason; L current/proposed table with overflow. **Bidi:** Credit amounts LTR, “Credits” unit and policy timezone explanation adjacent.

### R40 — `/admin/credits/reconciliation` — finance case shell

- **Purpose / trace:** A finance; independent finance_approver decision; SCR-033; FR-074–079/109; AC-024/035. **Fields:** intended case, exact entry/amount/evidence/reason and independent decision; reads unavailable UX-API-05. **Validation:** no direct balance update or guessed refund; no same-role bypass of required workflow. **CTA / hint:** financial actions unavailable until scoped case evidence can be reviewed.
- **API:** `POST /admin/users/{user_id}/credit-adjustments`; `POST /admin/users/{user_id}/credit-adjustments/{adjustment_id}/decisions`. **E/L/X/O/D:** E unavailable evidence, not “all reconciled”; L no fake case fetch; X safe conflict if future action enabled; O no writes; D all case/adjustment decisions off, never use Student wallet as Admin.
- **Wireframe M / L:** M disabled case outline + reason; L intended case/ledger/evidence comparison, no actual private data. **Bidi:** signed Credit values/IDs LTR; reason field auto.

### R41 — `/admin/support` — scoped support queue

- **Purpose / trace:** A support_queue; separate support_assignment scope to assign. SCR-034; FR-096/103/104; AC-032/033. **Fields:** loaded ticket IDs/state/category/priority only; assignment target agent ID/reason. **Validation:** do not infer subject, ownership, SLA due or attachment access from TicketPage; assignment requires trusted eligible-agent source, absent directory disables picker. UX-API-06.
- **API:** `GET /admin/tickets`; `POST /admin/tickets/{ticket_id}/assignments`. **CTA / hint:** Open assigned conversation; assignment request only where independently validated. **E/L/X/O/D:** E no visible tickets; L queue; X scope/reassignment conflicts; O no assignment; D unassigned thread/attachments denied, no queue-only access escalation.
- **Wireframe M / L:** M priority/category cards → assigned detail; L semantic queue table; richer due markers unavailable until authorized projection. **Bidi:** priority labels text+icon, ticket IDs isolated; no mirrored urgency scale.

### R42 — `/admin/support/{id}` — assigned agent conversation

- **Purpose / trace:** T current assignment; SCR-034; FR-094/096/099/102/104/110; AC-032/033/036. **Fields:** assigned messages, SLA due/calendar target, message/body, category/priority/reason, allowed transition; exact explicit ticket file if authorized reference exists. **Validation:** reassignment revokes future thread/file reads; read audit; no private library/list lookup; attachment listing/history limitations UX-API-06.
- **API:** `GET /admin/tickets/{ticket_id}/messages`; `GET /admin/tickets/{ticket_id}/sla`; `POST /admin/tickets/{ticket_id}/messages`; `PUT /admin/tickets/{ticket_id}/classification`; `POST /admin/tickets/{ticket_id}/transitions`; `POST /files/{file_id}/download-capabilities`. **CTA / hint:** Send human response, reclassify with reason, resolve; download only exact ticket_context share. **E/L/X/O/D:** E no visible messages; L assigned thread; X assignment changed → clear content and return queue; O no sends or stored transcript; D no share/assignment/audit → no bytes; no AI finance/account commands.
- **Wireframe M / L:** M due/status → thread → reply → selected-share section; L thread + minimal SLA/classification/attachment panel. **Bidi:** author/body auto; due zone explicit, file type/name isolated safely.

### R43 — `/admin/support/policy` — human calendar and SLA

- **Purpose / trace:** A support_policy; SCR-035; FR-100–103; AC-033/034. **Fields:** zone, weekdays, local opening/closing, holidays, four priority business-minute targets, warning lead values, effective_at/reason; current policy. **Validation:** valid IANA zone and opens<closes, target/warning bounds and configured escalation route; no invented route field. Closure/rating/escalation-route editors missing UX-API-06 remain disabled.
- **API:** `GET /admin/policies/{policy_kind}/current`; `POST /admin/policies/sla`. **CTA / hint:** Review/publish approved calendar/targets; existing cycle retains snapshot, no promised staffing. **E/L/X/O/D:** E no policy; L current schedule; X local time/ETag error; O publish off; D absent warning routing/config G-TICKET disables related automation, never silently choose thresholds.
- **Wireframe M / L:** M timezone → days/hours → holidays → per-priority targets → change summary; L week/targets alongside accessible text schedule. **Bidi:** weekday names localized, local time controls LTR, no calendar grid keyboard trap.

### R44 — `/admin/audit` — limited audit/system metadata

- **Purpose / trace:** A security_audit; SCR-036; FR-109/112/122/123; AC-035/040. **Fields:** available CommandPage ID/state/version/correlation; aggregate failure metrics only through R33. **Validation:** no raw prompt, document body, secret or arbitrary job inspector. **CTA / hint:** Refresh metadata; detailed audit not available UX-API-02.
- **API:** `GET /admin/audit`. **E/L/X/O/D:** E no loaded metadata not “no incidents”; L page; X denied/retry; O stale label; D before/after actor/reason detailed evidence and retry buttons unavailable until read/command contracts exist.
- **Wireframe M / L:** M metadata list with explanatory limitation; L scrollable metadata table. **Bidi:** correlation IDs LTR, state labels localized.

### R45 — `/admin/privacy/recovery-policy` — configurable recovery

- **Purpose / trace:** A retention; SCR-030/036; FR-117–120; AC-037–039 modified by UD-001. **Fields:** positive recovery_days, recovery_timezone, cutoff_algorithm, legal_envelope_ref, effective_at/reason; current version. **Validation:** approved legal envelope, exact ADR0008 calendar algorithm, ETag; no edit to existing deletion request or deadline. No inferred permanent 720h period.
- **API:** `GET /admin/retention-policies/current`; `POST /admin/retention-policies`. **CTA / hint:** Review/publish for future confirmations only. **E/L/X/O/D:** E no approved policy; L current version; X envelope/version errors; O publish off; D G-LEGAL/unreviewable legal evidence disables publish. Examples marked proposed/synthetic.
- **Wireframe M / L:** M current/default explanation → proposed days/zone → prospective impact/reason → confirm; L before/proposed comparison with immutable-cutoff warning. **Bidi:** days as integers; IANA zone/algorithm IDs LTR with plain translated explanation.

## Deferred paid surfaces and policy content

### R46 — `/credits/packages` — Beta purchase unavailable

- **Purpose / trace:** S; SCR-018; FR-080/081/088; AC-026–028 retained for Advanced MVP. **Fields / Validation:** none collected; no package, currency, account, proof or transfer reference invented. **API:** none (Beta disabled). **CTA / hint:** Back to Credits or human support; payments unavailable during Public Free Beta.
- **E/L/X/O/D:** E no packages is intentional; L no payment fetch; X wallet navigation failure safe retry; O static notice readable; D purchase always off, G-PAID cannot be enabled by UI. **Wireframe M / L:** M/laptop concise unavailable panel with reason/return. **Bidi:** fully localized notice, Credit unit consistent.

### R47 — `/payments/{id}` — deferred payment status

- **Purpose / trace:** S future owner; SCR-019; FR-081–088; AC-026–028. **Fields / Validation:** no lookup/data accepted in Beta; ID conveys no order existence. **API:** none (Beta disabled). **CTA / hint:** Return to wallet; no proof upload or cash-refund promise.
- **E/L/X/O/D:** E no accessible Beta order; L no request; X malformed ID safe unavailable; O notice only; D all payment state/actions unavailable, no fake Pending/Approved. **Wireframe M / L:** M/laptop reason and return, future state design deferred. **Bidi:** route ID not echoed as private order metadata.

### R48 — `/admin/payments` — deferred payment review

- **Purpose / trace:** A future finance; SCR-032; FR-080–088/106/109; AC-026–028/035. **Fields / Validation:** no receipt/transfer/account/approval fields active. Future verified funds/unique reference/one grant contract required separately. **API:** none (Beta disabled). **CTA / hint:** Return to authorized Admin overview.
- **E/L/X/O/D:** E no enabled queue; L no request; X permission denial safe; O notice only; D review/approval/refund controls off, no granting Credits from images. **Wireframe M / L:** M/laptop gated panel. **Bidi:** localized reason; no invented currency/local provider.

### R49 — `/policies/{document}` — terms, privacy and AI disclosure

- **Purpose / trace:** G; SCR-001/023; FR-113/115/120/121; NFR-026. **Fields:** approved static document selector `terms|privacy|ai`, language/version/effective date/contact only when supplied. **Validation:** approved jurisdiction-specific content; unsupported key safe 404; absence never replaced by generated legal policy. **API:** none (approved static content required); authenticated processing decisions stay R27.
- **CTA / hint:** Read linked policy, return; UI explanation is not legal approval. **E/L/X/O/D:** E policy not approved/available → explicit notice and real-user release gate; L static-content load only if present; X unavailable localized version; O already-rendered approved text with version label; D registration/processing blocked where required policy absent.
- **Wireframe M / L:** M document title/version → readable full text → related policies; L contents links + bounded reading column. **Bidi:** document-specific direction and semantic heading order; external references isolated.

## Source screen and acceptance mapping

Every source screen is accounted for; route names need not copy PRD logical screens. Source AC mappings refer to future observable behavior; a disabled shell is explicitly not completion of its feature AC.

| Source screens | Inventory / journey | Requirements and acceptance |
|---|---|---|
| SCR-001 | R01/R49; J01/J10 | FR-121; NFR-013–016/026 |
| SCR-002, SCR-003 | R05–R10/R30; J02 | FR-001–007; AC-001–003 |
| SCR-004, SCR-005, SCR-006 | R11–R13/R27; J03 | FR-008–014; AC-004/005 |
| SCR-007, SCR-008 | R02–R04; J01/J08 | FR-015–027; AC-006–008/012 |
| SCR-009, SCR-010 | R14/R15; J04 | FR-028–033/051; AC-009–011 |
| SCR-011, SCR-012 | R22/R23; J06 | FR-044/045/048/051–058; AC-018/019 |
| SCR-013, SCR-014 | R17/R18/R20; J05 | FR-034–042/122–125; AC-013–015/040/041 |
| SCR-015, SCR-016 | R19–R21; J06 | FR-043–050; AC-016/017 |
| SCR-017 | R16/R18; J05/J09 | FR-069–079; AC-023–025 |
| SCR-018, SCR-019, SCR-032 | R46–R48; J12 | FR-080–088; AC-026–028 DEFERRED Beta |
| SCR-020 | R24; J01/J06 | FR-089–093; AC-029/030 |
| SCR-021, SCR-022 | R25/R26; J07 | FR-094–105; AC-031–034 |
| SCR-023 | R27–R30/R45/R49; J10 | FR-113–121; AC-037–039 + UD-001 |
| SCR-024 | R31/R32; J11 | FR-059–068; AC-018/020–022 |
| SCR-025, SCR-026, SCR-027, SCR-028 | R33–R36; J08 | FR-015–024/106/108–112; AC-006–008/035/036 |
| SCR-029, SCR-030, SCR-031 | R37–R39/R45; J09 | FR-031/070/106/107/110; AC-003/023/035/036 |
| SCR-033 | R40; J09 | FR-074–079; AC-024/035 |
| SCR-034, SCR-035 | R41–R43; J07/J09 | FR-094–105; AC-031–034 |
| SCR-036 | R18/R33/R44/R45; J09 | FR-109/112/120/122–125; AC-035/040/041 |

## Route-gate acceptance review

| ID | Fixture / required observation | Mapping |
|---|---|---|
| UX-01 | Guest opens every protected deep link: no private first paint, no personal filter request; verified adult resumes safely after login | R04–R45 as applicable; AC-001–003/036; CASE-NFR-003 |
| UX-02 | For each R01–R49 exercise E/L/X/O/D and both locales; affected missing contracts show exact reason plus safe alternative | All routes; CASE-NFR-013–016/019/020; FR-125 |
| UX-03 | Admin gets library 403+audit; unassigned/removed agent cannot read thread/share; selected current share yields only exact bytes | R19/R26/R38/R41/R42; AC-036; D §أ 6 |
| UX-04 | Browser loses network after charged POST; resume same operation; RESERVED/RUNNING/RECONCILING never called final debit; SETTLED opens saved result, RELEASED no final charge | R16–R18; AC-023/024/040/041 |
| UX-05 | Missing review/evidence/typed result/impact/round projection leaves affected CTA disabled, with no undocumented or broadened API request | UX-API-01–13; phase gate; AC-004/006/011/035–039 remain conditional |
| UX-06 | Policy edit leaves prior quote and captured deletion deadline unchanged; restored version needs new approval; extension fill never sets Submitted | R18/R21/R23/R32/R39/R45; AC-016–019/023/037–039 + UD-001 |

These are planned interaction checks. Static route/API/source/state completeness is checked in Phase 04; browser, assistive-technology, real permission and bilingual UAT execution remain NOT RUN, as recorded in [report](../../tasks/phase-reports/04.md).
