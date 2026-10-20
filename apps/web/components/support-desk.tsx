"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { createHealthClient, getCsrf, validateSession } from "@minhaai/contracts";
import styles from "./support-desk.module.css";

type Language = "ar" | "en";
type TicketState = "NEW" | "AI_HANDLING" | "AWAITING_ADMIN" | "AWAITING_STUDENT" | "RESOLVED" | "CLOSED";
type Priority = "CRITICAL" | "HIGH" | "NORMAL" | "LOW";
type Sla = {
  cycle_no: number; human_requested_at: string | null; computed_due_at: string | null;
  calendar_policy_id: string | null; target_business_minutes: number | null;
  first_human_response_at: string | null; elapsed_business_minutes: number | null;
  warning: boolean; breached: boolean; met: boolean;
};
type Ticket = {
  id: string; state: TicketState; category: string; subject: string; priority: Priority;
  head_sequence: number; row_version: number; created_at: string; updated_at: string;
  assigned: boolean; suggested_category: string; suggested_priority: string;
  triage_confidence: number | null; triage_reason: string;
  resolved_at: string | null; closed_at: string | null; reopen_until: string | null;
  rating_window_until: string | null; rating: number | null; rating_available: boolean; rating_editable: boolean;
  sla: Sla;
};
type Notice = { sequence: number; author_kind: "STUDENT" | "ADMIN" | "AI"; body: string; substantive: boolean; created_at: string };
type Attachment = { id: string; asset_id: string; state: "SHARED" | "REVOKED"; version: number; created_at: string };
type OwnedFile = { id: string; state: string; declared_size: number; created_at: string };
type AiOutcome = { available: boolean; reason: string; category: string; priority: string; confidence: number | null };

const client = createHealthClient();
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const STATES: TicketState[] = ["NEW", "AI_HANDLING", "AWAITING_ADMIN", "AWAITING_STUDENT", "RESOLVED", "CLOSED"];
const PRIORITIES: Priority[] = ["CRITICAL", "HIGH", "NORMAL", "LOW"];

