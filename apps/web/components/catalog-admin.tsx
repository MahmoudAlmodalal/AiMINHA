"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { createHealthClient, getCsrf, validateSession } from "@minhaai/contracts";
import { CatalogRound, catalogLabel, catalogTime, safeCatalogUrl } from "./catalog-presentation";
import type { AdminScholarship, Candidate, Funding, Round, Source } from "./catalog-types";

const client = createHealthClient();
type SourceInput = Omit<Source, "id" | "version_id" | "revision" | "editor_id" | "automation_enabled">;
const blankSource: SourceInput = {
  name: "", url: "", permission_status: "UNVERIFIED", license_basis: "", permission_evidence: "",
  date_checked: null, valid_until: null, freshness_days: null, allow_manual: true, allow_import: false, reason: "",
};
const blankCandidate: Candidate = {
  source_id: "", title: "", provider: "", summary: "", education_levels: [], disciplines: [], countries: [],
  languages: [], funding: "UNKNOWN", criteria: [], required_documents: [], submission_url: null,
  rounds: [{ kind: "UNKNOWN", label: "", source_text: "", closes_at: null, deadline_date: null, timezone: null }],
  source_checked_at: null, internal_notes: "", origin: "MANUAL", reason: "",
};
const splitLines = (value: string) => value.split("\n");
const cleanLines = (values: string[]) => values.map(value => value.trim()).filter(Boolean);
const actionStates = {
  APPROVE: ["DRAFT", "REVERIFY"], REJECT: ["DRAFT", "REVERIFY"],
  REVERIFY: ["PUBLISHED", "REVERIFY"], SUSPEND: ["PUBLISHED", "REVERIFY"],
  ARCHIVE: ["PUBLISHED", "REVERIFY", "REJECTED", "SUSPENDED"], RESTORE: ["SUSPENDED", "ARCHIVED"],
};
function sourceInput(item: Source): SourceInput {
  return { name: item.name, url: item.url, permission_status: item.permission_status,
    license_basis: item.license_basis, permission_evidence: item.permission_evidence,
    date_checked: item.date_checked, valid_until: item.valid_until, freshness_days: item.freshness_days,
    allow_manual: item.allow_manual, allow_import: item.allow_import, reason: "" };
}
function candidateInput(item: AdminScholarship["latest"]): Candidate {
  return { source_id: item.source_id, title: item.title, provider: item.provider, summary: item.summary,
    education_levels: item.education_levels, disciplines: item.disciplines, countries: item.countries,
    languages: item.languages, funding: item.funding, criteria: item.criteria,
    required_documents: item.required_documents, submission_url: item.submission_url,
    rounds: item.rounds, source_checked_at: item.source_checked_at, internal_notes: item.internal_notes,
    origin: "MANUAL", reason: "" };
}

