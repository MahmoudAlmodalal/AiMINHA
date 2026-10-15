# Product backlog — traceable implementation handoff

2026-10-15. **Backlog artifact complete; all implementation stories TODO.** Sources are the supplied PRD, owner Beta choices and UD-001/002. [Matrix](../docs/specs/feature-matrix.md), [rules](../docs/specs/business-rules.md), [GWT scenarios](../docs/specs/acceptance-scenarios.md), [gates](../docs/specs/missing-inputs.md). Requirements marked Must remain Must; disabled/gated Advanced work is not relabeled P2. No app/UX/bootstrap code is authorized in this run.

## Epics and dependencies

Dependency edges here are feature delivery prerequisites, not a recommendation to mutate cross-module tables. Shared foundation E-15 can be designed/bootstrapped before its later handlers, avoiding a false implementation cycle with Credits/documents. One integrator controls contract/schema dependencies; no agent delegation is implied.

| Epic | Source / module | Delivery dependency | Priority / release / status | Acceptance |
|---|---|---|---|---|
| E-01 Identity and adult activation | F-01; FR-001–FR-007; identity | documented architecture/bootstrap (phase05) | Must; Beta core; TODO | CASE-FR-001..007; AC-001–AC-003; gate G-PROFILE |
| E-02 Reviewed profile and extraction | F-02; FR-008–FR-014; identity/files/ai_gateway | E-01 | Must; Beta; extraction gated; TODO | CASE-FR-008..014; AC-004–AC-005; gate G-PROFILE/G-SCANNER/G-PROVIDER |
| E-03 Permitted reviewed catalog | F-03; FR-015–FR-024; scholarships | E-01 | Must; Beta; ingestion gated; TODO | CASE-FR-015..024; AC-006–AC-008; gate G-SOURCE |
| E-04 Search, deterministic eligibility and match | F-04; FR-025–FR-033; scholarships/eligibility | E-02, E-03 | Must; Beta; AI/semantic route gated; TODO | CASE-FR-025..033; AC-009–AC-012; gate G-SOURCE/G-PROFILE/G-PROVIDER/G-MEASURE |
| E-05 Generation, review and export | F-05; FR-034–FR-042; documents/files/ai_gateway/credits | E-02, E-04, E-09, E-15 | Must; Beta; generation/export dependencies gated; TODO | CASE-FR-034..042; AC-013–AC-015; gate G-PROVIDER/G-SCANNER |
| E-06 Private library and immutable versions | F-06; FR-043–FR-050; documents/files | E-02, E-05 | Must; Beta; upload/export gated; TODO | CASE-FR-043..050; AC-016–AC-017; gate G-SCANNER/G-LEGAL |
| E-07 Applications, checklist and frozen submission | F-07; FR-051–FR-058; applications/notifications | E-03, E-06 | Must; Beta; official integration conditional; TODO | CASE-FR-051..058; AC-018–AC-019; gate G-STATUS/G-SOURCE |
| E-08 Review-only Chrome extension | F-08; FR-059–FR-068; extension/identity/applications | E-01, E-02, E-07 | Must; Beta gated / required Advanced MVP; TODO | CASE-FR-059..068; AC-020–AC-022; gate G-EXT |
| E-09 Credits and exactly-once operations | F-09; FR-069–FR-079; credits/configuration | E-01, E-15 | Must; Beta credits; paid packages unavailable; TODO | CASE-FR-069..079; AC-023–AC-025; gate G-LEGAL/G-PAID |
| E-10 Manual payments | F-10; FR-080–FR-088; payments/credits/files | E-06, E-09 | Must; Advanced paid; disabled Beta; TODO | CASE-FR-080..088; AC-026–AC-028; gate G-PAID/G-SCANNER |
| E-11 Typed in-app notification center | F-11; FR-089–FR-093; notifications | E-01, E-03, E-07 | Must; Beta core; affected domains gated; TODO | CASE-FR-089..093; AC-029–AC-030; gate G-LEGAL |
| E-12 AI/human tickets and business-hour SLA | F-12; FR-094–FR-105; support/notifications | E-01, E-09, E-11, E-15 | Must; Beta human core; AI and rating/escalation gated; TODO | CASE-FR-094..105; AC-031–AC-034; gate G-TICKET/G-PROVIDER/G-SCANNER |
| E-13 Scoped Admin governance and audit | F-13; FR-106–FR-112; configuration/audit | E-01, E-03, E-09, E-12 | Must; Beta operational; payment controls disabled; TODO | CASE-FR-106..112; AC-035–AC-036; gate G-SIGNOFF/G-MEASURE |
| E-14 Consent, configurable recovery and erasure | F-14; FR-113–FR-121; identity/files/audit | E-01, E-06, E-09 | Must; Beta design; real use legal-gated; TODO | CASE-FR-113..121; AC-037–AC-039; gate G-LEGAL/G-RESTORE/G-PROVIDER |
| E-15 Recoverable asynchronous processing | F-15; FR-122–FR-125; jobs/ai_gateway/audit | E-01 | Must; Beta core; actual handlers dependency-gated; TODO | CASE-FR-122..125; AC-040–AC-041; gate G-HOSTING/G-PROVIDER |