class RequestFailure extends Error {
  constructor(public code: string, public status = 0) { super(code); }
}
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new RequestFailure("INVALID_RESPONSE");
  return value as Record<string, unknown>;
}
function text(value: unknown, maximum = 12000): string {
  if (typeof value !== "string" || value.length > maximum) throw new RequestFailure("INVALID_RESPONSE");
  return value;
}
function id(value: unknown): string {
  const result = text(value, 64);
  if (!uuid.test(result)) throw new RequestFailure("INVALID_RESPONSE");
  return result;
}
function integer(value: unknown, minimum = 0): number {
  if (!Number.isSafeInteger(value) || Number(value) < minimum) throw new RequestFailure("INVALID_RESPONSE");
  return Number(value);
}
function flag(value: unknown): boolean {
  if (typeof value !== "boolean") throw new RequestFailure("INVALID_RESPONSE");
  return value;
}
function instant(value: unknown): string {
  const result = text(value, 64);
  if (!/(?:[zZ]|[+-]\d{2}:\d{2})$/.test(result) || !Number.isFinite(Date.parse(result))) throw new RequestFailure("INVALID_RESPONSE");
  return result;
}
function optionalInstant(value: unknown): string | null {
  return value === null ? null : instant(value);
}
function optionalInteger(value: unknown): number | null {
  return value === null ? null : integer(value);
}
function sla(value: unknown): Sla {
  const row = record(value);
  return {
    cycle_no: integer(row.cycle_no), human_requested_at: optionalInstant(row.human_requested_at),
    computed_due_at: optionalInstant(row.computed_due_at),
    calendar_policy_id: row.calendar_policy_id === null ? null : id(row.calendar_policy_id),
    target_business_minutes: optionalInteger(row.target_business_minutes),
    first_human_response_at: optionalInstant(row.first_human_response_at),
    elapsed_business_minutes: optionalInteger(row.elapsed_business_minutes),
    warning: flag(row.warning), breached: flag(row.breached), met: flag(row.met),
  };
}
function ticket(value: unknown): Ticket {
  const row = record(value);
  const state = text(row.state, 32) as TicketState;
  const priority = text(row.priority, 16) as Priority;
  if (!STATES.includes(state) || !PRIORITIES.includes(priority)) throw new RequestFailure("INVALID_RESPONSE");
  return {
    id: id(row.id), state, category: text(row.category, 128), subject: text(row.subject, 256), priority,
    head_sequence: integer(row.head_sequence), row_version: integer(row.row_version, 1),
    created_at: instant(row.created_at), updated_at: instant(row.updated_at), assigned: flag(row.assigned),
    suggested_category: text(row.suggested_category, 128), suggested_priority: text(row.suggested_priority, 16),
    triage_confidence: optionalInteger(row.triage_confidence), triage_reason: text(row.triage_reason, 512),
    resolved_at: optionalInstant(row.resolved_at), closed_at: optionalInstant(row.closed_at),
    reopen_until: optionalInstant(row.reopen_until), rating_window_until: optionalInstant(row.rating_window_until),
    rating: optionalInteger(row.rating), rating_available: flag(row.rating_available),
    rating_editable: flag(row.rating_editable), sla: sla(row.sla),
  };
}
function notice(value: unknown): Notice {
  const row = record(value);
  const kind = text(row.author_kind, 16);
  if (!["STUDENT", "ADMIN", "AI"].includes(kind)) throw new RequestFailure("INVALID_RESPONSE");
  return {
    sequence: integer(row.sequence, 1), author_kind: kind as Notice["author_kind"], body: text(row.body),
    substantive: flag(row.substantive), created_at: instant(row.created_at),
  };
}
function attachment(value: unknown): Attachment {
  const row = record(value);
  const state = text(row.state, 16);
  if (state !== "SHARED" && state !== "REVOKED") throw new RequestFailure("INVALID_RESPONSE");
  return { id: id(row.id), asset_id: id(row.asset_id), state, version: integer(row.version, 1), created_at: instant(row.created_at) };
}
function ownedFile(value: unknown): OwnedFile {
  const row = record(value);
  return { id: id(row.id), state: text(row.state, 16), declared_size: integer(row.declared_size, 0), created_at: instant(row.created_at) };
}
function aiOutcome(value: unknown): AiOutcome {
  const row = record(value);
  return {
    available: flag(row.available), reason: text(row.reason, 512), category: text(row.category, 128),
    priority: text(row.priority, 16), confidence: optionalInteger(row.confidence),
  };
}
async function request(path: string, init: RequestInit = {}): Promise<unknown> {
  const response = await fetch(`/api/v1${path}`, { ...init, credentials: "same-origin", cache: "no-store" });
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const code = body && typeof body === "object" && "code" in body && typeof body.code === "string" ? body.code : "REQUEST_FAILED";
    throw new RequestFailure(code, response.status);
  }
  return body;
}

