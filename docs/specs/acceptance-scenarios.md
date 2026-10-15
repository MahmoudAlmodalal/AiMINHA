# Requirement acceptance scenarios — planned, not executed

2026-10-15. **Documentation PASS; runtime cases NOT RUN.** These named Given/When/Then paths cover every supplied requirement. They are test designs, not a test suite or evidence of a running product. Use synthetic fixtures and actual non-owner database roles in later implementation. Gate absence must exercise fail-closed/manual paths. Original source scenarios below are retained verbatim; additional CASE IDs are engineering acceptance refinements, not invented PRD IDs.

## Original PRD acceptance criteria

| AC ID | Feature | Given | When | Then |
|---|---|---|---|---|
| AC-001 | F-01 | A new user declares a DOB indicating age < 18 | They attempt registration by email or Google | No active student account or signup Credits are created; a clear rejection is shown. |
| AC-002 | F-01 | An eligible new user activates a verified account | Signup verification completes, and later Google is safely linked | Initial Credits are granted exactly once across both auth paths. |
| AC-003 | F-01 | An Admin account lacks completed MFA | It requests a protected Admin function | Server denies the request and records a security-relevant event. |
| AC-004 | F-02 | Student uploads a readable CV after consenting | Extraction completes | Proposed facts are displayed for approval; no extracted fact is trusted before student confirmation. |
| AC-005 | F-02 | Student declines AI processing or uploads unreadable file | They continue their profile | Manual completion remains possible and missing inputs stay marked unknown. |
| AC-006 | F-03 | Source job discovers a scholarship | No Admin decision has been recorded | Student search does not expose the listing. |
| AC-007 | F-03 | An approved scholarship's official deadline changes materially | Monitor detects the change | Publication requires Admin review and source/time/difference is recorded. |
| AC-008 | F-03 | Student reports incorrect scholarship information | Admin accepts, rejects or suspends after review | Report decision, evidence and publication effect are attributable; report alone cannot silently delete listing. |
| AC-009 | F-04 | Student fails a confirmed mandatory nationality/degree condition | Match engine evaluates a high-fit profile | Eligibility is **Ineligible** irrespective of Match Score, with the blocking reason. |
| AC-010 | F-04 | Student lacks required language/GPA evidence | Eligibility is evaluated | Relevant criterion is **Undetermined**, missing input is disclosed, and no “Eligible” claim is inferred. |
| AC-011 | F-04 | A matching evaluation completes | Student inspects it | Score contributions, confidence/limitations, evaluation version and no-admission-guarantee statement are visible. |
| AC-012 | F-04 | Approved catalog contains matching and nonmatching scholarship records | Student searches and applies level/funding/deadline filters | Only appropriate results are returned, with source freshness and predictable sort; clear empty state if none. |
| AC-013 | F-05 | Student profile contains no verified employment or award | They generate a CV/letter | The draft does not assert invented employment, GPA or awards; unverified assertions are flagged or omitted. |
| AC-014 | F-05 | Student generates and edits a Motivation Letter | They preview and export in PDF and DOCX | Both documents open successfully and contain the manually edited approved text. |
| AC-015 | F-05 | Interface is Arabic and document output is selected as English | Student requests one of four agreed document types | Draft uses selected document language, while UI remains Arabic; credit quote appears before any paid run. |
| AC-016 | F-06 | Application is manually marked Submitted with a linked document version | Student tries editing that exact version | Normal edit is refused, while editing a new version remains available. |
| AC-017 | F-06 | Document has versions 1–3 | Student restores version 1 | Version 4 becomes current, versions 1–3 remain retrievable subject to lawful deletion, and submitted snapshots remain unchanged. |
| AC-018 | F-07 | Extension fills a portal form | Student has not submitted externally or confirmed in MinhaAI | Tracker is not marked **Submitted**. |
| AC-019 | F-07 | Student submits a portal application and confirms within MinhaAI | They choose **Submitted** | Timestamped student-reported state and exact linked document versions are saved; no false official-status claim. |
| AC-020 | F-08 | A permitted form has normal and sensitive mapped fields | Student launches extension and refuses consent for sensitive values | Extension does not insert refused values, leaves missing fields visible and allows student review. |
| AC-021 | F-08 | Form is unsupported or includes CAPTCHA/OTP/password | Student requests autofill | Extension does not bypass/intercept protected fields, shows limitation and offers manual entry. |
| AC-022 | F-08 | Extension inserts all recognized values successfully | Student reviews fields | External form is **not** auto-submitted; the student remains responsible for pressing submit. |
| AC-023 | F-09 | Student confirms a paid AI operation quoted at N Credits | Admin changes price before job completion | One successful settlement costs **N**, not the new price; retries do not duplicate it. |
| AC-024 | F-09 | A paid AI job reserves N Credits and fails technically | Worker processes failure and duplicate callback | Reserved Credits are released/refunded exactly once; no final incorrect debit remains. |
| AC-025 | F-09 | An account has non-expiring Credits | Time passes without spending or account deletion | Balance is not reduced solely due to age of Credits; history remains reconcilable. |
| AC-026 | F-10 | Student uploads payment proof, but bank/receiver confirmation is missing | Admin reviews the request | No Credits are added from the uploaded image alone. |
| AC-027 | F-10 | One transfer reference has already funded an approved order | Another request attempts to use the same reference | Duplicate approval is blocked/held and no additional Credit grant occurs. |
| AC-028 | F-10 | Admin rejects a request or requests new proof | Student views the payment request | Accurate state/reason is displayed and no unauthorized Credits are issued. |
| AC-029 | F-11 | A student is affected by an approved material source change | Notification event is generated | A context-linked in-app notice appears; no product email/WhatsApp/Web Push is required. |
| AC-030 | F-11 | Two identical delivery attempts occur for one notice event | Notification worker retries | Student does not receive duplicate equivalent notices and read/unread state remains correct. |
| AC-031 | F-12 | Support AI receives a request to approve a transfer or add Credits | Student submits the request | AI performs no financial change and routes/escalates to authorized Admin review. |
| AC-032 | F-12 | Student requests a human or AI confidence is low | AI handoff triggers | Ticket enters correct Admin queue with minimal necessary context and preserved history. |
| AC-033 | F-12 | Human support calendar has nonworking intervals and priority target configured | Ticket awaits first human response across one such interval | Computed SLA excludes configured nonworking time and warns/escalates at the configured threshold. |
| AC-034 | F-12 | Ticket is resolved | Student reopens within permitted policy or ticket reaches closure interval | Status/history/rating options follow the Admin-configured rule and every transition is logged. |
| AC-035 | F-13 | Admin changes a scholarship rule, Credit price or payment adjustment | Action is committed | Audit records authenticated actor, timestamp, reason/relevant before-after data and applicable version. |
| AC-036 | F-13 | An Admin uses standard user management or analytics access | They request arbitrary student's private CV file | Data/file access is denied unless a separately approved exceptional path exists. |
| AC-037 | F-14 | Student requests deletion and confirms disclosed impact | System processes the request | Access is disabled and Credits frozen for **30 calendar days**, without irreversible immediate removal in the recovery interval. |
| AC-038 | F-14 | Student proves ownership and restores account before deadline | Recovery succeeds | Account and retained data become available and wallet frozen Credits are restored. |
| AC-039 | F-14 | 30-day recovery period ends without restoration | Final deletion runs | Files/versions and in-scope linked data are deleted, remaining Credits canceled, and documented legal exceptions retained only as authorized. |
| AC-040 | F-15 | AI/file job exceeds an ordinary request duration | Student returns to job status screen | Authentic queued/running/completed/failed state is available; app does not invent a success. |
| AC-041 | F-15 | A successful job callback is replayed after a worker crash | Background worker retries | No duplicate published content, Credit debit or other irreversible effect is created. |

## Per-FR acceptance paths

### CASE-FR-001

Given An isolated synthetic fixture for F-01, with public signup / own account; admin mfa, the stated release mode and explicit enabled/disabled G-PROFILE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Register an eligible adult using email/password.

Then: The platform SHALL support student registration and authentication with email/password.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-001–AC-003; FR-001.

### CASE-FR-002

Given An isolated synthetic fixture for F-01, with public signup / own account; admin mfa, the stated release mode and explicit enabled/disabled G-PROFILE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Consume a valid verification challenge, then replay/expire it.

Then: The platform SHALL verify account email ownership through a secure, expiring verification process before the account receives the signup Credit grant.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-001–AC-003; FR-002.

### CASE-FR-003

Given An isolated synthetic fixture for F-01, with public signup / own account; admin mfa, the stated release mode and explicit enabled/disabled G-PROFILE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Attempt Google account linking using only an email collision, then valid identity proof.

Then: The platform SHALL support Google OAuth and SHALL require adequate identity proof before linking to an existing account; mere identical email text is insufficient to merge accounts.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-001–AC-003; FR-003.

### CASE-FR-004

Given An isolated synthetic fixture for F-01, with public signup / own account; admin mfa, the stated release mode and explicit enabled/disabled G-PROFILE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Register below/at the age boundary on both authentication paths.

