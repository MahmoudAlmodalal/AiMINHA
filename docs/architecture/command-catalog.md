# HTTP command/query catalog

2026-10-15. Documentation only. Routes below use `/api/v1`, the [OpenAPI 0.2.0 draft](openapi.json), [transport/error protocol](api-contracts.md), [domain contracts](domain-contracts.md) and [identity/extension proof flow](identity-and-extension-contracts.md). Request DTOs reject unknown fields; even schema-valid values require semantic ownership/snapshot/policy checks. List/replay/response authorization is current, not cached. No paid package/payment routes are enabled in Beta.

`If-Match` binds the target aggregate version; for collection policy creation it binds the current policy head, and for application requirement subresources it binds the application head. The schema requires it explicitly wherever stale writes could lose a version. Unsafe cookie routes require CSRF; cookie-free extension code exchange has the explicit one-use PKCE/origin proof exception and rejects cookies. Auth entry idempotency is scoped to pre-auth session+route+canonical target, never a global key that could leak another user's registration result. All sensitive responses no-store.

| Method / route | Request → success DTO | Actor proof | Concurrency / source / gate |
|---|---|---|---|
| GET `/session/csrf` | none → 200 CsrfView | public | read-only; A/D/P original contract; auth/lifecycle |
| POST `/session/login` | LoginRequest → 200 SessionView | public | X-CSRFToken; A/D/P original contract; auth/lifecycle |
| GET `/session` | none → 200 SessionView | authenticated | read-only; A/D/P original contract; auth/lifecycle |
| POST `/session/logout` | none → 204 none | authenticated | X-CSRFToken; A/D/P original contract; auth/lifecycle |
| GET `/scholarships` | none → 200 ScholarshipPage | public | read-only; A/D/P original contract; auth/lifecycle |
| POST `/operations/document-generations` | GenerationRequest → 202 OperationView | verified_active_adult_owner | X-CSRFToken, Idempotency-Key; A/D/P original contract; auth/lifecycle |
| GET `/operations/{operation_id}` | none → 200 OperationView | verified_active_adult_owner | read-only; A/D/P original contract; auth/lifecycle |
| POST `/files/uploads` | UploadRequest → 201 UploadSession | verified_active_adult_owner | X-CSRFToken, Idempotency-Key; A/D/P original contract; auth/lifecycle |
| POST `/files/{file_id}/complete` | CompleteUploadRequest → 202 FileView | verified_active_adult_owner | X-CSRFToken, Idempotency-Key; A/D/P original contract; auth/lifecycle |
| GET `/files/{file_id}` | none → 200 FileView | verified_active_adult_owner | read-only; A/D/P original contract; auth/lifecycle |
| DELETE `/files/{file_id}` | none → 202 AckView | verified_active_adult_owner | X-CSRFToken, If-Match; FR-116; G-LEGAL |
| POST `/files/{file_id}/download-capabilities` | DownloadRequest → 201 DownloadCapability | verified_active_adult_owner_or_assigned_support_explicit_attachment | X-CSRFToken; A/D/P original contract; auth/lifecycle |
| POST `/admin/scholarships/{scholarship_id}/publish` | PublishRequest → 200 ScholarshipView | admin_mfa_moderation_scope | If-Match, X-CSRFToken, Idempotency-Key; A/D/P original contract; auth/lifecycle |
| POST `/auth/registrations` | SignupRequest → 202 AckView | public | X-CSRFToken, Idempotency-Key; FR-001/004; G-PROFILE |
| POST `/auth/email-verifications` | ChallengeRequest → 200 AckView | public | X-CSRFToken, Idempotency-Key; FR-002/005; auth/lifecycle |
| POST `/auth/password-reset-requests` | EmailRequest → 202 AckView | public | X-CSRFToken, Idempotency-Key; FR-006; auth/lifecycle |
| POST `/auth/password-resets` | ResetPasswordRequest → 200 AckView | public | X-CSRFToken, Idempotency-Key; FR-006; auth/lifecycle |
| POST `/auth/google/authorizations` | GoogleStartRequest → 200 AuthorizationView | public | X-CSRFToken, Idempotency-Key; FR-003; G-SIGNOFF |
| POST `/auth/google/callbacks` | GoogleCallbackRequest → 200 SessionView | public | X-CSRFToken, Idempotency-Key; FR-003; G-SIGNOFF |
| POST `/auth/google/activation` | GoogleCompleteRequest → 200 AckView | preactivation_owned_identity | X-CSRFToken, Idempotency-Key; FR-003/004/005; G-PROFILE |
| POST `/admin/mfa/challenges` | none → 201 MfaChallengeView | admin_pre_mfa_own_auth | X-CSRFToken, Idempotency-Key; FR-007; auth/lifecycle |
| POST `/admin/mfa/verifications` | MfaRequest → 200 SessionView | admin_pre_mfa_own_auth | X-CSRFToken, Idempotency-Key; FR-007; auth/lifecycle |
| GET `/profile` | none → 200 ProfileView | verified_active_adult_owner | read-only; FR-008; auth/lifecycle |
| PUT `/profile` | ProfileRequest → 200 ProfileView | verified_active_adult_owner | X-CSRFToken, Idempotency-Key, If-Match; FR-008/009/010/013/014; G-PROFILE |
| GET `/consents` | none → 200 ConsentView | verified_active_adult_owner | read-only; FR-113; auth/lifecycle |
| POST `/consents` | ConsentRequest → 201 ConsentView | verified_active_adult_owner | X-CSRFToken, Idempotency-Key, If-Match; FR-012/113; G-PROVIDER |
| GET `/consents/disclosures` | none → 200 DisclosurePage | verified_active_adult_owner | read-only; FR-012/113; auth/lifecycle |
| POST `/account/deletions` | DeletionRequest → 201 DeletionView | verified_active_adult_owner_recent_reauth | X-CSRFToken, Idempotency-Key; FR-116/117; G-LEGAL |
| POST `/account/recovery-requests` | EmailRequest → 202 AckView | public | X-CSRFToken, Idempotency-Key; FR-118; G-LEGAL |
| POST `/account/restorations` | ChallengeRequest → 200 AckView | recovery_proof | X-CSRFToken, Idempotency-Key; FR-118; G-LEGAL |
| GET `/scholarships/{scholarship_id}` | none → 200 ScholarshipDetailView | public | read-only; FR-021/022/023/027; G-SOURCE |
| POST `/scholarships/{scholarship_id}/reports` | SourceReportRequest → 201 CommandResult | verified_active_adult_owner | X-CSRFToken, Idempotency-Key; FR-024; G-SOURCE |
| GET `/saved-opportunities` | none → 200 ScholarshipPage | verified_active_adult_owner | read-only; FR-051; auth/lifecycle |
| PUT `/saved-opportunities/{scholarship_id}` | SaveRequest → 200 CommandResult | verified_active_adult_owner | X-CSRFToken, Idempotency-Key; FR-051; auth/lifecycle |
| POST `/eligibility-evaluations` | EligibilityRequest → 201 EligibilityView | verified_active_adult_owner | X-CSRFToken, Idempotency-Key; FR-028/029/031/032/033; G-PROFILE |
| POST `/quotes` | QuoteRequest → 200 QuoteView | verified_active_adult_owner | X-CSRFToken, Idempotency-Key; FR-038/072/073; G-PROVIDER |
| POST `/operations/cv-extractions` | ExtractionRequest → 202 OperationView | verified_active_adult_owner | X-CSRFToken, Idempotency-Key; FR-011/012/013; G-PROVIDER/G-SCANNER |
| POST `/operations/match-explanations` | MatchRequest → 202 OperationView | verified_active_adult_owner | X-CSRFToken, Idempotency-Key; FR-030; G-PROVIDER |
| POST `/operations/support-replies` | SupportAiRequest → 202 OperationView | verified_active_adult_owner | X-CSRFToken, Idempotency-Key; FR-095/098; G-PROVIDER |
| GET `/wallet` | none → 200 WalletView | verified_active_adult_owner | read-only; FR-071/078; auth/lifecycle |
| GET `/wallet/entries` | none → 200 CreditEntryPage | verified_active_adult_owner | read-only; FR-077; auth/lifecycle |
| GET `/documents` | none → 200 DocumentPage | verified_active_adult_owner | read-only; FR-043; auth/lifecycle |
| GET `/documents/{document_id}` | none → 200 DocumentView | verified_active_adult_owner | read-only; FR-043/049; auth/lifecycle |
| PATCH `/documents/{document_id}` | DocumentMetadataRequest → 200 DocumentView | verified_active_adult_owner | X-CSRFToken, Idempotency-Key, If-Match; FR-043; auth/lifecycle |
| DELETE `/documents/{document_id}` | none → 202 AckView | verified_active_adult_owner | X-CSRFToken, If-Match; FR-043/116; G-LEGAL |
| POST `/documents/{document_id}/versions` | DocumentVersionRequest → 201 DocumentVersionView | verified_active_adult_owner | X-CSRFToken, Idempotency-Key, If-Match; FR-039/042/046; auth/lifecycle |
| GET `/documents/{document_id}/versions` | none → 200 VersionPage | verified_active_adult_owner | read-only; FR-046/047; auth/lifecycle |
| GET `/documents/{document_id}/versions/{version_id}` | none → 200 DocumentVersionView | verified_active_adult_owner | read-only; FR-046/047; auth/lifecycle |
| POST `/documents/{document_id}/restorations` | VersionSelection → 201 DocumentVersionView | verified_active_adult_owner | X-CSRFToken, Idempotency-Key, If-Match; FR-047; auth/lifecycle |
| POST `/documents/{document_id}/approvals` | DocumentApprovalRequest → 201 CommandResult | verified_active_adult_owner | X-CSRFToken, Idempotency-Key, If-Match; FR-037/039/040; auth/lifecycle |
| POST `/documents/{document_id}/exports` | ExportRequest → 202 CommandResult | verified_active_adult_owner | X-CSRFToken, Idempotency-Key; FR-040; G-SCANNER |
| GET `/applications` | none → 200 ApplicationPage | verified_active_adult_owner | read-only; FR-051/056; auth/lifecycle |
| POST `/applications` | ApplicationRequest → 201 ApplicationView | verified_active_adult_owner | X-CSRFToken, Idempotency-Key; FR-051/052; G-SOURCE |
| GET `/applications/{application_id}` | none → 200 ApplicationView | verified_active_adult_owner | read-only; FR-052; auth/lifecycle |
| PUT `/applications/{application_id}/notes` | ApplicationNotesRequest → 200 ApplicationView | verified_active_adult_owner | X-CSRFToken, Idempotency-Key, If-Match; FR-052/055; auth/lifecycle |
| POST `/applications/{application_id}/transitions` | ApplicationTransitionRequest → 200 ApplicationView | verified_active_adult_owner | X-CSRFToken, Idempotency-Key, If-Match; FR-053/054/055; G-STATUS |
| PUT `/applications/{application_id}/requirements/{requirement_key}/artifact` | ArtifactSelection → 200 CommandResult | verified_active_adult_owner | X-CSRFToken, Idempotency-Key, If-Match; FR-044/045/048; auth/lifecycle |
| PUT `/applications/{application_id}/requirements/{requirement_key}/completion` | ChecklistActionRequest → 200 CommandResult | verified_active_adult_owner | X-CSRFToken, Idempotency-Key, If-Match; FR-045/052; auth/lifecycle |
| GET `/notifications` | none → 200 NotificationPage | verified_active_adult_owner | read-only; FR-089/090; auth/lifecycle |
| POST `/notifications/{notification_id}/read` | none → 200 NotificationView | verified_active_adult_owner | X-CSRFToken, Idempotency-Key; FR-089/091; auth/lifecycle |
| PUT `/notification-preferences/{category}` | PreferenceRequest → 200 CommandResult | verified_active_adult_owner | X-CSRFToken, Idempotency-Key, If-Match; FR-092; auth/lifecycle |
| GET `/tickets` | none → 200 TicketPage | verified_active_adult_owner | read-only; FR-094; auth/lifecycle |
| POST `/tickets` | TicketRequest → 201 TicketView | verified_active_adult_owner | X-CSRFToken, Idempotency-Key; FR-094/097; auth/lifecycle |
| GET `/tickets/{ticket_id}` | none → 200 TicketView | verified_active_adult_owner | read-only; FR-094; auth/lifecycle |
| POST `/tickets/{ticket_id}/messages` | MessageRequest → 201 TicketView | verified_active_adult_owner | X-CSRFToken, Idempotency-Key; FR-094/097; auth/lifecycle |
| GET `/tickets/{ticket_id}/messages` | none → 200 MessagePage | verified_active_adult_owner | read-only; FR-094; auth/lifecycle |
| POST `/tickets/{ticket_id}/transitions` | TicketTransitionRequest → 200 TicketView | verified_active_adult_owner | X-CSRFToken, Idempotency-Key, If-Match; FR-099/100; auth/lifecycle |
| POST `/tickets/{ticket_id}/attachments` | ShareRequest → 201 CommandResult | verified_active_adult_owner | X-CSRFToken, Idempotency-Key; FR-094/110; auth/lifecycle |
| DELETE `/tickets/{ticket_id}/attachments/{attachment_id}` | none → 202 AckView | verified_active_adult_owner | X-CSRFToken, If-Match; FR-094/110; auth/lifecycle |
| PUT `/tickets/{ticket_id}/rating` | RatingRequest → 200 CommandResult | verified_active_adult_owner | X-CSRFToken, Idempotency-Key, If-Match; FR-100; G-TICKET |
| POST `/admin/retention-policies` | RetentionPolicyInput → 201 PolicyView | admin_mfa_retention_scope | X-CSRFToken, Idempotency-Key, If-Match; FR-117/119/120;UD-001; G-LEGAL |
| GET `/admin/retention-policies/current` | none → 200 PolicyView | admin_mfa_retention_scope | read-only; FR-117;UD-001; auth/lifecycle |
| POST `/admin/users/{user_id}/credit-adjustments` | AdjustmentRequest → 201 CommandResult | admin_mfa_finance_scope | X-CSRFToken, Idempotency-Key; FR-079; G-LEGAL |
| POST `/admin/users/{user_id}/credit-adjustments/{adjustment_id}/decisions` | AdjustmentDecision → 200 CommandResult | admin_mfa_finance_approver_scope | X-CSRFToken, Idempotency-Key, If-Match; FR-079; G-LEGAL |
| POST `/admin/sources` | SourceRequest → 201 CommandResult | admin_mfa_moderation_scope | X-CSRFToken, Idempotency-Key; FR-015; G-SOURCE |
| POST `/admin/scholarships/{scholarship_id}/moderation` | ModerationRequest → 200 ScholarshipView | admin_mfa_moderation_scope | X-CSRFToken, Idempotency-Key, If-Match; FR-018/020; G-SOURCE |
| POST `/admin/scholarship-reports/{report_id}/decisions` | ReportDecisionRequest → 200 CommandResult | admin_mfa_moderation_scope | X-CSRFToken, Idempotency-Key, If-Match; FR-024; G-SOURCE |
| GET `/admin/tickets` | none → 200 TicketPage | admin_mfa_support_queue_scope | read-only; FR-104; auth/lifecycle |
| POST `/admin/tickets/{ticket_id}/assignments` | AssignmentRequest → 201 CommandResult | admin_mfa_support_assignment_scope | X-CSRFToken, Idempotency-Key, If-Match; FR-104; auth/lifecycle |
| POST `/admin/tickets/{ticket_id}/messages` | MessageRequest → 201 TicketView | admin_mfa_currently_assigned_support_scope | X-CSRFToken, Idempotency-Key; FR-102/104; auth/lifecycle |
| GET `/admin/tickets/{ticket_id}/messages` | none → 200 MessagePage | admin_mfa_currently_assigned_support_scope | read-only; FR-094/104; auth/lifecycle |
| POST `/admin/tickets/{ticket_id}/transitions` | TicketTransitionRequest → 200 TicketView | admin_mfa_currently_assigned_support_scope | X-CSRFToken, Idempotency-Key, If-Match; FR-099/100; auth/lifecycle |
| POST `/extension/pairings` | ExtensionPairRequest → 201 ExtensionCodeView | verified_active_adult_owner_recent_reauth | X-CSRFToken, Idempotency-Key; FR-059/060; G-EXT |
| POST `/extension/token` | ExtensionExchangeRequest → 200 ExtensionTokenView | extension_code_pkce | Idempotency-Key; FR-059; G-EXT |
| GET `/extension/confirmed-data` | none → 200 ExtensionDataView | extension_scoped_owner | read-only; FR-062/063/064; G-EXT |
| GET `/applications/{application_id}/history` | none → 200 HistoryPage | verified_active_adult_owner | read-only; FR-055; auth/lifecycle |
| GET `/applications/{application_id}/requirements` | none → 200 RequirementPage | verified_active_adult_owner | read-only; FR-045/052; auth/lifecycle |
| GET `/tickets/{ticket_id}/history` | none → 200 HistoryPage | verified_active_adult_owner | read-only; FR-099; auth/lifecycle |
| GET `/tickets/{ticket_id}/sla` | none → 200 SlaView | verified_active_adult_owner | read-only; FR-102; auth/lifecycle |
| GET `/admin/tickets/{ticket_id}/sla` | none → 200 SlaView | admin_mfa_currently_assigned_support_scope | read-only; FR-102/104; auth/lifecycle |
| POST `/admin/scholarships` | ScholarshipCandidateRequest → 201 CommandResult | admin_mfa_moderation_scope | X-CSRFToken, Idempotency-Key; FR-016/017; G-SOURCE |
| GET `/admin/scholarships` | none → 200 CommandPage | admin_mfa_moderation_scope | read-only; FR-018/020; auth/lifecycle |
| POST `/admin/scholarships/{scholarship_id}/versions` | ScholarshipCandidateRequest → 201 CommandResult | admin_mfa_moderation_scope | X-CSRFToken, Idempotency-Key, If-Match; FR-016/018/020; G-SOURCE |
| GET `/admin/scholarship-reports` | none → 200 CommandPage | admin_mfa_moderation_scope | read-only; FR-024; auth/lifecycle |
| POST `/admin/policies/limits` | LimitsPolicyInput → 201 OperationalPolicyView | admin_mfa_cost_policy_scope | X-CSRFToken, Idempotency-Key, If-Match; FR-070/069; auth/lifecycle |
| POST `/admin/policies/prices` | PricesPolicyInput → 201 OperationalPolicyView | admin_mfa_cost_policy_scope | X-CSRFToken, Idempotency-Key, If-Match; FR-070/073; auth/lifecycle |
| POST `/admin/policies/eligibility` | EligibilityPolicyInput → 201 OperationalPolicyView | admin_mfa_matching_policy_scope | X-CSRFToken, Idempotency-Key, If-Match; FR-031/107; G-PROFILE |
| POST `/admin/policies/sla` | SlaPolicyInput → 201 OperationalPolicyView | admin_mfa_support_policy_scope | X-CSRFToken, Idempotency-Key, If-Match; FR-101/102/103; G-TICKET |
| GET `/admin/users` | none → 200 UserAdminPage | admin_mfa_identity_scope | read-only; FR-106/110; auth/lifecycle |
| POST `/admin/users/{user_id}/session-revocations` | ReasonRequest → 200 AckView | admin_mfa_identity_security_scope | X-CSRFToken, Idempotency-Key; FR-006/106; auth/lifecycle |
| POST `/admin/scope-grants` | ScopeGrantRequest → 201 CommandResult | admin_mfa_identity_security_approver_scope | X-CSRFToken, Idempotency-Key; FR-106/109; auth/lifecycle |
| POST `/admin/mfa/enrollments` | MfaEnrollmentRequest → 201 MfaChallengeView | admin_security_bootstrap_and_recent_reauth | X-CSRFToken, Idempotency-Key; FR-007; auth/lifecycle |
| GET `/admin/metrics` | none → 200 AggregatePage | admin_mfa_aggregate_metrics_scope | read-only; FR-105/108/112; G-MEASURE |
| GET `/admin/audit` | none → 200 CommandPage | admin_mfa_security_audit_scope | read-only; FR-109; auth/lifecycle |
| GET `/files` | none → 200 FilePage | verified_active_adult_owner | read-only; FR-043/049; auth/lifecycle |
| GET `/jobs/{job_id}` | none → 200 JobView | verified_active_adult_owner | read-only; FR-122/123; auth/lifecycle |
| GET `/admin/policies/{policy_kind}/current` | none → 200 OperationalPolicySnapshot | admin_mfa_policy_kind_scope | read-only; FR-070/101/107/117; auth/lifecycle |
| GET `/capabilities` | none → 200 CapabilityView | public | read-only; FR-041/125; auth/lifecycle |