export function CatalogAdmin({ locale }: { locale: "ar" | "en" }) {
  const ar = locale === "ar";
  const [sources, setSources] = useState<Source[]>([]);
  const [queue, setQueue] = useState<AdminScholarship[]>([]);
  const [selected, setSelected] = useState<AdminScholarship | null>(null);
  const [previous, setPrevious] = useState<AdminScholarship["latest"] | null>(null);
  const [sourceForm, setSourceForm] = useState<SourceInput>(blankSource);
  const [sourceEdit, setSourceEdit] = useState<Source | null>(null);
  const [candidate, setCandidate] = useState<Candidate>(blankCandidate);
  const [candidateEdit, setCandidateEdit] = useState<AdminScholarship | null>(null);
  const [reason, setReason] = useState("");
  const [reviewed, setReviewed] = useState(false);
  const [visibility, setVisibility] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [refresh, setRefresh] = useState(0);
  const [authorized, setAuthorized] = useState(false);
  const [busy, setBusy] = useState(true);
  const [message, setMessage] = useState("");
  const [failed, setFailed] = useState(false);
  const keys = useRef(new Map<string, string>());

  function clearRestrictedContent() {
    setAuthorized(false); setSources([]); setQueue([]); setSelected(null); setPrevious(null);
    setCandidate(blankCandidate); setCandidateEdit(null); setSourceForm(blankSource); setSourceEdit(null);
    setReason(""); setReviewed(false);
  }

  function errorMessage(code: string) {
    const messages: Record<string, [string, string]> = {
      ADMIN_UNAVAILABLE: ["المراجعة غير متاحة. يلزم حساب أدمن بصلاحية المراجعة وتحقق متعدد العوامل حديث من الخادم.", "Review is unavailable. A scoped Admin account and recent server-verified MFA are required."],
      ADMIN_MFA_REQUIRED: ["انتهى تحقق الجلسة أو لا تسمح صلاحياتها بالمراجعة. أعد تسجيل الدخول والتحقق المعتمد من الخادم.", "The session proof expired or does not permit review. Sign in and complete the approved server verification."],
      FORBIDDEN: ["لا تسمح صلاحيات الجلسة بهذه العملية. اعتماد المصدر يحتاج صلاحية مستقلة.", "This session does not permit the action. Source approval requires a separate scope."],
      SOURCE_NOT_PERMITTED: ["المصدر غير مأذون حاليًا لهذه العملية. راجع سجل الإذن.", "The source is not currently permitted for this operation. Review its permission record."],
      PRECONDITION_FAILED: ["تغيرت النسخة. أعد التحميل وراجع النسخة الحالية قبل القرار.", "The revision changed. Reload and review the current version before deciding."],
      STALE_REVISION: ["تغيرت النسخة. أعد التحميل وراجعها.", "The revision changed. Reload and review it."],
      UNKNOWN_OUTCOME: ["تعذر تأكيد النتيجة. أعد تحميل السجل أولًا؛ إعادة الطلب نفسه تستخدم معرف العملية نفسه.", "The outcome could not be confirmed. Reload the record first; retrying the same request uses the same operation key."],
    };
    return messages[code]?.[ar ? 0 : 1] ?? (ar ? "تعذر تأكيد النتيجة. راجع المدخلات والإذن والسجل الحالي قبل إعادة المحاولة." : "The outcome could not be confirmed. Review the input, permission and current record before retrying.");
  }

  async function headers(path: string, body: unknown, revision?: number) {
    const fingerprint = `${path}:${JSON.stringify(body)}:${revision ?? ""}`;
    if (!keys.current.has(fingerprint)) keys.current.set(fingerprint, crypto.randomUUID());
    return { "X-CSRFToken": await getCsrf(client), "Idempotency-Key": keys.current.get(fingerprint)!, ...(revision === undefined ? {} : { "If-Match": `"${revision}"` }) };
  }

  async function run(action: () => Promise<void>) {
    setBusy(true); setMessage(""); setFailed(false);
    try { await action(); }
    catch (error) {
      const code = error instanceof Error ? error.message : "UNKNOWN_OUTCOME";
      if (["ADMIN_UNAVAILABLE", "ADMIN_MFA_REQUIRED", "SESSION_EXPIRED", "VERIFIED_ADULT_REQUIRED"].includes(code)) clearRestrictedContent();
      setFailed(true); setMessage(errorMessage(code));
    } finally { setBusy(false); }
  }

  useEffect(() => {
    const controller = new AbortController();
    void (async () => {
      try {
        const session = await client.GET("/api/v1/session", { signal: controller.signal });
        if (!session.response.ok || !session.data || validateSession(session.data).roles[0] !== "ADMIN") throw new Error("ADMIN_UNAVAILABLE");
        const [registry, candidates] = await Promise.all([
          client.GET("/api/v1/admin/sources", { signal: controller.signal }),
          client.GET("/api/v1/admin/scholarships", { signal: controller.signal, params: { query: { page, page_size: 12, visibility: (visibility || undefined) as AdminScholarship["visibility"] | undefined } } }),
        ]);
        if (controller.signal.aborted) return;
        if (!registry.response.ok || !registry.data || !candidates.response.ok || !candidates.data) throw new Error("ADMIN_UNAVAILABLE");
        setSources(registry.data.items); setQueue(candidates.data.items); setTotal(candidates.data.total);
        setAuthorized(true); setFailed(false); setBusy(false);
      } catch {
        if (controller.signal.aborted) return;
        clearRestrictedContent(); setFailed(true); setMessage(errorMessage("ADMIN_UNAVAILABLE")); setBusy(false);
      }
    })();
    return () => controller.abort();
    // The localized failure message changes with the route's locale.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refresh, page, visibility, locale]);

  async function select(item: AdminScholarship) {
    await run(async () => {
      const response = await client.GET("/api/v1/admin/scholarships/{scholarship_id}", { params: { path: { scholarship_id: item.id } } });
      if (!response.response.ok || !response.data) throw new Error(response.response.status === 403 ? "ADMIN_UNAVAILABLE" : "UNKNOWN_OUTCOME");
      setSelected(response.data); setPrevious(response.data.versions.at(-2) ?? null); setReason(""); setReviewed(false);
    });
  }

  async function saveSource(event: FormEvent) {
    event.preventDefault();
    await run(async () => {
      const path = sourceEdit ? `/api/v1/admin/sources/${sourceEdit.id}/versions` : "/api/v1/admin/sources";
      const h = await headers(path, sourceForm, sourceEdit?.revision);
      const response = sourceEdit
        ? await client.POST("/api/v1/admin/sources/{source_id}/versions", { body: sourceForm, params: { path: { source_id: sourceEdit.id }, header: { ...h, "If-Match": `"${sourceEdit.revision}"` } } })
        : await client.POST("/api/v1/admin/sources", { body: sourceForm, params: { header: h } });
      if (!response.response.ok || !response.data) throw new Error(response.error?.code ?? "UNKNOWN_OUTCOME");
      setSourceForm(blankSource); setSourceEdit(null); setRefresh(value => value + 1);
      setMessage(ar ? "حُفظ إصدار المصدر. لم تُجلب أي صفحة خارجية." : "Source revision saved. No external page was fetched.");
    });
  }

  async function saveCandidate(event: FormEvent) {
    event.preventDefault();
    await run(async () => {
      const body = { ...candidate, origin: "MANUAL" as const,
        education_levels: candidate.education_levels.filter(Boolean), disciplines: cleanLines(candidate.disciplines),
        countries: cleanLines(candidate.countries), languages: cleanLines(candidate.languages),
        criteria: cleanLines(candidate.criteria), required_documents: cleanLines(candidate.required_documents),
      };
      const path = candidateEdit ? `/api/v1/admin/scholarships/${candidateEdit.id}/versions` : "/api/v1/admin/scholarships";
      const h = await headers(path, body, candidateEdit?.revision);
      const response = candidateEdit
        ? await client.POST("/api/v1/admin/scholarships/{scholarship_id}/versions", { body, params: { path: { scholarship_id: candidateEdit.id }, header: { ...h, "If-Match": `"${candidateEdit.revision}"` } } })
        : await client.POST("/api/v1/admin/scholarships", { body, params: { header: h } });
      if (!response.response.ok || !response.data) throw new Error(response.error?.code ?? "UNKNOWN_OUTCOME");
      setPrevious(response.data.versions.at(-2) ?? null); setSelected(response.data); setCandidate(blankCandidate);
      setCandidateEdit(null); setReviewed(false); setRefresh(value => value + 1);
      setMessage(ar ? "حُفظت مسودة جديدة. تحتاج مراجعة واعتمادًا بشريًا قبل الظهور العام." : "A new draft was saved. Human review and approval are required before public display.");
    });
  }

  async function moderate(action: "APPROVE" | "REJECT" | "REVERIFY" | "SUSPEND" | "ARCHIVE" | "RESTORE") {
    if (!selected) return;
    await run(async () => {
      const body = { version_id: selected.latest.id, action, reason };
      const response = await client.POST("/api/v1/admin/scholarships/{scholarship_id}/moderation", { body,
        params: { path: { scholarship_id: selected.id }, header: { ...await headers(`/api/v1/admin/scholarships/${selected.id}/moderation`, body, selected.revision), "If-Match": `"${selected.revision}"` } } });
      if (!response.response.ok || !response.data) throw new Error(response.error?.code ?? "UNKNOWN_OUTCOME");
      setSelected(response.data); setReviewed(false); setReason(""); setRefresh(value => value + 1);
      setMessage(ar ? "سُجل قرار المراجعة على النسخة المحددة." : "The moderation decision was recorded for the exact version.");
    });
  }

  const source = selected ? sources.find(item => item.id === selected.latest.source_id) : null;
  const setRound = (round: Round) => setCandidate({ ...candidate, rounds: [round] });
  const round = candidate.rounds[0] ?? blankCandidate.rounds[0];

  return <section aria-busy={busy}>
    <p className="catalog-note">{ar ? "المراجعة بصلاحية MODERATION والتحقق متعدد العوامل من الخادم. اعتماد إذن مصدر يتطلب SOURCE_APPROVAL أيضًا. لا تتوفر هنا أي آلية لتجاوز هذه الشروط." : "Review requires the MODERATION scope and recent server-verified MFA. Source permission approval additionally requires SOURCE_APPROVAL."}</p>
    <div className="catalog-actions"><button disabled={busy} onClick={() => { setBusy(true); setRefresh(value => value + 1); }}>{ar ? "إعادة تحميل السجل" : "Reload records"}</button><a href={`/${locale}/account`}>{ar ? "الحساب وتسجيل الدخول" : "Account and sign in"}</a></div>
    <p role={failed ? "alert" : "status"} aria-live="polite">{busy ? (ar ? "جارٍ التحقق والتحميل…" : "Checking access and loading…") : message}</p>
    {authorized && <>
      <h2>{ar ? "سجل المصادر والأذونات" : "Sources and permission registry"}</h2>
      <p>{ar ? "لا توجد أتمتة لجلب المصادر. السماح بالاستيراد ليس تشغيلًا للزحف؛ الإدخال الحالي يدوي فقط." : "Source fetching is unavailable. An import permission does not start a crawler; this interface uses manual entry."}</p>
      {sources.length === 0 && <p>{ar ? "لم تُسجل مصادر بعد." : "No sources have been registered."}</p>}
      <div className="catalog-grid">{sources.map(item => <article key={item.id}>
        <h3>{item.name}</h3><span className="catalog-badge">{catalogLabel(item.permission_status, ar)}</span>
        <p className="catalog-source"><bdi>{item.url}</bdi></p>
        <dl><dt>{ar ? "أساس الاستخدام" : "Use basis"}</dt><dd>{item.license_basis || "—"}</dd>
          <dt>{ar ? "دليل الإذن" : "Permission evidence"}</dt><dd>{item.permission_evidence || "—"}</dd>
          <dt>{ar ? "آخر فحص UTC" : "Checked UTC"}</dt><dd><bdi>{catalogTime(item.date_checked, locale)}</bdi></dd>
          <dt>{ar ? "ينتهي الإذن UTC" : "Permission expires UTC"}</dt><dd><bdi>{catalogTime(item.valid_until, locale)}</bdi></dd>
          <dt>{ar ? "نافذة التحقق بالأيام" : "Freshness window (days)"}</dt><dd>{item.freshness_days ?? (ar ? "غير محددة" : "Not defined")}</dd>
          <dt>{ar ? "الإصدار / المحرر" : "Revision / editor"}</dt><dd>{item.revision} / <bdi>{item.editor_id}</bdi></dd>
        </dl>
        <button disabled={busy} onClick={() => { setSourceEdit(item); setSourceForm(sourceInput(item)); }}>{ar ? "إعداد إصدار مصدر جديد" : "Prepare source revision"}</button>
      </article>)}</div>
      <details open={!!sourceEdit}><summary>{sourceEdit ? (ar ? "تعديل إذن المصدر بإصدار جديد" : "Revise source permission") : (ar ? "تسجيل مصدر" : "Register a source")}</summary>
        <form onSubmit={saveSource}>
          <div className="catalog-fields">
            <label>{ar ? "اسم المصدر" : "Source name"}<input required maxLength={200} value={sourceForm.name} onChange={e => setSourceForm({ ...sourceForm, name: e.target.value })} /></label>
            <label>{ar ? "رابط المصدر HTTPS" : "Source HTTPS URL"}<input required type="url" dir="ltr" value={sourceForm.url} onChange={e => setSourceForm({ ...sourceForm, url: e.target.value })} /></label>
            <label>{ar ? "حالة الإذن" : "Permission status"}<select value={sourceForm.permission_status} onChange={e => setSourceForm({ ...sourceForm, permission_status: e.target.value as SourceInput["permission_status"] })}>{["UNVERIFIED", "APPROVED", "BLOCKED", "REVOKED"].map(value => <option key={value} value={value}>{catalogLabel(value, ar)}</option>)}</select></label>
            <label>{ar ? "تاريخ الفحص (ISO UTC)" : "Checked at (ISO UTC)"}<input dir="ltr" placeholder="2026-10-16T12:00:00Z" value={sourceForm.date_checked ?? ""} onChange={e => setSourceForm({ ...sourceForm, date_checked: e.target.value || null })} /></label>
            <label>{ar ? "انتهاء الإذن (ISO UTC، اختياري)" : "Permission expiry (ISO UTC, optional)"}<input dir="ltr" value={sourceForm.valid_until ?? ""} onChange={e => setSourceForm({ ...sourceForm, valid_until: e.target.value || null })} /></label>
            <label>{ar ? "نافذة إعادة التحقق بالأيام، إن اعتمدت" : "Approved freshness window, days"}<input type="number" min={1} max={365} value={sourceForm.freshness_days ?? ""} onChange={e => setSourceForm({ ...sourceForm, freshness_days: e.target.value ? Number(e.target.value) : null })} /></label>
          </div>
          <label>{ar ? "أساس الترخيص والاستخدام" : "License and use basis"}<textarea value={sourceForm.license_basis} onChange={e => setSourceForm({ ...sourceForm, license_basis: e.target.value })} /></label>
          <label>{ar ? "دليل الإذن المتحقق" : "Verified permission evidence"}<textarea value={sourceForm.permission_evidence} onChange={e => setSourceForm({ ...sourceForm, permission_evidence: e.target.value })} /></label>
          <label className="confirm"><input type="checkbox" checked={sourceForm.allow_manual} onChange={e => setSourceForm({ ...sourceForm, allow_manual: e.target.checked })} />{ar ? "السماح بالإدخال اليدوي المأذون" : "Permit authorized manual entry"}</label>
          <label className="confirm"><input type="checkbox" checked={sourceForm.allow_import} onChange={e => setSourceForm({ ...sourceForm, allow_import: e.target.checked })} />{ar ? "إذن استيراد خاص بهذا المصدر (لا يجلب محتوى)" : "Source-specific import permission (does not fetch content)"}</label>
          <label>{ar ? "سبب القرار" : "Decision reason"}<textarea required value={sourceForm.reason} onChange={e => setSourceForm({ ...sourceForm, reason: e.target.value })} /></label>
          <div className="catalog-actions"><button disabled={busy}>{ar ? "حفظ إصدار المصدر" : "Save source revision"}</button><button type="button" className="secondary" onClick={() => { setSourceForm(blankSource); setSourceEdit(null); }}>{ar ? "إلغاء التعديل" : "Cancel edit"}</button></div>
        </form>
      </details>

      <h2>{ar ? "الإدخال اليدوي أولًا" : "Manual entry first"}</h2>
      <details open={!!candidateEdit}><summary>{candidateEdit ? (ar ? "إعداد نسخة جديدة للمنحة" : "Prepare a scholarship revision") : (ar ? "إنشاء مسودة منحة" : "Create a scholarship draft")}</summary>
        <form onSubmit={saveCandidate}>
          <p>{ar ? "لا يملأ النموذج حقائق ناقصة، ولا ينشر أي تعديل تلقائيًا. المعايير والمستندات: عنصر واحد في كل سطر." : "Missing facts stay unknown. No edit publishes automatically. Enter one criterion or document per line."}</p>
          <div className="catalog-fields">
            <label>{ar ? "المصدر" : "Source"}<select required value={candidate.source_id} onChange={e => setCandidate({ ...candidate, source_id: e.target.value })}><option value="">{ar ? "اختر مصدرًا مأذونًا" : "Choose a permitted source"}</option>{sources.map(item => <option key={item.id} value={item.id} disabled={item.permission_status !== "APPROVED" || !item.allow_manual}>{item.name} · {catalogLabel(item.permission_status, ar)}</option>)}</select></label>
            <label>{ar ? "العنوان" : "Title"}<input required maxLength={300} value={candidate.title} onChange={e => setCandidate({ ...candidate, title: e.target.value })} /></label>
            <label>{ar ? "الجهة المانحة" : "Provider"}<input required maxLength={200} value={candidate.provider} onChange={e => setCandidate({ ...candidate, provider: e.target.value })} /></label>
            <label>{ar ? "التمويل" : "Funding"}<select value={candidate.funding} onChange={e => setCandidate({ ...candidate, funding: e.target.value as Funding })}>{["UNKNOWN", "FULL", "PARTIAL", "WAIVER", "AID"].map(value => <option key={value} value={value}>{catalogLabel(value, ar)}</option>)}</select></label>
            <label>{ar ? "المستويات (اختيار متعدد)" : "Education levels (multiple selection)"}<select multiple value={candidate.education_levels} onChange={e => setCandidate({ ...candidate, education_levels: Array.from(e.target.selectedOptions, option => option.value as Candidate["education_levels"][number]) })}>{["BACHELOR", "MASTER", "PHD"].map(value => <option key={value} value={value}>{catalogLabel(value, ar)}</option>)}</select></label>
            <label>{ar ? "التخصصات، عنصر في كل سطر" : "Disciplines, one per line"}<textarea value={candidate.disciplines.join("\n")} onChange={e => setCandidate({ ...candidate, disciplines: splitLines(e.target.value) })} /></label>
            <label>{ar ? "البلدان، عنصر في كل سطر" : "Countries, one per line"}<textarea value={candidate.countries.join("\n")} onChange={e => setCandidate({ ...candidate, countries: splitLines(e.target.value) })} /></label>
            <label>{ar ? "اللغات، عنصر في كل سطر" : "Languages, one per line"}<textarea value={candidate.languages.join("\n")} onChange={e => setCandidate({ ...candidate, languages: splitLines(e.target.value) })} /></label>
            <label>{ar ? "رابط التقديم HTTPS، إن تأكد" : "Confirmed application HTTPS URL"}<input type="url" dir="ltr" value={candidate.submission_url ?? ""} onChange={e => setCandidate({ ...candidate, submission_url: e.target.value || null })} /></label>
            <label>{ar ? "فحص المصدر (ISO UTC)" : "Source checked (ISO UTC)"}<input dir="ltr" value={candidate.source_checked_at ?? ""} onChange={e => setCandidate({ ...candidate, source_checked_at: e.target.value || null })} /></label>
          </div>
          <label>{ar ? "الملخص، إن توفرت معلومات مؤكدة" : "Summary, when confirmed information is available"}<textarea value={candidate.summary} onChange={e => setCandidate({ ...candidate, summary: e.target.value })} /></label>
          <label>{ar ? "المعايير المؤكدة" : "Confirmed criteria"}<textarea value={candidate.criteria.join("\n")} onChange={e => setCandidate({ ...candidate, criteria: splitLines(e.target.value) })} /></label>
          <label>{ar ? "المستندات المطلوبة" : "Required documents"}<textarea value={candidate.required_documents.join("\n")} onChange={e => setCandidate({ ...candidate, required_documents: splitLines(e.target.value) })} /></label>
          <fieldset><legend>{ar ? "جولة التقديم" : "Application round"}</legend>
            <p>{ar ? "يمكن إضافة جولة واحدة هنا. عند تعديل سجل متعدد الجولات تبقى الجولات المحفوظة حتى تختار استبدالها بهذه الجولة." : "This form supports one round. Editing a record with multiple rounds preserves them until you explicitly replace them with this round."}</p>
            {candidate.rounds.length > 1 && <p className="catalog-warning">{ar ? "هذا السجل متعدد الجولات. تعديل أي حقل جولة يستبدل جميع الجولات بجولة واحدة." : "This record has multiple rounds. Changing any round field replaces all rounds with one."}</p>}
            <div className="catalog-fields">
              <label>{ar ? "نوع الموعد" : "Deadline kind"}<select value={round.kind} onChange={e => setRound({ ...round, kind: e.target.value as Round["kind"], closes_at: null, deadline_date: null, timezone: null })}><option value="UNKNOWN">{ar ? "غير معروف أو ملتبس" : "Unknown or ambiguous"}</option><option value="ROLLING">{ar ? "مستمر بدليل المصدر" : "Source-confirmed rolling"}</option><option value="DATE_ONLY">{ar ? "تاريخ فقط" : "Date only"}</option><option value="CONFIRMED">{ar ? "وقت مؤكد ومنطقة زمنية" : "Confirmed instant and timezone"}</option></select></label>
              <label>{ar ? "اسم الجولة" : "Round label"}<input value={round.label} onChange={e => setRound({ ...round, label: e.target.value })} /></label>
              {round.kind === "DATE_ONLY" && <label>{ar ? "التاريخ الوارد فقط" : "Source date only"}<input required type="date" value={round.deadline_date ?? ""} onChange={e => setRound({ ...round, deadline_date: e.target.value || null })} /></label>}
              {round.kind === "CONFIRMED" && <>
                <label>{ar ? "وقت إغلاق ISO مع إزاحة" : "Closing instant, ISO with offset"}<input required dir="ltr" placeholder="2026-12-01T17:00:00+02:00" value={round.closes_at ?? ""} onChange={e => setRound({ ...round, closes_at: e.target.value || null })} /></label>
                <label>{ar ? "منطقة IANA من المصدر" : "Source IANA timezone"}<input required dir="ltr" placeholder="Asia/Hebron" value={round.timezone ?? ""} onChange={e => setRound({ ...round, timezone: e.target.value || null })} /></label>
              </>}
            </div>
            <label>{ar ? "نص الموعد كما ورد" : "Deadline source wording"}<textarea value={round.source_text} onChange={e => setRound({ ...round, source_text: e.target.value })} /></label>
          </fieldset>
          <label>{ar ? "ملاحظات داخلية، لا تظهر للجمهور" : "Internal notes, excluded from public views"}<textarea value={candidate.internal_notes} onChange={e => setCandidate({ ...candidate, internal_notes: e.target.value })} /></label>
          <label>{ar ? "سبب الإدخال أو التعديل" : "Entry or revision reason"}<textarea required value={candidate.reason} onChange={e => setCandidate({ ...candidate, reason: e.target.value })} /></label>
          <div className="catalog-actions"><button disabled={busy}>{ar ? "حفظ مسودة غير منشورة" : "Save unpublished draft"}</button><button className="secondary" type="button" onClick={() => { setCandidate(blankCandidate); setCandidateEdit(null); }}>{ar ? "إلغاء التعديل" : "Cancel edit"}</button></div>
        </form>
      </details>

      <h2>{ar ? "قائمة المراجعة البشرية" : "Human moderation queue"}</h2>
      <label>{ar ? "الحالة" : "Visibility"}<select value={visibility} disabled={busy} onChange={e => { setBusy(true); setPage(1); setVisibility(e.target.value); setSelected(null); }}><option value="">{ar ? "كل الحالات" : "All states"}</option>{["DRAFT", "PUBLISHED", "REVERIFY", "SUSPENDED", "ARCHIVED", "REJECTED"].map(value => <option key={value} value={value}>{catalogLabel(value, ar)}</option>)}</select></label>
      {queue.length === 0 && <p>{ar ? "لا توجد منح بهذه الحالة." : "No scholarships in this state."}</p>}
      <div className="catalog-grid">{queue.map(item => <article key={item.id}><h3>{item.latest.title}</h3><p>{catalogLabel(item.visibility, ar)} · {ar ? "نسخة" : "Version"} {item.latest.version}</p><button disabled={busy} onClick={() => void select(item)}>{ar ? "افتح الأدلة والمراجعة" : "Open evidence and review"}</button></article>)}</div>
      {total > 12 && <nav className="catalog-pagination" aria-label={ar ? "صفحات المراجعة" : "Moderation pages"}><button disabled={busy || page === 1} onClick={() => { setBusy(true); setPage(value => value - 1); }}>{ar ? "السابق" : "Previous"}</button><span>{page} / {Math.ceil(total / 12)}</span><button disabled={busy || page * 12 >= total} onClick={() => { setBusy(true); setPage(value => value + 1); }}>{ar ? "التالي" : "Next"}</button></nav>}

      {selected && <article>
        <h2>{ar ? "مراجعة النسخة المحددة" : "Review the exact version"}: {selected.latest.title}</h2>
        <p>{catalogLabel(selected.visibility, ar)} · {ar ? "نسخة" : "Version"} {selected.latest.version} · {ar ? "مراجعة سجل" : "Record revision"} {selected.revision}</p>
        <dl><dt>{ar ? "معرف النسخة" : "Version ID"}</dt><dd><bdi>{selected.latest.id}</bdi></dd><dt>{ar ? "بصمة المحتوى" : "Content hash"}</dt><dd><bdi>{selected.latest.content_hash}</bdi></dd><dt>{ar ? "نسخة منشورة سابقة" : "Published version pointer"}</dt><dd><bdi>{selected.published_version_id ?? "—"}</bdi></dd><dt>{ar ? "المحرر / UTC" : "Editor / UTC"}</dt><dd><bdi>{selected.latest.created_by}</bdi> / <bdi>{catalogTime(selected.latest.created_at, locale)}</bdi></dd><dt>{ar ? "نسخة إذن المصدر" : "Source permission revision"}</dt><dd><bdi>{selected.latest.source_revision_id}</bdi></dd></dl>
        <h3>{ar ? "الحقائق المطلوب اعتمادها" : "Facts to approve"}</h3>
        <p>{selected.latest.summary}</p>
        <dl>{(["provider", "education_levels", "disciplines", "countries", "languages", "funding", "criteria", "required_documents", "submission_url", "source_checked_at", "origin"] as const).map(field => <div className="catalog-review-field" key={field}><dt><bdi>{field}</bdi></dt><dd>{Array.isArray(selected.latest[field]) ? (selected.latest[field] as string[]).join("\n") || "—" : String(selected.latest[field] ?? "—")}</dd></div>)}</dl>
        <ul>{selected.latest.rounds.map((item, i) => <CatalogRound key={i} round={item} locale={locale} />)}</ul>
        <h3>{ar ? "المصدر والإذن الحالي" : "Current source and permission"}</h3>
        {source ? <><p>{source.name} · {catalogLabel(source.permission_status, ar)}</p><p>{source.license_basis}</p><p>{source.permission_evidence}</p>{safeCatalogUrl(source.url) && <a href={safeCatalogUrl(source.url)!} target="_blank" rel="noopener noreferrer">{ar ? "افتح دليل المصدر" : "Open source"}</a>}<p>{ar ? "آخر فحص UTC: " : "Last checked UTC: "}<bdi>{catalogTime(source.date_checked, locale)}</bdi></p><p>{ar ? "انتهاء الإذن UTC: " : "Permission expires UTC: "}<bdi>{catalogTime(source.valid_until, locale)}</bdi></p></> : <p className="catalog-warning">{ar ? "دليل المصدر الحالي غير متاح. لا تعتمد النسخة." : "Current source evidence is unavailable. Do not approve this version."}</p>}
        <h3>{ar ? "ملاحظات داخلية" : "Internal notes"}</h3><p>{selected.latest.internal_notes || "—"}</p>
        {selected.latest.duplicate_ids.length > 0 && <p className="catalog-warning">{ar ? "توجد منح يحتمل تكرارها، يلزم فحص يدوي: " : "Possible duplicates require manual review: "}{selected.latest.duplicate_ids.join(", ")}</p>}
        {selected.versions.length > 1 && <>
          <label>{ar ? "اختر نسخة محفوظة للمقارنة" : "Compare with an immutable version"}<select value={previous?.id ?? ""} onChange={e => setPrevious(selected.versions.find(item => item.id === e.target.value) ?? null)}><option value="">{ar ? "دون مقارنة" : "No comparison"}</option>{selected.versions.filter(item => item.id !== selected.latest.id).map(item => <option key={item.id} value={item.id}>{ar ? "نسخة" : "Version"} {item.version}{item.id === selected.published_version_id ? (ar ? " · المنشورة السابقة" : " · published pointer") : ""}</option>)}</select></label>
          {previous && previous.id !== selected.latest.id && <details open><summary>{ar ? "مقارنة الحقائق بين النسخ" : "Compare versioned facts"}</summary><div className="catalog-grid"><section><h4>{ar ? "السابقة" : "Previous"} · {previous.version}</h4><pre>{JSON.stringify({ ...candidateInput(previous), origin: previous.origin, reason: previous.reason }, null, 2)}</pre></section><section><h4>{ar ? "المرشحة" : "Candidate"} · {selected.latest.version}</h4><pre>{JSON.stringify({ ...candidateInput(selected.latest), origin: selected.latest.origin, reason: selected.latest.reason }, null, 2)}</pre></section></div></details>}
        </>}
        <h3>{ar ? "سجل القرارات المنسوبة" : "Attributable decision history"}</h3>
        <ol>{selected.history.map(event => <li key={event.id}><bdi>{event.action}</bdi> · <bdi>{catalogTime(event.created_at, locale)}</bdi> · {event.reason} · <bdi>{event.actor_id}</bdi> · <bdi>{event.version_id}</bdi></li>)}</ol>
        <button disabled={busy} onClick={() => { setCandidateEdit(selected); setPrevious(selected.latest); setCandidate(candidateInput(selected.latest)); }}>{ar ? "إعداد تعديل كمسودة جديدة" : "Prepare an edit as a new draft"}</button>
        <label>{ar ? "سبب قرار المراجعة" : "Moderation reason"}<textarea value={reason} onChange={e => setReason(e.target.value)} /></label>
        <label className="confirm"><input type="checkbox" checked={reviewed} onChange={e => setReviewed(e.target.checked)} />{ar ? "راجعت هذه النسخة بعينها والأدلة والإذن والتكرارات المحتملة" : "I reviewed this exact version, its evidence, source permission and possible duplicates"}</label>
        {source?.version_id !== selected.latest.source_revision_id && <p className="catalog-warning">{ar ? "تغير إصدار إذن المصدر. أضف نسخة منحة جديدة مرتبطة بالإذن الحالي وراجعها قبل النشر." : "The source permission revision changed. Append a candidate tied to the current permission and review it before publishing."}</p>}
        <div className="catalog-actions">{(["APPROVE", "REJECT", "REVERIFY", "SUSPEND", "ARCHIVE", "RESTORE"] as const).map(action => <button key={action} disabled={busy || !reason.trim() || !reviewed || !actionStates[action].includes(selected.visibility) || (action === "APPROVE" && (source?.permission_status !== "APPROVED" || source.version_id !== selected.latest.source_revision_id))} onClick={() => void moderate(action)}>{({ APPROVE: ar ? "اعتماد ونشر النسخة" : "Approve and publish version", REJECT: ar ? "رفض" : "Reject", REVERIFY: ar ? "طلب إعادة التحقق" : "Require reverification", SUSPEND: ar ? "تعليق" : "Suspend", ARCHIVE: ar ? "أرشفة" : "Archive", RESTORE: ar ? "استعادة للمراجعة" : "Restore for review" })[action]}</button>)}</div>
      </article>}
    </>}
  </section>;
}