Then: Every new account registration path SHALL collect a date of birth, calculate age at registration and prevent activation if the declared age is below 18.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-001–AC-003; FR-004.

### CASE-FR-005

Given An isolated synthetic fixture for F-01, with public signup / own account; admin mfa, the stated release mode and explicit enabled/disabled G-PROFILE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Race activation and linked-auth callbacks for the same canonical account.

Then: A successfully activated, eligible student account SHALL receive the configured free Credit grant once, without duplication through retry or account-linking.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-001–AC-003; FR-005.

### CASE-FR-006

Given An isolated synthetic fixture for F-01, with public signup / own account; admin mfa, the stated release mode and explicit enabled/disabled G-PROFILE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Log out/reset credentials and retry operations from a revoked/deletion-pending session.

Then: Students SHALL be able to sign out and initiate secure password/account recovery, and inactive/deletion-pending accounts SHALL be unable to use authenticated product operations.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-001–AC-003; FR-006.

### CASE-FR-007

Given An isolated synthetic fixture for F-01, with public signup / own account; admin mfa, the stated release mode and explicit enabled/disabled G-PROFILE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Request an Admin operation without, then with, valid MFA.

Then: Admin accounts SHALL require MFA before general release and SHALL support secure session invalidation and audit of sensitive authentication events.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-001–AC-003; FR-007.

### CASE-FR-008

Given An isolated synthetic fixture for F-02, with verified adult owner; extraction consent, the stated release mode and explicit enabled/disabled G-PROFILE/G-SCANNER/G-PROVIDER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Save identity/contact/nationality/institution/GPA/scale/language/preferences.

Then: A profile SHALL support student name/identity and contact information, nationality/residency, educational level, field, institution, GPA and scale, language information, and preferred study interests.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-004–AC-005; FR-008.

### CASE-FR-009

Given An isolated synthetic fixture for F-02, with verified adult owner; extraction consent, the stated release mode and explicit enabled/disabled G-PROFILE/G-SCANNER/G-PROVIDER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Switch the academic stage with missing obligatory-field configuration.

Then: Profile forms SHALL adapt education-related fields and validation to Bachelor's, Master's or PhD applicants; the exact obligatory field schema is [TBD].

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-004–AC-005; FR-009.

### CASE-FR-010

Given An isolated synthetic fixture for F-02, with verified adult owner; extraction consent, the stated release mode and explicit enabled/disabled G-PROFILE/G-SCANNER/G-PROVIDER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Create and correct profile facts manually without any AI route.

Then: Students SHALL be able to add, correct and save their profile facts manually without using AI extraction.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-004–AC-005; FR-010.

### CASE-FR-011

Given An isolated synthetic fixture for F-02, with verified adult owner; extraction consent, the stated release mode and explicit enabled/disabled G-PROFILE/G-SCANNER/G-PROVIDER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Upload allowed credentials, and separately submit an invalid/unscanned object.

Then: Students SHALL be able to upload supported CV/credentials/transcript artifacts for optional extraction, subject to configured format/size checks and malware scanning.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-004–AC-005; FR-011.

### CASE-FR-012

Given An isolated synthetic fixture for F-02, with verified adult owner; extraction consent, the stated release mode and explicit enabled/disabled G-PROFILE/G-SCANNER/G-PROVIDER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Decline personal-file AI consent and attempt egress.

Then: The platform SHALL capture explicit consent before sending uploaded personal files to an AI processor and SHALL offer a manual path if that consent is declined.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-004–AC-005; FR-012.

### CASE-FR-013

Given An isolated synthetic fixture for F-02, with verified adult owner; extraction consent, the stated release mode and explicit enabled/disabled G-PROFILE/G-SCANNER/G-PROVIDER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Review extraction proposals, accept only selected corrected fields.

Then: Extracted facts SHALL be shown as proposed values with source/uncertainty indicators and SHALL become trusted student profile values only after student review/confirmation.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-004–AC-005; FR-013.

### CASE-FR-014

Given An isolated synthetic fixture for F-02, with verified adult owner; extraction consent, the stated release mode and explicit enabled/disabled G-PROFILE/G-SCANNER/G-PROVIDER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Leave a required fact unconfirmed and request its use.

Then: Incomplete or unverified profile data SHALL remain visibly missing/unconfirmed and SHALL never be silently fabricated to complete eligibility, documents, or forms.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-004–AC-005; FR-014.

### CASE-FR-015

Given An isolated synthetic fixture for F-03, with public published projection; scoped admin moderation; own report, the stated release mode and explicit enabled/disabled G-SOURCE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Configure a source with and without permitted-use evidence.

Then: Admin SHALL configure and manage scholarship sources and their permitted ingestion methods.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-006–AC-008; FR-015.

### CASE-FR-016

Given An isolated synthetic fixture for F-03, with public published projection; scoped admin moderation; own report, the stated release mode and explicit enabled/disabled G-SOURCE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Import permitted source facts or create a manual listing with provenance.

Then: The platform SHALL support hybrid permitted automatic import plus Admin-created/edited listings, capturing raw source link and extraction/check timestamps.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-006–AC-008; FR-016.

### CASE-FR-017

Given An isolated synthetic fixture for F-03, with public published projection; scoped admin moderation; own report, the stated release mode and explicit enabled/disabled G-SOURCE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Search the public catalog before an imported version is approved.

Then: Newly imported scholarships SHALL remain unpublished until an Admin has reviewed and approved them.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-006–AC-008; FR-017.

### CASE-FR-018

Given An isolated synthetic fixture for F-03, with public published projection; scoped admin moderation; own report, the stated release mode and explicit enabled/disabled G-SOURCE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Approve/reject/revise/suspend/archive/restore a version under concurrent edits.

Then: Admin SHALL be able to approve, reject, revise, suspend, archive and restore scholarship listings with an attributable history.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-006–AC-008; FR-018.

### CASE-FR-019

Given An isolated synthetic fixture for F-03, with public published projection; scoped admin moderation; own report, the stated release mode and explicit enabled/disabled G-SOURCE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Import likely duplicate URLs and inspect the moderation queue.

Then: The platform SHALL detect likely duplicates and flag uncertain entries for Admin review before publication; merging logic [TBD].

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-006–AC-008; FR-019.

### CASE-FR-020

Given An isolated synthetic fixture for F-03, with public published projection; scoped admin moderation; own report, the stated release mode and explicit enabled/disabled G-SOURCE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Detect a changed deadline/criterion while the prior version is published.

Then: Background monitoring SHALL detect materially changed eligibility, deadlines, funding and links and route significant changes to an Admin before publication.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-006–AC-008; FR-020.

### CASE-FR-021

Given An isolated synthetic fixture for F-03, with public published projection; scoped admin moderation; own report, the stated release mode and explicit enabled/disabled G-SOURCE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Read a published listing with old/unverified verification evidence.

Then: Each visible listing SHALL show an attributable source and latest verification date/status; the catalog SHALL distinguish unverified from verified information.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-006–AC-008; FR-021.

### CASE-FR-022

Given An isolated synthetic fixture for F-03, with public published projection; scoped admin moderation; own report, the stated release mode and explicit enabled/disabled G-SOURCE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Read full/partial/unknown funding details without inventing coverage.

Then: Scholarships SHALL represent full/partial funding, waivers and financial aid, and SHALL show unknown funding details as unknown rather than estimated.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-006–AC-008; FR-022.

### CASE-FR-023

Given An isolated synthetic fixture for F-03, with public published projection; scoped admin moderation; own report, the stated release mode and explicit enabled/disabled G-SOURCE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Read single/multiple/rolling/unknown rounds with uncertain time.

Then: Scholarships SHALL represent single, multiple, rolling or unknown application rounds, with known deadline timezone and uncertainty explicitly shown.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-006–AC-008; FR-023.

### CASE-FR-024

Given An isolated synthetic fixture for F-03, with public published projection; scoped admin moderation; own report, the stated release mode and explicit enabled/disabled G-SOURCE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Submit an incorrect-data report, then have scoped Admin decide it.

Then: Students SHALL be able to submit an incorrect-information report from a scholarship page; Admin SHALL review evidence, log an outcome and suspend a materially risky listing when warranted.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-006–AC-008; FR-024.

### CASE-FR-025

Given An isolated synthetic fixture for F-04, with public catalog; verified owner for personalization; scoped rule admin, the stated release mode and explicit enabled/disabled G-SOURCE/G-PROFILE/G-PROVIDER/G-MEASURE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Run text/approved semantic search including a zero-result query.

Then: Students SHALL search the approved catalog through text and semantic search with a clear zero-results state.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-009–AC-012; FR-025.

### CASE-FR-026

Given An isolated synthetic fixture for F-04, with public catalog; verified owner for personalization; scoped rule admin, the stated release mode and explicit enabled/disabled G-SOURCE/G-PROFILE/G-PROVIDER/G-MEASURE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Apply each supported allowlisted filter and sort with stable pagination.

Then: Filters SHALL cover education level, discipline, country, funding, eligibility, language, deadline and application/registration state; sorting SHALL include relevance and deadline when meaningful.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-009–AC-012; FR-026.

### CASE-FR-027