| PUT `/admin/tickets/{ticket_id}/classification` | TicketClassificationRequest → 200 TicketView | MFA current assigned Support Admin | CSRF, idempotency, If-Match; FR-096/104; no silent old-SLA target rewrite |

## Semantic checks the wire schema cannot replace

Profile fields are restricted by approved stage dictionary; source_result_id must be owned extraction evidence; only explicit student review changes trust. Scholarship version pairs must both be present, published/reviewed as required, and snapshotted. Document/export/ready requires the exact version's student approval, not just model validation. Artifact selection is exactly one owned document-version or accepted scanned upload and must match the current checklist. Submitted confirmation must be true only on explicit external-submission report; extension token has no status-write permission.

Generation uses signed expiring quote bound to exact service/input manifest, explicit confirm_price, owned profile/scholarship/consent versions, language and stable idempotency identity; no client price/provider/owner. Matching ties the existing deterministic evaluation; support AI ties the same ticket/selected message and separately authorized attachment inputs. Free AI still consumes logical/support/provider budget. Price and provider approvals are rechecked server-side; expired/unknown quote denies, never free execution. Quote itself creates no reservation.

Admin retention setting must satisfy ADR0008 legal envelope/current head, and new policy never mutates confirmed requests. Finance review/correction does not accept a student-supplied amount or grant from an image; approved bounded compensating journal only. Source-report review sees the submitted evidence through its own audited case projection, not reporter's library. Support queue metadata does not grant thread/attachment access before current assignment. Restore uses a one-purpose verified proof, not ordinary disabled-account login. Unknown feature configuration fails closed, with manual/help path.

Policy-kind payloads for credit caps/prices, eligibility rules, SLA calendars/warnings, privacy and flags are versioned domain contracts in domain-contracts.md; a general arbitrary settings JSON write endpoint is intentionally not exposed. Later typed endpoint additions must preserve the specified approval boundaries. General Advanced payment payloads await G-PAID and remain outside this selected Beta wire surface. No source or role approval is inferred from API existence.

Quote manifest commitment uses RFC8785 canonical JSON/SHA-256 over service kind, selected immutable resource IDs/versions, consent version and output language. The hash itself grants no ownership or egress permission; admission reconstructs and validates resources and exact normalized commitment before any hold or send. Quote expiry is a proposed 5-minute policy value. A replay of a committed idempotency key returns its original authorized operation even if its original quote has since expired; a new request must quote again.
