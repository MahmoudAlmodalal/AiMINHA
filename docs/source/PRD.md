# MinhaAI — Product Requirements Document

| Document control | Value |
|---|---|
| Product | **MinhaAI** (مِنحة AI) |
| Document type | Product Requirements Document (PRD) — web platform and companion browser extension |
| Version | **3.0.0 — consolidated Grill Me baseline** |
| Prepared | **14 October 2026** |
| Language | English; product interfaces will support Arabic and English |
| Status | **Requirements baseline; implementation conditional on P0 decisions and launch gates** |
| Target release | **Advanced MVP**, built in successive internal increments before general release |
| Product owner approval of this revision | **Not yet recorded** |

**Source-of-truth and decision convention.** This document consolidates the original MinhaAI requirements, the prior consolidated `MinhaAI_PRD.md` requirements record, and Grill Me decisions **D01–D67**. **[P]** means a direct product-owner selection in D01–D46; **[D]** means an analyst recommendation ratified by the owner's general delegation for D47–D67; **[A]** means a nonbinding analysis/implementation assumption pending verification; **[TBD]** means a decision or external fact remains open. The attached record `MinhaAI_Decisions_47-67-1.md` expressly distinguishes [D] from individual owner answers. Nothing marked [A] or [TBD] is an approved business rule. Requirement IDs are unique and intended for traceability, not a prescription for component structure.

**Interpretation of requirement language.** **SHALL** = required for the agreed Advanced MVP unless explicitly conditional; **MAY** = optional or constrained by external feasibility; **MUST NOT** = prohibited. A requirement marked `conditional` SHALL only be delivered when the dependency stated in it is validated. Where a release-blocking external decision is pending, engineering SHALL obtain approval rather than silently invent a default. References to AI or RAG specify product behavior, not a mandatory vendor or framework.

## 1. Product Overview

MinhaAI is a bilingual, student-centered SaaS web application for finding trustworthy scholarships and preparing applications. It combines **admin-reviewed scholarship ingestion**, searchable opportunities, **rule-based eligibility plus explainable AI/RAG matching**, student profiles, tailored document generation, an application tracker, and an optional browser extension to **assist with form completion** on allowed third-party portals. Freemium access is complemented by prepaid **Credits**, acquired through locally supported **manual payments** reviewed by administrators. A support desk combines a 24/7 AI assistant with human support during configurable working hours.

**Who and where:** initial target is **Palestinian students aged 18 or older**, seeking **Bachelor's, Master's, or PhD** scholarships; geographic expansion may follow. Students can interact in Arabic (RTL) or English (LTR), and may select the language of each generated document independently.

**Core promise:** make scholarship discovery and preparation more accurate, transparent, less repetitive, and easier to track. MinhaAI **does not determine admissions, guarantee acceptance, establish eligibility on behalf of a grantor, or submit third-party applications automatically**.

**Business model:** a free search/profile baseline, limited initial AI usage supported by a one-time registration grant, and administrator-configured paid Credit packages and per-service prices. Actual prices, quantities, currencies, eligible chargeable operations, payment destinations and financial/legal policy text are **[TBD]**.

**Technology preference [D67]:** maintainable **modular architecture**, replaceable AI, search and storage providers, and bounded agent-like workflows. **No implementation technology, cloud provider, LLM, vector store, payment gateway, or microservices approach has been approved as binding**. Final stack belongs in subsequent architecture decisions. **Competitors/reference products: [TBD]**; none was approved as a benchmark in the interview.

## 2. Problem Statement

1. Scholarship information is fragmented across universities, foundations, and other sources, and may expire or change without warning.
2. Applicants struggle to interpret variable eligibility conditions, distinguish known disqualifiers from missing information, and identify genuinely relevant opportunities.
3. Applicants repeatedly enter the same academic/personal facts into documents and third-party forms, increasing preparation time and mistakes.
4. Application packages have changing requirements, versions, deadlines, and statuses that are difficult to track reliably.
5. Students in the initial target market may need accessible, understandable payment methods for AI assistance rather than an assumed international card subscription.
6. AI systems can hallucinate credentials or imply admission probabilities, and browser automation can mishandle sensitive information unless constrained.

**Opportunity:** provide a trustworthy, reviewable workflow from discovery through preparation and student-confirmed application, without overstating automation or certainty.

## 3. Product Goals

| ID | Product goal | Outcome / measurement approach |
|---|---|---|
| G-01 | Surface current, traceable scholarship opportunities | Approved listings, last-verification age, valid-source ratio, substantiated error reports |
| G-02 | Improve understanding of eligibility and fit | Evaluations with explicit eligibility status, evidence, missing fields, explanations, and score version |
| G-03 | Reduce preparation effort | Time to complete a usable profile/document package; generation/export completion |
| G-04 | Keep students in control of applications | Student-confirmed submissions; correctly frozen submitted document versions |
| G-05 | Make paid AI operations predictable and fair | Upfront quoted Credits, balanced ledger, exactly-once settlements, payment disputes |
| G-06 | Build reliability and privacy into assisted workflows | Privacy incidents, access-control failures, extension failures, recoverable AI jobs |
| G-07 | Support students effectively | Human first-response SLA adherence (working hours), ticket resolution and ratings |
| G-08 | Validate product-market and operational feasibility in Palestine | Closed pilot feedback, support load, unit economics and extension compatibility |

**KPIs are defined in Section 22; numeric targets are not fabricated.** Self-reported scholarship acceptance can be observed but is not a promise or sole measure of platform quality.

## 4. Non-Goals

**Explicitly excluded from the agreed Advanced MVP [P/D]:**

- Automatic final submission of scholarship applications on third-party portals, or treating successful form fill as evidence of submission.
- Circumventing CAPTCHA, OTP/MFA, login security, website terms, or unauthorized third-party interfaces; collecting third-party passwords or OTP codes.
- Guaranteeing compatibility with every scholarship portal, a student's acceptance, or that a Match Score is an admission probability.
- Subscription billing (monthly/annual) or an automatic card-payment gateway in place of the agreed **manual local payment review**.
- Marketing/product alerts via email, WhatsApp, or Web Push; product notifications are **in-app only**. Essential account verification/recovery emails are an authentication exception.
- A conversational AI-powered document *editing* interface; the MVP includes **AI generation followed by manual editing**.
- Accounts for people below 18 and formal roles beyond **Student** and **Admin**.
- Training AI models on student files without separately obtained explicit permission.

**Not committed, rather than rejected:** native mobile apps, additional locales, geographically expanded launch, officially integrated third-party application status feeds, international payment methods and more elaborate analytics. None may be silently added to the MVP.

## 5. Target Users

| Segment | MVP position | Motivation and constraints |
|---|---|---|
| Palestinian student aged 18+ seeking Bachelor's aid | Primary | Secondary-school qualifications, country/citizenship and funding eligibility, accessible instructions |
| Palestinian student aged 18+ seeking Master's aid | Primary | University transcript, grades/scales, language proof, tailored statements and deadlines |
| Palestinian student aged 18+ seeking PhD aid | Primary | Specialization/research fit, evidence-heavy eligibility, application-document variation |
| Platform administrator | Internal operator | Approves listings and changes, manages prices/payments/support/security and performance |
| Broader Arab/global applicant | Future expansion | Localization, compliance and source coverage to be evaluated after initial pilot |

The age requirement is calculated from **self-declared date of birth** at registration; this does not constitute government-identity verification.

## 6. User Personas

| Persona | Situation / jobs-to-be-done | Pain points | Expected experience |
|---|---|---|---|
| UXP-01 — Prospective undergraduate | First-time scholarship applicant with school records | Unfamiliar eligibility language; uncertain funding scope | Simple profile onboarding; trustworthy search; reasons for eligibility |
| UXP-02 — Master's candidate | Degree holder applying to several institutions | Repeated CV/letter customization; multiple deadline rounds | Reusable profile and versioned documents per scholarship |
| UXP-03 — Research/PhD applicant | Specialized study/research plans and documentation | Hard-to-interpret fit; incomplete evidence | Explainable matching, explicit unknowns, tailored drafts under applicant review |
| UXP-04 — MinhaAI admin | Oversees sources, quality, financial cases and support | False listings, duplicate payment proofs, support urgency | Review queues, audit trails, payment verification, adjustable SLA rules |

These are **behavioral personas [A]**, not invented demographic research findings or separate roles.

## 7. User Needs

| Need ID | Need | User | Validation signal |
|---|---|---|---|
| UN-01 | Build a verified-by-student academic profile once | Student | Profile fields require confirmation before trusted use |
| UN-02 | Find scholarships with sources and freshness metadata | Student | Every published result links to its source and last verification |
| UN-03 | Understand hard eligibility versus personalized relevance | Student | Three-state eligibility separate from score |
| UN-04 | Prepare truthful, tailored documents and export them | Student | Manual review and valid PDF/DOCX |
| UN-05 | Save opportunities, requirements, versions and status | Student | Tracker and history preserve applicant intent |
| UN-06 | Reuse confirmed facts on allowed external forms | Student | Extension displays values for review; no auto-submit |
| UN-07 | See and control AI costs and manual payment outcomes | Student | Quote, wallet, payment state and no duplicate debit |
| UN-08 | Receive relevant updates without external messaging | Student | In-app notification center with destinations |
| UN-09 | Resolve issues with human escalation when necessary | Student | Ticket history, AI → Admin escalation, measurable first reply |
| UN-10 | Operate a safe, auditable service | Admin | Moderation, access control, durable payment and source records |

## 8. User Stories

| ID | User story | Feature |
|---|---|---|
| US-001 | As an adult student, I want to register with email/password or Google so that I can use the service securely. | F-01 |
| US-002 | As a student, I want to create a profile manually or extract facts from my CV and approve them before use. | F-02 |
| US-003 | As an admin, I want to review an imported scholarship before students can discover it. | F-03 |
| US-004 | As a student, I want to search and filter trustworthy scholarships by education level, discipline, funding and deadline. | F-04 |
| US-005 | As a student, I want to see eligible, unknown and ineligible criteria separately from a fit score. | F-04 |
| US-006 | As a student with an incomplete profile, I want a clearly qualified partial match rather than false certainty. | F-04 |
| US-007 | As a student, I want a truthful scholarship-specific CV or essay, edited by me and exported to PDF/DOCX. | F-05 |
| US-008 | As a student, I want to compare/revert revisions while preserving the exact version attached to a submitted application. | F-06 |
| US-009 | As a student, I want to save scholarships, organize requirements and confirm submissions myself. | F-07 |
| US-010 | As a student, I want a browser extension to propose and fill allowed fields only after explicit review. | F-08 |
| US-011 | As a student, I want a Credit price before using a chargeable service and no debit for technical failure. | F-09 |
| US-012 | As a student, I want to purchase a Credit package via locally available transfer and track admin review. | F-10 |
| US-013 | As a student, I want relevant in-app notices about scholarships, applications, payments and tickets. | F-11 |
| US-014 | As a student, I want 24/7 AI support and human escalation for complex or sensitive cases. | F-12 |
| US-015 | As an admin, I want configurable business-hour SLA, escalation and operational reporting. | F-12/F-13 |
| US-016 | As a student, I want to delete my account, recover it within 30 days, and know what data is retained. | F-14 |
| US-017 | As an admin, I want to review scholarship data reports and suspend unsafe listings. | F-03/F-13 |
| US-018 | As an admin, I want to detect duplicate transfer references and safely reconcile Credits. | F-09/F-10 |
| US-019 | As a student, I want to see a tracked progress/error state when AI or file processing takes time. | F-15 |

## 9. MVP Scope

**Agreed release definition:** an **Advanced MVP**; “MVP” does **not** authorize removing previously approved capabilities. Delivery is divided into internal phases for risk reduction, with the complete agreed scope validated before general availability [P12, D65].

| Scope group | Required capabilities | Release priority |
|---|---|---|
| Student foundation | 18+ registration, email/password, Google sign-in, profile, explicit AI consent, bilingual interface | Must Have |
| Scholarship intelligence | Permitted hybrid acquisition, Admin approval and monitoring, reporting, search, filters, funding and deadline information, rule-based eligibility + explainable AI/RAG score | Must Have |
| Application workflow | Save scholarships, checklist, tracker, student-confirmed submission, document/version association and in-app reminders | Must Have |
| Document workflow | Four agreed document types, trustworthy profile data, manual editor, PDF/DOCX, library, version comparison/revert, submitted-version freeze | Must Have |
| Browser assistance | Approved-site compatibility, best-effort analysis of other permitted forms, explicit fill, field review, manual fallback and no auto-submit | Must Have |
| Monetization | Free core usage, one-time registration Credits, variable service pricing, immutable ledger, reserve/settle/release, manual local payments, Admin adjustments | Must Have |
| Communication | In-app alerts, AI-first tickets, handoff to human, adjustable working-hours SLA, rating and history | Must Have |
| Operations and trust | Admin console, MFA, audits, analytics, account deletion/recovery, security, lawful retention policies | Must Have |

**Phase boundaries do not change scope.** Required Phase 3 features (extension/support) cannot be removed from the stated general-release Advanced MVP without a new owner-approved scope decision. Pilot release may intentionally use a controlled, incomplete feature set with its own published eligibility.

**External conditionality:** source ingestion and form-filling operate only where legal, technically feasible and tested; “official status integration if available” [P09] is a conditional enhancement, **not** guaranteed for launch. Portal allowlist, data sources, payment destinations and SLA numbers are [TBD].

**Definition of general-release readiness:** P0 open questions closed; required feature acceptance tests pass; tested third-party coverage documented; privacy/security and financial reconciliation gates passed; closed Palestinian-student pilot reviewed; product owner authorizes release.

## 10. Core Features