Given An isolated synthetic fixture for F-04, with public catalog; verified owner for personalization; scoped rule admin, the stated release mode and explicit enabled/disabled G-SOURCE/G-PROFILE/G-PROVIDER/G-MEASURE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Inspect detail source/funding/criteria/files/round/link/check metadata.

Then: The scholarship detail SHALL present provider, source, funding, criteria, required documents, verified deadline/round, submission link and last verification.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-009–AC-012; FR-027.

### CASE-FR-028

Given An isolated synthetic fixture for F-04, with public catalog; verified owner for personalization; scoped rule admin, the stated release mode and explicit enabled/disabled G-SOURCE/G-PROFILE/G-PROVIDER/G-MEASURE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Evaluate confirmed mandatory conditions independently of relevance score.

Then: The platform SHALL evaluate known mandatory eligibility conditions separately from relevance scoring and return **Eligible**, **Undetermined** or **Ineligible** with reasons/evidence.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-009–AC-012; FR-028.

### CASE-FR-029

Given An isolated synthetic fixture for F-04, with public catalog; verified owner for personalization; scoped rule admin, the stated release mode and explicit enabled/disabled G-SOURCE/G-PROFILE/G-PROVIDER/G-MEASURE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Evaluate a criterion with missing profile or unverified source evidence.

Then: A missing fact or unverified scholarship requirement SHALL yield **Undetermined** for that criterion and SHALL NOT count as satisfied.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-009–AC-012; FR-029.

### CASE-FR-030

Given An isolated synthetic fixture for F-04, with public catalog; verified owner for personalization; scoped rule admin, the stated release mode and explicit enabled/disabled G-SOURCE/G-PROFILE/G-PROVIDER/G-MEASURE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Inspect contribution/confidence/limitation and disclaimer for a scored result.

Then: The platform SHALL compute an explainable AI/RAG Match Score with criterion contributions, confidence/limitations and a clear disclaimer that it is not admission likelihood.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-009–AC-012; FR-030.

### CASE-FR-031

Given An isolated synthetic fixture for F-04, with public catalog; verified owner for personalization; scoped rule admin, the stated release mode and explicit enabled/disabled G-SOURCE/G-PROFILE/G-PROVIDER/G-MEASURE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Change weights and replay an older evaluation against its captured version.

Then: Admin SHALL be able to manage matching weights/rules with controlled versions; evaluations SHALL record the applicable ruleset/weight version and timestamp.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-009–AC-012; FR-031.

### CASE-FR-032

Given An isolated synthetic fixture for F-04, with public catalog; verified owner for personalization; scoped rule admin, the stated release mode and explicit enabled/disabled G-SOURCE/G-PROFILE/G-PROVIDER/G-MEASURE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Give AI a high fit score despite a deterministic mandatory failure.

Then: Results SHALL prioritize eligible matches while permitting users to inspect unknown/ineligible options and explanations; a failed mandatory criterion SHALL never become “Eligible” via a high score.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-009–AC-012; FR-032.

### CASE-FR-033

Given An isolated synthetic fixture for F-04, with public catalog; verified owner for personalization; scoped rule admin, the stated release mode and explicit enabled/disabled G-SOURCE/G-PROFILE/G-PROVIDER/G-MEASURE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Evaluate a partial profile without sufficient scoring coverage.

Then: An incomplete student profile SHALL permit qualified partial matching, identify missing inputs and avoid a falsely definitive score or eligibility conclusion.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-009–AC-012; FR-033.

### CASE-FR-034

Given An isolated synthetic fixture for F-05, with verified owner; exact quote/consent, approved route, the stated release mode and explicit enabled/disabled G-PROVIDER/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Request each of the four configured draft types.

Then: The system SHALL offer AI drafts for **CV**, **Motivation Letter**, **Personal Statement** and **Scholarship Essays**.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-013–AC-015; FR-034.

### CASE-FR-035

Given An isolated synthetic fixture for F-05, with verified owner; exact quote/consent, approved route, the stated release mode and explicit enabled/disabled G-PROVIDER/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Generate using a profile with no confirmed awards/jobs/grades.

Then: Drafting SHALL use trusted student-confirmed facts and, where relevant, the selected scholarship's reviewed criteria; unsupported credentials SHALL not be asserted.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-013–AC-015; FR-035.

### CASE-FR-036

Given An isolated synthetic fixture for F-05, with verified owner; exact quote/consent, approved route, the stated release mode and explicit enabled/disabled G-PROVIDER/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Choose English output with Arabic UI, then reverse the languages.

Then: Students SHALL select the output language independently from their interface language; known scholarship language requirements SHALL be clearly shown.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-013–AC-015; FR-036.

### CASE-FR-037

Given An isolated synthetic fixture for F-05, with verified owner; exact quote/consent, approved route, the stated release mode and explicit enabled/disabled G-PROVIDER/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Return a provider assertion requiring student confirmation.

Then: Statements requiring student verification SHALL be marked, withheld or clarified before final approval, rather than silently treated as factual.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-013–AC-015; FR-037.

### CASE-FR-038

Given An isolated synthetic fixture for F-05, with verified owner; exact quote/consent, approved route, the stated release mode and explicit enabled/disabled G-PROVIDER/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Submit an unconfirmed quote and then explicitly confirm the displayed quote.

Then: When a generation is chargeable, the platform SHALL show the exact Credit quote and obtain confirmation before reserving funds or starting work.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-013–AC-015; FR-038.

### CASE-FR-039

Given An isolated synthetic fixture for F-05, with verified owner; exact quote/consent, approved route, the stated release mode and explicit enabled/disabled G-PROVIDER/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Review a technically accepted draft, edit it manually and mark its exact version ready.

Then: Students SHALL review a preview and SHALL be able to edit generated documents manually before marking them ready.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-013–AC-015; FR-039.

### CASE-FR-040

Given An isolated synthetic fixture for F-05, with verified owner; exact quote/consent, approved route, the stated release mode and explicit enabled/disabled G-PROVIDER/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Export the student-approved version to both supported formats.

Then: Students SHALL be able to export approved document content to usable PDF and DOCX files.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-013–AC-015; FR-040.

### CASE-FR-041

Given An isolated synthetic fixture for F-05, with verified owner; exact quote/consent, approved route, the stated release mode and explicit enabled/disabled G-PROVIDER/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Interrupt generation and inspect queued/running/failed status without fake output.

Then: Generation SHALL expose status/progress and a visible failed/retry state without inventing completed output.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-013–AC-015; FR-041.

### CASE-FR-042

Given An isolated synthetic fixture for F-05, with verified owner; exact quote/consent, approved route, the stated release mode and explicit enabled/disabled G-PROVIDER/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Attempt conversational AI editing versus ordinary manual editing.

Then: The MVP document editor SHALL provide essential manual text/format editing, NOT AI chat-based editing.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-013–AC-015; FR-042.

### CASE-FR-043

Given An isolated synthetic fixture for F-06, with verified owner; admin library 403; selected shares only, the stated release mode and explicit enabled/disabled G-SCANNER/G-LEGAL branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: List/rename/organize/delete only owned uploaded/generated documents.

Then: A central library SHALL list student-owned uploaded and generated documents, with organization, rename and controlled deletion.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-016–AC-017; FR-043.

### CASE-FR-044

Given An isolated synthetic fixture for F-06, with verified owner; admin library 403; selected shares only, the stated release mode and explicit enabled/disabled G-SCANNER/G-LEGAL branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Create a scholarship-specific variant and select its exact version.

Then: The platform SHALL support scholarship-specific document variants and attach exact document versions to application requirements.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-016–AC-017; FR-044.

### CASE-FR-045

Given An isolated synthetic fixture for F-06, with verified owner; admin library 403; selected shares only, the stated release mode and explicit enabled/disabled G-SCANNER/G-LEGAL branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Inspect required/attached/missing checklist items with uncertain requirements.

Then: Each application SHALL show required, attached and missing document items based on currently approved requirement information.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-016–AC-017; FR-045.

### CASE-FR-046

Given An isolated synthetic fixture for F-06, with verified owner; admin library 403; selected shares only, the stated release mode and explicit enabled/disabled G-SCANNER/G-LEGAL branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Save a revision while a prior version is attached to a submission.

Then: Saving document edits SHALL preserve version history rather than overwrite prior submitted historical versions.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-016–AC-017; FR-046.

### CASE-FR-047

Given An isolated synthetic fixture for F-06, with verified owner; admin library 403; selected shares only, the stated release mode and explicit enabled/disabled G-SCANNER/G-LEGAL branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Restore version 1 after versions 2 and 3 already exist.

Then: The student SHALL be able to compare versions and restore an old version as a new current version, preserving existing history.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-016–AC-017; FR-047.

### CASE-FR-048

Given An isolated synthetic fixture for F-06, with verified owner; admin library 403; selected shares only, the stated release mode and explicit enabled/disabled G-SCANNER/G-LEGAL branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Try modifying/replacing the exact submitted version.

Then: When a student manually confirms a submission, linked document versions SHALL be frozen against ordinary editing/replacement.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-016–AC-017; FR-048.

### CASE-FR-049

