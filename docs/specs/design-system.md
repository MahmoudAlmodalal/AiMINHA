# MinhaAI design system — Phase 04

2026-10-15. **ASSUMPTION UX: accessible design specification; no component code, purchased assets or external design files.** Values below are proposed implementation tokens, not claimed original owner selections. Behavior derives from [PRD](../source/PRD.md) NFR-013–016/019/020/026–028, FR-021–042/069–079/089–125, [decision resolution](../source/MinhaAI_PRD_Decision_Resolution_AR.md) (D), [UD-001 recovery policy](../source/2026-10-15-owner-decisions.md), [API](../architecture/api-contracts.md), and [state machines](../architecture/state-machines.md). Use with [flows](user-flows.md) and [route inventory](screen-inventory.md). Missing wire data and external approvals keep affected components disabled; polished appearance never implies feature availability.

## Foundations and semantic tokens

Proposed accessibility target: **WCAG 2.2 AA**, supplementing PRD NFR-015's unspecified exact target. This is an engineering target pending implementation and audit, not certification. Normal text ≥4.5:1, large text ≥3:1 (24px regular or about 18.7px bold), essential control boundaries/icons/focus ≥3:1 against adjacent colors. Never use color alone for status, selected state, required fields, charts or diffs. Colors apply to the exact pair below; new combinations require recalculation. Light theme only is specified; a dark theme would require a separately tested token mapping.

| Token | Value | Semantic use / paired background |
|---|---|---|
| color.canvas | #F8FAFC | Page background |
| color.surface | #FFFFFF | Forms, cards, tables, dialogs |
| color.text | #14213D | Primary text on surface/canvas |
| color.text.secondary | #475569 | Hints, placeholders, metadata on surface/canvas; still readable text |
| color.action | #155E75 | Primary button background with #FFFFFF text; links on surface |
| color.action.hover | #164E63 | Hover/pressed action with #FFFFFF text; selected state also has icon/text |
| color.border.control | #64748B | Essential input/control boundary on surface/canvas |
| color.border.decorative | #CBD5E1 | Nonessential separators only; cannot alone identify an input |
| color.focus | #1D4ED8 | Focus ring against white isolation gap and surface/canvas |
| color.success.text / surface | #166534 / #F0FDF4 | Confirmed success or Eligible; icon + explicit label |
| color.warning.text / surface | #854D0E / #FFFBEB | Unknown, reverify, reconciliation; never imply eligibility passed |
| color.danger.text / surface | #991B1B / #FEF2F2 | Error, Ineligible or destructive consequence; distinct labels |
| color.info.text / surface | #1E40AF / #EFF6FF | Informational notices and queued operations |
| color.disabled.text / surface | #475569 / #E2E8F0 | Unavailable action + reason; no low-opacity text |

Focus: proposed 2px color.focus outline, 2px white separation around a control. It must remain visible on action fills and tinted panels and not be clipped by overflow. Test focus on actual adjacent backgrounds, including browser forced-colors; use system Highlight/CanvasText when appropriate. Underline inline links; retain underline or another persistent shape distinction on hover/focus. Destructive filled action uses color.danger.text as fill with white label only after contrast check. A noninteractive disabled control still has a readable reason; do not make every unavailable item a tab stop.

| Token group | Proposed values | Rule |
|---|---|---|
| space | 0, 4, 8, 12, 16, 24, 32, 48px | Logical gaps/padding; use rem equivalents at 16px root and allow user text scaling |
| radius | control 8px; card/dialog 12px | Consistent grouping; no pill-only information hierarchy |
| border | 1px controls; 2px selected/focus-adjacent emphasis | Selection also uses checked state/text |
| target | minimum 44×44 CSS px | Design preference above AA minimum; includes icon buttons, checkbox label hit areas and close controls |
| motion | 120ms feedback, 180ms panel transition | Optional; reduce-motion removes transforms/animation, progress remains textual |
| layer | content 0; sticky 10; menu 20; dialog 30; toast 40 | Dialog backdrop/inert background; toasts never cover focused controls or primary actions |