## Original source user stories — Given/When/Then paths

### US-001 — TODO

As an adult student, I want to register with email/password or Google so that I can use the service securely.

Epic/source: F-01; FR-001–FR-007. Module: identity. Priority: Must. Release: Beta core. Dependencies: phase05 foundation. Gate: G-PROFILE.

Given the source fixtures for AC-001–AC-003, when the story's student/Admin action occurs under the documented ownership/policy branches, then the exact source Given/When/Then outcomes in AC-001–AC-003 and CASE-FR-001..007 must pass. The referenced scenario rows contain concrete actions and expected persisted/response evidence, including duplicate, stale and cross-owner paths.

Deliver as an owned domain-service/database → server-authorized API → translated accessible UI → integration/adversarial test slice. Do not implement a feature with unresolved gate by inventing a provider, policy or personal fact. Test execution: NOT RUN; this is backlog planning.

### US-002 — TODO

As a student, I want to create a profile manually or extract facts from my CV and approve them before use.

Epic/source: F-02; FR-008–FR-014. Module: identity/files/ai_gateway. Priority: Must. Release: Beta; extraction gated. Dependencies: E-01. Gate: G-PROFILE/G-SCANNER/G-PROVIDER.

Given the source fixtures for AC-004–AC-005, when the story's student/Admin action occurs under the documented ownership/policy branches, then the exact source Given/When/Then outcomes in AC-004–AC-005 and CASE-FR-008..014 must pass. The referenced scenario rows contain concrete actions and expected persisted/response evidence, including duplicate, stale and cross-owner paths.

Deliver as an owned domain-service/database → server-authorized API → translated accessible UI → integration/adversarial test slice. Do not implement a feature with unresolved gate by inventing a provider, policy or personal fact. Test execution: NOT RUN; this is backlog planning.

### US-003 — TODO

As an admin, I want to review an imported scholarship before students can discover it.

Epic/source: F-03; FR-015–FR-024. Module: scholarships. Priority: Must. Release: Beta; ingestion gated. Dependencies: E-01. Gate: G-SOURCE.

Given the source fixtures for AC-006–AC-008, when the story's student/Admin action occurs under the documented ownership/policy branches, then the exact source Given/When/Then outcomes in AC-006–AC-008 and CASE-FR-015..024 must pass. The referenced scenario rows contain concrete actions and expected persisted/response evidence, including duplicate, stale and cross-owner paths.

Deliver as an owned domain-service/database → server-authorized API → translated accessible UI → integration/adversarial test slice. Do not implement a feature with unresolved gate by inventing a provider, policy or personal fact. Test execution: NOT RUN; this is backlog planning.