Given An isolated synthetic fixture for F-06, with verified owner; admin library 403; selected shares only, the stated release mode and explicit enabled/disabled G-SCANNER/G-LEGAL branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Guess another owner library ID as student and as ordinary Admin.

Then: The library SHALL enforce per-owner access to metadata and file bytes; Admin has no default permission to inspect private document content.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-016–AC-017; FR-049.

### CASE-FR-050

Given An isolated synthetic fixture for F-06, with verified owner; admin library 403; selected shares only, the stated release mode and explicit enabled/disabled G-SCANNER/G-LEGAL branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Swap object bytes/version after scanning and attempt acceptance.

Then: Uploaded documents SHALL pass content/type/size scanning, quarantine if unsafe and use access-controlled storage; format and numeric limits [TBD].

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-016–AC-017; FR-050.

### CASE-FR-051

Given An isolated synthetic fixture for F-07, with verified owner; student confirms external submission; no ai mutation, the stated release mode and explicit enabled/disabled G-STATUS/G-SOURCE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Save/unsave a scholarship and create its application preparation record.

Then: A student SHALL be able to save/unsave a scholarship and create/manage a corresponding application preparation record.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-018–AC-019; FR-051.

### CASE-FR-052

Given An isolated synthetic fixture for F-07, with verified owner; student confirms external submission; no ai mutation, the stated release mode and explicit enabled/disabled G-STATUS/G-SOURCE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Read/update owned checklist, notes, selected versions, verified dates and history.

Then: Each application SHALL present requirements, selected document versions, deadlines (where verified), user-owned notes and history.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-018–AC-019; FR-052.

### CASE-FR-053

Given An isolated synthetic fixture for F-07, with verified owner; student confirms external submission; no ai mutation, the stated release mode and explicit enabled/disabled G-STATUS/G-SOURCE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Apply each documented legal and illegal application status edge.

Then: The application tracker SHALL support at least **Preparing**, **Ready to Apply**, **Submitted**, **Under Review**, **Accepted**, **Rejected**; final transition policy and additional states [TBD].

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-018–AC-019; FR-053.

### CASE-FR-054

Given An isolated synthetic fixture for F-07, with verified owner; student confirms external submission; no ai mutation, the stated release mode and explicit enabled/disabled G-STATUS/G-SOURCE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Complete autofill without external submission, then explicitly confirm submission.

Then: The **Submitted** state SHALL be set only by an explicit student confirmation after the student submits on the third-party portal; autofill success SHALL not set it.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-018–AC-019; FR-054.

### CASE-FR-055

Given An isolated synthetic fixture for F-07, with verified owner; student confirms external submission; no ai mutation, the stated release mode and explicit enabled/disabled G-STATUS/G-SOURCE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Compare student assertions and a separately sourced official report.

Then: The system SHALL preserve a timestamped application-status and activity history, distinguishing student-reported statuses from officially sourced status data.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-018–AC-019; FR-055.

### CASE-FR-056

Given An isolated synthetic fixture for F-07, with verified owner; student confirms external submission; no ai mutation, the stated release mode and explicit enabled/disabled G-STATUS/G-SOURCE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Read own application counts and progress without invented official outcome.

Then: The tracker SHALL provide personal application counts and progress indicators without converting inferred outcomes into official decisions.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-018–AC-019; FR-056.

### CASE-FR-057

Given An isolated synthetic fixture for F-07, with verified owner; student confirms external submission; no ai mutation, the stated release mode and explicit enabled/disabled G-STATUS/G-SOURCE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Deliver missing-document/source/deadline events twice with verified or unknown facts.

Then: The system SHALL generate in-app deadline, document-missing and relevant source-change notices to affected students when information can be verified.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-018–AC-019; FR-057.

### CASE-FR-058

Given An isolated synthetic fixture for F-07, with verified owner; student confirms external submission; no ai mutation, the stated release mode and explicit enabled/disabled G-STATUS/G-SOURCE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Attempt official status integration without a lawful registered integration.

Then: **Conditional:** official application-status integrations MAY update a tracked application only where a lawful documented integration exists; changes SHALL be source-attributed and conflict-safe.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-018–AC-019; FR-058.

### CASE-FR-059

Given An isolated synthetic fixture for F-08, with owner initiated allowed form; no third-party password/otp, the stated release mode and explicit enabled/disabled G-EXT branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Associate extension session without storing portal credentials.

Then: The companion browser extension SHALL authenticate/associate an active student session without storing third-party portal passwords.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-020–AC-022; FR-059.

### CASE-FR-060

Given An isolated synthetic fixture for F-08, with owner initiated allowed form; no third-party password/otp, the stated release mode and explicit enabled/disabled G-EXT branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Activate a fill only on an explicitly initiated permitted form.

Then: Autofill SHALL run only after a user-initiated action on a permitted site/form, with least-privilege site access.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-020–AC-022; FR-060.

### CASE-FR-061

Given An isolated synthetic fixture for F-08, with owner initiated allowed form; no third-party password/otp, the stated release mode and explicit enabled/disabled G-EXT branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Use a tested portal and a different permitted best-effort portal.

Then: The extension SHALL provide a tested-site support path and a clearly labeled best-effort path for other permitted forms; unsupported-site limitations SHALL be visible.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-020–AC-022; FR-061.

### CASE-FR-062

Given An isolated synthetic fixture for F-08, with owner initiated allowed form; no third-party password/otp, the stated release mode and explicit enabled/disabled G-EXT branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Map confirmed versus missing facts to external fields.

Then: The extension SHALL map confirmed profile/application data to recognizable form fields, leaving unknown fields for student input.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-020–AC-022; FR-062.

### CASE-FR-063

Given An isolated synthetic fixture for F-08, with owner initiated allowed form; no third-party password/otp, the stated release mode and explicit enabled/disabled G-EXT branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Refuse sensitive-field confirmation and inspect resulting proposed fill.

Then: Sensitive personal fields SHALL require a suitable explicit confirmation before the extension inserts their values.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-020–AC-022; FR-063.

### CASE-FR-064

Given An isolated synthetic fixture for F-08, with owner initiated allowed form; no third-party password/otp, the stated release mode and explicit enabled/disabled G-EXT branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Review and manually correct proposed/inserted values before student submission.

Then: Before third-party submission, the student SHALL be able to inspect all values inserted or proposed and manually correct/complete fields.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-020–AC-022; FR-064.

### CASE-FR-065

Given An isolated synthetic fixture for F-08, with owner initiated allowed form; no third-party password/otp, the stated release mode and explicit enabled/disabled G-EXT branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Request password/OTP/CAPTCHA or automatic external Submit handling.

Then: The extension SHALL NOT collect passwords/OTP, solve or bypass CAPTCHA, bypass logins, submit an application automatically, or work in breach of portal permissions.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-020–AC-022; FR-065.

### CASE-FR-066

Given An isolated synthetic fixture for F-08, with owner initiated allowed form; no third-party password/otp, the stated release mode and explicit enabled/disabled G-EXT branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Fail a field mapping, retry within bounds and use manual fallback.

Then: On mapping or site failures, the extension SHALL show failed/missing fields, allow bounded retry and offer manual copy-entry instructions.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-020–AC-022; FR-066.

### CASE-FR-067

Given An isolated synthetic fixture for F-08, with owner initiated allowed form; no third-party password/otp, the stated release mode and explicit enabled/disabled G-EXT branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Interrupt allowed/local save and inspect honest known preparation state.

Then: The extension MAY save **local/allowed** preparation progress only where the external page supports it; it SHALL not claim remote submission or save guarantees.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-020–AC-022; FR-067.

### CASE-FR-068

Given An isolated synthetic fixture for F-08, with owner initiated allowed form; no third-party password/otp, the stated release mode and explicit enabled/disabled G-EXT branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Inspect diagnostic events after an extension error.

Then: Extension diagnostics SHALL record sanitized site/error categories without logging form secrets, third-party passwords/OTP or unnecessary personal content.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-020–AC-022; FR-068.

### CASE-FR-069

Given An isolated synthetic fixture for F-09, with owner wallet/quote; scoped mfa admin correction; no ai finance, the stated release mode and explicit enabled/disabled G-LEGAL/G-PAID branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Browse/profile manually for free and exhaust configured AI allowance.

Then: Basic scholarship browsing/search and student profile SHALL remain free of charge; initial AI allowances SHALL be bounded by configurable policies [TBD].

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-023–AC-025; FR-069.

### CASE-FR-070

Given An isolated synthetic fixture for F-09, with owner wallet/quote; scoped mfa admin correction; no ai finance, the stated release mode and explicit enabled/disabled G-LEGAL/G-PAID branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Edit grant/service policies; try enabling paid package purchase in Beta.

Then: Admin SHALL configure the one-time free grant, Credit packages, individual chargeable service prices and package availability.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-023–AC-025; FR-070.

### CASE-FR-071

Given An isolated synthetic fixture for F-09, with owner wallet/quote; scoped mfa admin correction; no ai finance, the stated release mode and explicit enabled/disabled G-LEGAL/G-PAID branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Compare available/reserved/settled wallet amounts under concurrency.

