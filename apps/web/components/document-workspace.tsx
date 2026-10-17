"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { createHealthClient, getCsrf, validateSession } from "@minhaai/contracts";
import styles from "./document-workspace.module.css";

type Language = "ar" | "en";
type Kind = "CV" | "MOTIVATION_LETTER" | "PERSONAL_STATEMENT" | "ESSAY";
type Version = {
  id: string; number: number; title: string; language: Language; content: string;
  content_hash: string; approved: boolean; created_at: string;
};
type Document = { id: string; kind: Kind; revision: number; current: Version };
type Asset = { id: string; state: string; declared_size: number; created_at: string };
type FileCapabilities = { upload_available: boolean; max_file_bytes: number; max_student_bytes: number };
type Access = "loading" | "ready" | "denied" | "unavailable";
const client = createHealthClient();
const kinds: Kind[] = ["CV", "MOTIVATION_LETTER", "PERSONAL_STATEMENT", "ESSAY"];
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

class RequestFailure extends Error {
  constructor(public code: string, public status = 0) { super(code); }
}

function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new RequestFailure("INVALID_RESPONSE");
  return value as Record<string, unknown>;
}
function identifier(value: unknown): string {
  if (typeof value !== "string" || !uuid.test(value)) throw new RequestFailure("INVALID_RESPONSE");
  return value;
}
function version(value: unknown): Version {
  const row = record(value);
  if (!Number.isInteger(row.number) || Number(row.number) < 1 || typeof row.title !== "string" ||
      typeof row.content !== "string" || row.content.length > 40000 || !["ar", "en"].includes(String(row.language)) ||
      typeof row.content_hash !== "string" || !/^[a-f0-9]{64}$/.test(row.content_hash) ||
      typeof row.approved !== "boolean" || typeof row.created_at !== "string" || !Number.isFinite(Date.parse(row.created_at))) {
    throw new RequestFailure("INVALID_RESPONSE");
  }
  return { id: identifier(row.id), number: Number(row.number), title: row.title, content: row.content,
    language: row.language as Language, content_hash: row.content_hash, approved: row.approved, created_at: row.created_at };
}
function document(value: unknown): Document {
  const row = record(value);
  if (!kinds.includes(row.kind as Kind) || !Number.isInteger(row.revision) || Number(row.revision) < 1) throw new RequestFailure("INVALID_RESPONSE");
  return { id: identifier(row.id), kind: row.kind as Kind, revision: Number(row.revision), current: version(row.current) };
}
function asset(value: unknown): Asset {
  const row = record(value);
  if (typeof row.state !== "string" || !Number.isInteger(row.declared_size) || Number(row.declared_size) < 1 ||
      typeof row.created_at !== "string" || !Number.isFinite(Date.parse(row.created_at))) throw new RequestFailure("INVALID_RESPONSE");
  return { id: identifier(row.id), state: row.state, declared_size: Number(row.declared_size), created_at: row.created_at };
}
function items(value: unknown): unknown[] {
  const rows = record(value).items;
  if (!Array.isArray(rows)) throw new RequestFailure("INVALID_RESPONSE");
  return rows;
}
async function jsonRequest(path: string, init: RequestInit = {}): Promise<unknown> {
  const response = await fetch(`/api/v1${path}`, { ...init, credentials: "same-origin", cache: "no-store" });
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const code = body && typeof body === "object" && "code" in body && typeof body.code === "string" ? body.code : "REQUEST_FAILED";
    throw new RequestFailure(code, response.status);
  }
  return body;
}