### US-004 — TODO

As a student, I want to search and filter trustworthy scholarships by education level, discipline, funding and deadline.

Epic/source: F-04; FR-025–FR-033. Module: scholarships/eligibility. Priority: Must. Release: Beta; AI/semantic route gated. Dependencies: E-02, E-03. Gate: G-SOURCE/G-PROFILE/G-PROVIDER/G-MEASURE.

Given the source fixtures for AC-009–AC-012, when the story's student/Admin action occurs under the documented ownership/policy branches, then the exact source Given/When/Then outcomes in AC-009–AC-012 and CASE-FR-025..033 must pass. The referenced scenario rows contain concrete actions and expected persisted/response evidence, including duplicate, stale and cross-owner paths.

Deliver as an owned domain-service/database → server-authorized API → translated accessible UI → integration/adversarial test slice. Do not implement a feature with unresolved gate by inventing a provider, policy or personal fact. Test execution: NOT RUN; this is backlog planning.

### US-005 — TODO

As a student, I want to see eligible, unknown and ineligible criteria separately from a fit score.

Epic/source: F-04; FR-025–FR-033. Module: scholarships/eligibility. Priority: Must. Release: Beta; AI/semantic route gated. Dependencies: E-02, E-03. Gate: G-SOURCE/G-PROFILE/G-PROVIDER/G-MEASURE.

Given the source fixtures for AC-009–AC-012, when the story's student/Admin action occurs under the documented ownership/policy branches, then the exact source Given/When/Then outcomes in AC-009–AC-012 and CASE-FR-025..033 must pass. The referenced scenario rows contain concrete actions and expected persisted/response evidence, including duplicate, stale and cross-owner paths.

Deliver as an owned domain-service/database → server-authorized API → translated accessible UI → integration/adversarial test slice. Do not implement a feature with unresolved gate by inventing a provider, policy or personal fact. Test execution: NOT RUN; this is backlog planning.

### US-006 — TODO

As a student with an incomplete profile, I want a clearly qualified partial match rather than false certainty.

Epic/source: F-04; FR-025–FR-033. Module: scholarships/eligibility. Priority: Must. Release: Beta; AI/semantic route gated. Dependencies: E-02, E-03. Gate: G-SOURCE/G-PROFILE/G-PROVIDER/G-MEASURE.

Given the source fixtures for AC-009–AC-012, when the story's student/Admin action occurs under the documented ownership/policy branches, then the exact source Given/When/Then outcomes in AC-009–AC-012 and CASE-FR-025..033 must pass. The referenced scenario rows contain concrete actions and expected persisted/response evidence, including duplicate, stale and cross-owner paths.

Deliver as an owned domain-service/database → server-authorized API → translated accessible UI → integration/adversarial test slice. Do not implement a feature with unresolved gate by inventing a provider, policy or personal fact. Test execution: NOT RUN; this is backlog planning.

### US-007 — TODO

As a student, I want a truthful scholarship-specific CV or essay, edited by me and exported to PDF/DOCX.

Epic/source: F-05; FR-034–FR-042. Module: documents/files/ai_gateway/credits. Priority: Must. Release: Beta; generation/export dependencies gated. Dependencies: E-02, E-04, E-09, E-15. Gate: G-PROVIDER/G-SCANNER.

Given the source fixtures for AC-013–AC-015, when the story's student/Admin action occurs under the documented ownership/policy branches, then the exact source Given/When/Then outcomes in AC-013–AC-015 and CASE-FR-034..042 must pass. The referenced scenario rows contain concrete actions and expected persisted/response evidence, including duplicate, stale and cross-owner paths.

Deliver as an owned domain-service/database → server-authorized API → translated accessible UI → integration/adversarial test slice. Do not implement a feature with unresolved gate by inventing a provider, policy or personal fact. Test execution: NOT RUN; this is backlog planning.