export function SupportDesk({ locale }: { locale: Language }) {
  const ar = locale === "ar";
  const [access, setAccess] = useState<"loading" | "ready" | "denied" | "unavailable">("loading");
  const [rows, setRows] = useState<Ticket[]>([]);
  const [selected, setSelected] = useState<Ticket | null>(null);
  const [thread, setThread] = useState<Notice[]>([]);
  const [shares, setShares] = useState<Attachment[]>([]);
  const [files, setFiles] = useState<OwnedFile[]>([]);
  const [chosenFile, setChosenFile] = useState("");
  const [confirmShare, setConfirmShare] = useState(false);
  const [draft, setDraft] = useState({ category: "", subject: "", message: "", request_human: false });
  const [reply, setReply] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [failed, setFailed] = useState(false);
  const [stale, setStale] = useState(false);
  const [reference, setReference] = useState<string>("");
  const keys = useRef(new Map<string, string>());
  const date = (value: string) => new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
  const labels: Record<TicketState, string> = ar
    ? { NEW: "جديد", AI_HANDLING: "مع المساعد الذكي", AWAITING_ADMIN: "بانتظار الدعم البشري", AWAITING_STUDENT: "بانتظار ردك", RESOLVED: "مُحل", CLOSED: "مغلق" }
    : { NEW: "New", AI_HANDLING: "AI handling", AWAITING_ADMIN: "Awaiting a human agent", AWAITING_STUDENT: "Awaiting your reply", RESOLVED: "Resolved", CLOSED: "Closed" };
  const priorityLabels: Record<Priority, string> = ar
    ? { CRITICAL: "حرجة", HIGH: "عالية", NORMAL: "عادية", LOW: "منخفضة" }
    : { CRITICAL: "Critical", HIGH: "High", NORMAL: "Normal", LOW: "Low" };

  function clearPrivate() { setRows([]); setSelected(null); setThread([]); setShares([]); keys.current.clear(); }
  function report(error: unknown) {
    if (error instanceof RequestFailure && [401, 403].includes(error.status)) { clearPrivate(); setAccess("denied"); return; }
    setFailed(true);
    if (error instanceof RequestFailure && [409, 412, 428].includes(error.status)) {
      setStale(true);
      setMessage(ar ? "تغيّرت التذكرة. حدّث البيانات قبل المتابعة." : "The ticket changed. Refresh it before continuing.");
    } else {
      setMessage(ar ? "تعذر إتمام الطلب. لم نفترض نجاحه؛ أعد المحاولة." : "The request could not be completed. Success was not assumed; retry.");
    }
  }
  async function mutate(path: string, method: string, body: unknown, revision?: number | string) {
    const encoded = JSON.stringify(body);
    const fingerprint = `${path}:${revision ?? ""}:${encoded}`;
    let key = keys.current.get(fingerprint);
    if (!key) { key = crypto.randomUUID(); keys.current.set(fingerprint, key); }
    const result = await request(path, {
      method,
      headers: {
        "Content-Type": "application/json", "X-CSRFToken": await getCsrf(client), "Idempotency-Key": key,
        ...(revision === undefined ? {} : { "If-Match": `"${revision}"` }),
      },
      body: encoded,
    });
    keys.current.delete(fingerprint);
    return result;
  }
  async function loadTicket(ticketId: string) {
    const [detail, messages, attachments, owned] = await Promise.all([
      request(`/tickets/${ticketId}`),
      request(`/tickets/${ticketId}/messages`),
      request(`/tickets/${ticketId}/attachments`),
      request("/files"),
    ]);
    const current = ticket(detail);
    const threadRows = record(messages);
    if (!Array.isArray(threadRows.items)) throw new RequestFailure("INVALID_RESPONSE");
    const shareRows = record(attachments);
    if (!Array.isArray(shareRows.items)) throw new RequestFailure("INVALID_RESPONSE");
    const fileRows = record(owned);
    if (!Array.isArray(fileRows.items)) throw new RequestFailure("INVALID_RESPONSE");
    setSelected(current);
    setThread(threadRows.items.map(notice));
    setShares(shareRows.items.map(attachment));
    setFiles(fileRows.items.map(ownedFile).filter(item => item.state === "ACCEPTED"));
    setReference(new Date().toISOString());
    return current;
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
        const listed = await request("/tickets?page=1&page_size=20", { signal: controller.signal });
        const page = record(listed);
        if (!Array.isArray(page.items)) throw new RequestFailure("INVALID_RESPONSE");
        setRows(page.items.map(ticket));
        setStale(false);
        setAccess("ready");
      } catch (error) {
        if (!controller.signal.aborted) {
          clearPrivate();
          setAccess(error instanceof RequestFailure && [401, 403].includes(error.status) ? "denied" : "unavailable");
        }
      }
    })();
    return () => controller.abort();
  }, []);

  async function open(ticketId: string) {
    setBusy(true); setMessage(""); setFailed(false);
    try {
      await loadTicket(ticketId);
      setStale(false);
    } catch (error) { report(error); } finally { setBusy(false); }
  }
  async function create(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setMessage(""); setFailed(false);
    try {
      const created = ticket(await mutate("/tickets", "POST", draft));
      setRows(current => [created, ...current]);
      setDraft({ category: "", subject: "", message: "", request_human: false });
      await loadTicket(created.id);
      setMessage(ar ? "تم فتح التذكرة." : "The ticket was opened.");
    } catch (error) { report(error); } finally { setBusy(false); }
  }
  async function sendReply(event: FormEvent) {
    event.preventDefault();
    if (!selected || !reply.trim()) return;
    setBusy(true); setMessage(""); setFailed(false);
    try {
      const updated = ticket(await mutate(`/tickets/${selected.id}/messages`, "POST", { body: reply, request_human: false }));
      setReply("");
      setSelected(updated);
      await loadTicket(updated.id);
      setMessage(ar ? "أُرسلت الرسالة." : "The message was sent.");
    } catch (error) { report(error); } finally { setBusy(false); }
  }
  async function askAi() {
    if (!selected) return;
    setBusy(true); setMessage(""); setFailed(false);
    try {
      const result = record(await mutate(`/tickets/${selected.id}/ai-replies`, "POST", {}));
      const outcome = aiOutcome(result.ai);
      setSelected(ticket(result.ticket));
      await loadTicket(selected.id);
      setMessage(outcome.available
        ? (ar ? "رد المساعد الذكي. يمكنك طلب تدخل بشري في أي وقت." : "The AI assistant replied. You can ask for a human at any time.")
        : (ar ? "لم يتوفر رد ذكي؛ أُحيل طلبك إلى الدعم البشري." : "No AI answer was available; your request went to a human agent."));
    } catch (error) { report(error); } finally { setBusy(false); }
  }
  async function requestHuman() {
    if (!selected) return;
    setBusy(true); setMessage(""); setFailed(false);
    try {
      const updated = ticket(await mutate(`/tickets/${selected.id}/transitions`, "POST", { to_state: "AWAITING_ADMIN", reason_code: "STUDENT_REQUESTED_HUMAN" }, selected.row_version));
      setSelected(updated);
      await loadTicket(updated.id);
      setStale(false);
      setMessage(ar ? "طلبك ان转到 الدعم البشري." : "Your request went to a human agent.");
    } catch (error) { report(error); } finally { setBusy(false); }
  }
  async function confirmResolution() {
    if (!selected) return;
    setBusy(true); setMessage(""); setFailed(false);
    try {
      const updated = ticket(await mutate(`/tickets/${selected.id}/transitions`, "POST", { to_state: "RESOLVED", reason_code: "STUDENT_CONFIRMED" }, selected.row_version));
      setSelected(updated);
      await loadTicket(updated.id);
      setStale(false);
      setMessage(ar ? "تم تأكيد الحل وإغلاق التذكرة." : "The resolution was confirmed and the ticket closed.");
    } catch (error) { report(error); } finally { setBusy(false); }
  }
  async function reopen() {
    if (!selected) return;
    setBusy(true); setMessage(""); setFailed(false);
    try {
      const updated = ticket(await mutate(`/tickets/${selected.id}/transitions`, "POST", { to_state: "AWAITING_ADMIN", reason_code: "STUDENT_REOPENED" }, selected.row_version));
      setSelected(updated);
      await loadTicket(updated.id);
      setStale(false);
      setMessage(ar ? "أُعيد فتح التذكرة." : "The ticket was reopened.");
    } catch (error) { report(error); } finally { setBusy(false); }
  }
  async function rate(value: number) {
    if (!selected) return;
    setBusy(true); setMessage(""); setFailed(false);
    try {
      await mutate(`/tickets/${selected.id}/rating`, "PUT", { rating: value }, selected.row_version);
      await loadTicket(selected.id);
      setStale(false);
      setMessage(ar ? "شكرًا على تقييمك." : "Thank you for the rating.");
    } catch (error) { report(error); } finally { setBusy(false); }
  }

  async function attachFile() {
    if (!selected || !chosenFile || !confirmShare) return;
    setBusy(true); setMessage(""); setFailed(false);
    try {
      await mutate(`/tickets/${selected.id}/attachments`, "POST", { asset_id: chosenFile });
      setChosenFile(""); setConfirmShare(false);
      await loadTicket(selected.id);
      setMessage(ar ? "تمت مشاركة الملف مع الدعم." : "The file was shared with support.");
    } catch (error) { report(error); } finally { setBusy(false); }
  }

  async function revokeShare(item: Attachment) {
    if (!selected) return;
    setBusy(true); setMessage(""); setFailed(false);
    try {
      await mutate(`/tickets/${selected.id}/attachments/${item.id}`, "DELETE", undefined, `share-${item.id}-${item.version}`);
      await loadTicket(selected.id);
      setMessage(ar ? "أُلغي مشاركة الملف." : "The file share was revoked.");
    } catch (error) { report(error); } finally { setBusy(false); }
  }

  if (access === "loading") return <p className="status">{ar ? "جارٍ التحميل…" : "Loading…"}</p>;
  if (access === "denied") return <p className="status">{ar ? "يلزم حساب طالب بالغ مُفعّل لعرض الدعم." : "An activated adult student account is required to use support."}</p>;
  if (access === "unavailable") return <p className="status">{ar ? "خدمة الدعم غير متاحة الآن. حاول لاحقًا." : "The support service is unavailable right now. Try again later."}</p>;

  const openTickets = rows.filter(row => !["RESOLVED", "CLOSED"].includes(row.state));
  const closedTickets = rows.filter(row => ["RESOLVED", "CLOSED"].includes(row.state));
  const slaExpectation = selected?.sla;
  const canReopen = Boolean(selected && selected.reopen_until && reference && Date.parse(selected.reopen_until) > Date.parse(reference));
  const canRate = Boolean(selected && selected.rating_available);
  const attachable = files.filter(file => !shares.some(share => share.asset_id === file.id && share.state === "SHARED"));

  return <div className={styles.desk}>
    <section>
      <h2>{ar ? "فتح تذكرة دعم" : "Open a support ticket"}</h2>
      <form onSubmit={create}>
        <label>
          {ar ? "الفئة" : "Category"}
          <input type="text" required maxLength={128} value={draft.category}
            onChange={event => setDraft({ ...draft, category: event.target.value })} />
        </label>
        <label>
          {ar ? "الموضوع" : "Subject"}
          <input type="text" required maxLength={256} value={draft.subject}
            onChange={event => setDraft({ ...draft, subject: event.target.value })} />
        </label>
        <label>
          {ar ? "التفاصيل" : "Details"}
          <textarea required maxLength={12000} value={draft.message}
            onChange={event => setDraft({ ...draft, message: event.target.value })} />
        </label>
        <div className="confirm">
          <input id="request-human" type="checkbox" checked={draft.request_human}
            onChange={event => setDraft({ ...draft, request_human: event.target.checked })} />
          <label htmlFor="request-human">{ar ? "أريد ردًا من دعم بشري" : "I want a reply from a human agent"}</label>
        </div>
        <button type="submit" disabled={busy}>{ar ? "فتح التذكرة" : "Open the ticket"}</button>
      </form>
    </section>

    <section>
      <h2>{ar ? "تذاكري" : "My tickets"}</h2>
      {rows.length === 0 ? <p>{ar ? "لا توجد تذاكر بعد." : "No tickets yet."}</p> : <>
        <h3>{ar ? "مفتوحة" : "Open"}</h3>
        <ul className="ticket-list">
          {openTickets.map(row => <li key={row.id}>
            <button type="button" className="secondary" onClick={() => open(row.id)} disabled={busy}>
              {row.subject}
            </button>
            <span className="badge">{labels[row.state]}</span>
            <span className="badge">{priorityLabels[row.priority]}</span>
          </li>)}
        </ul>
        <h3>{ar ? "مغلقة" : "Closed"}</h3>
        <ul className="ticket-list">
          {closedTickets.map(row => <li key={row.id}>
            <button type="button" className="secondary" onClick={() => open(row.id)} disabled={busy}>
              {row.subject}
            </button>
            <span className="badge">{labels[row.state]}</span>
          </li>)}
        </ul>
      </>}
    </section>

    {selected && <section aria-live="polite">
      <h2>{selected.subject}</h2>
      <dl>
        <dt>{ar ? "الحالة" : "State"}</dt><dd>{labels[selected.state]}</dd>
        <dt>{ar ? "الأولوية" : "Priority"}</dt><dd>{priorityLabels[selected.priority]}</dd>
        <dt>{ar ? "الفئة" : "Category"}</dt><dd>{selected.category}</dd>
        {selected.suggested_category && <>
          <dt>{ar ? "اقتراح المساعد الذكي" : "AI suggestion"}</dt>
          <dd>{selected.suggested_category}{selected.suggested_priority ? ` · ${priorityLabels[selected.suggested_priority as Priority] ?? selected.suggested_priority}` : ""}</dd>
        </>}
        <dt>{ar ? "أول رد بشري متوقع" : "Expected first human response"}</dt>
        <dd>{slaExpectation?.computed_due_at ? date(slaExpectation.computed_due_at) : (ar ? "لم يبدأ القياس بعد" : "Not measured yet")}</dd>
        {slaExpectation?.first_human_response_at && <>
          <dt>{ar ? "أول رد بشري" : "First human response"}</dt>
          <dd>{date(slaExpectation.first_human_response_at)}</dd>
        </>}
        <dt>{ar ? "المرفقات المشاركة" : "Shared attachments"}</dt>
        <dd>{shares.length === 0
          ? (ar ? "لم تشارك أي ملف." : "You have not shared any file.")
          : shares.map(item => <span key={item.id} className="badge">
            {item.state === "SHARED" ? (ar ? "مشارك" : "shared") : (ar ? "ملغى" : "revoked")}
            {item.state === "SHARED" && <>{" "}
              <button type="button" className="secondary" onClick={() => revokeShare(item)} disabled={busy}>
                {ar ? "إلغاء المشاركة" : "Revoke"}
              </button>
            </>}
          </span>)}</dd>
      </dl>

      <ol className="thread">
        {thread.map(item => <li key={item.sequence} data-author={item.author_kind}>
          <bdi>{item.author_kind === "AI" ? (ar ? "المساعد الذكي" : "AI assistant") : item.author_kind === "ADMIN" ? (ar ? "دعم بشري" : "Human agent") : (ar ? "أنت" : "You")}</bdi>
          <p>{item.body}</p>
          <small>{date(item.created_at)}</small>
        </li>)}
      </ol>

      <form onSubmit={sendReply}>
        <label>
          {ar ? "رد جديد" : "Add a reply"}
          <textarea required maxLength={12000} value={reply} onChange={event => setReply(event.target.value)} />
        </label>
        <button type="submit" disabled={busy}>{ar ? "إرسال" : "Send"}</button>
      </form>

      <div className="actions">
        <button type="button" className="secondary" onClick={askAi} disabled={busy}>
          {ar ? "اسأل المساعد الذكي" : "Ask the AI assistant"}
        </button>
        <button type="button" className="secondary" onClick={requestHuman} disabled={busy}>
          {ar ? "اطلب دعمًا بشريًا" : "Ask for a human agent"}
        </button>
        {!["RESOLVED", "CLOSED"].includes(selected.state) && <>
          <button type="button" className="secondary" onClick={confirmResolution} disabled={busy}>
            {ar ? "أكّد أن المشكلة حُلّت" : "Confirm the issue is resolved"}
          </button>
        </>}
        {["RESOLVED", "CLOSED"].includes(selected.state) && canReopen && <>
          <button type="button" className="secondary" onClick={reopen} disabled={busy}>
            {ar ? "أعد فتح التذكرة" : "Reopen the ticket"}
          </button>
        </>}
      </div>

      <div className="actions">
        <label className="attach">
          {ar ? "مشاركة ملف من مكتبتي" : "Share a file from my library"}
          <select value={chosenFile} onChange={event => setChosenFile(event.target.value)}>
            <option value="">{ar ? "اختر ملفًا" : "Choose a file"}</option>
            {attachable.map(file => <option key={file.id} value={file.id}>
              {ar ? "ملف" : "File"} · {file.id.slice(0, 8)} · {file.declared_size} B
            </option>)}
          </select>
        </label>
        <div className="confirm">
          <input id="confirm-share" type="checkbox" checked={confirmShare}
            onChange={event => setConfirmShare(event.target.checked)} />
          <label htmlFor="confirm-share">{ar ? "أؤكد مشاركة هذا الملف مع الدعم" : "I confirm sharing this file with support"}</label>
        </div>
        <button type="button" className="secondary" onClick={attachFile} disabled={busy || !chosenFile || !confirmShare}>
          {ar ? "شارك الملف" : "Share the file"}
        </button>
      </div>

      {canRate && <div className="actions">
        <span>{ar ? "قيّم جودة الدعم:" : "Rate the support quality:"}</span>
        {[1, 2, 3, 4, 5].map(value => <button key={value} type="button" className="secondary" onClick={() => rate(value)} disabled={busy}>
          {value}
        </button>)}
      </div>}

      <p className="status" role="status">{failed ? message : message}</p>
      {stale && <p className="status">{ar ? "حدّث التذكرة قبل المتابعة." : "Refresh the ticket before continuing."}</p>}
    </section>}
  </div>;
}