Each feature card references globally defined requirements (Section 11), business rules (Section 11), edge cases (Section 18), error states (Section 19), and detailed Given/When/Then acceptance cases (Section 23). **Feature IDs and priorities apply to the agreed Advanced MVP**; [P] and [D] trace to the interview, not to the individual examples in this PRD.

### F-01 — Registration, Identity and Age Gate

| Field | Specification |
|---|---|
| Purpose | Establish a secure adult student identity and grant initial Credits exactly once. |
| Story | US-001 |
| Functional requirements | FR-001–FR-007 |
| Business rules | BR-001–BR-004, BR-027 |
| Edge cases | EC-001, EC-002 |
| Error states | ERR-001, ERR-002 |
| Acceptance criteria | AC-001, AC-002, AC-003 |
| Priority | **Must Have** |

**Behavior:** email/password plus Google authentication; age checked on every sign-up path using birth date; verified/eligible account obtains initial grant once; existing accounts are linked only through safe identity proof, not matching an email string alone. Recoverable sessions and password reset supported. Admin sign-in requires MFA prior to release.

### F-02 — Student Profile and Consent-Based Extraction

| Field | Specification |
|---|---|
| Purpose | Create a reusable, student-approved source of applicant facts. |
| Story | US-002 |
| Functional requirements | FR-008–FR-014 |
| Business rules | BR-005, BR-006, BR-016 |
| Edge cases | EC-003, EC-004 |
| Error states | ERR-003, ERR-004 |
| Acceptance criteria | AC-004, AC-005 |
| Priority | **Must Have** |

**Behavior:** the student may complete fields manually, or explicitly consent to AI extraction from uploaded CV/credentials; proposed extracted values remain untrusted until reviewed. Missing fields are shown; stage-specific education fields are conditional, but missing facts are never invented.

### F-03 — Scholarship Sources, Approval, Monitoring and Reports

| Field | Specification |
|---|---|
| Purpose | Maintain a trustworthy, traceable and monitored catalog. |
| Story | US-003, US-017 |
| Functional requirements | FR-015–FR-024 |
| Business rules | BR-007–BR-010 |
| Edge cases | EC-005, EC-006, EC-007 |
| Error states | ERR-005, ERR-006 |
| Acceptance criteria | AC-006, AC-007, AC-008 |
| Priority | **Must Have** |

**Behavior:** ingest from permitted sources, detect duplicates and material changes, queue for Admin approval, record source/last check, and allow students to report incorrect information. A dangerous or unverifiable listing can be suspended pending documented review; publication and material revisions are not automatically approved.

### F-04 — Scholarship Search, Eligibility and Explainable Matching

| Field | Specification |
|---|---|
| Purpose | Match students to relevant scholarships without confusing fit with acceptance eligibility. |
| Story | US-004, US-005, US-006 |
| Functional requirements | FR-025–FR-033 |
| Business rules | BR-011–BR-014 |
| Edge cases | EC-004, EC-008, EC-009 |
| Error states | ERR-007, ERR-008 |
| Acceptance criteria | AC-009, AC-010, AC-011, AC-012 |
| Priority | **Must Have** |

**Behavior:** text/semantic search and decision-defined filters; mandatory rules yield **Eligible**, **Undetermined**, or **Ineligible** with evidence/missing data. AI/RAG provides an independently explained match score, confidence and criterion contributions with rule/weight version. A hard failure cannot be overridden by a high score. Partial profiles get qualified results.

### F-05 — AI Document Creation, Manual Editing and Export

| Field | Specification |
|---|---|
| Purpose | Generate scholarship-tailored, reviewable content grounded in approved applicant facts. |
| Story | US-007 |
| Functional requirements | FR-034–FR-042 |
| Business rules | BR-015, BR-016, BR-029–BR-033 |
| Edge cases | EC-010, EC-011, EC-012 |
| Error states | ERR-009, ERR-010 |
| Acceptance criteria | AC-013, AC-014, AC-015 |
| Priority | **Must Have** |

**Behavior:** create **CV, Motivation Letter, Personal Statement, Scholarship Essays** in a student-selected language; no fabricated qualifications; flag statements requiring confirmation; quote chargeable work before execution, then allow manual preview/edit/approval and PDF/DOCX export. AI conversational document re-editing is excluded.

### F-06 — Document Library, Versions and Submission Freeze

| Field | Specification |
|---|---|
| Purpose | Reuse and organize documents while preserving exactly what was submitted. |
| Story | US-008 |
| Functional requirements | FR-043–FR-050 |
| Business rules | BR-017, BR-018, BR-051 |
| Edge cases | EC-013, EC-014 |
| Error states | ERR-011, ERR-012 |
| Acceptance criteria | AC-016, AC-017 |
| Priority | **Must Have** |

**Behavior:** central uploaded/generated library, scholarship-specific variants, linked checklists, revision history, compare and restore. Restoring creates a new current revision; a version connected to a student-confirmed submitted application is immutable to normal editing but not exempt from lawful deletion.

### F-07 — Saved Scholarships and Application Tracker

| Field | Specification |
|---|---|
| Purpose | Give the student an accurate history of preparation, submission and reported outcomes. |
| Story | US-009 |
| Functional requirements | FR-051–FR-058 |
| Business rules | BR-019–BR-021 |
| Edge cases | EC-015, EC-016 |
| Error states | ERR-013 |
| Acceptance criteria | AC-018, AC-019 |
| Priority | **Must Have** |

**Behavior:** saved listings, one or more application records where justified by scholarship rounds (uniqueness policy [TBD]), requirements and missing files, history and student-reported status. The student alone confirms external submission. Official status updates are conditional on a lawful, documented integration and must be source-labeled.

### F-08 — Browser Extension and Assisted Third-Party Autofill

| Field | Specification |
|---|---|
| Purpose | Reduce redundant data entry on eligible external portals while preserving student control. |
| Story | US-010 |
| Functional requirements | FR-059–FR-068 |
| Business rules | BR-022–BR-025 |
| Edge cases | EC-017, EC-018, EC-019 |
| Error states | ERR-014, ERR-015 |
| Acceptance criteria | AC-020, AC-021, AC-022 |
| Priority | **Must Have** |

**Behavior:** extension operates on a user-initiated supported/permitted page, shows values and incomplete fields, requests consent for sensitive values, fills without submitting, and offers a manual fallback after bounded retry. No password/OTP scraping or CAPTCHA bypass. Other permitted sites may be attempted on a best-effort basis, not marketed as guaranteed compatibility.

### F-09 — Credit Wallet, Pricing and Exactly-Once Accounting

| Field | Specification |
|---|---|
| Purpose | Finance configurable AI services predictably, with auditable non-expiring balances. |
| Story | US-011, US-018 |
| Functional requirements | FR-069–FR-079 |
| Business rules | BR-026–BR-033 |
| Edge cases | EC-020, EC-021 |
| Error states | ERR-016, ERR-017 |
| Acceptance criteria | AC-023, AC-024, AC-025 |
| Priority | **Must Have** |

**Behavior:** free baseline, one-time initial grant, Admin-created packages and service pricing; quote snapshot; reserve Credits before execution, settle exactly once on success, release/refund reserved Credits upon technical failure; ledger is append-only from application operations. No time-based Credit expiry, subject to final-account-deletion rule.

### F-10 — Manually Verified Local Payments

| Field | Specification |
|---|---|
| Purpose | Enable paid package purchases without assuming an automated international gateway. |
| Story | US-012, US-018 |
| Functional requirements | FR-080–FR-088 |
| Business rules | BR-034–BR-037 |
| Edge cases | EC-022, EC-023 |
| Error states | ERR-018, ERR-019 |
| Acceptance criteria | AC-026, AC-027, AC-028 |
| Priority | **Must Have** |

**Behavior:** the student selects a published package, transfers through an approved local method outside the platform and uploads proof/reference. Admin verifies **received funds**, not just an image, before adding Credits once; Admin may reject with recorded reason or request replacement evidence. Exact local rails, prices, receipt formats and currency remain [TBD].

### F-11 — In-App Notification Center

| Field | Specification |
|---|---|
| Purpose | Deliver actionable, non-duplicative updates without extra messaging channels. |
| Story | US-013 |
| Functional requirements | FR-089–FR-093 |
| Business rules | BR-038, BR-039 |
| Edge cases | EC-024 |
| Error states | ERR-020 |
| Acceptance criteria | AC-029, AC-030 |
| Priority | **Must Have** |

**Behavior:** read/unread status, deep links and user preferences for optional categories; scholarship deadline/source changes, application checklists, payment and support events. No product email, push or WhatsApp in the MVP; security/account email remains allowed.

### F-12 — AI/Human Support Ticketing and SLA

| Field | Specification |
|---|---|
| Purpose | Resolve student problems at any hour with responsible human escalation and transparent service windows. |
| Story | US-014, US-015 |
| Functional requirements | FR-094–FR-105 |
| Business rules | BR-040–BR-045 |
| Edge cases | EC-025, EC-026 |
| Error states | ERR-021, ERR-022 |
| Acceptance criteria | AC-031, AC-032, AC-033, AC-034 |
| Priority | **Must Have** |

**Behavior:** AI triages/responds 24/7 but escalates on request, low confidence, repeated failure, financial/sensitive topics or critical deadline. Human support operates in Admin-defined working hours; **first human response SLA** is priority-configurable and records warnings/escalations. Tickets have documented lifecycle, resolution/reopen and ratings. AI cannot authorize money movement or payment approval.

### F-13 — Admin Operations, Governance and Analytics

| Field | Specification |
|---|---|
| Purpose | Govern catalog quality, accounts, payments, support, score rules and system health. |
| Story | US-015, US-017, US-018 |
| Functional requirements | FR-106–FR-112 |
| Business rules | BR-046, BR-047 |
| Edge cases | EC-027 |
| Error states | ERR-023 |
| Acceptance criteria | AC-035, AC-036 |
| Priority | **Must Have** |

**Behavior:** protected admin views for source queue, reports, eligibility weights, user/account operations, packages/payment references, sensitive ledger adjustments, support schedules and dashboards. Sensitive actions are attributed and audited. Admin does not receive routine access to student document contents.

### F-14 — Privacy, Account Deletion and 30-Day Recovery

| Field | Specification |
|---|---|
| Purpose | Give students informed data control consistent with legitimate retention obligations. |
| Story | US-016 |
| Functional requirements | FR-113–FR-121 |
| Business rules | BR-048–BR-052 |
| Edge cases | EC-028, EC-029 |
| Error states | ERR-024, ERR-025 |
| Acceptance criteria | AC-037, AC-038, AC-039 |
| Priority | **Must Have** |

**Behavior:** documented processing consent; encrypted and access-controlled files; deletion preview; disabled account and frozen Credits for **30 days**; restore in window; after window begin irreversible deletion of documents/versions/linked data and cancel remaining Credits subject only to defined lawful records and backup policy. Exact retention and backup schedules remain [TBD].

### F-15 — Asynchronous AI, File and Source Jobs

| Field | Specification |
|---|---|
| Purpose | Make long-running work observable, retry-safe and economically consistent. |
| Story | US-019 |
| Functional requirements | FR-122–FR-125 |
| Business rules | BR-053, BR-054 |
| Edge cases | EC-030 |
| Error states | ERR-026 |
| Acceptance criteria | AC-040, AC-041 |
| Priority | **Must Have** |

**Behavior:** user-visible queued/running/completed/failed states where relevant; bounded retry; durable operation identity and progress visibility; recoverable failures without multiple debits or duplicated published actions. No arbitrary speed promises are committed before measurement.

## 11. Functional Requirements

The following are **MVP functional commitments** unless flagged conditional. Each operation SHALL enforce the role and ownership checks in Section 15. Product decisions and user-visible rules are explicitly collected below; component-level implementation is out of scope.

### 11.1 Identity and profile

| ID | Requirement | Priority / origin |
|---|---|---|
| FR-001 | The platform SHALL support student registration and authentication with email/password. | Must / P29 |
| FR-002 | The platform SHALL verify account email ownership through a secure, expiring verification process before the account receives the signup Credit grant. | Must / P29 |
| FR-003 | The platform SHALL support Google OAuth and SHALL require adequate identity proof before linking to an existing account; mere identical email text is insufficient to merge accounts. | Must / P29; detail A |
| FR-004 | Every new account registration path SHALL collect a date of birth, calculate age at registration and prevent activation if the declared age is below 18. | Must / P30–P31 |
| FR-005 | A successfully activated, eligible student account SHALL receive the configured free Credit grant once, without duplication through retry or account-linking. | Must / P13/P29 |
| FR-006 | Students SHALL be able to sign out and initiate secure password/account recovery, and inactive/deletion-pending accounts SHALL be unable to use authenticated product operations. | Must / operational safeguard |
| FR-007 | Admin accounts SHALL require MFA before general release and SHALL support secure session invalidation and audit of sensitive authentication events. | Must / D60 |
| FR-008 | A profile SHALL support student name/identity and contact information, nationality/residency, educational level, field, institution, GPA and scale, language information, and preferred study interests. | Must / D52 |
| FR-009 | Profile forms SHALL adapt education-related fields and validation to Bachelor's, Master's or PhD applicants; the exact obligatory field schema is [TBD]. | Must / P16/D52 |
| FR-010 | Students SHALL be able to add, correct and save their profile facts manually without using AI extraction. | Must / P03 |
| FR-011 | Students SHALL be able to upload supported CV/credentials/transcript artifacts for optional extraction, subject to configured format/size checks and malware scanning. | Must / P03/D54 |
| FR-012 | The platform SHALL capture explicit consent before sending uploaded personal files to an AI processor and SHALL offer a manual path if that consent is declined. | Must / P14/D53 |
| FR-013 | Extracted facts SHALL be shown as proposed values with source/uncertainty indicators and SHALL become trusted student profile values only after student review/confirmation. | Must / P03 |
| FR-014 | Incomplete or unverified profile data SHALL remain visibly missing/unconfirmed and SHALL never be silently fabricated to complete eligibility, documents, or forms. | Must / P32/D52 |