### US-008 — TODO

As a student, I want to compare/revert revisions while preserving the exact version attached to a submitted application.

Epic/source: F-06; FR-043–FR-050. Module: documents/files. Priority: Must. Release: Beta; upload/export gated. Dependencies: E-02, E-05. Gate: G-SCANNER/G-LEGAL.

Given the source fixtures for AC-016–AC-017, when the story's student/Admin action occurs under the documented ownership/policy branches, then the exact source Given/When/Then outcomes in AC-016–AC-017 and CASE-FR-043..050 must pass. The referenced scenario rows contain concrete actions and expected persisted/response evidence, including duplicate, stale and cross-owner paths.

Deliver as an owned domain-service/database → server-authorized API → translated accessible UI → integration/adversarial test slice. Do not implement a feature with unresolved gate by inventing a provider, policy or personal fact. Test execution: NOT RUN; this is backlog planning.

### US-009 — TODO

As a student, I want to save scholarships, organize requirements and confirm submissions myself.

Epic/source: F-07; FR-051–FR-058. Module: applications/notifications. Priority: Must. Release: Beta; official integration conditional. Dependencies: E-03, E-06. Gate: G-STATUS/G-SOURCE.

Given the source fixtures for AC-018–AC-019, when the story's student/Admin action occurs under the documented ownership/policy branches, then the exact source Given/When/Then outcomes in AC-018–AC-019 and CASE-FR-051..058 must pass. The referenced scenario rows contain concrete actions and expected persisted/response evidence, including duplicate, stale and cross-owner paths.

Deliver as an owned domain-service/database → server-authorized API → translated accessible UI → integration/adversarial test slice. Do not implement a feature with unresolved gate by inventing a provider, policy or personal fact. Test execution: NOT RUN; this is backlog planning.

### US-010 — TODO

As a student, I want a browser extension to propose and fill allowed fields only after explicit review.

Epic/source: F-08; FR-059–FR-068. Module: extension/identity/applications. Priority: Must. Release: Beta gated / required Advanced MVP. Dependencies: E-01, E-02, E-07. Gate: G-EXT.

Given the source fixtures for AC-020–AC-022, when the story's student/Admin action occurs under the documented ownership/policy branches, then the exact source Given/When/Then outcomes in AC-020–AC-022 and CASE-FR-059..068 must pass. The referenced scenario rows contain concrete actions and expected persisted/response evidence, including duplicate, stale and cross-owner paths.

Deliver as an owned domain-service/database → server-authorized API → translated accessible UI → integration/adversarial test slice. Do not implement a feature with unresolved gate by inventing a provider, policy or personal fact. Test execution: NOT RUN; this is backlog planning.

### US-011 — TODO

As a student, I want a Credit price before using a chargeable service and no debit for technical failure.

Epic/source: F-09; FR-069–FR-079. Module: credits/configuration. Priority: Must. Release: Beta credits; paid packages unavailable. Dependencies: E-01, E-15. Gate: G-LEGAL/G-PAID.

Given the source fixtures for AC-023–AC-025, when the story's student/Admin action occurs under the documented ownership/policy branches, then the exact source Given/When/Then outcomes in AC-023–AC-025 and CASE-FR-069..079 must pass. The referenced scenario rows contain concrete actions and expected persisted/response evidence, including duplicate, stale and cross-owner paths.

Deliver as an owned domain-service/database → server-authorized API → translated accessible UI → integration/adversarial test slice. Do not implement a feature with unresolved gate by inventing a provider, policy or personal fact. Test execution: NOT RUN; this is backlog planning.

### US-012 — TODO

As a student, I want to purchase a Credit package via locally available transfer and track admin review.

Epic/source: F-10; FR-080–FR-088. Module: payments/credits/files. Priority: Must. Release: Advanced paid; disabled Beta. Dependencies: E-06, E-09. Gate: G-PAID/G-SCANNER.