No animation conveys the only evidence of progress. Use measured status, not a fake percentage. No flashing, autoplay or time pressure outside an actual server-issued proof/quote expiry. Expiry is explained in text and offers restart; do not announce every second to assistive technology.

## Semantic typography and language

| Semantic token | Size / weight / line height | Use |
|---|---|---|
| type.page-title | 28px mobile, 36px laptop / 700 / 1.35 EN, 1.55 AR | One h1 identifying route purpose |
| type.section-title | 24px / 700 / 1.4 EN, 1.6 AR | h2 sections; hierarchy not chosen for visual size alone |
| type.group-title | 20px / 600 / 1.45 EN, 1.65 AR | h3 groups and card headings |
| type.body | 16px / 400 / 1.65 EN, 1.8 AR | Main copy, fields, table cells |
| type.label | 16px / 600 / 1.5 EN, 1.75 AR | Persistent visible labels and action names |
| type.meta | 14px / 400 / 1.6 EN, 1.8 AR | Source/date/version; essential meaning never solely tiny text |
| type.numeric | Inherit size, tabular numerals when supported | Credit/date columns; keep number and unit understandable |
| type.code | 14px system monospace / 1.6 | Opaque operation/version IDs, not prose |

Use OS system fonts first; Arabic-capable fallback such as installed Noto Sans Arabic/Tahoma and English system sans. Any later bundled font requires license review, local hosting and complete Arabic glyph coverage; do not add a tracking font service. Arabic has no letter-spacing/tracking or uppercase transformation. Do not fix line-box heights that clip diacritics; textarea and button heights expand with content. User browser font preferences and 200% text zoom must work without loss. No icon-only heading or placeholder-only label.

Root `lang` and `dir` follow the UI (`ar`/RTL, `en`/LTR). Use logical start/end instead of left/right. DOM order follows visual reading order; do not use CSS reversal to create a contradictory keyboard path. Navigation arrows/step progression mirror; logos, checkmarks, credit signs, media controls and external-site content do not mirror blindly. Mixed Arabic/English names, file names and user text use auto direction/bidi isolation. Email, URLs, operation IDs, version strings and Latin code use isolated LTR. Document body direction follows its output language independently, including preview, editor and eventual PDF/DOCX.

Localize full sentences with placeholders and plural forms; no string concatenation around Arabic numerals or Credits. Accept localized digits where safe and normalize to validated canonical numbers before submission. Do not transliterate names or convert GPA scales on the client. `UNKNOWN` in eligibility is displayed as **Undetermined / غير محسومة**; missing profile input as **Not provided / غير مُدخل**. A missing value is never 0, “No”, a passing criterion or a dash without explanation.

## Responsive widths, density and overflow

| Context | Proposed width/layout | Behavior |
|---|---|---|
| Small mobile ≥320px | 16px inline gutters, one column | Header and menu compact; controls wrap; sticky contextual action reserves content/safe-area space and never covers focus |
| Tablet 768–1023px | 24px gutters, one or two columns when content fits | Filter sheet may become side panel; no task depends on pointer hover |
| Laptop ≥1024px | 24–32px gutters; app max 1200px; Admin max 1440px | Rail about 224px with remaining flexible content; sensible max widths prevent stretched forms |
| Reading/legal/consent | max about 70ch EN, 60ch AR; width ≤100% | Full text visible, headings/contents navigation; no forced scrolling to imply consent |
| Sign-in/profile form | max about 40rem | One labelled field per row by default; short related pairs may share row and stack on mobile |
| Editor | flexible content area | Editable text reflows; optional print preview has separate zoom/scroll with text alternative |