### 11.2 Scholarship catalog and recommendation

| ID | Requirement | Priority / origin |
|---|---|---|
| FR-015 | Admin SHALL configure and manage scholarship sources and their permitted ingestion methods. | Must / P01/D66 |
| FR-016 | The platform SHALL support hybrid permitted automatic import plus Admin-created/edited listings, capturing raw source link and extraction/check timestamps. | Must / P01 |
| FR-017 | Newly imported scholarships SHALL remain unpublished until an Admin has reviewed and approved them. | Must / P01 |
| FR-018 | Admin SHALL be able to approve, reject, revise, suspend, archive and restore scholarship listings with an attributable history. | Must / P08/P17 |
| FR-019 | The platform SHALL detect likely duplicates and flag uncertain entries for Admin review before publication; merging logic [TBD]. | Must / P17; method A |
| FR-020 | Background monitoring SHALL detect materially changed eligibility, deadlines, funding and links and route significant changes to an Admin before publication. | Must / P17 |
| FR-021 | Each visible listing SHALL show an attributable source and latest verification date/status; the catalog SHALL distinguish unverified from verified information. | Must / D49–D50 |
| FR-022 | Scholarships SHALL represent full/partial funding, waivers and financial aid, and SHALL show unknown funding details as unknown rather than estimated. | Must / P35 |
| FR-023 | Scholarships SHALL represent single, multiple, rolling or unknown application rounds, with known deadline timezone and uncertainty explicitly shown. | Must / P36 |
| FR-024 | Students SHALL be able to submit an incorrect-information report from a scholarship page; Admin SHALL review evidence, log an outcome and suspend a materially risky listing when warranted. | Must / D49 |
| FR-025 | Students SHALL search the approved catalog through text and semantic search with a clear zero-results state. | Must / D50 |
| FR-026 | Filters SHALL cover education level, discipline, country, funding, eligibility, language, deadline and application/registration state; sorting SHALL include relevance and deadline when meaningful. | Must / D50 |
| FR-027 | The scholarship detail SHALL present provider, source, funding, criteria, required documents, verified deadline/round, submission link and last verification. | Must / P04/D50 |
| FR-028 | The platform SHALL evaluate known mandatory eligibility conditions separately from relevance scoring and return **Eligible**, **Undetermined** or **Ineligible** with reasons/evidence. | Must / P33/D51 |
| FR-029 | A missing fact or unverified scholarship requirement SHALL yield **Undetermined** for that criterion and SHALL NOT count as satisfied. | Must / P32/D51 |
| FR-030 | The platform SHALL compute an explainable AI/RAG Match Score with criterion contributions, confidence/limitations and a clear disclaimer that it is not admission likelihood. | Must / P04/P34 |
| FR-031 | Admin SHALL be able to manage matching weights/rules with controlled versions; evaluations SHALL record the applicable ruleset/weight version and timestamp. | Must / P34/D51 |
| FR-032 | Results SHALL prioritize eligible matches while permitting users to inspect unknown/ineligible options and explanations; a failed mandatory criterion SHALL never become “Eligible” via a high score. | Must / P33 |
| FR-033 | An incomplete student profile SHALL permit qualified partial matching, identify missing inputs and avoid a falsely definitive score or eligibility conclusion. | Must / P32 |

### 11.3 Documents, applications and extension

| ID | Requirement | Priority / origin |
|---|---|---|
| FR-034 | The system SHALL offer AI drafts for **CV**, **Motivation Letter**, **Personal Statement** and **Scholarship Essays**. | Must / P07 |
| FR-035 | Drafting SHALL use trusted student-confirmed facts and, where relevant, the selected scholarship's reviewed criteria; unsupported credentials SHALL not be asserted. | Must / D53 |
| FR-036 | Students SHALL select the output language independently from their interface language; known scholarship language requirements SHALL be clearly shown. | Must / P06 |
| FR-037 | Statements requiring student verification SHALL be marked, withheld or clarified before final approval, rather than silently treated as factual. | Must / D53 |
| FR-038 | When a generation is chargeable, the platform SHALL show the exact Credit quote and obtain confirmation before reserving funds or starting work. | Must / P13/P28 |
| FR-039 | Students SHALL review a preview and SHALL be able to edit generated documents manually before marking them ready. | Must / P23/D53 |
| FR-040 | Students SHALL be able to export approved document content to usable PDF and DOCX files. | Must / P24 |
| FR-041 | Generation SHALL expose status/progress and a visible failed/retry state without inventing completed output. | Must / D63 |
| FR-042 | The MVP document editor SHALL provide essential manual text/format editing, NOT AI chat-based editing. | Must / P23, explicit exclusion |
| FR-043 | A central library SHALL list student-owned uploaded and generated documents, with organization, rename and controlled deletion. | Must / P37 |
| FR-044 | The platform SHALL support scholarship-specific document variants and attach exact document versions to application requirements. | Must / P37 |
| FR-045 | Each application SHALL show required, attached and missing document items based on currently approved requirement information. | Must / P37 |
| FR-046 | Saving document edits SHALL preserve version history rather than overwrite prior submitted historical versions. | Must / P38 |
| FR-047 | The student SHALL be able to compare versions and restore an old version as a new current version, preserving existing history. | Must / P38 |
| FR-048 | When a student manually confirms a submission, linked document versions SHALL be frozen against ordinary editing/replacement. | Must / P38 |
| FR-049 | The library SHALL enforce per-owner access to metadata and file bytes; Admin has no default permission to inspect private document content. | Must / P14/D60 |
| FR-050 | Uploaded documents SHALL pass content/type/size scanning, quarantine if unsafe and use access-controlled storage; format and numeric limits [TBD]. | Must / D54 |
| FR-051 | A student SHALL be able to save/unsave a scholarship and create/manage a corresponding application preparation record. | Must / P09 |
| FR-052 | Each application SHALL present requirements, selected document versions, deadlines (where verified), user-owned notes and history. | Must / P09/P37 |
| FR-053 | The application tracker SHALL support at least **Preparing**, **Ready to Apply**, **Submitted**, **Under Review**, **Accepted**, **Rejected**; final transition policy and additional states [TBD]. | Must / P09; states baseline |
| FR-054 | The **Submitted** state SHALL be set only by an explicit student confirmation after the student submits on the third-party portal; autofill success SHALL not set it. | Must / P22 |
| FR-055 | The system SHALL preserve a timestamped application-status and activity history, distinguishing student-reported statuses from officially sourced status data. | Must / P09 |
| FR-056 | The tracker SHALL provide personal application counts and progress indicators without converting inferred outcomes into official decisions. | Must / P09 |
| FR-057 | The system SHALL generate in-app deadline, document-missing and relevant source-change notices to affected students when information can be verified. | Must / P10/P36 |
| FR-058 | **Conditional:** official application-status integrations MAY update a tracked application only where a lawful documented integration exists; changes SHALL be source-attributed and conflict-safe. | Conditional / P09 |
| FR-059 | The companion browser extension SHALL authenticate/associate an active student session without storing third-party portal passwords. | Must / P18/D55 |
| FR-060 | Autofill SHALL run only after a user-initiated action on a permitted site/form, with least-privilege site access. | Must / P18/D55 |
| FR-061 | The extension SHALL provide a tested-site support path and a clearly labeled best-effort path for other permitted forms; unsupported-site limitations SHALL be visible. | Must / P19 |
| FR-062 | The extension SHALL map confirmed profile/application data to recognizable form fields, leaving unknown fields for student input. | Must / P20 |
| FR-063 | Sensitive personal fields SHALL require a suitable explicit confirmation before the extension inserts their values. | Must / P20/D55 |
| FR-064 | Before third-party submission, the student SHALL be able to inspect all values inserted or proposed and manually correct/complete fields. | Must / P20/D55 |
| FR-065 | The extension SHALL NOT collect passwords/OTP, solve or bypass CAPTCHA, bypass logins, submit an application automatically, or work in breach of portal permissions. | Must / P18/D55 |
| FR-066 | On mapping or site failures, the extension SHALL show failed/missing fields, allow bounded retry and offer manual copy-entry instructions. | Must / P21 |
| FR-067 | The extension MAY save **local/allowed** preparation progress only where the external page supports it; it SHALL not claim remote submission or save guarantees. | Must safeguard / P21 |
| FR-068 | Extension diagnostics SHALL record sanitized site/error categories without logging form secrets, third-party passwords/OTP or unnecessary personal content. | Must / P21/D55 |

### 11.4 Credits, manual payments and notifications

| ID | Requirement | Priority / origin |
|---|---|---|
| FR-069 | Basic scholarship browsing/search and student profile SHALL remain free of charge; initial AI allowances SHALL be bounded by configurable policies [TBD]. | Must / P05/P13 |
| FR-070 | Admin SHALL configure the one-time free grant, Credit packages, individual chargeable service prices and package availability. | Must / P13/P28 |
| FR-071 | A Credit wallet SHALL show available balance and correctly distinguish reserved versus settled amounts. | Must / P13/D58 |
| FR-072 | Before any configured paid AI operation, the student SHALL see the exact quoted price and explicitly authorize the operation. | Must / P13 |
| FR-073 | An authorized operation SHALL use a price snapshot so later Admin price changes do not alter its accepted charge. | Must / P28 |
| FR-074 | The platform SHALL reserve the agreed Credits before starting a paid operation and SHALL prevent execution if available balance is insufficient. | Must / D58 |
| FR-075 | A successfully completed operation SHALL settle its reservation into one final debit; it SHALL NOT charge again on callback/retry. | Must / D58 |
| FR-076 | A technically failed operation SHALL release its reservation or refund an already settled technical-error charge exactly once, leaving no inappropriate final debit. | Must / P13/D58 |
| FR-077 | Wallet transactions SHALL be represented by append-only ledger entries with actor, reason, transaction identity, amount, type and audit timestamps. | Must / P26/D58 |
| FR-078 | Credits SHALL not expire due to elapsed time, but SHALL freeze during the deletion recovery window and be canceled at final deletion as agreed. | Must / P27/P41 |
| FR-079 | An Admin SHALL be able to add/remove Credits manually only through reasoned, auditable adjustments, without rewriting past ledger entries. | Must / P26 |
| FR-080 | The student SHALL be able to select a published Credit package and see the exact manual-payment instructions for an approved local method. | Must / P25 |
| FR-081 | The student SHALL submit a payment request with reference/proof through validated safe upload and see its review state. | Must / P25/D57 |
| FR-082 | A pending request SHALL not credit the student automatically, regardless of whether a receipt image is uploaded. | Must / P25/D57 |
| FR-083 | Admin SHALL verify actual receipt of funds outside the uploaded proof prior to approving payment. | Must / P25/D57 |
| FR-084 | Admin SHALL approve, reject with explanation or request replacement evidence, and the student SHALL see the resulting status in-app. | Must / D57 |
| FR-085 | A payment reference/verified transfer SHALL NOT be accepted twice to issue separate Credit additions; approval SHALL be idempotent. | Must / P26/D57 |
| FR-086 | A successful payment approval SHALL generate exactly one ledger Credit grant matching the package's confirmed purchase snapshot. | Must / P26/D58 |
| FR-087 | Payment status, reviewer, verified reference, decision, evidence metadata and timestamps SHALL be auditable with access restrictions. | Must / P26 |
| FR-088 | The system SHALL not represent discretionary cash refunds as automatic; approved refund handling SHALL follow agreed legal/technical-failure obligations and documented policy. | Must / P27/D66 |
| FR-089 | The platform SHALL provide a student in-app notification inbox with unread/read state and contextual destination links. | Must / P10/D56 |
| FR-090 | Notifications SHALL cover eligible scholarship/deadline/source changes, application/document alerts, wallet/payment events and support responses. | Must / P10/D56 |
| FR-091 | The system SHALL avoid repeated equivalent notifications for the same event/recipient. | Must / D56 |
| FR-092 | Students SHALL configure preferences for optional notification types; mandatory account/security messages SHALL not be blocked by optional preferences. | Must / D56 |
| FR-093 | The product SHALL NOT require email/WhatsApp/Web Push to deliver product notifications during MVP; authentication-related email remains permitted. | Must / P10/D56 |

### 11.5 Support, Admin, privacy and processing