Then: A Credit wallet SHALL show available balance and correctly distinguish reserved versus settled amounts.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-023–AC-025; FR-071.

### CASE-FR-072

Given An isolated synthetic fixture for F-09, with owner wallet/quote; scoped mfa admin correction; no ai finance, the stated release mode and explicit enabled/disabled G-LEGAL/G-PAID branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Attempt service admission without explicit exact-price approval.

Then: Before any configured paid AI operation, the student SHALL see the exact quoted price and explicitly authorize the operation.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-023–AC-025; FR-072.

### CASE-FR-073

Given An isolated synthetic fixture for F-09, with owner wallet/quote; scoped mfa admin correction; no ai finance, the stated release mode and explicit enabled/disabled G-LEGAL/G-PAID branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Change price after the student accepts its immutable quote.

Then: An authorized operation SHALL use a price snapshot so later Admin price changes do not alter its accepted charge.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-023–AC-025; FR-073.

### CASE-FR-074

Given An isolated synthetic fixture for F-09, with owner wallet/quote; scoped mfa admin correction; no ai finance, the stated release mode and explicit enabled/disabled G-LEGAL/G-PAID branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Reserve near available balance concurrently.

Then: The platform SHALL reserve the agreed Credits before starting a paid operation and SHALL prevent execution if available balance is insufficient.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-023–AC-025; FR-074.

### CASE-FR-075

Given An isolated synthetic fixture for F-09, with owner wallet/quote; scoped mfa admin correction; no ai finance, the stated release mode and explicit enabled/disabled G-LEGAL/G-PAID branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Replay a successful finalizer/callback after worker crash.

Then: A successfully completed operation SHALL settle its reservation into one final debit; it SHALL NOT charge again on callback/retry.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-023–AC-025; FR-075.

### CASE-FR-076

Given An isolated synthetic fixture for F-09, with owner wallet/quote; scoped mfa admin correction; no ai finance, the stated release mode and explicit enabled/disabled G-LEGAL/G-PAID branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Fail technically before/after settlement, duplicate release/reversal callbacks.

Then: A technically failed operation SHALL release its reservation or refund an already settled technical-error charge exactly once, leaving no inappropriate final debit.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-023–AC-025; FR-076.

### CASE-FR-077

Given An isolated synthetic fixture for F-09, with owner wallet/quote; scoped mfa admin correction; no ai finance, the stated release mode and explicit enabled/disabled G-LEGAL/G-PAID branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Inspect signed journal actor/reason/type/identity/timestamps and reconciliation.

Then: Wallet transactions SHALL be represented by append-only ledger entries with actor, reason, transaction identity, amount, type and audit timestamps.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-023–AC-025; FR-077.

### CASE-FR-078

Given An isolated synthetic fixture for F-09, with owner wallet/quote; scoped mfa admin correction; no ai finance, the stated release mode and explicit enabled/disabled G-LEGAL/G-PAID branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Advance time, then request deletion/restore/final cancellation.

Then: Credits SHALL not expire due to elapsed time, but SHALL freeze during the deletion recovery window and be canceled at final deletion as agreed.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-023–AC-025; FR-078.

### CASE-FR-079

Given An isolated synthetic fixture for F-09, with owner wallet/quote; scoped mfa admin correction; no ai finance, the stated release mode and explicit enabled/disabled G-LEGAL/G-PAID branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Try direct balance edit versus authorized reasoned adjustment workflow.

Then: An Admin SHALL be able to add/remove Credits manually only through reasoned, auditable adjustments, without rewriting past ledger entries.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-023–AC-025; FR-079.

### CASE-FR-080

Given An isolated synthetic fixture for F-10, with owner purchase; scoped mfa admin verifies actual received funds, the stated release mode and explicit enabled/disabled G-PAID/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture. Beta must reject the purchase path without any ledger mutation; the positive case is Advanced-only after G-PAID approval.

When: Select a published package outside Beta only after paid-release approval.

Then: The student SHALL be able to select a published Credit package and see the exact manual-payment instructions for an approved local method.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-026–AC-028; FR-080.

### CASE-FR-081

Given An isolated synthetic fixture for F-10, with owner purchase; scoped mfa admin verifies actual received funds, the stated release mode and explicit enabled/disabled G-PAID/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture. Beta must reject the purchase path without any ledger mutation; the positive case is Advanced-only after G-PAID approval.

When: Upload validated payment proof and inspect review state.

Then: The student SHALL submit a payment request with reference/proof through validated safe upload and see its review state.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-026–AC-028; FR-081.

### CASE-FR-082

Given An isolated synthetic fixture for F-10, with owner purchase; scoped mfa admin verifies actual received funds, the stated release mode and explicit enabled/disabled G-PAID/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture. Beta must reject the purchase path without any ledger mutation; the positive case is Advanced-only after G-PAID approval.

When: Upload an image without independent received-funds confirmation.

Then: A pending request SHALL not credit the student automatically, regardless of whether a receipt image is uploaded.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-026–AC-028; FR-082.

### CASE-FR-083

Given An isolated synthetic fixture for F-10, with owner purchase; scoped mfa admin verifies actual received funds, the stated release mode and explicit enabled/disabled G-PAID/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture. Beta must reject the purchase path without any ledger mutation; the positive case is Advanced-only after G-PAID approval.

When: Review funds using the independent approved receiver confirmation.

Then: Admin SHALL verify actual receipt of funds outside the uploaded proof prior to approving payment.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-026–AC-028; FR-083.

### CASE-FR-084

Given An isolated synthetic fixture for F-10, with owner purchase; scoped mfa admin verifies actual received funds, the stated release mode and explicit enabled/disabled G-PAID/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture. Beta must reject the purchase path without any ledger mutation; the positive case is Advanced-only after G-PAID approval.

When: Approve/reject/request replacement evidence with reason.

Then: Admin SHALL approve, reject with explanation or request replacement evidence, and the student SHALL see the resulting status in-app.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-026–AC-028; FR-084.

### CASE-FR-085

Given An isolated synthetic fixture for F-10, with owner purchase; scoped mfa admin verifies actual received funds, the stated release mode and explicit enabled/disabled G-PAID/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture. Beta must reject the purchase path without any ledger mutation; the positive case is Advanced-only after G-PAID approval.

When: Submit one transfer reference from two accounts/concurrent review.

Then: A payment reference/verified transfer SHALL NOT be accepted twice to issue separate Credit additions; approval SHALL be idempotent.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-026–AC-028; FR-085.

### CASE-FR-086

Given An isolated synthetic fixture for F-10, with owner purchase; scoped mfa admin verifies actual received funds, the stated release mode and explicit enabled/disabled G-PAID/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture. Beta must reject the purchase path without any ledger mutation; the positive case is Advanced-only after G-PAID approval.

When: Approve one purchase repeatedly using its confirmed snapshot.

Then: A successful payment approval SHALL generate exactly one ledger Credit grant matching the package's confirmed purchase snapshot.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-026–AC-028; FR-086.

### CASE-FR-087

Given An isolated synthetic fixture for F-10, with owner purchase; scoped mfa admin verifies actual received funds, the stated release mode and explicit enabled/disabled G-PAID/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture. Beta must reject the purchase path without any ledger mutation; the positive case is Advanced-only after G-PAID approval.

When: Read payment reviewer/reference/decision/evidence only with permitted scope.

Then: Payment status, reviewer, verified reference, decision, evidence metadata and timestamps SHALL be auditable with access restrictions.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-026–AC-028; FR-087.

### CASE-FR-088

Given An isolated synthetic fixture for F-10, with owner purchase; scoped mfa admin verifies actual received funds, the stated release mode and explicit enabled/disabled G-PAID/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture. Beta must reject the purchase path without any ledger mutation; the positive case is Advanced-only after G-PAID approval.

When: Request a cash remedy under unresolved versus approved legal policy.

Then: The system SHALL not represent discretionary cash refunds as automatic; approved refund handling SHALL follow agreed legal/technical-failure obligations and documented policy.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-026–AC-028; FR-088.

### CASE-FR-089

Given An isolated synthetic fixture for F-11, with owner recipient/preferences; mandatory security never suppressed, the stated release mode and explicit enabled/disabled G-LEGAL branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Open own inbox and follow a typed inaccessible destination.

Then: The platform SHALL provide a student in-app notification inbox with unread/read state and contextual destination links.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-029–AC-030; FR-089.

### CASE-FR-090

Given An isolated synthetic fixture for F-11, with owner recipient/preferences; mandatory security never suppressed, the stated release mode and explicit enabled/disabled G-LEGAL branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Deliver source/checklist/document/wallet/support events.

Then: Notifications SHALL cover eligible scholarship/deadline/source changes, application/document alerts, wallet/payment events and support responses.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-029–AC-030; FR-090.

### CASE-FR-091

Given An isolated synthetic fixture for F-11, with owner recipient/preferences; mandatory security never suppressed, the stated release mode and explicit enabled/disabled G-LEGAL branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Replay equivalent event/version/category for the same recipient.