At 320 CSS px / 400% browser zoom from a 1280px viewport, page content reflows without two-dimensional page scrolling. Genuine data tables/diffs may scroll inside named regions. Long URLs/IDs wrap with safe break opportunities; never break or truncate the accessible value. No content is hover-only. Dialog becomes full-width within gutters on mobile, max-height viewport with internally scrollable content and visible labelled actions; keyboard/focus stays reachable when virtual keyboard opens.

Use semantic table caption, header cells, scope/associations and real rows for ledger/Admin data. Put wide tables in an overflow-x region with visible “Scroll for more columns” hint and keyboard focus only when actually overflowing. Preserve header context, ensure sticky columns do not cover focus, and provide a list/card presentation with explicit labels on mobile when it is easier to read. One accessible representation at a time; never duplicate announced rows. Sort button announces direction; only offer server-supported sorting. Loaded-page counts are labelled as such; do not invent totals from `items.length`. Filtering a loaded page must be labelled local, not global. Status boards always have list controls and never require drag-and-drop.

## Common components and state rules

- **Forms:** persistent label, optional/required text, input-specific hint, inline error linked with `aria-describedby`, `aria-invalid` only after meaningful validation. Submit failure focuses a summary linking to each field, retains safe values in memory and clears secrets as appropriate. Support password managers, paste and autocomplete; visible password toggle has a name/state. Requiredness follows actual server dictionary, never invented academic criteria.
- **Buttons and gates:** one primary action per decision region, imperative label with object/cost where relevant. Disabled state shows what is unavailable, why and the safe next action. A focusable explanation link can use `aria-describedby`; HTML disabled button itself is not relied on to expose its reason. If `aria-disabled` is used for discoverability, block pointer and keyboard activation. Scope failure cannot be fixed by frontend flags.
- **Navigation/dialogs:** skip link to main; labelled header/nav/main; current item `aria-current`; logical heading order; Enter/Space for buttons, Escape closes menus/sheets and returns focus to invoker. Modal focus is contained, background inert. Route changes focus h1 and announce title; do not steal focus on polling updates. Native select/checkbox preferred to custom widgets; advanced widgets implement standard arrow/Home/End behavior.
- **Status and async:** `role=status` for one concise progress/success update; `role=alert` for actionable failure, no repeated live announcements from polling. Skeleton is hidden from accessibility tree. Preserve authoritative state during network failure, labelled stale; no “failed” solely because a request timed out. Success requires server confirmation and output existence.
- **Toasts and undo:** toast supplements durable inline status; no destructive/financial/consent decision exists only in a disappearing toast. Undo is offered only when an actual reversible command exists. Reconciliation, submitted-version freeze and deletion consequences cannot be dismissed into apparent success.
- **Privacy:** protected state is current-memory only; no service-worker/localStorage/IndexedDB draft or token persistence. No sensitive content in URL/query, page title, analytics, console, error logs or shared caches. Signed capabilities are short-lived, no-store, and not pasted into support messages. Session expiry/logout clears protected content; do not promise immediate recall of previously downloaded bytes.

## Date, source and credit disclosures

Use **Gregorian calendar as an ASSUMPTION UX** for interoperable academic deadlines and DOB, locale-formatted day/month names without ambiguous numeric ordering; expose ISO value in accessible help where needed. Persist canonical dates or UTC instants according to the API. Do not treat DOB as midnight in an invented timezone. Validate adult age on server using approved policy; unresolved leap-day/legal edge fails closed.

Scholarship deadline shows verified donor date/time and known IANA timezone/offset, with local equivalent if available and labelled. General events use user display zone, proposed default Asia/Hebron, with full date/time/zone on details. Example formatting only: `15 Oct 2026, 17:00 Asia/Hebron (UTC+03:00)` / `15 أكتوبر 2026، 17:00 Asia/Hebron (UTC+03:00)`. Do not infer donor timezone from residence or language. The current detail wire exposes a UTC confirmed instant but no donor-zone/round structure: show UTC explicitly until source-zone data exists; donor-zone and multi-round enhancements remain unavailable rather than invented. “Deadline unknown / الموعد غير معروف” has no countdown, deadline sort placement claim or scheduled timed alert. Rolling rounds need a real source label; do not turn null into rolling. Last verified time is not publication time. Show source + exact verification date/status, using R02 detail enrichment; unavailable metadata says it is unavailable.

