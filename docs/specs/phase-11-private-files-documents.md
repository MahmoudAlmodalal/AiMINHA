# Phase11 — private files and document workflows

## Scope and authority

The execution authority is `prompts/11-private-files-and-ai-documents.md` and the
current owner's request to execute that phase with multiple agents. The original
source files remain unchanged. Sources are present, not fabricated or missing:
`docs/source/PRD.md`, `MinhaAI_PRD_Decision_Resolution_AR.md` and
`ai-provider-strategy.md`. This phase does not implement application tracking,
support ticket lifecycle, paid resources, deployments or a live AI transport.

| Implemented boundary | Requirement/source trace |
|---|---|
| Verified adult ownership, private metadata/bytes and staff denial | FR-007/011/049/110; decision §أ5–6, OQ-007/022; AC-036 |
| Format/content/size checks and mandatory exact-byte malware scan | FR-011/050; PRD §20.5; decision OQ-013, §د safe failure; architecture R16, ADR0004 |
| Expiring, session-authorized owner/assigned-share reads | FR-049/110; decision OQ-007; architecture privacy boundaries, R03/R19 |
| Manual entry and private AI safely unavailable | FR-010/012–014/034–039; decision OQ-004/022; provider strategy §§2–5; AC-004/005 |
| Four document kinds, selected language, manual edits and safe preview | FR-034–042; BR-015/016; AC-013–015 |
| Immutable versions, exact approval, restore-as-new and private exports | FR-043/046–050; BR-017/018; AC-016/017 |
| Save before settlement; once-only charges and free repeat export | FR-072–077; BR-029–033; decision OQ-016 and §د export failure; AC-023/024/041 |
| Internal immutable submission snapshot prerequisite | FR-044/048; BR-017; architecture R17; application binding remains Phase12 |

## Security and integration contract

`private_files` extends the existing `privacy.PrivateAsset` boundary. A new
accepted byte object must have measured bytes, SHA256 and successful actual
ClamAV receipt for that exact object. A declaration, file extension, provider
success message or test fixture cannot substitute for a scanner success.
Storage roots are private and outside web assets. Random object keys do not
include student names. The server bounds input rather than trusting Content-Length.

Decimal MB is the existing **ASSUMPTION** from architecture R16: 5,000,000 bytes
per object, 10,000,000 per owner, 750,000,000 globally. Quarantine and temporary
exports count; quota is reserved before storage writes and only confirmed
cleanup releases it. A missing scanner, error, stale signatures or unknown
storage state fails closed. Manual profile/document entry remains available.
The backend reauthorizes expiring grants at actual download, including account
lifecycle and explicit ticket share/assignment. Grants confer no staff library
access. The existing support projections are reused without creating Phase13.

`documents` stores bounded plain text rather than executable HTML. Immutable
content versions preserve title, output language, hash and provenance. Preview
escapes markup; exact owner approval is distinct from technical validation.
Editing and restore append a version. PDF/DOCX conversion is local, and exported
bytes must pass the same storage/scanner/quota boundary before download.
Re-export reuses the saved version/format without any AI operation or new debit.
Conversion, scanning or storage failure preserves the original saved version.

The private generation/extraction API stays unavailable: there is no approved
scoped private-processing pipeline or real transport in Phase10. Generic consent,
an API key, provider approval metadata or client-declared synthetic classification
cannot enable it. No student data is routed to any model. A distinctly named
server-only local synthetic fixture exercises document/proposal validation,
reservation, persistence and once-only settlement. Its inputs are fixed synthetic
evidence, never a student's uploaded CV/profile. The old synthetic credit validator
is preserved; document jobs add a persisted artifact witness rather than treating
the old synthetic receipt as a real private result. Failed validation releases a
known local failure; uncertain outcomes retain their holds for reconciliation.

The immutable submission snapshot primitive does not implement or claim a
submitted application. A future Phase12 caller must supply a trusted owned
application binding; no HTTP request may invent a submission reference here.

## External gates and bounded limitations

- Storage encryption, residency, processor/legal approval, production credentials,
  erasure policy/backups and restore rehearsal remain **EXTERNAL_GATE**.
- Current official scanner signatures and operational availability must be
  maintained in the deployed runtime; local evidence does not approve hosting.
- Real private AI requires precise provider/model/data/purpose/region consent,
  contracts/security approval, quota proof, real transport and domain quality
  validation. These remain **EXTERNAL_GATE**, with private processing disabled.
- Document templates and Arabic/English export visual quality require product
  review; local structural validation does not certify academic truth or quality.
- Application submission bindings and support lifecycle belong to Phases12/13.

Exact verification commands, failures, outcomes and skipped external checks are
recorded in `tasks/phase-reports/11.md` after implementation verification.
