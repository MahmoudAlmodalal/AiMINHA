# خطة بناء MinhaAI بواسطة AI Coding Agent

## الفكرة

نفّذ المنتج بأسلوب **Spec → Architecture → Tasks → Vertical Slices → Automated Tests → Security Review → Controlled Release**. لا ترسل PRD كاملًا كل مرة، ولا تطلب بناء كل المشروع في برومبت واحد. اجعل `AGENTS.md` تعليمات دائمة، وملف prompt واحد هو المهمة الحالية، وتقرير تسليم يجعل الجلسة التالية قابلة للاستئناف.

## قبل أول تشغيل

1. افتح المستودع الحقيقي، وانسخ محتويات هذه الحزمة إلى جذره.
2. أضف `docs/source/PRD.md` و`docs/source/ai-provider-strategy.md` الفعليين (ملف القرارات المرفق وحده لا يغني عنهما).
3. ابدأ بـ `prompts/00-repository-discovery.md`، ولا تسمح بوصف متطلبات النظام بأنها مكتملة دون الوثائق الأصلية.
4. احفظ تغييرات كل مرحلة في فرع/تقريرها، ثم اختبرها قبل الانتقال.

## البرومبت العام لتشغيل أي مرحلة

```text
You are the implementation agent for MinhaAI. Read AGENTS.md,
tasks/implementation-plan.md, the source docs, and prompts/XX-<phase>.md.
Execute ONLY this phase. Do not invent missing PRD requirements.
Plan briefly, implement requested deliverables, run the actual tests,
update the roadmap and write tasks/phase-reports/XX.md.
Report changed files, commands and exit results, acceptance status,
security/cost/privacy blockers, and next-phase handoff.
Do not push, deploy, purchase plans, or expose private student data.
```

## مراحل التنفيذ
- **00 — Repository audit and source inventory** → `prompts/00-repository-discovery.md`
- **01 — Requirements and traceable backlog** → `prompts/01-requirements-and-backlog.md`
- **02 — Architecture and API contracts** → `prompts/02-architecture-and-boundaries.md`
- **03 — Data model, ERD and state machines** → `prompts/03-domain-model-and-erd.md`
- **04 — UX specification and design system** → `prompts/04-ux-and-journeys.md`
- **05 — Project setup, baseline CI and developer environment** → `prompts/05-monorepo-bootstrap.md`
- **06 — Identity, permissions, consent and account lifecycle** → `prompts/06-identity-roles-privacy.md`
- **07 — Scholarship catalog, permitted sources, moderation and search** → `prompts/07-scholarships-and-moderation.md`
- **08 — Deterministic eligibility and evidence-backed matching** → `prompts/08-eligibility-and-matching.md`
- **09 — Credit accounting, entitlements and concurrency** → `prompts/09-credits-and-ledger.md`
- **10 — AI gateway, classification, provider adapters and budget stop** → `prompts/10-ai-gateway-and-fallback.md`
- **11 — Private files, CV and document workflows** → `prompts/11-private-files-and-ai-documents.md`
- **12 — Application tracker, status history and deadline alerts** → `prompts/12-applications-and-reminders.md`
- **13 — Support tickets, AI triage and business-hours SLA** → `prompts/13-support-tickets-and-sla.md`
- **14 — Chrome extension with review-before-fill** → `prompts/14-chrome-extension-review-only.md`
- **15 — Admin workflows, configuration and operations** → `prompts/15-admin-operations-and-ui.md`
- **16 — Full testing, integration and security review** → `prompts/16-e2e-security-and-quality.md`
- **17 — Deployment plan and controlled release** → `prompts/17-deployment-runbook-and-go-no-go.md`

## التقسيم المقترح للمستودع بعد مرحلة التهيئة

```text
minhaai/
├── AGENTS.md
├── README.md
├── .env.example
├── apps/
│   ├── web/              # Next.js UI + route layouts (ar/en)
│   ├── api/              # Django settings, DRF, modular domain apps
│   │   └── modules/      # identity, scholarships, eligibility, credits,
│   │                     # ai_gateway, documents, applications, support, audit
│   ├── worker/           # recoverable jobs and reconciliation
│   └── extension/        # Chrome MV3 review-only
├── packages/
│   └── contracts/        # generated typed API schemas if justified
├── docs/
│   ├── source/           # original PRD, strategy, decision log (do not alter)
│   ├── specs/            # derived requirements, UI/flows, acceptance
│   ├── architecture/     # Mermaid/ERD, design, API conventions
│   └── adr/              # architectural decisions
├── prompts/              # 00 through 17, one prompt per agent run
├── tasks/                # implementation plan + backlog + phase reports
├── tests/                # end-to-end, security and integration fixtures
└── infra/                # local compose, CI/deploy docs, rollback
```

## قاعدة الـAgent

- **المدخلات:** مصدر أصلي + Task واحدة + قواعد المشروع.
- **المخرجات:** كود محدد + اختبارات فعلية + وثائق مصغرة + تقرير واضح.
- **التحقق:** إذا لم تكتمل معايير القبول، تبقى المهمة BLOCKED بدل كتابة DONE.
- **التكامل:** يمكن تشغيل Agents بالتوازي على مجالات لا تتشارك migrations أو صلاحيات أو عقود API.
- **الخصوصية:** AI مزودي الخدمات والملفات الخاصة والدفع وبوابات النشر ذات صلاحيات وقواعد مستقلة لا يمكن للـAgent إلغاؤها.

## ترتيب عملي لأول أسبوع تطوير (بلا التزام زمني)

أكمل بالتتابع 00–05 أولًا (مصادر، نطاق، معمارية، ERD، UX، تشغيل محلي)، ثم ابنِ شريحة المستخدم والصلاحيات 06، وبعدها كتالوج المنح 07. لا تبدأ ربط AI بمعلومات طلاب حقيقيين قبل اعتماد تصنيف ومزودي البيانات وسلامة الملفات.