Deletion duration follows Admin's versioned policy under UD-001/ADR0008. Default 30 calendar days is a configurable initial proposal, never a perpetual “30×24h” promise. Use returned `recovery_days`, `recovery_timezone`, `policy_id`, `confirmed_at` and immutable `restore_until`; only server receipt strictly before that instant permits recovery. Later settings cannot move it. Before confirmation, approved impact/proof preflight is required and currently MISSING UX-API-07. Do not extrapolate a new cutoff on the device. Backup/processor erasure/exception dates appear only from approved policy/evidence; no blanket instant-erasure promise.

Wallet separates **available**, **reserved**, **posted** and **frozen** with definitions. Posted net ledger balance is not an extra spendable pot; do not sum posted + available. Credit entries show signed integer amount, type, reason and timestamp. Credits are product units, not currency. No expiry due solely to age while active; freeze/cancellation on deletion are separate. Proposed Beta defaults (D §ب): 30 once after eligible verified activation, 6 daily spending cap in Asia/Hebron, matching 1/extraction 4/document 6, support 5 AI messages/day under shared caps. These are examples pending effective server policy, never live balances, daily top-ups, guaranteed AI capacity or a reason to ask for payment. An extraction costing 4 can prevent a 6-Credit draft that same day even if balance covers it; explain daily limit separately from insufficient balance. If live remaining cap/reset time is absent, state limit reached using safe server reason, no fabricated remaining counter.

Before an AI run, show service, output language, exact integer quote, policy reference, expiry, what data is used, consent status, and **“Confirm N Credits”**. The quote is not a reservation; changing inputs requires a new quote and review. A zero-price AI action still needs approved data route, current consent, budget and explicit initiation; missing quote never means free. On confirmed admission keep the accepted price despite later edits. Never present quoted free-provider cost as a cash price. No purchase link that implies payments can unlock a Beta quota.

| Authoritative operation state | English / Arabic label | Required Credit meaning / safe action |
|---|---|---|
| RESERVED | Credits reserved / رصيد محجوز | Held for this operation, no final debit; wait/refresh same operation |
| RUNNING | In progress / قيد التنفيذ | Reservation retained; no second start or fake ETA |
| RECONCILING | Checking the outcome / جارٍ التحقق من النتيجة | Final outcome unresolved; hold may remain, no guaranteed refund or rerun; support with operation ID |
| SETTLED | Saved; Credits charged / تم الحفظ وخصم الرصيد | Valid saved result exists and exactly one final debit; owner content review/approval still required |
| RELEASED | Reservation released / أُلغي الحجز | No final operation charge; failed output not success; distinguish an actual posted reversal if separately returned |

15-minute reconciliation entry and 24-hour review target are D proposed operational defaults, not timers that authorize release or a support guarantee. File scan state is separate from job/credit state; QUARANTINED/SCANNING is not accepted. Submitted is **Student-reported submission / تقديم أكّده الطالب**, never a verified admission or an inference from fill.

## Essential bilingual hints

These are proposed product copy, requiring human language review G-MEASURE; backend codes map to localized safe text. Include the next step beside the gated action.