Then: The system SHALL avoid repeated equivalent notifications for the same event/recipient.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-029–AC-030; FR-091.

### CASE-FR-092

Given An isolated synthetic fixture for F-11, with owner recipient/preferences; mandatory security never suppressed, the stated release mode and explicit enabled/disabled G-LEGAL branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Disable optional category while a mandatory account event occurs.

Then: Students SHALL configure preferences for optional notification types; mandatory account/security messages SHALL not be blocked by optional preferences.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-029–AC-030; FR-092.

### CASE-FR-093

Given An isolated synthetic fixture for F-11, with owner recipient/preferences; mandatory security never suppressed, the stated release mode and explicit enabled/disabled G-LEGAL branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Try product email/push/WhatsApp versus transactional verification email.

Then: The product SHALL NOT require email/WhatsApp/Web Push to deliver product notifications during MVP; authentication-related email remains permitted.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-029–AC-030; FR-093.

### CASE-FR-094

Given An isolated synthetic fixture for F-12, with owner tickets; currently assigned scoped mfa admin; ai limited, the stated release mode and explicit enabled/disabled G-TICKET/G-PROVIDER/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Create and inspect an owned categorized ticket with a selected accepted attachment.

Then: Students SHALL create and view their own support tickets with categories, attachments (validated) and message history.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-031–AC-034; FR-094.

### CASE-FR-095

Given An isolated synthetic fixture for F-12, with owner tickets; currently assigned scoped mfa admin; ai limited, the stated release mode and explicit enabled/disabled G-TICKET/G-PROVIDER/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Request AI guidance with current policy/budget or an unavailable route.

Then: Support AI SHALL be available 24/7 for guidance, ticket triage and limited authorized assistance.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-031–AC-034; FR-095.

### CASE-FR-096

Given An isolated synthetic fixture for F-12, with owner tickets; currently assigned scoped mfa admin; ai limited, the stated release mode and explicit enabled/disabled G-TICKET/G-PROVIDER/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Inspect AI category/priority suggestion then Admin override.

Then: Support AI SHALL identify category and suggested priority, while Admin SHALL retain authority to change the priority and disposition.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-031–AC-034; FR-096.

### CASE-FR-097

Given An isolated synthetic fixture for F-12, with owner tickets; currently assigned scoped mfa admin; ai limited, the stated release mode and explicit enabled/disabled G-TICKET/G-PROVIDER/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Ask for human help or trigger low confidence/failures/financial/critical case.

Then: The system SHALL hand off to Admin on student request, low AI confidence, recurring failed answers, financial/sensitive issues, or critical approaching deadline, passing minimum necessary conversation context.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-031–AC-034; FR-097.

### CASE-FR-098

Given An isolated synthetic fixture for F-12, with owner tickets; currently assigned scoped mfa admin; ai limited, the stated release mode and explicit enabled/disabled G-TICKET/G-PROVIDER/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Ask support AI to approve funds or change balance.

Then: Support AI SHALL never approve payment or perform sensitive financial balance changes. Any other AI action requires an explicitly defined authorization policy [TBD].

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-031–AC-034; FR-098.

### CASE-FR-099

Given An isolated synthetic fixture for F-12, with owner tickets; currently assigned scoped mfa admin; ai limited, the stated release mode and explicit enabled/disabled G-TICKET/G-PROVIDER/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Transition through each of the six canonical support states.

Then: Tickets SHALL support statuses **New, AI Handling, Awaiting Admin, Awaiting Student, Resolved, Closed**, with an auditable transition log.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-031–AC-034; FR-099.

### CASE-FR-100

Given An isolated synthetic fixture for F-12, with owner tickets; currently assigned scoped mfa admin; ai limited, the stated release mode and explicit enabled/disabled G-TICKET/G-PROVIDER/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Resolve, object, auto-close, reopen and rate at configured boundaries.

Then: Students SHALL be able to confirm resolution, reopen eligible tickets and provide a support-quality rating; auto-close follows a configurable Admin-defined interval.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-031–AC-034; FR-100.

### CASE-FR-101

Given An isolated synthetic fixture for F-12, with owner tickets; currently assigned scoped mfa admin; ai limited, the stated release mode and explicit enabled/disabled G-TICKET/G-PROVIDER/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Edit human workdays/hours/holiday policy without changing AI availability labels.

Then: Admin SHALL configure human-support working days, working hours and holidays; 24/7 AI availability SHALL be represented separately.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-031–AC-034; FR-101.

### CASE-FR-102

Given An isolated synthetic fixture for F-12, with owner tickets; currently assigned scoped mfa admin; ai limited, the stated release mode and explicit enabled/disabled G-TICKET/G-PROVIDER/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Calculate first-human SLA across nonworking and DST intervals.

Then: Admin SHALL configure the first-human-response SLA goal by priority, and the system SHALL measure the target using the Admin-defined working calendar.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-031–AC-034; FR-102.

### CASE-FR-103

Given An isolated synthetic fixture for F-12, with owner tickets; currently assigned scoped mfa admin; ai limited, the stated release mode and explicit enabled/disabled G-TICKET/G-PROVIDER/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Cross each configured warning/breach/escalation threshold repeatedly.

Then: The system SHALL warn/escalate tickets approaching or exceeding the configured human-response SLA target and record relevant events.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-031–AC-034; FR-103.

### CASE-FR-104

Given An isolated synthetic fixture for F-12, with owner tickets; currently assigned scoped mfa admin; ai limited, the stated release mode and explicit enabled/disabled G-TICKET/G-PROVIDER/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Inspect assigned queue due time/category/history/escalation markers.

Then: Admin SHALL have a queue with ticket ownership, category, priority, history, status, due calculation and escalation markers.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-031–AC-034; FR-104.

### CASE-FR-105

Given An isolated synthetic fixture for F-12, with owner tickets; currently assigned scoped mfa admin; ai limited, the stated release mode and explicit enabled/disabled G-TICKET/G-PROVIDER/G-SCANNER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Compare aggregate support response/SLA/resolution/rating metrics to underlying cases.

Then: Aggregate support performance SHALL report ticket volumes, first human response, SLA violations, resolution events and ratings.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-031–AC-034; FR-105.

### CASE-FR-106

Given An isolated synthetic fixture for F-13, with mfa admin scope; operational aggregates, no private library, the stated release mode and explicit enabled/disabled G-SIGNOFF/G-MEASURE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Attempt each scoped governance action without and then with MFA/scope.

Then: Admin SHALL manage catalog sources/reviews, student reports, user administration, Credit packages/prices, payment verification, support and operational settings in protected views.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-035–AC-036; FR-106.

### CASE-FR-107

Given An isolated synthetic fixture for F-13, with mfa admin scope; operational aggregates, no private library, the stated release mode and explicit enabled/disabled G-SIGNOFF/G-MEASURE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Publish new rule weights without mutating past evaluations.

Then: Admin SHALL have controlled actions for changing matching weights/rules, with versioning and documented publication.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-035–AC-036; FR-107.

### CASE-FR-108

Given An isolated synthetic fixture for F-13, with mfa admin scope; operational aggregates, no private library, the stated release mode and explicit enabled/disabled G-SIGNOFF/G-MEASURE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Inspect aggregate operational dashboards with personal essay content present in storage.

Then: Admin SHALL view aggregate operational dashboards covering source freshness, matching, documents, student-confirmed applications, Credits/payment status, ticket SLA and extension error categories.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-035–AC-036; FR-108.

### CASE-FR-109

Given An isolated synthetic fixture for F-13, with mfa admin scope; operational aggregates, no private library, the stated release mode and explicit enabled/disabled G-SIGNOFF/G-MEASURE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Commit a sensitive Admin price/rule/adjustment and inspect attributed before/after audit.

Then: Sensitive administrative operations SHALL create audit events including authenticated actor, operation, before/after identifiers where appropriate, reason and timestamp.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-035–AC-036; FR-109.

### CASE-FR-110

Given An isolated synthetic fixture for F-13, with mfa admin scope; operational aggregates, no private library, the stated release mode and explicit enabled/disabled G-SIGNOFF/G-MEASURE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Request unrelated student CV through ordinary Admin management.

Then: Normal Admin use SHALL NOT grant blanket read access to student private file contents; any necessary exceptional support access requires a separately authorized and audited procedure [TBD].

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-035–AC-036; FR-110.

### CASE-FR-111

Given An isolated synthetic fixture for F-13, with mfa admin scope; operational aggregates, no private library, the stated release mode and explicit enabled/disabled G-SIGNOFF/G-MEASURE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Review a suspect report/material change without automatic publication.

Then: Admin SHALL be able to suspend suspect listings and handle reports without automatic publication of unreviewed material changes.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-035–AC-036; FR-111.

### CASE-FR-112

Given An isolated synthetic fixture for F-13, with mfa admin scope; operational aggregates, no private library, the stated release mode and explicit enabled/disabled G-SIGNOFF/G-MEASURE branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Inspect AI retry/unit-cost reporting without exposing private payload.

Then: Admin SHALL see AI failure/retry, extension and Credit-unit-cost reporting without displaying unnecessary personal document text in analytics.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-035–AC-036; FR-112.