Given the source fixtures for AC-026–AC-028, when the story's student/Admin action occurs under the documented ownership/policy branches, then the exact source Given/When/Then outcomes in AC-026–AC-028 and CASE-FR-080..088 must pass. The referenced scenario rows contain concrete actions and expected persisted/response evidence, including duplicate, stale and cross-owner paths.

Deliver as an owned domain-service/database → server-authorized API → translated accessible UI → integration/adversarial test slice. Do not implement a feature with unresolved gate by inventing a provider, policy or personal fact. Test execution: NOT RUN; this is backlog planning.

### US-013 — TODO

As a student, I want relevant in-app notices about scholarships, applications, payments and tickets.

Epic/source: F-11; FR-089–FR-093. Module: notifications. Priority: Must. Release: Beta core; affected domains gated. Dependencies: E-01, E-03, E-07. Gate: G-LEGAL.

Given the source fixtures for AC-029–AC-030, when the story's student/Admin action occurs under the documented ownership/policy branches, then the exact source Given/When/Then outcomes in AC-029–AC-030 and CASE-FR-089..093 must pass. The referenced scenario rows contain concrete actions and expected persisted/response evidence, including duplicate, stale and cross-owner paths.

Deliver as an owned domain-service/database → server-authorized API → translated accessible UI → integration/adversarial test slice. Do not implement a feature with unresolved gate by inventing a provider, policy or personal fact. Test execution: NOT RUN; this is backlog planning.

### US-014 — TODO

As a student, I want 24/7 AI support and human escalation for complex or sensitive cases.

Epic/source: F-12; FR-094–FR-105. Module: support/notifications. Priority: Must. Release: Beta human core; AI and rating/escalation gated. Dependencies: E-01, E-09, E-11, E-15. Gate: G-TICKET/G-PROVIDER/G-SCANNER.

Given the source fixtures for AC-031–AC-034, when the story's student/Admin action occurs under the documented ownership/policy branches, then the exact source Given/When/Then outcomes in AC-031–AC-034 and CASE-FR-094..105 must pass. The referenced scenario rows contain concrete actions and expected persisted/response evidence, including duplicate, stale and cross-owner paths.

Deliver as an owned domain-service/database → server-authorized API → translated accessible UI → integration/adversarial test slice. Do not implement a feature with unresolved gate by inventing a provider, policy or personal fact. Test execution: NOT RUN; this is backlog planning.

### US-015 — TODO

As an admin, I want configurable business-hour SLA, escalation and operational reporting.

Epic/source: F-12/F-13; FR-094–FR-105. Module: support/notifications. Priority: Must. Release: Beta human core; AI and rating/escalation gated. Dependencies: E-01, E-09, E-11, E-15. Gate: G-TICKET/G-PROVIDER/G-SCANNER.

Given the source fixtures for AC-031–AC-034, when the story's student/Admin action occurs under the documented ownership/policy branches, then the exact source Given/When/Then outcomes in AC-031–AC-034 and CASE-FR-094..105 must pass. The referenced scenario rows contain concrete actions and expected persisted/response evidence, including duplicate, stale and cross-owner paths.

Deliver as an owned domain-service/database → server-authorized API → translated accessible UI → integration/adversarial test slice. Do not implement a feature with unresolved gate by inventing a provider, policy or personal fact. Test execution: NOT RUN; this is backlog planning.

### US-016 — TODO

As a student, I want to delete my account, recover it within 30 days, and know what data is retained.

Epic/source: F-14; FR-113–FR-121. Module: identity/files/audit. Priority: Must. Release: Beta design; real use legal-gated. Dependencies: E-01, E-06, E-09. Gate: G-LEGAL/G-RESTORE/G-PROVIDER.

Given the source fixtures for AC-037–AC-039, when the story's student/Admin action occurs under the documented ownership/policy branches, then the exact source Given/When/Then outcomes in AC-037–AC-039 and CASE-FR-113..121 must pass. The referenced scenario rows contain concrete actions and expected persisted/response evidence, including duplicate, stale and cross-owner paths.