| ID | Requirement | Priority / origin |
|---|---|---|
| FR-094 | Students SHALL create and view their own support tickets with categories, attachments (validated) and message history. | Must / P42 |
| FR-095 | Support AI SHALL be available 24/7 for guidance, ticket triage and limited authorized assistance. | Must / P43/P45 |
| FR-096 | Support AI SHALL identify category and suggested priority, while Admin SHALL retain authority to change the priority and disposition. | Must / P42/P44 |
| FR-097 | The system SHALL hand off to Admin on student request, low AI confidence, recurring failed answers, financial/sensitive issues, or critical approaching deadline, passing minimum necessary conversation context. | Must / D48 |
| FR-098 | Support AI SHALL never approve payment or perform sensitive financial balance changes. Any other AI action requires an explicitly defined authorization policy [TBD]. | Must / P43/D48 |
| FR-099 | Tickets SHALL support statuses **New, AI Handling, Awaiting Admin, Awaiting Student, Resolved, Closed**, with an auditable transition log. | Must / D47 |
| FR-100 | Students SHALL be able to confirm resolution, reopen eligible tickets and provide a support-quality rating; auto-close follows a configurable Admin-defined interval. | Must / D47 |
| FR-101 | Admin SHALL configure human-support working days, working hours and holidays; 24/7 AI availability SHALL be represented separately. | Must / P45 |
| FR-102 | Admin SHALL configure the first-human-response SLA goal by priority, and the system SHALL measure the target using the Admin-defined working calendar. | Must / P44/P46 |
| FR-103 | The system SHALL warn/escalate tickets approaching or exceeding the configured human-response SLA target and record relevant events. | Must / P44/D59 |
| FR-104 | Admin SHALL have a queue with ticket ownership, category, priority, history, status, due calculation and escalation markers. | Must / P42/D59 |
| FR-105 | Aggregate support performance SHALL report ticket volumes, first human response, SLA violations, resolution events and ratings. | Must / P42/D64 |
| FR-106 | Admin SHALL manage catalog sources/reviews, student reports, user administration, Credit packages/prices, payment verification, support and operational settings in protected views. | Must / P08 |
| FR-107 | Admin SHALL have controlled actions for changing matching weights/rules, with versioning and documented publication. | Must / P34 |
| FR-108 | Admin SHALL view aggregate operational dashboards covering source freshness, matching, documents, student-confirmed applications, Credits/payment status, ticket SLA and extension error categories. | Must / D64 |
| FR-109 | Sensitive administrative operations SHALL create audit events including authenticated actor, operation, before/after identifiers where appropriate, reason and timestamp. | Must / P14/D60 |
| FR-110 | Normal Admin use SHALL NOT grant blanket read access to student private file contents; any necessary exceptional support access requires a separately authorized and audited procedure [TBD]. | Must / P14/D60 |
| FR-111 | Admin SHALL be able to suspend suspect listings and handle reports without automatic publication of unreviewed material changes. | Must / P17/D49 |
| FR-112 | Admin SHALL see AI failure/retry, extension and Credit-unit-cost reporting without displaying unnecessary personal document text in analytics. | Must / D64 |
| FR-113 | The platform SHALL capture and retain scoped consent records for AI processing of student-provided documents, and present plain-language AI disclosures. | Must / P14/D66 |
| FR-114 | File content and sensitive personal data SHALL be encrypted in transit and at rest with role- and owner-restricted retrieval. | Must / P14/D54 |
| FR-115 | Uploaded student files SHALL NOT be used for training AI models absent distinct explicit permission, and provider agreements/settings SHALL honor this. | Must / P14/D66 |
| FR-116 | Students SHALL be able to request individual-document deletion and view the effects/limitations of account deletion before confirmation. | Must / P39 |
| FR-117 | Upon confirmed account deletion request, access SHALL be disabled promptly and Credits frozen for a 30-calendar-day recovery period. | Must / P40–P41/D61 |
| FR-118 | A valid recovery request within the 30-day window SHALL restore eligible profile/files/history access and frozen Credits. | Must / P40/D61 |
| FR-119 | After that window, the system SHALL initiate permanent deletion of account data, student files and versions, and cancel remaining Credits, except narrowly defined legal retention. | Must / P39–P41/D61 |
| FR-120 | Deletion execution, retention exceptions and backup lifecycle SHALL be documented, recorded and retryable without re-enabling service implicitly. | Must / D61 |
| FR-121 | The platform SHALL publish suitable Terms of Use, Privacy Policy and AI-use disclosures, including admissions non-guarantee and lawful source/extension behavior, before launch. | Must / D66 |
| FR-122 | Long-running document generation, extraction, source monitoring and other intensive workflows SHALL expose trackable job identity and status. | Must / D63 |
| FR-123 | Jobs SHALL use bounded retries, visible failure outcomes and operational monitoring without claiming a successful result before it exists. | Must / D63 |
| FR-124 | Repeated requests or callbacks SHALL NOT duplicate financial settlement, document publication or other irreversible effects. | Must / D58/D63 |
| FR-125 | A failed external integration/job SHALL preserve already confirmed student data, surface a recoverable explanation and allow an appropriate manual or later retry path. | Must / P21/D63 |

### 11.6 Business Rules

These **BR** statements govern cross-feature behavior and take precedence over presentation shortcuts. Where they refer to a configurable value, its initial setting still requires approval.

| Rule ID | Testable business rule | Decision trace |
|---|---|---|
| BR-001 | A registration with self-declared age under 18 must not activate a student account. | P30–P31 |
| BR-002 | Birth date checks are declaration-based and must not be presented as independent identity verification. | P31 |
| BR-003 | Each eligible account can receive the signup grant only once, including after linked OAuth login. | P13/P29 |
| BR-004 | Only **Student** and **Admin** are formal MVP user roles; AI and extension are controlled system actors, not user roles. | P11/D60 |
| BR-005 | AI-extracted profile fields remain proposals until accepted/corrected by the student. | P03 |
| BR-006 | Missing facts are never invented or treated as confirmed. | P32/D52 |
| BR-007 | No unapproved imported scholarship may be publicly listed. | P01 |
| BR-008 | A material source change requires documented review before altering approved published criteria. | P17 |
| BR-009 | Every published listing must have a traceable source and latest check state/date. | D49–D50 |
| BR-010 | A student report does not automatically erase a scholarship; Admin evaluates and may suspend it for credible risk. | D49 |
| BR-011 | Hard eligibility criteria take precedence over Match Score. | P33/D51 |
| BR-012 | Unknown mandatory-criterion evidence means **Undetermined**, not satisfied. | P32/D51 |
| BR-013 | Match Score is explainable fit, **never** an admission-probability statement. | P34/D51 |
| BR-014 | Matching results retain the applicable rule/weight version. | D51 |
| BR-015 | Supported AI draft types are CV, Motivation Letter, Personal Statement and Scholarship Essays. | P07 |
| BR-016 | AI cannot fabricate GPA, awards, degrees, jobs or credentials; student approves final content. | D53 |
| BR-017 | Versions attached to student-confirmed submitted applications cannot be modified through ordinary edits. | P38 |
| BR-018 | Restoring a historic document version creates a new current version instead of deleting history. | P38 |
| BR-019 | The student—not MinhaAI—performs the actual application submission on the external portal. | P02/P18/P22 |
| BR-020 | Autofill success must never automatically mark an application **Submitted**. | P22 |
| BR-021 | Student-reported statuses and any officially integrated statuses must remain source-distinguishable. | P09 |
| BR-022 | Extension autofill requires explicit student initiation on a permitted form. | P18/D55 |
| BR-023 | Unconfirmed sensitive fields cannot be inserted as though approved. | P20/D55 |
| BR-024 | No external password/OTP capture, CAPTCHA bypass or automated final submission. | P18/D55 |
| BR-025 | External compatibility and remote saving are not guaranteed; failed forms must offer a manual path. | P19/P21 |
| BR-026 | Core profile/basic search are free; paid AI services are governed by configured Credits. | P05/P13 |
| BR-027 | Free onboarding Credits may only be granted after qualifying account activation and cannot be farmed through auth method switching. | P13/P29 |
| BR-028 | Credits do not expire because of elapsed time while the account remains active; deletion is a separate cancellation event. | P27/P41 |
| BR-029 | A configured paid service may start only after the student sees and confirms its Credit price. | P13 |
| BR-030 | Price changes do not retroactively change a previously confirmed operation. | P28 |
| BR-031 | Before execution, an accepted operation reserves the agreed available Credits. | D58 |
| BR-032 | Each successful paid operation produces one settled debit, even under retries/concurrent callbacks. | D58 |
| BR-033 | Technical failure releases/resolves the reservation without an incorrect final debit. | P13/D58 |
| BR-034 | A transfer receipt by itself is not proof of funds received; Admin verification is mandatory. | P25/D57 |
| BR-035 | A transfer/payment reference cannot activate two purchases or duplicate Credits. | P26/D57 |
| BR-036 | Rejection or request-for-new-proof must carry an Admin reason and user-visible state. | D57 |
| BR-037 | Credits are not ordinarily refunded as money following approved payments except where technical failure or applicable law requires a remedy; final legal policy [TBD]. | P27 |
| BR-038 | Product notices are delivered in-app only during MVP. | P10/D56 |
| BR-039 | Equivalent notices for the same event and recipient should be deduplicated while preserving material subsequent changes. | D56 |
| BR-040 | Support tickets follow the six named states, retaining a full transition history. | D47 |
| BR-041 | Human handoff is triggered by request, low confidence, repeated failure, sensitive/financial issue or critical deadline. | D48 |
| BR-042 | AI Support must not approve money receipt or alter financial balance. | P43/D48 |
| BR-043 | AI Support can respond 24/7; human agents work within the Admin-configured schedule. | P45 |
| BR-044 | Human **first-response** SLA is configurable by priority and measured in configured working time. | P44–P46/D59 |
| BR-045 | Resolved/closed tickets permit configured closure/reopen and support-quality rating; exact timing [TBD]. | D47 |
| BR-046 | Admin access requires MFA for launch and enforces least privilege over personal documents. | D60 |
| BR-047 | Sensitive Admin changes and financial actions must be attributable and auditable. | P14/D60 |
| BR-048 | A confirmed account deletion request immediately disables service and freezes Credits for **30 calendar days**. | P40–P41/D61 |
| BR-049 | Restoring a deletion-pending account within 30 days restores uncanceled wallet balance and retained data. | P40/D61 |
| BR-050 | After 30 days, deletion of eligible user data begins and remaining Credits are canceled. | P41/D61 |
| BR-051 | Document-version immutability for applications cannot obstruct legally valid permanent data deletion. | P38–P39/D61 |
| BR-052 | Only valid, documented legal retention exceptions survive final deletion; backup handling follows approved policy [TBD]. | P39/D61 |
| BR-053 | Work that runs asynchronously must expose nonmisleading progress and failed states. | D63 |
| BR-054 | Retried operations must not replay irreversible effects or money movement. | D58/D63 |

## 12. Non-Functional Requirements

Quantitative operational targets intentionally remain **[TBD]** where not approved; their absence is tracked as a release dependency rather than concealed behind invented service-level promises.

| ID | Area | Measurable requirement / verification approach | Status |
|---|---|---|---|
| NFR-001 | Security | HTTPS/TLS for client and service traffic carrying credentials or user data; reject insecure production access. | Must / P14 |
| NFR-002 | Security | Encrypt stored sensitive files/data; use access-scoped file access and safe link expiry; test unauthorized access rejection. | Must / P14/D54 |
| NFR-003 | Security | Enforce authorization on server for all endpoints and objects, including files, application versions, payments and support tickets. | Must / D60 |
| NFR-004 | Admin security | MFA enforced for all Admin sign-ins before launch; denied sign-ins cannot reach protected operations. | Must / D60 |
| NFR-005 | Abuse control | Rate-limit high-risk endpoints/AI consumption and detect anomalous retry/credit-grant patterns; thresholds [TBD]. | Must safeguard / A |
| NFR-006 | Uploads | Validate MIME/content, block unsafe formats or scanned threats, apply configurable max size and storage quota. | Must / D54 |
| NFR-007 | Secrets | Never store or log student third-party portal passwords, OTP/MFA values, payment credentials or unrestricted document contents in telemetry. | Must / D55 |
| NFR-008 | Financial integrity | Concurrent and duplicate transactions must not create duplicate accepted charges, grants or payment approvals. | Must / D58 |
| NFR-009 | Auditability | Retain append-only financial history and protected security/admin events; verify actors and operation IDs. | Must / P26/D60 |
| NFR-010 | Privacy | Explicit, separately scoped AI file-processing consent; verify processor policy forbids training without separate permission. | Must / P14/D66 |
| NFR-011 | Privacy | Apply data minimization, purpose restriction and legally validated retention and subject-request workflows. | Must / D66 |
| NFR-012 | Deletion | Enforce 30-day account recovery semantics; document hard-deletion and backup expiry behavior [TBD]. | Must / P40/D61 |
| NFR-013 | Localization | All student and Admin core flows usable in Arabic RTL and English LTR, including dates, mixed-language names and numeric values. | Must / P06 |
| NFR-014 | Responsive | Web core features SHALL function on contemporary mobile and desktop viewports; browser-extension platform coverage documented separately [TBD]. | Must / D62 |
| NFR-015 | Accessibility | Forms, major dialogs and navigation operable using keyboard; labels readable to assistive technologies and appropriate contrast; exact conformance target [TBD]. | Must / D62 |
| NFR-016 | UX transparency | Mark AI suggestions, verification dates, unknown eligibility, paid Credit quotations and irreversible actions conspicuously. | Must / P34/D51 |
| NFR-017 | Availability | Define and measure uptime/SLO after hosting and operational baseline tests; target [TBD] before launch. | Required decision / D63 |
| NFR-018 | Performance | Benchmark search, matching, extraction, document export and browser fill with a realistic dataset; target distributions [TBD]. | Required decision / D63 |
| NFR-019 | Job stability | User-visible status for long jobs and bounded retries without duplicate financial or publication side effects. | Must / D63 |
| NFR-020 | Fault tolerance | AI/source provider outage SHALL degrade safely with an error/manual fallback; never misreport success. | Must / D63 |
| NFR-021 | Data recovery | Backup, restore validation, RPO/RTO and deletion-conformant backup retention documented [TBD] before launch. | Required decision / D61/D63 |
| NFR-022 | Maintainability | Modular domains and replaceable AI/search/storage providers; no mandatory microservices or framework lock-in. | Must / D67 |
| NFR-023 | Observability | Monitor job failure, source freshness, SLA events, payment reconciliation and extension compatibility without unnecessary sensitive payloads. | Must / D64 |
| NFR-024 | Testing | Automated/instrumented integration and adversarial tests cover RBAC, idempotency, AI grounding, account deletion and external-fill safety. | Must / D65 |
| NFR-025 | Compatibility | Extension support is tied to a documented tested-browser/portal matrix; supported versions/sites [TBD] prior to launch. | Required decision / P19/D55 |
| NFR-026 | Legal | Terms/privacy/disclaimer/payment/source-use review approved for actual launch geography and involved providers. | Must / D66 |
| NFR-027 | Service limits | Configurable quotas on uploads, AI and credits protect operations; actual values/periods [TBD], not implicit arbitrary caps. | Required decision / P13/D54 |
| NFR-028 | Integrity | Versioned provenance for scholarship criteria, match evaluation, price quotes, submitted files and status origins. | Must / P17/P28/P38/D51 |