### CASE-FR-113

Given An isolated synthetic fixture for F-14, with owner deletion/recovery; scoped policy admin; narrow lawful purge, the stated release mode and explicit enabled/disabled G-LEGAL/G-RESTORE/G-PROVIDER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Grant/revoke purpose-specific processing disclosure/version.

Then: The platform SHALL capture and retain scoped consent records for AI processing of student-provided documents, and present plain-language AI disclosures.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-037–AC-039; FR-113.

### CASE-FR-114

Given An isolated synthetic fixture for F-14, with owner deletion/recovery; scoped policy admin; narrow lawful purge, the stated release mode and explicit enabled/disabled G-LEGAL/G-RESTORE/G-PROVIDER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Attempt insecure transfer/read of protected stored sensitive content.

Then: File content and sensitive personal data SHALL be encrypted in transit and at rest with role- and owner-restricted retrieval.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-037–AC-039; FR-114.

### CASE-FR-115

Given An isolated synthetic fixture for F-14, with owner deletion/recovery; scoped policy admin; narrow lawful purge, the stated release mode and explicit enabled/disabled G-LEGAL/G-RESTORE/G-PROVIDER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Attempt provider training without distinct permission and compliant processor policy.

Then: Uploaded student files SHALL NOT be used for training AI models absent distinct explicit permission, and provider agreements/settings SHALL honor this.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-037–AC-039; FR-115.

### CASE-FR-116

Given An isolated synthetic fixture for F-14, with owner deletion/recovery; scoped policy admin; narrow lawful purge, the stated release mode and explicit enabled/disabled G-LEGAL/G-RESTORE/G-PROVIDER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Request individual-document erasure and preview account deletion impact.

Then: Students SHALL be able to request individual-document deletion and view the effects/limitations of account deletion before confirmation.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-037–AC-039; FR-116.

### CASE-FR-117

Given An isolated synthetic fixture for F-14, with owner deletion/recovery; scoped policy admin; narrow lawful purge, the stated release mode and explicit enabled/disabled G-LEGAL/G-RESTORE/G-PROVIDER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Confirm account deletion under the current Admin recovery policy.

Then: Upon confirmed account deletion request, access SHALL be disabled promptly and Credits frozen for a 30-calendar-day recovery period. UD-001 applies the captured Admin policy/cutoff; changing the current policy cannot alter an existing request. See ADR 0008.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-037–AC-039; FR-117.

### CASE-FR-118

Given An isolated synthetic fixture for F-14, with owner deletion/recovery; scoped policy admin; narrow lawful purge, the stated release mode and explicit enabled/disabled G-LEGAL/G-RESTORE/G-PROVIDER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Restore just before its captured deadline after Admin changes the current policy.

Then: A valid recovery request within the 30-day window SHALL restore eligible profile/files/history access and frozen Credits. UD-001 applies the captured Admin policy/cutoff; changing the current policy cannot alter an existing request. See ADR 0008.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-037–AC-039; FR-118.

### CASE-FR-119

Given An isolated synthetic fixture for F-14, with owner deletion/recovery; scoped policy admin; narrow lawful purge, the stated release mode and explicit enabled/disabled G-LEGAL/G-RESTORE/G-PROVIDER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Finish irreversible purge and race duplicate remaining-Credit cancellation.

Then: After that window, the system SHALL initiate permanent deletion of account data, student files and versions, and cancel remaining Credits, except narrowly defined legal retention. UD-001 applies the captured Admin policy/cutoff; changing the current policy cannot alter an existing request. See ADR 0008.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-037–AC-039; FR-119.

### CASE-FR-120

Given An isolated synthetic fixture for F-14, with owner deletion/recovery; scoped policy admin; narrow lawful purge, the stated release mode and explicit enabled/disabled G-LEGAL/G-RESTORE/G-PROVIDER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Retry deletion with lawful retention exception and restored backup replay.

Then: Deletion execution, retention exceptions and backup lifecycle SHALL be documented, recorded and retryable without re-enabling service implicitly.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-037–AC-039; FR-120.

### CASE-FR-121

Given An isolated synthetic fixture for F-14, with owner deletion/recovery; scoped policy admin; narrow lawful purge, the stated release mode and explicit enabled/disabled G-LEGAL/G-RESTORE/G-PROVIDER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Inspect launch-facing legal/AI/source disclosures under missing signoff.

Then: The platform SHALL publish suitable Terms of Use, Privacy Policy and AI-use disclosures, including admissions non-guarantee and lawful source/extension behavior, before launch.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-037–AC-039; FR-121.

### CASE-FR-122

Given An isolated synthetic fixture for F-15, with typed fenced worker; no arbitrary owner impersonation, the stated release mode and explicit enabled/disabled G-HOSTING/G-PROVIDER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Poll identity/status for a long source/file/extraction/generation job.

Then: Long-running document generation, extraction, source monitoring and other intensive workflows SHALL expose trackable job identity and status.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-040–AC-041; FR-122.

### CASE-FR-123

Given An isolated synthetic fixture for F-15, with typed fenced worker; no arbitrary owner impersonation, the stated release mode and explicit enabled/disabled G-HOSTING/G-PROVIDER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Crash/retry past bounded handler policy without claiming successful output.

Then: Jobs SHALL use bounded retries, visible failure outcomes and operational monitoring without claiming a successful result before it exists.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-040–AC-041; FR-123.

### CASE-FR-124

Given An isolated synthetic fixture for F-15, with typed fenced worker; no arbitrary owner impersonation, the stated release mode and explicit enabled/disabled G-HOSTING/G-PROVIDER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Replay a callback after its irreversible effect committed.

Then: Repeated requests or callbacks SHALL NOT duplicate financial settlement, document publication or other irreversible effects.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-040–AC-041; FR-124.

### CASE-FR-125

Given An isolated synthetic fixture for F-15, with typed fenced worker; no arbitrary owner impersonation, the stated release mode and explicit enabled/disabled G-HOSTING/G-PROVIDER branches. Authentication/public paths use the corresponding unauthenticated fixture.

When: Fail an external integration while previously confirmed student data exists.

Then: A failed external integration/job SHALL preserve already confirmed student data, surface a recoverable explanation and allow an appropriate manual or later retry path.

Evidence: owner-scoped persisted state and response/status/audit for this feature; compare stable operation/event/version IDs, not analytics assertions. Also run the distinct-owner, stale-version, duplicate-delivery and missing-gate variants relevant to this action. Source: AC-040–AC-041; FR-125.

## Per-NFR verification paths

### CASE-NFR-001

Given the synthetic fixture and configured policy for Security, when the corresponding deployment/integration/adversarial measurement is performed, then verify: HTTPS/TLS for client and service traffic carrying credentials or user data; reject insecure production access. Record commands, measured result and approved target. A source TBD value is an unresolved decision/G-MEASURE, not a guessed threshold or a passed test.

### CASE-NFR-002

Given the synthetic fixture and configured policy for Security, when the corresponding deployment/integration/adversarial measurement is performed, then verify: Encrypt stored sensitive files/data; use access-scoped file access and safe link expiry; test unauthorized access rejection. Record commands, measured result and approved target. A source TBD value is an unresolved decision/G-MEASURE, not a guessed threshold or a passed test.

### CASE-NFR-003

Given the synthetic fixture and configured policy for Security, when the corresponding deployment/integration/adversarial measurement is performed, then verify: Enforce authorization on server for all endpoints and objects, including files, application versions, payments and support tickets. Record commands, measured result and approved target. A source TBD value is an unresolved decision/G-MEASURE, not a guessed threshold or a passed test.

### CASE-NFR-004

Given the synthetic fixture and configured policy for Admin security, when the corresponding deployment/integration/adversarial measurement is performed, then verify: MFA enforced for all Admin sign-ins before launch; denied sign-ins cannot reach protected operations. Record commands, measured result and approved target. A source TBD value is an unresolved decision/G-MEASURE, not a guessed threshold or a passed test.

### CASE-NFR-005

Given the synthetic fixture and configured policy for Abuse control, when the corresponding deployment/integration/adversarial measurement is performed, then verify: Rate-limit high-risk endpoints/AI consumption and detect anomalous retry/credit-grant patterns; thresholds [TBD]. Record commands, measured result and approved target. A source TBD value is an unresolved decision/G-MEASURE, not a guessed threshold or a passed test.

### CASE-NFR-006

Given the synthetic fixture and configured policy for Uploads, when the corresponding deployment/integration/adversarial measurement is performed, then verify: Validate MIME/content, block unsafe formats or scanned threats, apply configurable max size and storage quota. Record commands, measured result and approved target. A source TBD value is an unresolved decision/G-MEASURE, not a guessed threshold or a passed test.

### CASE-NFR-007

Given the synthetic fixture and configured policy for Secrets, when the corresponding deployment/integration/adversarial measurement is performed, then verify: Never store or log student third-party portal passwords, OTP/MFA values, payment credentials or unrestricted document contents in telemetry. Record commands, measured result and approved target. A source TBD value is an unresolved decision/G-MEASURE, not a guessed threshold or a passed test.

### CASE-NFR-008

