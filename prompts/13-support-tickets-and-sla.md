# Phase 13 — Support tickets, AI triage and business-hours SLA

**Objective:** Perform exactly one bounded phase of the MinhaAI build.

## Work
1. Implement tickets and explicit ticket file attachments distinct from student private library. Support agent reads only attachments explicitly sent to a ticket assigned to them; audit every access.
2. Default work hours Sun–Thu 09:00–17:00 Asia/Hebron, configurable holidays. Experimental first human response targets: critical 4, high 8, normal 24, low 48 BUSINESS hours.
3. First response SLA starts on human request/handoff and ends on substantive human reply. AI bot does not satisfy human SLA. After first response, waiting for student does not change that metric.
4. Ticket Resolved→Closed after 7 days without objection; 14-day reopening window; rating once/edit within 7 days, policy configurable.
5. AI triage (only allowed context) can classify/suggest priority; cannot change credits/accounts or open private files; hand off on user request, two failures, uncertainty, financial/security issues.
6. Limit experiment to 5 free AI-support messages/student/day within global budget; fall back to human ticket rather than unsupported AI usage.

**Gate:** No support privilege escalation; business-hours clock tested over weekends/holidays and DST.
## Required execution contract
- Read `AGENTS.md`, `tasks/implementation-plan.md`, `docs/source/MinhaAI_PRD_Decision_Resolution_AR.md`, and the authoritative source files where available.
- Execute only THIS phase. Identify source/requirement traces and unresolved external gates. Do not invent absent documents.
- Produce exact named artifacts, run relevant checks, update roadmap statuses, and write `tasks/phase-reports/13.md`. Report skipped checks truthfully.
- Do not push, deploy, create paid resources, or change other phases.