**Performance interpretation:** legacy ideas such as “search in 3 seconds” or “AI document in 15 seconds” are **not approved targets**. The team SHALL propose empirically achievable percentiles, load profiles and failure budgets before setting release thresholds. No universally supported browsers, university portals or file-size limits are assumed.

## 13. User Flows

Each named flow specifies the normal path and consequential alternatives; unresolved transition semantics remain explicitly identified. Screens are mapped in Section 14.

| Flow ID | Actor and normal sequence | Exceptions, safety and branch behavior |
|---|---|---|
| FLOW-01 — Signup | Student → choose email/Google → enter DOB → age gate → verify/activate → grant initial Credits once → choose UI language → start profile | Minor/invalid DOB blocked; duplicate identity securely linked or rejected; no grant until eligible activation |
| FLOW-02 — Profile | Student → manual fields or consented CV upload → extraction proposed → inspect/edit → confirm → stored trusted facts | Extraction failure returns manual entry; uncertain/missing fields remain unknown; denial of consent does not block manual profile |
| FLOW-03 — Catalog publication | Permitted source or Admin entry → extract/normalize → detect duplicate → Admin review → approve → publish with source/check date | Rejection remains unpublished; material update sent to review; credible danger suspends listing and may notify affected students |
| FLOW-04 — Discovery/matching | Student → query/filter → approved results → evaluate mandatory criteria → calculate explainable fit and confidence → read details → save | Missing data → Undetermined; hard failure → Ineligible even with high score; outdated data warns rather than speculates |
| FLOW-05 — Draft generation | Student → select scholarship, doc type/language → verify confirmed facts → Credit quote (if applicable) → consent/confirm → reserve → tracked AI job → preview/manual edit/approve → export/version | Insufficient balance blocks charged job; technical failure releases Credits; fabricated claim must be challenged; export failure does not destroy draft |
| FLOW-06 — Document revision | Student → open library → customize/compare/restore → attach exact version to application → confirm submission → freeze linked version | Old version restore creates new revision; attempted edit of frozen version is denied; deletion request follows lawful deletion policy |
| FLOW-07 — Application | Student → save opportunity → create preparation/checklist → attach versions → Ready to Apply → open official portal → student submits externally → student confirms Submitted → optionally updates Under Review/Accepted/Rejected | Autofill alone leaves Preparing/Ready; third-party submission failure leaves unsubmitted; official status sync only if verified integration exists |
| FLOW-08 — Extension | Student at allowed portal → activate extension → identify fields → select approved profile facts → sensitive-field consent → propose/fill → review & edit → student handles CAPTCHA/OTP and presses external Submit | Unsupported form → explicit notice/manual fallback; unmapped fields remain empty; no password/OTP interception; never mark application Submitted automatically |
| FLOW-09 — Credit purchase | Student → view package/payment instructions → pay externally → upload proof/reference → Pending Review → Admin confirms actual receipt/uniqueness → approve/credit once → in-app notice | Suspect/duplicate transfer refused; reviewer may request replacement proof; upload alone never transfers Credits |
| FLOW-10 — Credit usage | Student → choose chargeable service → see snapshot price → confirm → reserve → work finishes → settle debit once | Low balance blocks; timeout/retry must not double-charge; definite technical failure releases reservation; uncertain completion reconciled without guessing |
| FLOW-11 — Support | Student opens ticket → AI triage and response → resolves or escalates → Admin replies within work-hour SLA → Resolved → student confirms/reopens → Closed and rating | Financial/sensitive/critical escalates; human out-of-hours time counted per calendar; AI prohibited from approving money movement; waiting-student pause policy [TBD] |
| FLOW-12 — Account deletion | Student reviews disclosure → confirms → account disabled; wallet frozen 30 calendar days → restore in window **or** final deletion/cancellation after window | Exactly-at-boundary restoration semantics [TBD]; failed deletion is queued and audited; retained legal records and backups handled by approved policy |
| FLOW-13 — Admin source report | Student reports incorrect listing → Admin sees evidence and provenance → validates against source → reject report/correct under review/suspend → log decision | Malicious report alone cannot permanently remove valid content; changes affecting subscribers trigger appropriately deduplicated in-app notices |

**Unresolved flow details:** application status rollback/re-submission/withdrawal, payment proof resubmission limit, ticket SLA pausing on `Awaiting Student`, automatic ticket closure grace period, exact deadline-notification offset, and whether multiple applications to distinct rounds of a listing are separate records are all **[TBD]**; they must be resolved before implementing corresponding state-machine constraints.

## 14. Pages / Screens

These are **logical product screens**, not UI designs, navigation blueprints or a mandate to make one route per row. Equivalent drawers/tabs are allowed if every specified user task remains discoverable and testable. `A` means access is authenticated; `Public` means public access if business policy allows (public browsing itself [TBD]).

| Screen ID | Screen/area | Actor | Primary functions / important states | Features |
|---|---|---|---|---|
| SCR-001 | Landing, terms, privacy and AI disclosure | Public/Student | Product explanation, non-guarantee, policies, sign in | F-01/F-14 |
| SCR-002 | Registration / sign-in / Google callback | Public | Login methods, declared DOB, verification, errors | F-01 |
| SCR-003 | Email verification and account recovery | Student | Verified/unverified/retry/expired links | F-01 |
| SCR-004 | Student home/dashboard | Student A | Profile completeness, saved opportunities, application status, Credits, alerts | F-02/F-07/F-09/F-11 |
| SCR-005 | Personal and academic profile | Student A | Stage-specific fields, evidence, missing facts, manual corrections | F-02 |
| SCR-006 | Profile upload/extraction review | Student A | Consent, quarantine, proposed facts, confirm/reject | F-02/F-14/F-15 |
| SCR-007 | Scholarship discovery | Student A | Text/semantic search, filters, sort, eligibility and empty results | F-04 |
| SCR-008 | Scholarship detail and report form | Student A | Source, funding, deadlines, criteria, matching explanation, report | F-03/F-04 |
| SCR-009 | Saved scholarships | Student A | Bookmarks, expiry/change warnings | F-07 |
| SCR-010 | Matching explanation | Student A | Hard conditions, score contributions, confidence, rule version | F-04 |
| SCR-011 | My applications / tracker | Student A | Status columns/list, submission history, personal stats | F-07 |
| SCR-012 | Application detail / requirements | Student A | Checklist, attached exact versions, missing files, confirm submission | F-06/F-07 |
| SCR-013 | Document generation wizard | Student A | Type/language/scholarship, approved facts, Credit quote, job status | F-05/F-09/F-15 |
| SCR-014 | Document manual editor / preview | Student A | Review flags, manual edits, approval, PDF/DOCX export | F-05 |
| SCR-015 | Document library | Student A | Uploaded/generated docs, grouping, deletion, linkage | F-06 |
| SCR-016 | Document versions / compare / restore | Student A | Historical revisions, compare, frozen-submission notice | F-06 |
| SCR-017 | Credit wallet / ledger history | Student A | Available/reserved balance, transactions, grants and reversals | F-09 |
| SCR-018 | Credit packages / manual payment | Student A | Active packages, local instructions, proof and transfer reference | F-10 |
| SCR-019 | Payment requests/details | Student A | Pending, new-proof requested, approved, rejected with reason | F-10 |
| SCR-020 | In-app notification center / preferences | Student A | Read/unread, links, optional category preferences | F-11 |
| SCR-021 | Support ticket inbox / new ticket | Student A | Ticket categories, AI entry, own tickets | F-12 |
| SCR-022 | Support ticket conversation/detail | Student A | AI/human handoff, history, current state, reopen, rating | F-12 |
| SCR-023 | Account / privacy / deletion / restore | Student A or recovery | Consent overview, pre-delete impact, 30-day state and lawful notices | F-14 |
| SCR-024 | Extension popup and on-page review | Student + extension | Site status, authorized facts, mapping, sensitive consent, failures | F-08 |
| SCR-025 | Admin overview/analytics | Admin A+MFA | Operational aggregation and diagnostics | F-13 |
| SCR-026 | Admin source management/import | Admin A+MFA | Sources, permitted ingest settings and check history | F-03/F-13 |
| SCR-027 | Admin scholarship review/moderation | Admin A+MFA | Pending/new/changed/suspended; diff, approve, reject | F-03/F-13 |
| SCR-028 | Admin student error reports | Admin A+MFA | Evidence, review state, action, audit | F-03/F-13 |
| SCR-029 | Admin matching policy | Admin A+MFA | Rule/weight edits, versions and validation | F-04/F-13 |
| SCR-030 | Admin users / controlled access | Admin A+MFA | Account status and scoped operations; no default file read | F-13/F-14 |
| SCR-031 | Admin packages / price table | Admin A+MFA | Free grant, packages, chargeable services, audit | F-09/F-13 |
| SCR-032 | Admin payment verification | Admin A+MFA | Reconcile incoming transfers, evidence, uniqueness and outcomes | F-10/F-13 |
| SCR-033 | Admin Credit reconciliation | Admin A+MFA | Ledger, manual adjustment, reversal investigation | F-09/F-13 |
| SCR-034 | Admin support queue / ticket | Admin A+MFA | Escalations, working-hour SLA and conversations | F-12/F-13 |
| SCR-035 | Admin SLA/working-hours settings | Admin A+MFA | Priorities, schedules, first-response targets, closure interval | F-12/F-13 |
| SCR-036 | Admin audit / system failures | Admin A+MFA | Sensitive action history, source/job/extension failure trends | F-13/F-15 |

**Screen-level design constraints:** all relevant core web screens must work in Arabic/English and responsive layouts, show appropriate loading/empty/error/permission states, and not treat the extension as a mobile-browser feature until compatibility is validated. Student and Admin consoles never mix private data merely because an interface component is reused.

## 15. Roles & Permissions

Exactly **two official roles** are in scope. AI Support, import workers and extension code are service principals with narrower scoped grants, **not additional formal end-user roles**. Backend checks are authoritative.

| Capability | Student | Admin | AI Support / system actor | Safety rule |
|---|---|---|---|---|
| Register/manage identity and DOB | Own only | Admin identity under separate controls | No direct authority | Adult gate; secure linked identity |
| Create/edit profile | Own | No unrestricted edits | Consent-bound extraction proposals | Student must confirm AI facts |
| Read private documents | Own | **No routine content access**; exceptional path [TBD] | Scoped job only with consent | Isolated file ownership |
| Generate/edit/export documents | Own | No routine access | Scoped generation only | Student review, price approval |
| View approved scholarships | Yes | Yes | Read approved content needed for tasks | Source and freshness visible |
| Approve/suspend scholarship/source | Report problems only | Full authorized workflow | Ingest proposals only | Never automatic approval |
| Configure eligibility and matching weights | No | Yes, audited | Run current approved rules | Versioned; hard rules prevail |
| Save/update application statuses | Own; confirms external submission | No routine status edits on student's behalf | **Cannot mark Submitted** | Origin and timestamp preserved |
| Initiate extension fill | Own on permitted site | No | User-initiated scoped fill only | No auto-submit/secrets |
| View wallet / payment requests | Own | Authorized oversight | No money approval | Financial records protected |
| Adjust Credits / approve transfer | No | Yes, reasoned and auditable | **Forbidden** | Verified funds and exactly-once ledger |
| View/create support tickets | Own only | Ticket queue assigned/authorized to operations | Context-minimized assist/triage | Escalate financial/sensitive |
| Configure SLA and support calendar | No | Yes | Read permitted settings | Only human first-response SLA |
| Notification preferences | Own only | Configuration of non-personal policy only | Generate scoped events | In-app product notices |
| See aggregate analytics | Personal metrics only | Approved aggregate operational data | Sanitized telemetry only | No unsolicited personal-file text |
| Request deletion / recover | Own only | Process lawful exceptions under authorized workflow | No unilateral deletion decisions | Thirty-day recovery/cancellation |
| View audit trail | Personal operation history where offered | Security-authorized records | Write limited events only | Tamper resistance and minimum data |

**Undefined access policy [TBD]:** conditions under which Admin may inspect a student's support attachment or document, consent/legal basis, exact approval workflow, break-glass access, and which Admin users may operate payment verification versus support. Because the MVP has only one formal Admin role, these are **scoped permissions within Admin**, not an authorization to add new external roles. **Do not infer blanket access**.

## 16. Data Requirements

This section is a **conceptual data inventory**, explicitly **not an ERD** or implementation schema. PII categories, retention and exact cardinalities must be validated during subsequent data modeling.