Deliver as an owned domain-service/database → server-authorized API → translated accessible UI → integration/adversarial test slice. Do not implement a feature with unresolved gate by inventing a provider, policy or personal fact. Test execution: NOT RUN; this is backlog planning.

### US-017 — TODO

As an admin, I want to review scholarship data reports and suspend unsafe listings.

Epic/source: F-03/F-13; FR-015–FR-024. Module: scholarships. Priority: Must. Release: Beta; ingestion gated. Dependencies: E-01. Gate: G-SOURCE.

Given the source fixtures for AC-006–AC-008, when the story's student/Admin action occurs under the documented ownership/policy branches, then the exact source Given/When/Then outcomes in AC-006–AC-008 and CASE-FR-015..024 must pass. The referenced scenario rows contain concrete actions and expected persisted/response evidence, including duplicate, stale and cross-owner paths.

Deliver as an owned domain-service/database → server-authorized API → translated accessible UI → integration/adversarial test slice. Do not implement a feature with unresolved gate by inventing a provider, policy or personal fact. Test execution: NOT RUN; this is backlog planning.

### US-018 — TODO

As an admin, I want to detect duplicate transfer references and safely reconcile Credits.

Epic/source: F-09/F-10; FR-069–FR-079. Module: credits/configuration. Priority: Must. Release: Beta credits; paid packages unavailable. Dependencies: E-01, E-15. Gate: G-LEGAL/G-PAID.

Given the source fixtures for AC-023–AC-025, when the story's student/Admin action occurs under the documented ownership/policy branches, then the exact source Given/When/Then outcomes in AC-023–AC-025 and CASE-FR-069..079 must pass. The referenced scenario rows contain concrete actions and expected persisted/response evidence, including duplicate, stale and cross-owner paths.

Deliver as an owned domain-service/database → server-authorized API → translated accessible UI → integration/adversarial test slice. Do not implement a feature with unresolved gate by inventing a provider, policy or personal fact. Test execution: NOT RUN; this is backlog planning.

### US-019 — TODO

As a student, I want to see a tracked progress/error state when AI or file processing takes time.

Epic/source: F-15; FR-122–FR-125. Module: jobs/ai_gateway/audit. Priority: Must. Release: Beta core; actual handlers dependency-gated. Dependencies: E-01. Gate: G-HOSTING/G-PROVIDER.

Given the source fixtures for AC-040–AC-041, when the story's student/Admin action occurs under the documented ownership/policy branches, then the exact source Given/When/Then outcomes in AC-040–AC-041 and CASE-FR-122..125 must pass. The referenced scenario rows contain concrete actions and expected persisted/response evidence, including duplicate, stale and cross-owner paths.

Deliver as an owned domain-service/database → server-authorized API → translated accessible UI → integration/adversarial test slice. Do not implement a feature with unresolved gate by inventing a provider, policy or personal fact. Test execution: NOT RUN; this is backlog planning.

## Prioritized slice order and P2 boundary

P0 implementation foundations: identity/adult/MFA/session/owner isolation, immutable policy/consent/audit, permitted catalog, queue fencing, journal/idempotency/limits and deletion cancellation. Establish scanner/private storage and approved AI/free budget before dependent features. P1 delivery completes documented matching/document/application/notification/support/extension experience and operational reporting; these remain Must for the stated Advanced MVP. E-10 is held for explicit paid-release approval and its real financial policy, never enabled by Beta settings.

Future candidates FUT-001–FUT-010 (new geography/locales/types/mobile/advanced guidance/channels/AI iterative editing) require separate scope decisions; prohibited automation/OTP/password capture/underage accounts/admission guarantees never enter the implementation backlog. Phase04 UX and phase05 bootstrap are next only under separate authorization. This file creates no runtime tasks automatically and no paid resources.
