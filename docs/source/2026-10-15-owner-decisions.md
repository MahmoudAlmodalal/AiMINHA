# Recorded owner direction — 2026-10-15

This is an additive session decision record, not an edited or replacement PRD. The supplied PRD/decision resolution/provider strategy bytes are preserved. Latest explicit user direction takes precedence for its stated scope under AGENTS.md and the session execution contract.

## UD-001 — configurable account recovery period

Owner's exact message: «3المهلة بتتعدل من الادمن وخلث اول 3 برممبت كامل».

Confirmed policy: the account-deletion recovery period is configurable by Admin. This resolves the earlier assumption that the recovery period is permanently fixed. Scoped Admin changes a versioned policy prospectively; every deletion request captures that policy and its computed `restore_until`. A later Admin edit never silently shortens/extends an already confirmed deletion request. Policy edits require MFA, a reason and audit, and cannot bypass approved legal retention limits.

Engineering interpretation, explicitly ASSUMPTION: represent the setting as a positive integer `recovery_days`, using PRD FR-117/BR-048's calendar-day basis, default 30 from the sources, and IANA `Asia/Hebron`. The source's older 720-hour default is not an unconditional invariant. No claim is made that the owner independently selected a duration unit, timezone or DST algorithm. The exact proposed calculation is in the business rules/ADR 0008; these choices are documented so implementation need not guess. Legal policy approval remains an external launch gate.

## UD-002 — finish the first three prompts and reconcile the active design

The same message authorizes completion of prompts 00, 01 and 02 using the supplied source files and reconciliation of the already authorized Phase 03 with UD-001. No phase 04–17 implementation is authorized. Where individual prompt boilerplate says to execute only one phase, this later explicit session instruction authorizes the bounded 00–03 documentation work, performed in dependency order.

The user supplied `PRD.md` v3.0.0 as the working functional source and requests completion of its early design workflow. This establishes the working documentation baseline for this task; it is not a fabricated retroactive signature of all original interview decisions or approval to launch, send private data, spend money, push, deploy, or provision resources. The PRD's historical “Not yet recorded” release revision signature remains honestly recorded as a release/owner gate, not a claim that its file is missing or a reason to leave traceability work undone.