| Data area | Minimum conceptual information | Integrity / provenance rules |
|---|---|---|
| Identity/account | User identifier, role, login methods, verified email, declared DOB, account status, MFA status (Admin) | No duplicated signup grant; no plaintext credentials |
| Student profile | Identity/contact, nationality/residency, education level, discipline, institution, GPA + scale, language, preferences, optional validated achievements | Fact origin (manual/extraction) and student-confirmed state; no invention |
| Processing consent | Student, purpose, data category, policy/version, grant/withdraw status and timestamp | Consent proof exists before processor disclosure |
| Scholarship source | Authority/site/source link, allowed ingestion method, last checked, terms review status | Catalog never treats unknown verification as authoritative |
| Scholarship listing | Title/provider, study level, discipline, geography, funding and coverage, eligibility criteria, required files, official URL, opening/closing round(s), timezone, status | Approved version, source citation, review and change provenance |
| Scholarship change/report | Detected difference, report evidence, Admin decision, affected students, moderation state | All material corrections reviewed and attributable |
| Eligibility/match | Criterion outcomes and evidence, score components, confidence, missing facts, ruleset version, time | Hard rules and Match Score separated; evaluation reproducibility to feasible degree |
| Documents | Owner, document category, uploaded/generated origin, language, scholarship customization, quarantine/scan result | Protected file object; content never in general analytics |
| Document versions | Version ID, parent doc, authored/approved times, content reference and change history | Submitted version exact linkage/freeze; retention subject to deletion |
| Saved/applications | Student, scholarship/round, requirements, attached version IDs, deadline, notes, status, history and state origin | Submitted only on student confirmation; official origin separately attributed |
| Extension attempts | Student-scoped attempt, permitted site identifier, field counts, error type, completion status | No passwords/OTP or sensitive value telemetry |
| Credit configuration | One-time signup grant, packages, service prices, active/inactive configuration, price version/snapshot | Admin changes auditable; amount/currency/rates [TBD] |
| Wallet/ledger | Student account, available/reserved/settled amounts, immutable movement IDs, operation link, reason and actor | Sum/reconciliation accurate; idempotent transaction identities |
| Payment request | Student/package, quoted amount/currency, approved transfer method, unique reference, proof asset, review status and decision | Funds independently verified before one grant |
| Notification | Recipient, category, event identity, destination, timestamp, read state | De-duplicate; preferences respected where optional |
| Support ticket | Student, category, priority, state, thread, attachments, actors, handoffs, rating | Privacy-limited AI context; history unaltered |
| SLA policy/event | Priority, human work calendar, first-response target, measured business-time events, escalations | Exact calendar math reproducible; values [TBD] |
| AI/background job | Correlation ID, type, status, retry record, output reference, provider failure class and costs | Repeated callbacks don't duplicate ledger/document outcomes |
| Audit/deletion | Sensitive operation actor/time/reason, deletion request, recovery deadline, progress, legal exception | Smallest legally necessary retention; access restricted |

**Data correctness:** timestamps stored unambiguously and displayed in the relevant known timezone; unknown deadlines must not receive invented timezone or countdown; GPA requires its scale; a source-derived criterion must preserve evidence/provenance; only confirmed profile facts are safe for external form fill and AI drafts. **Retention schedule for profiles, support, payment proof, audit records and backups is [TBD] subject to applicable law**. A stored source document is not permission to use it to train an AI model.

## 17. Integrations

| Integration | MVP commitment / boundary | Required precondition | Status |
|---|---|---|---|
| Google OAuth | One approved sign-in channel in addition to email/password | OAuth credentials, secure redirect, identity linking | Confirmed behavior [P29]; provider configuration [TBD] |
| Transactional authentication email | Verification and recovery only; not product notifications | Approved mail delivery, templates and abuse protections | Needed for email login; provider [TBD] |
| Scholarship websites/feeds | Hybrid discovery via permissible source methods; Admin verification | Permission/terms, quality, availability and source list | Confirmed pattern [P01]; sources [TBD] |
| LLM/RAG and extraction | Profile extraction, explainable scholarship matching and document generation; constrained support AI | Security, privacy, no-training controls, cost/quality evaluation | Capabilities confirmed; exact providers [TBD] |
| File storage and scan service | Secure uploaded/generated files; malware/type validation | Region/legal suitability, encryption, size/retention policy | Behavior confirmed; provider and limits [TBD] |
| Browser extension / third-party forms | Controlled fill on tested permitted forms; best-effort others | Chosen browser versions, site allowlist, form testing and consent | Confirmed [P18–P21]; initial coverage [TBD] |
| Local manual payment rails | **External** transfer; student uploads evidence and Admin reconciles receipt | Actual available method, account holder, currency and lawful policy | Confirmed manual workflow; providers [TBD] |
| Official scholarship application-status feeds | Only if available under a documented legal integration; source labels required | Explicit partner/API availability and approved contract | **Conditional; not promised for MVP** |
| Monitoring/analytics | Operational metrics and error tracking, ideally aggregate/privacy-safe | Vendor privacy/security review and retention policy | Capability confirmed; provider [TBD] |

**Proposed $0 AI-provider fallback strategy [A; post-interview technical decision, not a product requirement]:** use Cloudflare Workers AI as the primary inference provider; try GroqCloud first when an approved workload encounters quota exhaustion, throttling, timeout or provider outage; consider Gemini API Free as a subsequent fallback **only for non-sensitive/synthetic content** after current terms and data-handling review; keep OpenRouter free models as a final, **non-sensitive/test-only** fallback pending approval of the underlying routed model and processor. Before any provider receives a student's CV, transcripts, identity details, application materials or support messages containing personal data, Security/Legal must confirm appropriate privacy/no-training terms, data residency and configured controls (Groq ZDR where required). A provider must be skipped if not approved for the data class; no automatic sensitive-data downgrade. If no provider passes policy and quota checks, fail gracefully, preserve the draft and reconcile any reserved Credits once rather than reroute unsafely or charge the student. Deterministic eligibility rules remain authoritative even when inference changes. Detailed proposal: [`docs/ai-provider-strategy.md`](ai-provider-strategy.md). **OQ-004 remains open** until provider review is complete; this note does not override the interview or commit to an API vendor.

**Disallowed inference:** none of Stripe, PayPal, Supabase, Firebase, Pinecone, Chroma, LangChain, CrewAI, AutoGen, a particular LLM or microservice deployment is binding simply because it appeared in an earlier draft or technical discussion.

## 18. Edge Cases

Edge-case IDs referenced by Section 10 have corresponding error states in Section 19, acceptance coverage in Section 23 or an explicit [TBD] decision in Section 26.

| ID | Trigger / edge case | Required safe behavior |
|---|---|---|
| EC-001 | Student birth date is invalid, exactly at the adult boundary, or indicates under 18 | Calculate age consistently using current registration date; deny underage/invalid activation; document boundary/timezone choice [TBD] |
| EC-002 | Google identity/email collides with an existing account or signup request is repeated | Require validated linking; no accidental takeover, duplicate account activation or duplicate free grant |
| EC-003 | Uploaded CV is unreadable/scanned poorly or extraction is contradictory | Offer manual entry, label uncertain proposals; never auto-confirm extracted facts |
| EC-004 | Missing GPA scale, nationality, language or mandatory scholarship prerequisite | Return **Undetermined** for relevant criterion; show missing input instead of inferring a pass |
| EC-005 | Duplicate scholarship records appear through different URLs or syndication | Flag equivalence for Admin; no automatic irreversible merge that loses provenance |
| EC-006 | Scholarship deadline moves, link breaks, source disappears or enrollment becomes rolling | Recheck/flag with source timestamp; material change requires Admin review; avoid false countdown |
| EC-007 | Student submits a mistaken or malicious incorrect-data report | Preserve original listing and evidence; Admin assesses severity, suspending only on justified risk |
| EC-008 | Hard nationality/degree condition fails while AI score is high | Show **Ineligible** despite the fit score and explain the hard disqualifier |
| EC-009 | External scholarship data cannot support a mandatory eligibility verdict | Display **Undetermined**, source/provenance warning and a safe next step to verify |
| EC-010 | Student requests a paid draft without sufficient available Credits | Quote price and required difference; no reserve, job or unauthorized debit |
| EC-011 | AI output invents a job/award/grade or contains unconfirmed assertion | Reject or flag claim for student confirmation; cannot quietly certify fabricated fact |
| EC-012 | AI draft succeeds but PDF or DOCX export fails | Preserve edited draft and relevant version; report export failure; do not re-charge generation by default |
| EC-013 | Student changes profile or base CV after submitting an application | Frozen version remains unchanged; new application versions may use new facts |
| EC-014 | Student restores an older document while later versions exist | Create new current revision without overwriting frozen or historical versions |
| EC-015 | Extension fills fields but student leaves portal without submitting | Tracker status remains preparing/ready; no inferred submitted event |
| EC-016 | A student reports accepted/rejected status that conflicts with future official data | Keep both with provenance and timestamps; conflict-resolution rule [TBD] |
| EC-017 | Form fields change or portal is unsupported, blocked or against portal terms | Refuse prohibited automation; show field failures/manual entry; no claim of compatibility |
| EC-018 | Portal asks for OTP, password, MFA, CAPTCHA or unsupported sensitive values | Student handles those externally; extension does not collect or solve them |
| EC-019 | Form save/autofill process is interrupted or duplicated | Bounded retry, preserve safely known local work, avoid duplicate irreversible external actions |
| EC-020 | Paid AI request is retried after slow callback or provider timeout | Same operation identity and accepted price; reconcile outcome before deciding settle/release |
| EC-021 | Price changes while an already approved student operation is still running | Complete/reconcile at the captured price; do not debit new amount |
| EC-022 | Student reuploads one transfer receipt or different students use one reference | Flag/reject duplicate pending investigation; never double-credit |
| EC-023 | Admin double-clicks Approve or payment state changes concurrently | Single authorization and single ledger grant, with safe conflict state |
| EC-024 | The same scholarship update is discovered by multiple monitoring runs | One relevant notification per event version/recipient; substantive changes still delivered |
| EC-025 | High-priority ticket appears out of human support hours or just before scholarship deadline | AI available, escalate appropriately; measure human first-response SLA only against configured work calendar |
| EC-026 | AI support is asked to approve transfer or change balance, or repeats poor answers | Deny money action, escalate to Admin, preserve minimum necessary context |
| EC-027 | Admin attempts to inspect an unrelated student's protected document | Reject absent explicit authorized exception and create security audit event |
| EC-028 | Student restores deletion-pending account near day 30 | Restore only while recovery window remains valid; exact cutoff policy [TBD] |
| EC-029 | Final deletion includes previously frozen submitted versions, legal hold or delayed backups | Enforce lawful deletion except defined minimum retention; record pending backup erasure and exceptions |
| EC-030 | Worker crashes after completing output or ledger action but before acknowledging job | Idempotent restart; exactly one user-visible output/financial settlement and correct eventual state |

## 19. Error States

**General rule:** the interface SHALL describe the actual state, the action the student can safely take, and whether money was charged. Do not expose internal stack traces, raw model prompts, private files or secret provider details.

| Error ID | Detectable state | UX and system response | Recovery / test oracle |
|---|---|---|---|
| ERR-001 | `AGE_RESTRICTED` / invalid DOB | Registration refused with clear age/date message | Correct eligible DOB with new attempt; no activated account/bonus |
| ERR-002 | `AUTH_VERIFICATION_FAILED` / identity collision | Block access/link with non-enumerating message | Secure retry or account recovery; no duplicate grant |
| ERR-003 | `EXTRACTION_FAILED` | Explain that AI extraction failed/was partial | Profile remains editable manually; no guessed facts |
| ERR-004 | `FILE_REJECTED` / scan pending | Block unsafe/oversized/unsupported upload, show non-sensitive cause | Try permitted file after scan; nothing public/AI-processed prematurely |
| ERR-005 | `SOURCE_FETCH_FAILED` / stale source | Surface in Admin source queue and monitor state | Do not publish unreviewed update; students see known verification status |
| ERR-006 | `SCHOLARSHIP_REVIEW_REQUIRED` | Imported/materially changed listing held pending review | Admin resolves; unapproved data not public |
| ERR-007 | `ELIGIBILITY_UNDETERMINED` | Explain unknown fact/criterion, not a terminal platform error | Student supplies confirmed facts or consults source |
| ERR-008 | `MATCH_PROVIDER_UNAVAILABLE` | Distinguish AI score unavailable from mandatory-rule result | Retry later; preserve existing confirmed student inputs |
| ERR-009 | `GENERATION_FAILED` / `INSUFFICIENT_CREDITS` | Show correct job outcome/quote and debit status | Technical failures release/reconcile reservation; low funds block initiation |
| ERR-010 | `DOCUMENT_EXPORT_FAILED` | Keep edited content and advise retry | Regenerate export without unwanted new drafting fee |
| ERR-011 | `DOCUMENT_VERSION_LOCKED` | Explain submitted-version freeze | Edit a new version instead; original immutable |
| ERR-012 | `DOCUMENT_ACCESS_DENIED` | Deny file bytes and metadata beyond authorized scope | Log security-relevant event; no signed URL leak |
| ERR-013 | `APPLICATION_STATE_CONFLICT` | Show state origin and clash; do not overwrite history | Student/admin follows approved conflict policy [TBD] |
| ERR-014 | `EXTENSION_UNSUPPORTED_PORTAL` | State limitation and show manual-fill option | No prohibited extraction/filling or inferred submission |
| ERR-015 | `EXTENSION_PARTIAL_FILL` | Show successful/failed fields separately | Student corrects fields and submits externally |
| ERR-016 | `CREDIT_HOLD_UNRESOLVED` | Mark processing/reconciliation, not definite charge success/failure | Reconcile provider result, settle/release only once |
| ERR-017 | `CREDIT_BALANCE_INSUFFICIENT` | Refuse operation and show current wallet vs price | Buy more Credits or stop |
| ERR-018 | `PAYMENT_REVIEW_REJECTED` | Rejection reason visible; no Credits granted | Correct proof / submit a new valid case per approved policy |
| ERR-019 | `PAYMENT_DUPLICATE_REFERENCE` | Hold/reject suspect duplicate without crediting it | Admin investigations, no repeated ledger grant |
| ERR-020 | `NOTIFICATION_LINK_UNAVAILABLE` | Show message while destination is withdrawn/deleted/inaccessible | Return to notification center; don't bypass authorization |
| ERR-021 | `SUPPORT_ESCALATION_REQUIRED` | Move to human queue, show working-time expectations | Maintain record; no implied immediate human availability |
| ERR-022 | `SLA_BREACH` | Surface Admin warning/escalation and audit | Apply configured escalation; no claim ticket already resolved |
| ERR-023 | `ADMIN_ACTION_UNAUTHORIZED` | Deny high-risk action and capture audit as applicable | Authorized Admin/MFA approval only |
| ERR-024 | `ACCOUNT_DELETION_PENDING` | Block standard login/use; show recoverable state through safe verified flow | Restore in approved window or allow deletion process |
| ERR-025 | `FINAL_DELETION_RETRYING` | Disabled account and pending deletion work recorded | Retry safely; do not silently re-enable service |
| ERR-026 | `ASYNC_JOB_INTERRUPTED` | Show last authoritative queued/running/failed state | Bounded retry and idempotent financial/output resolution |

