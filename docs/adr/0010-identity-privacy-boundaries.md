# ADR 0010 — Phase06 identity and privacy enforcement

Status: implemented for local/synthetic verification, 2026-10-16. Authority:
current Phase06 request; AGENTS security invariants; PRD FR-001–007/012/110/113–120;
decision resolution §أ5/6, OQ-006/007/020/022; UD-001; ADR0001/0007/0008.

Age is computed from the server UTC date; the unapproved Feb29 legal anniversary
edge is conservatively delayed until March1 in a non-leap 18th year. No identity
verification or jurisdiction-specific legal approval is inferred from a declared DOB.

The latest Phase06 request expressly tests an exact 30-day UTC boundary.
Retain the owner's Admin-configurable duration from UD-001 and replace only the
earlier derived calendar/Asia-Hebron calculation assumption for this runtime
with `UTC_ELAPSED_DAYS`. Default30 means precisely 720 elapsed hours. A deletion
stores policy/version, duration, algorithm, confirmation and UTC deadline once.
Policy edits affect future confirmations. Restore equality is expired. The
source documents and earlier ADR are preserved; C06-01 records this disposition.
Independent approved legal bounds remain required before activating deletion.

Trusted restoration receipt means the server accepts the proof while holding
the canonical account lock. Client timestamps and pre-lock arrival timestamps
are never accepted. Restore and purge planning lock account, then deletion;
whichever obtains the lock follows the stored deadline/state. This is explicit
lock arbitration, not a promise to honor a network request queued before expiry.
Physical erasure remains blocked without approved storage/legal/backup handling.

Use Django password hashing/validation and DB-backed sessions. Canonical UUID
account and case-insensitive unique email precede linking. One-use challenge
digests bind purpose/account/session/deletion as appropriate. Raw verification
codes go only to private local mail or configured SMTP, never ordinary API DTOs,
logs or audit. Masked CSRF and a five-minute session-bound reauthentication
capability are the deliberate browser protocol exceptions; neither is reusable
as a login session. Sessions rotate, recheck lifecycle/epoch, and expire after
24h inactivity/7d absolute (engineering defaults from ADR0001).

Exactly STUDENT/ADMIN roles. Admin scope/MFA proof is server controlled; no
request can grant a role, mark email/adulthood/MFA verified, choose an owner or
approve a provider/legal envelope. No MFA enrollment/verification backend is
configured, so real privileged Admin operations stay unavailable. Synthetic
proof fixtures test the positive support boundary without enabling an MFA bypass.

Google uses a maintained signature-verification library and trusted fixed token/
certificate endpoints, nonce, audience, issuer, expiry, PKCE S256 and browser-bound
one-use state. LINK requires active verified adult ownership and recent password
reauthentication. SIGN_IN resolves an already linked provider subject. Email text
never merges identities; Google-only new account activation is not advertised.
Missing approved client/redirect configuration returns503. Live OAuth is not
verified. OAuth endpoints use fresh, one-use attempts rather than replaying an
authorization URL or callback from the generic command-response receipt store;
this narrowed runtime protocol is recorded in C06-04. Other documented commands
require session/actor-scoped idempotency with payload HMAC conflict detection.

Consent is append-only and purpose/disclosure-version-specific. Personal-AI
consent is never inferred from signup/privacy/terms/upload/support share. New
disclosures invalidate old grants; revoke/delete invalidates captured versions.
Deletion revokes personal-AI consent and restore does not silently grant it again.
Consent alone grants no provider approval and no AI egress exists in Phase06.

Private file metadata is an authorization projection, not an upload pipeline.
All staff library list/read requests return403 plus metadata audit, including
unknown IDs. Student foreign/missing IDs also return403 under this phase's explicit
gate (a documented change from the earlier404 design). Support can read only the
exact accepted, owner-explicit share in its currently assigned ticket with current
SUPPORT scope/MFA and an active owner. No storage key/version, bytes or signed URL
is returned. Ticket creation/assignment workflow remains Phase13.

Success audit commits with the mutation/read transaction. API-denial audit runs
after a failed service transaction has rolled back. Audit outage fails closed.
PostgreSQL triggers guard append-only evidence, frozen deletion snapshots, exact
purge targets and cross-owner share references. These are not claims of complete
RLS/production DB-role separation or of domain/file/credit security certification.