| Situation | English | العربية |
|---|---|---|
| Private AI route unavailable | AI processing is unavailable for this data. Continue with manual entry or try later. | معالجة هذه البيانات بالذكاء الاصطناعي غير متاحة. تابع بالإدخال اليدوي أو حاول لاحقًا. |
| Scanner unavailable | File upload is unavailable while safety scanning is unavailable. Enter your details manually. | رفع الملفات غير متاح حاليًا لتعذّر فحصها أمنيًا. أدخل بياناتك يدويًا. |
| Unknown eligibility | We cannot determine this criterion. Add the missing information or check the official source. | لا يمكن حسم هذا الشرط. أضف المعلومات الناقصة أو راجع المصدر الرسمي. |
| Match disclaimer | Fit guidance, not a probability of admission. | إرشاد حول الملاءمة، وليس احتمالًا للقبول. |
| Reserved outcome unknown | We are checking this operation. Do not start it again; its Credits may remain reserved. | نتحقق من نتيجة هذه العملية. لا تبدأها مجددًا؛ قد يبقى رصيدها محجوزًا. |
| Payment unavailable | Purchases are unavailable during the free Beta. Return to your Credits. | الشراء غير متاح خلال التجربة المجانية. ارجع إلى صفحة الرصيد. |
| Unsupported extension | This form is not supported. Complete it manually on the official site. | هذا النموذج غير مدعوم. أكمله يدويًا على الموقع الرسمي. |
| Review-only fill | Review every filled value. You submit on the official site yourself. | راجع كل قيمة مُعبّأة. أنت تُرسل الطلب بنفسك على الموقع الرسمي. |
| Missing review data | Review data is unavailable. This action is disabled until the required evidence can be shown. | بيانات المراجعة غير متاحة. هذا الإجراء معطّل حتى يمكن عرض الأدلة المطلوبة. |
| Connection lost after send | The result is not confirmed. Reconnect to check the same request. | لم تتأكد النتيجة. أعد الاتصال للتحقق من الطلب نفسه. |

## Acceptance mapping

These are future implementation review fixtures. Only token contrast and documentation structure are statically checked in this phase; no browser/UAT/conformance claim.

| ID | Fixture and observable acceptance | Source / routes |
|---|---|---|
| DS-01 | Every specified text/background and essential border/focus pair passes calculated thresholds; status understandable in monochrome; disabled explanation readable | NFR-015/016; all routes |
| DS-02 | 320px, 768px and 1366px plus 200% text/400% browser zoom: no lost CTA, clipped Arabic diacritics or page-wide table overflow; keyboard can scroll a named table | NFR-013–015; R02/R12/R16/R20/R35/R39/R43/R49 |
| DS-03 | Keyboard-only public search → signup → profile → quote/dialog → version compare → tracker → ticket; no trap, visible unoccluded focus and correct return, errors labelled/read | NFR-015; AC-001/004/012/014/019/032 |
| DS-04 | Arabic UI + English document and inverse, mixed names/URLs/signed Credits localized without reordered IDs, corrupted numbers or changed output language | NFR-013; FR-036; AC-015; R12/R17/R20/R21 |
| DS-05 | Known donor date versus unknown/rolling/DST/cutoff boundary; no invented zone/reminder; Admin policy change cannot alter existing restore_until | FR-023/057/117–120; AC-007/029/037–039 + UD-001 |
| DS-06 | Low balance versus daily cap versus global cap/scanner/consent gate are distinct; 0-price operation still checked; uncertain outcome shows hold, not automatic refund; same accepted price/retry | FR-038/071–078/123–125; AC-023–025/040/041; R13–R18 |
| DS-07 | Screen reader announces labelled fields/errors/status once; table headers, author/source labels, no hidden duplicate cards; reduced motion and forced colors retain meaning | NFR-015/019; R02/R16/R20/R26/R35/R42 |
| DS-08 | Guest/private deep-link, Admin library, removed support assignment, consent withdrawal and expired extension token deny data/action despite visible navigation/flag | FR-049/060/110/113; AC-003/020/036; UX-01/03/05 |

Manual keyboard, browser screenshot, PDF/DOCX round-trip, Arabic linguistic review, screen reader and measured performance checks belong to later implemented phases. [Report 04](../../tasks/phase-reports/04.md) distinguishes static evidence, MISSING contracts and external gates from those unrun obligations.