## 20. Security & Privacy Requirements

**Protective model:** sensitive identity data, academic records, documents, application history, financial references and support records are student-linked personal data. The following rules are **MVP release blockers**, not optional polish.

1. **Identity and authorization:** enforce backend RBAC and ownership checks on every resource, including files/versions, signed download URLs, transcripts, wallet movements, ticket messages and Admin operations. Student A never gains access to Student B merely by changing identifiers. Admin MFA is mandatory before launch; normal Admin access does not authorize browsing private document contents. [NFR-002–NFR-004, BR-046]
2. **Processing consent:** present purpose-specific informed disclosure before transmitting CVs/credentials to AI services. Record the decision and relevant policy version. If denied, preserve the manual profile path. Support future withdrawal consistent with an approved processing/retention policy [TBD]. [FR-012, FR-113]
3. **LLM and retrieval safeguards:** use only facts confirmed by the student for definitive applicant claims; label unknowns and AI suggestions. Isolate per-student context and constrain agent actions by the actual user's permissions. Do not use uploaded documents for model training without separate explicit permission, and verify provider terms before integration. [BR-006, BR-016, FR-115]
4. **Browser extension controls:** explicit activation; least-privilege per-site access; no blanket harvesting, secrets, password/OTP storage, CAPTCHA circumvention, invisible auto-submission or cross-student data leakage. Preview what will be inserted; require additional confirmation for sensitive values. Logs shall be sanitized. [BR-022–BR-025]
5. **Uploaded file controls:** MIME/content validation, malware scanning, file isolation/quarantine, access checks, and configured size/quota caps. Restrict file download links to authorized owners; prevent external public indexing. Actual scanned formats and caps require approval. [FR-050, NFR-006]
6. **Money and abuse defenses:** append-only, audited Credit ledger; unique payment-reference handling; exactly-once grant/settlement/reversal; reasoned Admin manual adjustments; no authority for AI to approve receipts or change balances. [BR-031–BR-037, BR-042]
7. **Retention and deletion:** documented 30-day account recovery, immediate service lock and Credit freeze, then lawful permanent deletion and cancellation. Map deletion across file versions, archives, job artifacts, temporary objects, logs and backups; only legal minimum may remain under an approved retention policy. No indefinite anonymous “backup exception” can be presumed. [BR-048–BR-052]
8. **Legal and supplier review:** final Terms, Privacy Policy, disclaimer of admission guarantees, source scraping/filling permissions, manual-payment/refund obligations, provider data-processing terms and cross-border transfer constraints must be reviewed against the **actual launch jurisdictions** before deployment. [FR-121, NFR-026]
9. **Incident readiness [A]:** define contact, logging access controls, secret rotation, incident triage, breach response and file restore/deletion verification; detailed response commitments [TBD]. This is a recommended security prerequisite, not a separately approved user-facing feature.

**Privacy by design test rule:** an internal dashboard must not need the content of a scholarship essay to display “one document generated”; a support AI agent must not read files merely because a student has a ticket; an Admin payment reviewer must be able to inspect transfer evidence without automatically receiving access to unrelated academic documents.

## 21. Analytics & Tracking

Instrumentation SHALL measure funnel performance and operational correctness with minimized personal data. Detailed event payload schemas and retention periods are **[TBD]**. Use stable anonymous/internal IDs where feasible and avoid scholarship-essay text, CV content, national ID scans, contact details, transfer proof or filled form values in analytics.

| Event ID | Event / trigger | Recommended non-sensitive dimensions | Owner / use |
|---|---|---|---|
| EVT-001 | `account_activated` | Auth method class, declared age eligibility result, locale | Product: onboarding and duplicate-grant monitoring |
| EVT-002 | `profile_completed_or_updated` | Stage, completion band, extraction/manual route | Product: onboarding friction |
| EVT-003 | `scholarship_import_reviewed` | Source ID, review outcome, freshness age | Admin: catalog quality |
| EVT-004 | `scholarship_report_resolved` | Issue category, outcome, response latency | Admin: data quality |
| EVT-005 | `scholarship_search_completed` | Filter categories, result count, query mode (no raw PII text) | Product: findability |
| EVT-006 | `eligibility_evaluated` | Eligible/Undetermined/Ineligible, rule version, missing-criteria count | Product: recommendation quality |
| EVT-007 | `match_score_displayed` | Score band, confidence category, explanation presence | Product: explainability |
| EVT-008 | `document_generation_requested` | Type, locale, quoted Credits, AI job ID | Product/finance: usage |
| EVT-009 | `document_generation_completed` | Success/fail, latency class, charges reconciled | Product/finance: yield and cost |
| EVT-010 | `document_exported` | PDF/DOCX, success/failure | Product: workflow completion |
| EVT-011 | `application_status_changed` | Old/new state, actor/source and timestamp | Product: confirmed submission funnel |
| EVT-012 | `extension_attempt_finished` | Tested portal ID/category, mapping success/failure, no field values | Tech: compatibility |
| EVT-013 | `credit_transaction_settled` | Transaction type, amount, operation ID, dedupe outcome | Finance: ledger reconciliation |
| EVT-014 | `manual_payment_reviewed` | Package, approval/reject/new-proof state | Finance: manual payment queue |
| EVT-015 | `notification_delivered_or_read` | Category, event identity, read outcome | Product: in-app relevance |
| EVT-016 | `support_ticket_state_changed` | Category, priority, state, AI/human route, SLA event | Support: case quality |
| EVT-017 | `account_deletion_requested_or_completed` | Stage, restore/completion flag, no files | Trust: privacy execution |
| EVT-018 | `async_job_failed_or_retried` | Job type, safe provider error class, retries | Engineering: reliability |

**Product dashboards:** approved catalog/freshness; search/match funnel; profile/document throughput; saved-to-student-confirmed application stages; extension success by permitted portal; wallet/payment and AI-cost reports; ticket first-response SLA and satisfaction; deletion completion. Use time windows, aggregate cohorts and appropriate safeguards against displaying identifiable small groups. Personal dashboard metrics are visible only to their student; Admin sees aggregated indicators and authorized case-level work queues.

**Validation:** cross-check Credit consumption against ledger (not analytics events), approved catalog against moderation records, and student-confirmed submissions against tracker events (not external autofill clicks). Track telemetry coverage/consent if required by applicable law.

## 22. Success Metrics / KPIs

Targets, baselines, pilot sample size and reporting cadence are **[TBD]**; definitions below are intended to prevent later metric ambiguity.

| KPI ID | Indicator and precise calculation | Success interpretation | Target |
|---|---|---|---|
| KPI-001 | **Catalog freshness:** approved active scholarships whose last verified check is within the policy-defined freshness window ÷ approved active scholarships with a check policy | Credible data currency | [TBD window/target] |
| KPI-002 | **Source quality:** substantiated incorrect-listing reports ÷ unique approved listings viewed during the same cohort/window | Lower indicates fewer material inaccuracies; account for reporting exposure | [TBD] |
| KPI-003 | **Activation:** verified eligible new student accounts completing configured minimum profile fields ÷ verified eligible new student accounts | Onboarding usability | [TBD required fields/target] |
| KPI-004 | **Eligibility transparency:** evaluated results showing three-state eligibility plus evidence/unknowns where applicable ÷ evaluated results | Hard-rule explainability completeness | [TBD] |
| KPI-005 | **Match explainability:** scored results with criteria contributions, confidence/limitations and version ÷ all scored results | Explainable AI fulfillment | [TBD] |
| KPI-006 | **Document job success:** generation jobs with a usable preview ÷ started generation jobs, excluding explicitly user-cancelled jobs if cancellation semantics approved | Model and worker quality | [TBD] |
| KPI-007 | **Document usability:** successful readable PDF/DOCX exports ÷ attempted exports by format | File reliability | [TBD] |
| KPI-008 | **Confirmed submission conversion:** applications explicitly marked Submitted by their student ÷ applications created in the same eligible period | Workflow adoption; **not** evidence of verified external success | [TBD] |
| KPI-009 | **Extension quality:** fill attempts producing reviewed, usable field mapping ÷ eligible attempts on separately reported supported sites | Site-by-site compatibility | [TBD] |
| KPI-010 | **Ledger correctness:** count of unexplained financial differences, duplicate settled debits or duplicate payment grants in reconciliation window | Must show **zero known critical integrity violations** at release gate | 0 known critical violations; ongoing threshold review |
| KPI-011 | **Manual payment review performance:** reviewed requests within defined internal target ÷ eligible review requests | Operational responsiveness | [TBD] |
| KPI-012 | **Support first-reply SLA:** tickets receiving first human response within configured business-hour target ÷ tickets requiring human first response, by priority | Human coverage realism | [TBD priority target] |
| KPI-013 | **Support satisfaction:** mean/median rating and response count for resolved/closed tickets | Quality with sample-size context | [TBD] |
| KPI-014 | **Privacy execution:** confirmed deletion operations completed under approved policy; count of unauthorized file accesses | Trust and compliance | [TBD legal timetable]; zero known unauthorized exposure at launch gate |
| KPI-015 | **AI unit economics:** realized cost of AI services ÷ Credits revenue attributable to those services (with discount/free-grant accounting separately) | Sustainability, not yet priced | [TBD] |
| KPI-016 | **Pilot readiness:** proportion of predefined acceptance cases passing and severity of unresolved incidents during Palestinian-student pilot | Readiness to open public launch | [TBD gate]; all safety-critical cases pass |

**Do not use “scholarship admission rate” as an advertised AI prediction.** If collected later, an applicant outcome is self-reported unless independently verifiable, and depends heavily on external selection decisions beyond product control.

## 23. Acceptance Criteria

The following compact **Given / When / Then** tests are contractual acceptance examples, not exhaustive scripts. Each references its feature in Section 10. Run security, concurrency, localization and error-path variants alongside happy-path tests. Precise numeric/time inputs remain fixture-dependent where [TBD] appears.

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

### 23.1 Cross-cutting release gate

- **Release blocker:** any repeatable unauthorized cross-student file exposure; payment granting from unverified proof; duplicate Credit settlement; automatic submission of a scholarship application; collection of OTP/passwords by the extension; absence of required Admin MFA; demonstrably fabricated academic facts presented as verified; inability to enforce the account deletion/recovery policy.
- **Required test suites:** role/ownership API and download tests; Google/email registration age-gating; source-review change/dedup tests; matching with missing/failed hard criteria; document groundedness and export round-trip; frozen version and deletion interaction; portal allowlist and prohibited-field tests; concurrent debit/grant reconciliation; SLA math across holidays; long-running job interruption; Arabic/English RTL/LTR accessibility checks.
- **Pilot/UAT:** recruit Palestinian students across the three educational levels and trained Admin reviewers; evaluate actual permitted sources and third-party portals before general availability. Pilot size, pass-rate thresholds and approved performance budget are [TBD].

## 24. Future Features

These are **future candidates** rather than authorizations to implement; all need separate validation and a product-owner scope decision. Do not convert explicitly rejected MVP behavior into a current hidden requirement.

| Candidate ID | Potential future capability | Why deferred / constraints |
|---|---|---|
| FUT-001 | Expand geography beyond Palestinian-first rollout | Requires region-specific scholarship coverage, access and policy review |
| FUT-002 | More interface/document languages | Validate actual demand, quality and compliance |
| FUT-003 | Official scholarship-portal status integrations | Available only where explicit permission/APIs permit; preserve source-origin labeling |
| FUT-004 | Additional tested portal/browser combinations | Only after per-site legal and compatibility tests |
| FUT-005 | Additional document types and advanced templates | Four initial types already approved; prioritize evidence of usage |
| FUT-006 | More payment collection methods | Evaluate legality, availability and reconciliation; manual local transfer remains the MVP commitment |
| FUT-007 | Advanced comparative recommendation and career guidance | Requires new value, bias and reliability research; avoid admission probability claims |
| FUT-008 | Dedicated mobile application | Not needed to implement responsive web MVP; extension compatibility may differ |
| FUT-009 | AI-assisted iterative document editing | **Explicitly out of MVP**; consider only with new approval and strict factual review |
| FUT-010 | Additional delivery channels for notifications | **Explicitly out of MVP**; require opt-in, compliance and new business decision |

**Never carry forward as an implied future promise:** CAPTCHA/OTP circumvention, unauthorized portal submission, harvesting third-party passwords, admitting under-18 users under the current eligibility policy, or guaranteeing scholarship acceptance.

## 25. Risks & Dependencies