Given the synthetic fixture and configured policy for Financial integrity, when the corresponding deployment/integration/adversarial measurement is performed, then verify: Concurrent and duplicate transactions must not create duplicate accepted charges, grants or payment approvals. Record commands, measured result and approved target. A source TBD value is an unresolved decision/G-MEASURE, not a guessed threshold or a passed test.

### CASE-NFR-009

Given the synthetic fixture and configured policy for Auditability, when the corresponding deployment/integration/adversarial measurement is performed, then verify: Retain append-only financial history and protected security/admin events; verify actors and operation IDs. Record commands, measured result and approved target. A source TBD value is an unresolved decision/G-MEASURE, not a guessed threshold or a passed test.

### CASE-NFR-010

Given the synthetic fixture and configured policy for Privacy, when the corresponding deployment/integration/adversarial measurement is performed, then verify: Explicit, separately scoped AI file-processing consent; verify processor policy forbids training without separate permission. Record commands, measured result and approved target. A source TBD value is an unresolved decision/G-MEASURE, not a guessed threshold or a passed test.

### CASE-NFR-011

Given the synthetic fixture and configured policy for Privacy, when the corresponding deployment/integration/adversarial measurement is performed, then verify: Apply data minimization, purpose restriction and legally validated retention and subject-request workflows. Record commands, measured result and approved target. A source TBD value is an unresolved decision/G-MEASURE, not a guessed threshold or a passed test.

### CASE-NFR-012

Given the synthetic fixture and configured policy for Deletion, when the corresponding deployment/integration/adversarial measurement is performed, then verify: Enforce 30-day account recovery semantics; document hard-deletion and backup expiry behavior [TBD]. Record commands, measured result and approved target. A source TBD value is an unresolved decision/G-MEASURE, not a guessed threshold or a passed test.

### CASE-NFR-013

Given the synthetic fixture and configured policy for Localization, when the corresponding deployment/integration/adversarial measurement is performed, then verify: All student and Admin core flows usable in Arabic RTL and English LTR, including dates, mixed-language names and numeric values. Record commands, measured result and approved target. A source TBD value is an unresolved decision/G-MEASURE, not a guessed threshold or a passed test.

### CASE-NFR-014

Given the synthetic fixture and configured policy for Responsive, when the corresponding deployment/integration/adversarial measurement is performed, then verify: Web core features SHALL function on contemporary mobile and desktop viewports; browser-extension platform coverage documented separately [TBD]. Record commands, measured result and approved target. A source TBD value is an unresolved decision/G-MEASURE, not a guessed threshold or a passed test.

### CASE-NFR-015

Given the synthetic fixture and configured policy for Accessibility, when the corresponding deployment/integration/adversarial measurement is performed, then verify: Forms, major dialogs and navigation operable using keyboard; labels readable to assistive technologies and appropriate contrast; exact conformance target [TBD]. Record commands, measured result and approved target. A source TBD value is an unresolved decision/G-MEASURE, not a guessed threshold or a passed test.

### CASE-NFR-016

Given the synthetic fixture and configured policy for UX transparency, when the corresponding deployment/integration/adversarial measurement is performed, then verify: Mark AI suggestions, verification dates, unknown eligibility, paid Credit quotations and irreversible actions conspicuously. Record commands, measured result and approved target. A source TBD value is an unresolved decision/G-MEASURE, not a guessed threshold or a passed test.

### CASE-NFR-017

Given the synthetic fixture and configured policy for Availability, when the corresponding deployment/integration/adversarial measurement is performed, then verify: Define and measure uptime/SLO after hosting and operational baseline tests; target [TBD] before launch. Record commands, measured result and approved target. A source TBD value is an unresolved decision/G-MEASURE, not a guessed threshold or a passed test.

### CASE-NFR-018

Given the synthetic fixture and configured policy for Performance, when the corresponding deployment/integration/adversarial measurement is performed, then verify: Benchmark search, matching, extraction, document export and browser fill with a realistic dataset; target distributions [TBD]. Record commands, measured result and approved target. A source TBD value is an unresolved decision/G-MEASURE, not a guessed threshold or a passed test.

### CASE-NFR-019

Given the synthetic fixture and configured policy for Job stability, when the corresponding deployment/integration/adversarial measurement is performed, then verify: User-visible status for long jobs and bounded retries without duplicate financial or publication side effects. Record commands, measured result and approved target. A source TBD value is an unresolved decision/G-MEASURE, not a guessed threshold or a passed test.

### CASE-NFR-020

Given the synthetic fixture and configured policy for Fault tolerance, when the corresponding deployment/integration/adversarial measurement is performed, then verify: AI/source provider outage SHALL degrade safely with an error/manual fallback; never misreport success. Record commands, measured result and approved target. A source TBD value is an unresolved decision/G-MEASURE, not a guessed threshold or a passed test.

### CASE-NFR-021

Given the synthetic fixture and configured policy for Data recovery, when the corresponding deployment/integration/adversarial measurement is performed, then verify: Backup, restore validation, RPO/RTO and deletion-conformant backup retention documented [TBD] before launch. Record commands, measured result and approved target. A source TBD value is an unresolved decision/G-MEASURE, not a guessed threshold or a passed test.

### CASE-NFR-022

Given the synthetic fixture and configured policy for Maintainability, when the corresponding deployment/integration/adversarial measurement is performed, then verify: Modular domains and replaceable AI/search/storage providers; no mandatory microservices or framework lock-in. Record commands, measured result and approved target. A source TBD value is an unresolved decision/G-MEASURE, not a guessed threshold or a passed test.

### CASE-NFR-023

Given the synthetic fixture and configured policy for Observability, when the corresponding deployment/integration/adversarial measurement is performed, then verify: Monitor job failure, source freshness, SLA events, payment reconciliation and extension compatibility without unnecessary sensitive payloads. Record commands, measured result and approved target. A source TBD value is an unresolved decision/G-MEASURE, not a guessed threshold or a passed test.

### CASE-NFR-024

Given the synthetic fixture and configured policy for Testing, when the corresponding deployment/integration/adversarial measurement is performed, then verify: Automated/instrumented integration and adversarial tests cover RBAC, idempotency, AI grounding, account deletion and external-fill safety. Record commands, measured result and approved target. A source TBD value is an unresolved decision/G-MEASURE, not a guessed threshold or a passed test.

### CASE-NFR-025

Given the synthetic fixture and configured policy for Compatibility, when the corresponding deployment/integration/adversarial measurement is performed, then verify: Extension support is tied to a documented tested-browser/portal matrix; supported versions/sites [TBD] prior to launch. Record commands, measured result and approved target. A source TBD value is an unresolved decision/G-MEASURE, not a guessed threshold or a passed test.

### CASE-NFR-026

Given the synthetic fixture and configured policy for Legal, when the corresponding deployment/integration/adversarial measurement is performed, then verify: Terms/privacy/disclaimer/payment/source-use review approved for actual launch geography and involved providers. Record commands, measured result and approved target. A source TBD value is an unresolved decision/G-MEASURE, not a guessed threshold or a passed test.

### CASE-NFR-027

Given the synthetic fixture and configured policy for Service limits, when the corresponding deployment/integration/adversarial measurement is performed, then verify: Configurable quotas on uploads, AI and credits protect operations; actual values/periods [TBD], not implicit arbitrary caps. Record commands, measured result and approved target. A source TBD value is an unresolved decision/G-MEASURE, not a guessed threshold or a passed test.

### CASE-NFR-028

Given the synthetic fixture and configured policy for Integrity, when the corresponding deployment/integration/adversarial measurement is performed, then verify: Versioned provenance for scholarship criteria, match evaluation, price quotes, submitted files and status origins. Record commands, measured result and approved target. A source TBD value is an unresolved decision/G-MEASURE, not a guessed threshold or a passed test.

## Cross-cutting negative schedules

- A changes B's profile/file/operation/document/version/application/notification/ticket/MFA IDs: no data/capability/mutation; Admin library returns 403+audit, other cross-owner reads use 404.
- Race signup/Google link and finalizers/releases: one grant, one accepted result/debit/terminal witness, correct wallet/day/global conservation; uncertain send never automatically repeats.
- Revoke consent/provider approval/account lifecycle before intent and before result acceptance: current gates apply while frozen task tuple stays unchanged; already-in-flight recall is not promised.
- Fail scanner/audit/quota meter: no file acceptance, no sensitive unaudited read, no unsafe egress. Stage/orphan bytes remain counted until confirmed cleanup.
- Admin changes recovery policy after request confirmation: old request deadline/policy remains; new request takes new policy; exact cutoff restore denied, purge/restore lock arbitration and DST gap/fold tested per ADR 0008.
- Extension sees OTP/password/Submit: no read/no click/no inferred Submitted state. Payment evidence without independent funds verification never grants Credits; Beta purchase endpoints absent/disabled.
- Submitted artifact edit/restore/delete: original snapshot frozen for ordinary writes; restoration creates new current version; lawful approved erasure still works.

Detailed database crash/barrier schedules T03-01..21 are in [migration sequencing](../architecture/migration-sequencing.md); reference them when implementing the backlog, not as passed tests.