export function DocumentWorkspace({ locale }: { locale: Language }) {
  const ar = locale === "ar";
  const [access, setAccess] = useState<Access>("loading");
  const [documents, setDocuments] = useState<Document[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [capabilities, setCapabilities] = useState<FileCapabilities | null>(null);
  const [manualAvailable, setManualAvailable] = useState(false);
  const [selected, setSelected] = useState<Document | null>(null);
  const [versions, setVersions] = useState<Version[]>([]);
  const [viewed, setViewed] = useState<Version | null>(null);
  const [kind, setKind] = useState<Kind>("CV");
  const [language, setLanguage] = useState<Language>(locale);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [reviewed, setReviewed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const fileInput = useRef<HTMLInputElement>(null);
  const keys = useRef(new Map<string, string>());
  const uploadKey = useRef<{ file: File; key: string } | null>(null);
  const kindLabels: Record<Kind, string> = ar ? {
    CV: "سيرة ذاتية", MOTIVATION_LETTER: "خطاب الدافع", PERSONAL_STATEMENT: "بيان شخصي", ESSAY: "مقال المنحة",
  } : { CV: "CV", MOTIVATION_LETTER: "Motivation letter", PERSONAL_STATEMENT: "Personal statement", ESSAY: "Scholarship essay" };
  const dirty = viewed ? title !== viewed.title || content !== viewed.content || language !== viewed.language : Boolean(title || content);
  const count = (value: number) => new Intl.NumberFormat(locale).format(value);

  function clearPrivate() {
    setDocuments([]); setAssets([]); setSelected(null); setVersions([]); setViewed(null);
    setTitle(""); setContent(""); setFile(null); setReviewed(false); keys.current.clear();
    uploadKey.current = null;
    if (fileInput.current) fileInput.current.value = "";
  }

  function errorMessage(error: unknown) {
    const code = error instanceof RequestFailure ? error.code : "REQUEST_FAILED";
    const messages: Record<string, [string, string]> = {
      FILE_SCANNER_UNAVAILABLE: ["فحص الملفات غير متاح حاليًا. لم يُقبل الملف؛ يمكنك إدخال معلوماتك يدويًا.", "File scanning is currently unavailable. The file was not accepted; you can enter your information manually."],
      PRIVATE_STORAGE_UNAVAILABLE: ["رفع الملفات وتنزيلها غير متاح حاليًا. احتفظ بنسختك واستخدم الإدخال اليدوي.", "File upload and download are currently unavailable. Keep your copy and use manual entry."],
      FILE_TYPE_REJECTED: ["تعذر التحقق من صيغة الملف أو محتواه. استخدم ملف PDF أو DOCX أو PNG أو JPG صالحًا.", "The file format or content could not be verified. Use a valid PDF, DOCX, PNG or JPG file."],
      FILE_TOO_LARGE: ["يتجاوز الملف حد 5 ميغابايت. اختر ملفًا أصغر أو أدخل المعلومات يدويًا.", "This file exceeds 5 MB. Choose a smaller file or enter the information manually."],
      FILE_MALWARE_DETECTED: ["رفض فحص الأمان هذا الملف. لم يُقبل؛ استخدم ملفًا آمنًا أو الإدخال اليدوي.", "The security scan rejected this file. It was not accepted; use a safe file or manual entry."],
      STORAGE_QUOTA_EXCEEDED: ["مساحة التخزين المتاحة لا تكفي. يمكنك متابعة العمل بإدخال المعلومات يدويًا.", "There is not enough available storage. You can continue by entering information manually."],
      FILE_NOT_READY: ["الملف غير جاهز للتنزيل. حدّث القائمة وحاول لاحقًا.", "The file is not ready to download. Refresh the list and try later."],
      ACCESS_GRANT_INVALID: ["انتهت صلاحية التنزيل أو تغيّر الوصول. حاول التنزيل مجددًا.", "Download access expired or changed. Try downloading again."],
      PRIVATE_AI_PIPELINE_UNAVAILABLE: ["معالجة المستندات بالذكاء الاصطناعي غير متاحة حاليًا. يمكنك التحرير وإدخال معلوماتك يدويًا.", "AI document processing is currently unavailable. You can edit and enter your information manually."],
      DOCUMENT_NOT_APPROVED: ["راجع النسخة المحفوظة واعتمدها قبل التصدير.", "Review and approve the saved version before exporting."],
      EXPORT_UNAVAILABLE: ["تعذر إتمام التصدير. بقي المستند المحفوظ متاحًا؛ أعد تصدير النسخة نفسها دون خصم إضافي.", "Export could not be completed. Your saved document remains available; retry the same version without an additional charge."],
      STALE_DOCUMENT: ["تغيّر المستند. احتفظ بنصك، وحدّث المستند قبل إعادة الحفظ.", "The document changed. Keep your text and reload the document before saving again."],
      IDEMPOTENCY_CONFLICT: ["تغيّر الطلب عن المحاولة السابقة. حدّث المستند وتحقق من النسخة المحفوظة.", "This request differs from the previous attempt. Reload the document and check the saved version."],
    };
    if (error instanceof RequestFailure && [412, 428].includes(error.status)) return messages.STALE_DOCUMENT[ar ? 0 : 1];
    return messages[code]?.[ar ? 0 : 1] ?? (ar
      ? "تعذر إتمام الطلب. بقي النص الحالي كما هو. تحقق من النسخة المحفوظة ثم أعد المحاولة."
      : "The request could not be completed. Your current text is unchanged. Check the saved version and try again.");
  }

  async function mutation(path: string, body: unknown, revision?: number) {
    const encoded = JSON.stringify(body);
    const fingerprint = `${path}:${revision ?? ""}:${encoded}`;
    let key = keys.current.get(fingerprint);
    if (!key) { key = crypto.randomUUID(); keys.current.set(fingerprint, key); }
    return jsonRequest(path, { method: "POST", headers: {
      "Content-Type": "application/json", "X-CSRFToken": await getCsrf(client), "Idempotency-Key": key,
      ...(revision === undefined ? {} : { "If-Match": `"${revision}"` }),
    }, body: encoded });
  }

  async function run(action: () => Promise<void>) {
    setBusy(true); setMessage(""); setFailed(false);
    try { await action(); }
    catch (error) {
      if (error instanceof RequestFailure && error.status === 401) {
        clearPrivate(); setAccess("denied");
      } else { setFailed(true); setMessage(errorMessage(error)); }
    } finally { setBusy(false); }
  }

  useEffect(() => {
    const controller = new AbortController();
    void (async () => {
      setAccess("loading");
      try {
        const session = await client.GET("/api/v1/session", { signal: controller.signal });
        if (controller.signal.aborted) return;
        if ([401, 403].includes(session.response.status)) { clearPrivate(); setAccess("denied"); return; }
        if (!session.response.ok || !session.data) throw new RequestFailure("SESSION_UNAVAILABLE");
        const proof = validateSession(session.data);
        if (proof.roles[0] !== "STUDENT" || Date.parse(proof.expires_at) <= Date.now()) { clearPrivate(); setAccess("denied"); return; }
        const results = await Promise.all([
          jsonRequest("/documents", { signal: controller.signal }), jsonRequest("/files", { signal: controller.signal }),
          jsonRequest("/files/capabilities", { signal: controller.signal }), jsonRequest("/documents/capabilities", { signal: controller.signal }),
        ]);
        if (controller.signal.aborted) return;
        const caps = record(results[2]);
        if (typeof caps.upload_available !== "boolean" || !Number.isInteger(caps.max_file_bytes) || !Number.isInteger(caps.max_student_bytes)) throw new RequestFailure("INVALID_RESPONSE");
        setDocuments(items(results[0]).map(document)); setAssets(items(results[1]).map(asset));
        setCapabilities({ upload_available: caps.upload_available, max_file_bytes: Number(caps.max_file_bytes), max_student_bytes: Number(caps.max_student_bytes) });
        setManualAvailable(record(results[3]).manual_editing === true); setAccess("ready");
      } catch (error) {
        if (!controller.signal.aborted) {
          clearPrivate(); setCapabilities(null); setManualAvailable(false);
          setAccess(error instanceof RequestFailure && [401, 403].includes(error.status) ? "denied" : "unavailable");
        }
      }
    })();
    return () => controller.abort();
  }, [attempt]);

  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);

  function showVersion(value: Version) {
    setViewed(value); setTitle(value.title); setContent(value.content); setLanguage(value.language); setReviewed(false);
  }
  function mayDiscard() {
    return !dirty || window.confirm(ar ? "توجد تعديلات غير محفوظة. هل تريد تركها؟" : "You have unsaved changes. Discard them?");
  }
  async function loadDocument(id: string, versionId?: string) {
    const [detail, history] = await Promise.all([jsonRequest(`/documents/${id}`), jsonRequest(`/documents/${id}/versions`)]);
    const current = document(detail);
    const savedVersions = items(history).map(version);
    setSelected(current); setKind(current.kind); setVersions(savedVersions);
    showVersion(savedVersions.find(row => row.id === versionId) ?? current.current);
    setDocuments(rows => rows.some(row => row.id === id) ? rows.map(row => row.id === id ? current : row) : [current, ...rows]);
  }
  async function save(event: FormEvent) {
    event.preventDefault();
    await run(async () => {
      const path = selected ? `/documents/${selected.id}/versions` : "/documents";
      const body = { title, language, content, ...(selected ? {} : { kind }) };
      const result = await mutation(path, body, selected?.revision);
      const id = selected?.id ?? document(result).id;
      await loadDocument(id);
      setMessage(ar ? "حُفظت نسخة جديدة. راجعها قبل الاعتماد والتصدير." : "A new version was saved. Review it before approval and export.");
    });
  }
  async function download(assetId: string, filename: string) {
    const grant = record(await jsonRequest(`/files/${identifier(assetId)}/access-grants`, { method: "POST", headers: {
      "Content-Type": "application/json", "X-CSRFToken": await getCsrf(client),
    }, body: "{}" }));
    if (typeof grant.token !== "string" || !grant.token) throw new RequestFailure("INVALID_RESPONSE");
    const response = await fetch(`/api/v1/files/${assetId}/content`, { credentials: "same-origin", cache: "no-store", headers: { "X-File-Access-Grant": grant.token } });
    if (!response.ok) {
      const body: unknown = await response.json().catch(() => null);
      throw new RequestFailure(body && typeof body === "object" && "code" in body && typeof body.code === "string" ? body.code : "REQUEST_FAILED", response.status);
    }
    const blob = await response.blob();
    if (blob.size === 0) throw new RequestFailure("INVALID_RESPONSE");
    const extensions: Record<string, string> = { "application/pdf": "pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx", "image/png": "png", "image/jpeg": "jpg" };
    const extension = extensions[response.headers.get("Content-Type")?.split(";")[0] ?? ""];
    const downloadName = /\.(pdf|docx|png|jpg|jpeg)$/i.test(filename) || !extension ? filename : `${filename}.${extension}`;
    const url = URL.createObjectURL(blob);
    const anchor = window.document.createElement("a");
    anchor.href = url; anchor.download = downloadName; anchor.click();
    window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  async function exportDocument(format: "PDF" | "DOCX") {
    if (!selected || !viewed) return;
    await run(async () => {
      try {
        const result = record(await mutation(`/documents/${selected.id}/exports`, { version_id: viewed.id, format }));
        await download(identifier(result.asset_id), `${viewed.title.replace(/[^\p{L}\p{N} ._-]/gu, "").slice(0, 100) || "document"}.${format.toLowerCase()}`);
      } catch (error) {
        if (error instanceof RequestFailure && [401, 403, 404].includes(error.status)) throw error;
        throw new RequestFailure("EXPORT_UNAVAILABLE", error instanceof RequestFailure ? error.status : 0);
      }
      setMessage(ar ? "أُرسل الملف إلى التنزيل. إعادة تصدير هذه النسخة لا تخصم رصيدًا إضافيًا." : "The file was sent to download. Re-exporting this version does not charge additional Credits.");
    });
  }
  async function upload(event: FormEvent) {
    event.preventDefault();
    if (!file || !capabilities?.upload_available) return;
    await run(async () => {
      if (file.size > capabilities.max_file_bytes) throw new RequestFailure("FILE_TOO_LARGE", 413);
      if (uploadKey.current?.file !== file) uploadKey.current = { file, key: crypto.randomUUID() };
      const body = new FormData(); body.append("file", file);
      const saved = asset(await jsonRequest("/files/uploads", { method: "POST", headers: {
        "X-CSRFToken": await getCsrf(client), "Idempotency-Key": uploadKey.current.key,
      }, body }));
      if (saved.state !== "ACCEPTED") throw new RequestFailure("FILE_NOT_READY", 409);
      setAssets(rows => rows.some(row => row.id === saved.id) ? rows : [saved, ...rows]);
      setFile(null); uploadKey.current = null; if (fileInput.current) fileInput.current.value = "";
      setMessage(ar ? "قُبل الملف بعد اجتياز فحص الأمان. لا تُرسل الملفات إلى الذكاء الاصطناعي تلقائيًا." : "The file passed its security scan and was accepted. Files are not sent to AI automatically.");
    });
  }

  return <div className={styles.workspace} dir={ar ? "rtl" : "ltr"} aria-busy={access === "loading" || busy}>
    <p className="catalog-note">{ar ? "مستنداتك وملفاتك خاصة بحسابك. التحرير اليدوي وإعادة تصدير النسخة المحفوظة مجانيان." : "Your documents and files are private to your account. Manual editing and re-exporting a saved version are free."}</p>
    <p>{ar ? "استخراج السيرة الذاتية وإنشاء المستندات بالذكاء الاصطناعي غير متاحين حاليًا. يمكنك كتابة مستندك يدويًا أو " : "AI CV extraction and document generation are currently unavailable. You can write your document manually or "}<a href={`/${locale}/eligibility`}>{ar ? "إكمال بياناتك يدويًا" : "complete your profile manually"}</a>.</p>
    {access === "loading" && <p role="status">{ar ? "جارٍ التحقق وتحميل مستنداتك…" : "Verifying access and loading your documents…"}</p>}
    {access === "denied" && <p role="alert">{ar ? "يلزم حساب طالب بالغ ومؤكد البريد لعرض مستنداتك الخاصة. " : "A verified adult student account is required to access your private documents. "}<a href={`/${locale}/account`}>{ar ? "تسجيل الدخول وإدارة الحساب" : "Sign in or manage your account"}</a></p>}
    {access === "unavailable" && <p role="alert">{ar ? "تعذر تحميل مكتبتك. لا يعني ذلك حذف الملفات أو فقدان مستنداتك." : "Your library could not be loaded. This does not mean your files or documents were deleted."}</p>}
    <button type="button" disabled={busy || access === "loading"} onClick={() => { if (mayDiscard()) { clearPrivate(); setAttempt(value => value + 1); } }}>{ar ? "تحديث المكتبة" : "Refresh library"}</button>
    <p className={styles.status} role={failed ? "alert" : "status"} aria-live="polite">{busy ? (ar ? "جارٍ تنفيذ طلبك…" : "Processing your request…") : message}</p>
    {access === "ready" && <>
      <section aria-labelledby="document-library-title">
        <h2 id="document-library-title">{ar ? "المستندات المحفوظة" : "Saved documents"}</h2>
        {documents.length === 0 ? <p>{ar ? "لا توجد مستندات محفوظة. ابدأ مستندًا يدويًا أدناه." : "No documents are saved. Start a manual document below."}</p> : <ul className={styles.library}>{documents.map(row => <li key={row.id}>
          <button type="button" disabled={busy} aria-pressed={selected?.id === row.id} onClick={() => { if (mayDiscard()) void run(() => loadDocument(row.id)); }}><bdi>{row.current.title}</bdi></button>
          <p>{kindLabels[row.kind]} · {ar ? "نسخة" : "Version"} {count(row.current.number)} · {row.current.approved ? (ar ? "معتمدة" : "Approved") : (ar ? "تحتاج مراجعتك" : "Needs your review")}</p>
        </li>)}</ul>}
        <button type="button" disabled={busy || !manualAvailable} onClick={() => {
          if (!mayDiscard()) return;
          setSelected(null); setVersions([]); setViewed(null); setTitle(""); setContent(""); setLanguage(locale); setKind("CV"); setReviewed(false); setMessage("");
        }}>{ar ? "مستند يدوي جديد" : "New manual document"}</button>
      </section>

      <section aria-labelledby="document-editor-title">
        <h2 id="document-editor-title">{selected ? (ar ? "تحرير نسخة جديدة" : "Edit a new version") : (ar ? "اكتب مستندك" : "Write your document")}</h2>
        <p>{ar ? "اكتب حقائقك المؤكدة فقط. تحفظ التعديلات نسخة جديدة؛ لا تستبدل النسخ السابقة أو المستندات المرفقة بطلبات مقدّمة." : "Use only your confirmed facts. Saving edits creates a new version and preserves earlier versions and submitted attachments."}</p>
        {!manualAvailable && <p className="catalog-warning">{ar ? "التحرير غير متاح حاليًا. احتفظ بنصك وأعد المحاولة لاحقًا." : "Editing is currently unavailable. Keep your text and try later."}</p>}
        {selected && <>
          <h3>{ar ? "النسخ المحفوظة" : "Saved versions"}</h3>
          <nav className={styles.versions} aria-label={ar ? "اختيار نسخة المستند" : "Choose a document version"}>{versions.map(row => <button key={row.id} type="button" disabled={busy} aria-pressed={viewed?.id === row.id} onClick={() => { if (mayDiscard()) showVersion(row); }}>{ar ? "نسخة" : "Version"} {count(row.number)}{row.id === selected.current.id ? (ar ? " · الحالية" : " · current") : ""}</button>)}</nav>
          {viewed && viewed.id !== selected.current.id && <>
            <details><summary>{ar ? "مقارنة النسخة المختارة بالحالية" : "Compare selected and current versions"}</summary><div className={styles.compare}><div><h4>{ar ? "النسخة المختارة" : "Selected version"}</h4><pre dir={viewed.language === "ar" ? "rtl" : "ltr"} lang={viewed.language}>{viewed.content}</pre></div><div><h4>{ar ? "النسخة الحالية" : "Current version"}</h4><pre dir={selected.current.language === "ar" ? "rtl" : "ltr"} lang={selected.current.language}>{selected.current.content}</pre></div></div></details>
            <button type="button" disabled={busy || dirty || !manualAvailable} onClick={() => void run(async () => { await mutation(`/documents/${selected.id}/restore`, { version_id: viewed.id }, selected.revision); await loadDocument(selected.id); setMessage(ar ? "استعيدت النسخة كنسخة جديدة، مع حفظ السجل السابق." : "Restored as a new version, preserving the previous history."); })}>{ar ? "استعادة هذه النسخة كنسخة جديدة" : "Restore this as a new version"}</button>
          </>}
        </>}
        <form onSubmit={save}>
          <fieldset disabled={busy || !manualAvailable}>
            <div className="catalog-fields">
              <label>{ar ? "نوع المستند" : "Document type"}<select value={kind} disabled={Boolean(selected)} onChange={event => setKind(event.target.value as Kind)}>{kinds.map(value => <option key={value} value={value}>{kindLabels[value]}</option>)}</select></label>
              <label>{ar ? "لغة المستند" : "Document language"}<select value={language} onChange={event => { setLanguage(event.target.value as Language); setReviewed(false); }}><option value="ar">العربية</option><option value="en">English</option></select></label>
            </div>
            <label>{ar ? "عنوان المستند" : "Document title"}<input value={title} dir="auto" onChange={event => { setTitle(event.target.value); setReviewed(false); }} required maxLength={200} /></label>
            <label>{ar ? "نص المستند" : "Document text"}<textarea value={content} dir={language === "ar" ? "rtl" : "ltr"} lang={language} onChange={event => { setContent(event.target.value); setReviewed(false); }} required maxLength={40000} /></label>
            <p>{count(content.length)} / {count(40000)} · {dirty ? (ar ? "تعديلات غير محفوظة" : "Unsaved changes") : (ar ? "لا تعديلات غير محفوظة" : "No unsaved changes")}</p>
            <button type="submit" disabled={!dirty || !title.trim() || !content.trim()}>{ar ? "حفظ نسخة جديدة" : "Save a new version"}</button>
          </fieldset>
        </form>
        <h3>{ar ? "معاينة النص" : "Text preview"}</h3>
        <div className={styles.preview} dir={language === "ar" ? "rtl" : "ltr"} lang={language}><h4><bdi>{title || (ar ? "دون عنوان" : "Untitled")}</bdi></h4><pre>{content || (ar ? "اكتب نصًا لعرض المعاينة." : "Enter text to preview it.")}</pre></div>
        {selected && viewed && <>
          <p>{viewed.approved ? (ar ? "النسخة المحفوظة معتمدة. أي تعديل يحتاج حفظًا واعتمادًا جديدين." : "The saved version is approved. Any edits require saving and approving a new version.") : (ar ? "راجع حقائق النسخة المحفوظة ولغتها قبل اعتمادها." : "Review the saved version’s facts and language before approving it.")}</p>
          <label className="confirm"><input type="checkbox" checked={reviewed} disabled={busy || dirty || viewed.approved} onChange={event => setReviewed(event.target.checked)} />{ar ? "راجعت النسخة المحفوظة وأؤكد صحة معلوماتها" : "I reviewed the saved version and confirm its information"}</label>
          <div className="catalog-actions">
            <button type="button" disabled={busy || dirty || !reviewed || viewed.approved} onClick={() => void run(async () => { await mutation(`/documents/${selected.id}/approvals`, { version_id: viewed.id, content_hash: viewed.content_hash, confirm: true }); await loadDocument(selected.id, viewed.id); setMessage(ar ? "تم اعتماد النسخة المحفوظة." : "The saved version was approved."); })}>{ar ? "اعتماد النسخة" : "Approve version"}</button>
            <button type="button" disabled={busy || dirty || !viewed.approved} onClick={() => void exportDocument("PDF")}>{ar ? "تصدير PDF" : "Export PDF"}</button>
            <button type="button" disabled={busy || dirty || !viewed.approved} onClick={() => void exportDocument("DOCX")}>{ar ? "تصدير DOCX" : "Export DOCX"}</button>
          </div>
          <p>{ar ? "إذا فشل التصدير، يبقى المستند المحفوظ متاحًا. يمكنك إعادة تصدير النسخة نفسها دون خصم إضافي." : "If export fails, the saved document remains available. You can re-export the same version without an additional charge."}</p>
        </>}
      </section>

      <section aria-labelledby="document-upload-title">
        <h2 id="document-upload-title">{ar ? "رفع ملف خاص" : "Upload a private file"}</h2>
        <p>{ar ? "الصيغ: PDF وDOCX وPNG وJPG. الحد 5 ميغابايت للملف و10 ميغابايت لحسابك. لا يُقبل أي ملف قبل نجاح فحصه." : "Formats: PDF, DOCX, PNG and JPG. Limit: 5 MB per file and 10 MB for your account. Files are accepted only after a successful security scan."}</p>
        {!capabilities?.upload_available && <p className="catalog-warning">{ar ? "رفع الملفات غير متاح حاليًا. يمكنك متابعة كتابة مستندك أو إدخال بياناتك يدويًا." : "File upload is currently unavailable. You can continue writing your document or enter your information manually."}</p>}
        <form onSubmit={upload}><label>{ar ? "اختر ملفًا" : "Choose a file"}<input ref={fileInput} type="file" accept=".pdf,.docx,.png,.jpg,.jpeg" disabled={busy || !capabilities?.upload_available} onChange={event => setFile(event.target.files?.[0] ?? null)} /></label><button type="submit" disabled={busy || !file || !capabilities?.upload_available}>{ar ? "رفع وفحص الملف" : "Upload and scan file"}</button></form>
        <h3>{ar ? "ملفاتك الخاصة" : "Your private files"}</h3>
        {assets.length === 0 ? <p>{ar ? "لا توجد ملفات في مكتبتك الحالية." : "There are no files in your current library."}</p> : <ul className={styles.library}>{assets.map((row, index) => <li key={row.id}>
          <p>{ar ? "ملف" : "File"} {count(index + 1)} · {count(row.declared_size)} {ar ? "بايت" : "bytes"} · {row.state === "ACCEPTED" ? (ar ? "مقبول" : "Accepted") : (ar ? "غير متاح للتنزيل" : "Unavailable for download")}</p>
          <button type="button" disabled={busy || row.state !== "ACCEPTED"} onClick={() => void run(async () => { await download(row.id, `private-file-${index + 1}`); setMessage(ar ? "أُرسل الملف إلى التنزيل." : "The file was sent to download."); })}>{ar ? "تنزيل الملف" : "Download file"}</button>
        </li>)}</ul>}
      </section>
    </>}
  </div>;
}