| ID | Risk or dependency | Impact | Response / owner | Severity |
|---|---|---|---|---|
| RSK-001 | Scholarship sites prohibit scraping or change structure | Legal exposure, catalog gaps | Approve allowed source inventory; monitor and provide Admin manual import — Product/Legal | High |
| RSK-002 | Incorrect or stale eligibility/deadline criteria | Student misses deadlines or relies on false fit | Verified provenance, review gates, date monitoring, qualified unknowns — Product/Admin | High |
| RSK-003 | Hallucinated AI scholarship/application facts | Student credibility and trust harmed | Confirmed-data grounding, review flags, sample testing, no acceptance prediction — Product/AI QA | High |
| RSK-004 | Browser extension unsafe/unstable across portals | Failed applications, privacy issues | Minimum permissions, portal/browser test matrix, no auto-submit, manual fallback — Engineering/Security | High |
| RSK-005 | Vulnerable data access/AI leakage | Exposure of academic documents or identities | Ownership tests, encryption, consent, audit and vendor restrictions — Security/Legal | Critical |
| RSK-006 | Fraudulent local transfer proof or duplicated approval | Direct financial loss | Independent receipt verification, unique reference and exactly-once ledger — Finance/Admin | Critical |
| RSK-007 | Unsettled AI jobs or partial provider failures | Balance disputes and missing documents | Reservation/reconciliation/idempotency and visible errors — Engineering/Finance | High |
| RSK-008 | MVP too broad for staff/budget | Slippage and incomplete testing | Controlled phase gates without stealth scope cuts — Product/Engineering | High |
| RSK-009 | Human support schedule cannot satisfy configured targets | SLA breaches and poor trust | Realistic calendar/priority targets, workforce/pilot measurement — Operations | High |
| RSK-010 | Unresolved local legal/retention/refund requirements | Launch blocker | Legal sign-off and policy/backup implementation before GA — Legal/Founder | Critical |
| RSK-011 | AI/service cost exceeds Credit income | Unsustainable unit economics | Measure real unit costs, quotas/pricing policies and financial dashboard — Finance/Product | High |
| RSK-012 | Nonexistent or weak official status integrations | Misleading tracking | Student-owned status and transparent source labels; integration optional — Product | Medium |
| RSK-013 | Match Score misread as acceptance probability | Misleading product claims | Explain eligibility separately; disclaimer on result — Product/UX | High |
| RSK-014 | Unclear Admin private-document exception | Unauthorized access or inability to assist | P0 permission policy; least-privilege default deny — Security/Product | High |
| RSK-015 | Deletion 30-day window inconsistent with backup/legal holds | Privacy/compliance breach | Retention map, backup deletion policy, recovery boundary test — Security/Legal | Critical |
| RSK-016 | No MinhaAI repository identified for documentation placement | PRD may not yet be in actual source-controlled `docs/` | Provide standalone `docs/PRD.md`; repository owner to add/commit when confirmed — Owner | Low |

### 25.1 Consistency and quality review

| Check | Finding | Resolution status |
|---|---|---|
| Product scope | Advanced MVP includes extension and AI/human support even if developed last | **Consistent**; no feature silently postponed beyond general release |
| Roles | Exactly Student and Admin; support AI/extension remain system actors | **Consistent**; exceptional Admin document permissions are [TBD] |
| Application ownership | External site does submission; MinhaAI records explicit student confirmation | **Consistent**; no automatic external submission |
| Eligibility versus relevance | Hard conditions are authoritative over high Match Score | **Consistent**; unknown mandatory fact never equals pass |
| Document mutability versus deletion | Submitted version frozen for editing; full account deletion can still remove it | **Consistent**; legal retention details [TBD] |
| Price changes versus delayed jobs | Price snapshot fixed at confirmation and settled once | **Consistent**; uncertain worker state reconciled before refund/settle |
| Credits never expire versus account deletion | Nonexpiring while active; frozen/canceled upon deletion process | **Consistent** when lifecycle rule is explicit |
| AI 24/7 versus human working-hours SLA | AI availability is not a promise of immediate human response | **Consistent**; wait-state pause policy [TBD] |
| Manual payment proof versus actual funds | Proof starts review; actual receipt required before approval | **Consistent**; real payment method [TBD] |
| Native notifications versus verification email | Product notices in-app; identity recovery/verification messages are operational exceptions | **Consistent** |
| Browser capability | Tested portals supported; other legal forms best effort; no broad compatibility guarantee | **Consistent**; exact sites/browser matrix [TBD] |
| Performance figures and providers | No unvalidated vendor, speed or cost figures made binding | **Consistent**; quantitative baselines [TBD] |
| Submission status vs official API | Student-reported only by default; future/conditional official source must be labeled | **Consistent**; conflict transitions [TBD] |
| Feature completeness | Each of F-01–F-15 has purpose, story, FRs, BRs, ECs, errors, ACs and priority | **Checked**; cross-reference validation below |

**Remaining implementation blockers are summarized in Section 26 rather than filled with assumptions.** The presence of an unresolved setting does not negate the confirmed behavior it configures, but an unapproved setting SHALL not be invented as a default in production.

## 26. Open Questions

`P0` must be resolved before a corresponding production implementation/launch decision can be accepted; `P1` before completion of the affected feature or final release validation; `P2` when relevant to future planning. Suggested owners are **planning suggestions [A]**, not roles added to the application.

| ID | Priority | Open decision, not resolved by interview | Proposed decision owner | Affected requirements |
|---|---|---|---|---|
| OQ-001 | P0 | Which **specific local payment providers/transfer accounts**, currencies, confirmation source and legal payment instructions are valid for launch? | Founder/Finance/Legal | FR-080–FR-088 |
| OQ-002 | P0 | What is the one-time signup Credit amount, available packages, individual AI service Credit prices, exchange assumptions, complimentary allowance and paid-service catalog? | Product/Finance | FR-005, FR-069–FR-079 |
| OQ-003 | P0 | Which initial permitted scholarship sources and third-party application portals are in the source/extension allowlist, and what are their terms? | Product/Legal/Engineering | FR-015–FR-024, FR-059–FR-068 |
| OQ-004 | P0 | Which AI providers/processors and data regions can contractually meet the **no-training-without-consent**, privacy and security constraints? | Security/Legal/Engineering | FR-012, FR-113–FR-115 |
| OQ-005 | P0 | What local/legal jurisdiction-specific Terms, Privacy Policy, lawful retention, refund and data-transfer obligations apply? | Legal/Founder | FR-088, FR-113–FR-121 |
| OQ-006 | P0 | What exact record types survive legal retention, for how long, and how are temporary files, backups and third-party processors erased after deletion? | Legal/Security | FR-116–FR-120 |
| OQ-007 | P0 | Which exceptional, justified Admin access to private support attachments/documents is allowed, with whose consent and what audit/approval? | Product/Security | FR-049, FR-110 |
| OQ-008 | P1 | What are the human working days, holidays, time zone, targets per priority, warning/escalation offsets and overdue routing? | Support/Operations | FR-101–FR-105 |
| OQ-009 | P1 | Does human SLA pause while **Awaiting Student**, and which other ticket states consume first-response/business time? | Support/Product | FR-099–FR-103 |
| OQ-010 | P1 | What is the auto-close delay, reopen eligibility/window and rating submission policy for resolved/closed tickets? | Support/Product | FR-099–FR-100 |
| OQ-011 | P1 | Which GPA scales, language proof types, academic-stage fields and incomplete-profile threshold are required for each level? | Product/Student research | FR-008–FR-014 |
| OQ-012 | P1 | Which mandatory eligibility criteria and documented default weights/confidence rules will be used for matching, and how will scoring quality be validated? | Product/AI QA | FR-028–FR-033 |
| OQ-013 | P1 | What are supported file formats (including image types), maximum bytes, per-user storage quota, malware scanning limits and file disposal timing? | Engineering/Security | FR-011, FR-050 |
| OQ-014 | P1 | What exact statuses, transitions, withdrawal/reapply behavior, duplicate application/round policy and official-vs-student status conflict precedence are authorized? | Product | FR-051–FR-058 |
| OQ-015 | P1 | Which browsers, extension versions, permitted form types and minimum site compatibility pass rate constitute launch support? | Engineering/QA | FR-059–FR-068 |
| OQ-016 | P1 | Which callback/timeout outcome determines “technical failure” of a paid AI operation, how long can a Credit reservation stay unresolved, and how are manual disputes reconciled? | Engineering/Finance | FR-074–FR-078 |
| OQ-017 | P1 | What is the initial deadline-alert offset, timezone interpretation policy, user preference model and notification deduplication window? | Product/Engineering | FR-023, FR-089–FR-092 |
| OQ-018 | P1 | What are quantitative performance goals, expected pilot/production load, availability target, worker retry cap, RPO/RTO, monitoring retention and backup intervals? | Engineering/Operations | NFR-017–NFR-023 |
| OQ-019 | P1 | What exact AI Support actions beyond guidance are authorized with student consent, and what escalation confidence/failure thresholds apply? | Product/Security/Support | FR-095–FR-098 |
| OQ-020 | P1 | What is the treatment of account recovery **exactly** at the 30-day cutoff and how do calendar/timezone boundaries work? | Product/Legal | FR-117–FR-120 |
| OQ-021 | P1 | What are release acceptance percentiles and pilot size/cohort, plus formal go/no-go sign-off roles and criteria? | Product/QA | KPI-001–KPI-016, D65 |
| OQ-022 | P1 | Is public scholarship browsing available before login or is browsing restricted to active students? The prior decisions only establish that search is **free**, not anonymous. | Product | SCR-001/SCR-007, FR-069 |
| OQ-023 | P1 | Which event/analytics services, retention, consent and dashboard cohort privacy controls will be approved? | Security/Product | EVT-001–EVT-018 |
| OQ-024 | P1 | Is the repository that should receive `docs/PRD.md` on GitHub, elsewhere, or local only? No connected MinhaAI repo was identified. | Repository owner | Document delivery |
| OQ-025 | P2 | Which competitor benchmarks and design references (if any) should guide later UX research? | Product/Design | Future design research |
| OQ-026 | P2 | Which additional geographies, languages, payment methods or document types warrant future investment? | Product/Strategy | FUT-001–FUT-006 |

**Explicit boundary on assumptions.** Personas, suggested operational ownership, metadata names, telemetry event names, protected audit details, and proposed test infrastructure are analytical documentation conveniences. They are **not** approvals of financial amounts, staffing commitments, service hours, legal policy, vendors, per-browser support or admission probabilities. No critical unresolved requirement has been silently converted to a product decision.

## 27. Recommended Development Phases

**This is a sequencing recommendation, not a development task breakdown or a scope reduction.** All approved feature capabilities remain within the declared Advanced MVP before general availability; follow-on artifacts (user-flow diagrams, ERD, UI, code and sprint tasks) must be commissioned separately.

| Phase | Product outcome / included feature set | Entry decisions | Exit/verification gate |
|---|---|---|---|
| Phase 0 — Validation and release policy | Confirm P0 source/portal legality, payment rails, prices, AI privacy vendors, retention, scope governance and source-of-truth PRD | Review OQ-001–OQ-007 and repo destination | Signed/recorded critical business policies; no hidden assumptions |
| Phase 1 — Accounts and trusted scholarship foundation | Identity/age/Google, bilingual student profile, consented extraction, permitted source catalog, Admin approval, basic search, mandatory eligibility and notification foundation | Profile schema, approved sources, access policy | No unapproved listings; age/auth/ownership tests pass; missing facts remain unknown |
| Phase 2 — Application intelligence, documents and payments | Explainable AI/RAG score, full filters, documents editor/export/library/versions, application tracker, Credit pricing/reservations/ledger and local manual payments | Weights and AI policy, packages/prices, finance confirmation, status rules | Grounded document tests, PDF/DOCX validity, frozen versions, duplicate-grant/debit tests pass |
| Phase 3 — Extension, support and operational hardening | Permitted-site browser autofill, AI-human ticket handling, working-hours SLA, source change monitoring, analytics, privacy/deletion and resilient jobs | Portal/browser matrix, support policy, retention/backup mapping | Extension no-auto-submit/security tests, SLA math, deletion/recovery, job reconciliation pass |
| Phase 4 — Closed Palestinian-student pilot | Real-user and real-Admin testing across Bachelor's/Master's/PhD, with approved source/portal coverage and recorded feedback | Pilot criteria, lawful external sources and payments | Release-gate incidents closed, KPI baselines established, operational cost/risk reviewed |
| Phase 5 — General Advanced MVP release | Production availability with user support and ongoing catalog monitoring | All P0/P1 launch blockers resolved and accepted | Product owner go/no-go, security/legal approval, acceptance suite and finance reconciliation clean |
| Phase 6 — Post-MVP discovery | Reassess geographic growth, official integrations and deferred capabilities | Pilot learnings and separate approval | New PRD/change control for any scope addition |

### 27.1 Release readiness checklist

- [ ] Product owner acknowledges the 67-decision provenance and signs off this revision, including delegated decisions 47–67.
- [ ] Complete all P0 legal/source/payments/AI-provider/retention/permission decisions, and feature-blocking P1 values.
- [ ] Every F-01–F-15 feature meets its referenced FR, BR and AC tests, including error/edge paths.
- [ ] Role/ownership tests confirm no cross-student file leaks; every production Admin requires MFA.
- [ ] Scholarship publication and material-update reviews preserve approved-source provenance.
- [ ] AI produces no unverified asserted credentials in adversarial acceptance tests; score never implies admission probability.
- [ ] Extension supports the agreed tested sites, does not handle CAPTCHA/OTP/passwords and never submits applications.
- [ ] Wallet/payment ledger reconciles exactly; manual payments credit only verified received funds.
- [ ] Submitted application versions remain immutable during normal usage and removable under lawful deletion.
- [ ] Human support SLA passes tests over working hours/holidays; AI 24/7 is represented without fake human availability.
- [ ] Arabic/English RTL/LTR, responsiveness and accessible controls pass documented acceptance checks.
- [ ] A closed initial student pilot and Admin review validate functionality, security, economics and real third-party compatibility.
- [ ] The final artifact is committed to the **actual** project's `docs/PRD.md` once repository identity and permissions are confirmed.

### 27.2 Final change-control statement

This PRD is the **implementation-facing functional baseline** for MinhaAI. It is intentionally detailed enough to prepare separate screen flows, data modeling, architecture decisions and test specifications **without beginning implementation**. Every material departure from a confirmed [P] decision or a delegated [D] decision requires recorded owner approval. Open questions remain in Section 26 until resolved. No application code, ERD, UI designs or engineering tasks are part of this deliverable.
