"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { createHealthClient, getCsrf, validateSession } from "@minhaai/contracts";
import styles from "./notification-inbox.module.css";

type Language = "ar" | "en";
type Preferences = { revision: number; timezone: string; deadline_enabled: boolean; source_enabled: boolean; document_enabled: boolean };
type Notice = {
  id: string; category: "DEADLINE" | "SOURCE_CHANGE" | "DOCUMENT_MISSING";
  event_id: string; event_version: number; offset_minutes: number | null; created_at: string; read_at: string | null;
  target: { kind: "APPLICATION" | "SCHOLARSHIP"; id: string; available: boolean };
  deadline: { closes_at: string; source_timezone: string; display_at: string; display_timezone: string; current: boolean } | null;
};
type Inbox = { items: Notice[]; total: number; unread_count: number; page: number; page_size: number };
const client = createHealthClient();
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
class RequestFailure extends Error { constructor(public code: string, public status = 0) { super(code); } }
function record(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new RequestFailure("INVALID_RESPONSE");
  return value as Record<string, unknown>;
}
function string(value: unknown): string { if (typeof value !== "string") throw new RequestFailure("INVALID_RESPONSE"); return value; }
function id(value: unknown): string { const result = string(value); if (!uuid.test(result)) throw new RequestFailure("INVALID_RESPONSE"); return result; }
function integer(value: unknown, minimum = 0): number { if (!Number.isSafeInteger(value) || Number(value) < minimum) throw new RequestFailure("INVALID_RESPONSE"); return Number(value); }
function flag(value: unknown): boolean { if (typeof value !== "boolean") throw new RequestFailure("INVALID_RESPONSE"); return value; }
function instant(value: unknown): string { const result = string(value); if (!/(?:[zZ]|[+-]\d{2}:\d{2})$/.test(result) || !Number.isFinite(Date.parse(result))) throw new RequestFailure("INVALID_RESPONSE"); return result; }
function zone(value: unknown): string { const result = string(value); try { new Intl.DateTimeFormat("en", { timeZone: result }).format(); } catch { throw new RequestFailure("INVALID_TIMEZONE"); } return result; }
function preferences(value: unknown): Preferences {
  const row = record(value);
  return { revision: integer(row.revision), timezone: zone(row.timezone), deadline_enabled: flag(row.deadline_enabled), source_enabled: flag(row.source_enabled), document_enabled: flag(row.document_enabled) };
}
function notice(value: unknown): Notice {
  const row = record(value), target = record(row.target);
  if (!["DEADLINE", "SOURCE_CHANGE", "DOCUMENT_MISSING"].includes(string(row.category)) || !["APPLICATION", "SCHOLARSHIP"].includes(string(target.kind))) throw new RequestFailure("INVALID_RESPONSE");
  const deadline = row.deadline === null ? null : record(row.deadline);
  return {
    id: id(row.id), category: row.category as Notice["category"], event_id: id(row.event_id), event_version: integer(row.event_version, 1),
    offset_minutes: row.offset_minutes === null ? null : integer(row.offset_minutes, 1), created_at: instant(row.created_at), read_at: row.read_at === null ? null : instant(row.read_at),
    target: { kind: target.kind as Notice["target"]["kind"], id: id(target.id), available: flag(target.available) },
    deadline: deadline ? { closes_at: instant(deadline.closes_at), source_timezone: zone(deadline.source_timezone), display_at: instant(deadline.display_at), display_timezone: zone(deadline.display_timezone), current: flag(deadline.current) } : null,
  };
}
function inbox(value: unknown): Inbox {
  const row = record(value);
  if (!Array.isArray(row.items)) throw new RequestFailure("INVALID_RESPONSE");
  return { items: row.items.map(notice), total: integer(row.total), unread_count: integer(row.unread_count), page: integer(row.page, 1), page_size: integer(row.page_size, 1) };
}
async function request(path: string, init: RequestInit = {}): Promise<unknown> {
  const response = await fetch(`/api/v1${path}`, { ...init, credentials: "same-origin", cache: "no-store" });
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new RequestFailure(body && typeof body === "object" && "code" in body && typeof body.code === "string" ? body.code : "REQUEST_FAILED", response.status);
  return body;
}

export function NotificationInbox({ locale }: { locale: Language }) {
  const ar = locale === "ar";
  const [access, setAccess] = useState<"loading" | "ready" | "denied" | "unavailable">("loading");
  const [data, setData] = useState<Inbox | null>(null);
  const [savedPreferences, setSavedPreferences] = useState<Preferences | null>(null);
  const [draft, setDraft] = useState<Preferences | null>(null);
  const [page, setPage] = useState(1), [unreadOnly, setUnreadOnly] = useState(false), [attempt, setAttempt] = useState(0);
  const [busy, setBusy] = useState(false), [message, setMessage] = useState(""), [failed, setFailed] = useState(false);
  const [stale, setStale] = useState(false);
  const keys = useRef(new Map<string, string>());
  const count = (value: number) => new Intl.NumberFormat(locale).format(value);
  const date = (value: string, timezone: string) => new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short", timeZone: timezone }).format(new Date(value));
  const labels: Record<Notice["category"], string> = ar ? { DEADLINE: "تذكير بموعد مؤكد", SOURCE_CHANGE: "تغيير في مصدر المنحة", DOCUMENT_MISSING: "متطلبات مستندات الطلب" } : { DEADLINE: "Confirmed deadline reminder", SOURCE_CHANGE: "Scholarship source change", DOCUMENT_MISSING: "Application document requirements" };

  function clearPrivate() { setData(null); setSavedPreferences(null); setDraft(null); keys.current.clear(); }
  function report(error: unknown) {
    if (error instanceof RequestFailure && [401, 403].includes(error.status)) { clearPrivate(); setAccess("denied"); return; }
    setFailed(true);
    if (error instanceof RequestFailure && [409, 412, 428].includes(error.status)) {
      setStale(true); setMessage(ar ? "تغيّرت الإعدادات. حدّث البيانات وراجع النسخة الحالية قبل الحفظ." : "Preferences changed. Refresh and review the current version before saving.");
    } else setMessage(ar ? "تعذر إتمام الطلب. لم نفترض نجاحه؛ حدّث البيانات ثم أعد المحاولة." : "The request could not be completed. Success was not assumed; refresh the data and retry.");
  }
  async function mutate(path: string, method: string, body: unknown, revision?: number) {
    const encoded = JSON.stringify(body), fingerprint = `${path}:${revision ?? ""}:${encoded}`;
    let key = keys.current.get(fingerprint);
    if (!key) { key = crypto.randomUUID(); keys.current.set(fingerprint, key); }
    const result = await request(path, { method, headers: { "Content-Type": "application/json", "X-CSRFToken": await getCsrf(client), "Idempotency-Key": key, ...(revision === undefined ? {} : { "If-Match": `"${revision}"` }) }, body: encoded });
    keys.current.delete(fingerprint);
    return result;
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
        const [rows, settings] = await Promise.all([request(`/notifications?page=${page}&page_size=20&unread_only=${unreadOnly}`, { signal: controller.signal }), request("/notification-preferences", { signal: controller.signal })]);
        if (controller.signal.aborted) return;
        const parsed = preferences(settings);
        setData(inbox(rows)); setSavedPreferences(parsed); setDraft(parsed); setStale(false); setAccess("ready");
      } catch (error) {
        if (!controller.signal.aborted) { clearPrivate(); setAccess(error instanceof RequestFailure && [401, 403].includes(error.status) ? "denied" : "unavailable"); }
      }
    })();
    return () => controller.abort();
  }, [page, unreadOnly, attempt]);

  async function markRead(item: Notice) {
    setBusy(true); setMessage(""); setFailed(false);
    try {
      const result = notice(await mutate(`/notifications/${item.id}/read`, "POST", {}));
      if (result.id !== item.id || !result.read_at) throw new RequestFailure("INVALID_RESPONSE");
      setData(current => current ? { ...current, items: unreadOnly ? current.items.filter(row => row.id !== result.id) : current.items.map(row => row.id === result.id ? result : row), total: unreadOnly ? Math.max(0, current.total - 1) : current.total, unread_count: Math.max(0, current.unread_count - (item.read_at ? 0 : 1)) } : null);
      setMessage(ar ? "سُجلت قراءة الإشعار." : "The notification was marked as read.");
    } catch (error) { report(error); } finally { setBusy(false); }
  }
  async function save(event: FormEvent) {
    event.preventDefault(); if (!draft || !savedPreferences) return;
    setBusy(true); setMessage(""); setFailed(false);
    try {
      zone(draft.timezone);
      const { revision: _revision, ...body } = draft;
      void _revision;
      const result = preferences(await mutate("/notification-preferences", "PUT", body, savedPreferences.revision));
      setSavedPreferences(result); setDraft(result); setStale(false); setMessage(ar ? "حُفظت التفضيلات." : "Preferences saved.");
    } catch (error) {
      if (error instanceof RequestFailure && error.code === "INVALID_TIMEZONE") { setFailed(true); setMessage(ar ? "أدخل منطقة زمنية IANA صالحة مثل Asia/Hebron." : "Enter a valid IANA timezone such as Asia/Hebron."); }
      else report(error);
    } finally { setBusy(false); }
  }
  return <div className={styles.inbox} aria-busy={access === "loading" || busy}>
    <p className="catalog-note">{ar ? "الإشعارات داخل المنصة. لا تضمن عرض الطالب للتذكير، ولا تؤكد تقديم طلب على موقع خارجي." : "Notifications appear in the app. A reminder does not guarantee that you will see it or confirm submission on an external site."}</p>
    {access === "loading" && <p role="status">{ar ? "جارٍ التحقق وتحميل الإشعارات…" : "Verifying access and loading notifications…"}</p>}
    {access === "denied" && <p role="alert">{ar ? "يلزم حساب طالب بالغ ومؤكد البريد لعرض إشعاراتك." : "A verified adult student account is required to view your own notifications."} <a href={`/${locale}/account`}>{ar ? "الدخول وإدارة الحساب" : "Sign in or manage account"}</a></p>}
    {access === "unavailable" && <p role="alert">{ar ? "تعذر تحميل الإشعارات؛ لا يعني ذلك عدم وجود إشعارات." : "Notifications could not be loaded; this does not mean there are none."}</p>}
    <button type="button" disabled={access === "loading" || busy} onClick={() => { setMessage(""); setAttempt(value => value + 1); }}>{ar ? "تحديث البيانات" : "Refresh data"}</button>
    <div className={styles.status} role={failed ? "alert" : "status"}>{message}</div>
    {access === "ready" && data && savedPreferences && draft && <>
      <section aria-labelledby="inbox-heading">
        <h2 id="inbox-heading">{ar ? "صندوق الإشعارات" : "Notification inbox"}</h2>
        <p>{ar ? "غير المقروء إجمالًا: " : "Total unread: "}{count(data.unread_count)}. {ar ? "منطقة العرض: " : "Display timezone: "}<bdi dir="ltr">{savedPreferences.timezone}</bdi></p>
        <label className={styles.confirm}><input type="checkbox" checked={unreadOnly} disabled={busy} onChange={event => { setPage(1); setUnreadOnly(event.target.checked); }} />{ar ? "عرض غير المقروء فقط" : "Show unread only"}</label>
        {data.items.length === 0 ? <p>{ar ? "لا توجد إشعارات ضمن هذا العرض." : "There are no notifications in this view."}</p> : <ol className={styles.messages}>{data.items.map(item => <li key={item.id}><article data-unread={item.read_at === null}>
          <h3>{labels[item.category]}</h3>
          <p><span className="catalog-badge">{item.read_at ? (ar ? "مقروء" : "Read") : (ar ? "غير مقروء" : "Unread")}</span> <time dateTime={item.created_at}>{date(item.created_at, savedPreferences.timezone)}</time></p>
          {item.deadline && <>
            <p className={item.deadline.current ? "catalog-note" : "catalog-warning"}>{item.deadline.current ? (ar ? "الموعد المؤكد المسجل لهذا التذكير: " : "Confirmed deadline recorded for this reminder: ") : (ar ? "تذكير تاريخي؛ تغيّر المصدر أو الموعد. لا تعتمد على هذا الموعد حاليًا: " : "Historical reminder: the source or deadline changed. Do not rely on this deadline now: ")}<time dateTime={item.deadline.closes_at}>{date(item.deadline.closes_at, savedPreferences.timezone)}</time></p>
            <p>{ar ? "بتوقيت الجهة المانحة: " : "In the sponsor timezone: "}<time dateTime={item.deadline.closes_at}>{date(item.deadline.closes_at, item.deadline.source_timezone)}</time> · <bdi dir="ltr">{item.deadline.source_timezone}</bdi></p>
            <p>{ar ? "التذكير المجدول قبل الموعد بـ " : "Scheduled lead time: "}{item.offset_minutes === 1440 ? (ar ? "24 ساعة" : "24 hours") : item.offset_minutes !== null ? `${count(item.offset_minutes / 1440)} ${ar ? "يومًا" : "days"}` : (ar ? "غير محدد" : "unspecified")}{ar ? ". وقت الإشعار ليس عدادًا للوقت المتبقي الآن." : ". This is not a live countdown."}</p>
          </>}
          <p>{ar ? "نسخة الحدث: " : "Event version: "}{count(item.event_version)}</p>
          <div className={styles.actions}>
            {item.target.available ? <a href={item.target.kind === "APPLICATION" ? `/${locale}/applications?application=${item.target.id}` : `/${locale}/scholarships/${item.target.id}`}>{item.target.kind === "APPLICATION" ? (ar ? "فتح الطلب" : "Open application") : (ar ? "فتح المنحة" : "Open scholarship")}</a> : <span>{ar ? "الوجهة غير متاحة حاليًا. يبقى الإشعار في السجل." : "This destination is currently unavailable. The notice remains in your history."}</span>}
            <button type="button" disabled={busy || item.read_at !== null} onClick={() => void markRead(item)}>{ar ? "تحديد كمقروء" : "Mark as read"}</button>
          </div>
        </article></li>)}</ol>}
        <nav className={styles.actions} aria-label={ar ? "صفحات الإشعارات" : "Notification pages"}>
          <button type="button" disabled={busy || data.page <= 1} onClick={() => setPage(value => value - 1)}>{ar ? "السابق" : "Previous"}</button>
          <span>{ar ? "الصفحة " : "Page "}{count(data.page)} · {count(data.total)} {ar ? "إشعارًا في هذا العرض" : "notifications in this view"}</span>
          <button type="button" disabled={busy || data.page * data.page_size >= data.total} onClick={() => setPage(value => value + 1)}>{ar ? "التالي" : "Next"}</button>
        </nav>
      </section>
      <section aria-labelledby="notice-preferences-heading"><h2 id="notice-preferences-heading">{ar ? "المنطقة الزمنية والتفضيلات الاختيارية" : "Timezone and optional preferences"}</h2>
        <form onSubmit={save}><fieldset disabled={busy || stale}>
          <label htmlFor="notification-timezone">{ar ? "منطقة العرض الزمنية (IANA)" : "Display timezone (IANA)"}<input id="notification-timezone" type="text" dir="ltr" required maxLength={100} value={draft.timezone} onChange={event => setDraft({ ...draft, timezone: event.target.value })} aria-describedby="timezone-hint" /></label>
          <p id="timezone-hint">{ar ? "مثل Asia/Hebron أو Europe/London. لا نغيّر توقيت المصدر أو نخمن وقتًا لموعد مجهول." : "For example Asia/Hebron or Europe/London. This does not change the source timezone or invent a time for an unknown deadline."}</p>
          <label className={styles.confirm}><input type="checkbox" checked={draft.deadline_enabled} onChange={event => setDraft({ ...draft, deadline_enabled: event.target.checked })} />{ar ? "تذكير المواعيد المؤكدة" : "Confirmed deadline reminders"}</label>
          <label className={styles.confirm}><input type="checkbox" checked={draft.source_enabled} onChange={event => setDraft({ ...draft, source_enabled: event.target.checked })} />{ar ? "تغييرات مصدر المنحة" : "Scholarship source changes"}</label>
          <label className={styles.confirm}><input type="checkbox" checked={draft.document_enabled} onChange={event => setDraft({ ...draft, document_enabled: event.target.checked })} />{ar ? "تنبيهات المستندات الناقصة" : "Missing document alerts"}</label>
          <p>{ar ? "لا توقف هذه الخيارات رسائل الأمان والحساب الإلزامية. تعديل التفضيلات لا يحذف الإشعارات السابقة." : "These options do not disable required security or account messages. Changing preferences does not delete previous notifications."}</p>
          <button type="submit">{ar ? "حفظ التفضيلات" : "Save preferences"}</button>
        </fieldset></form>
      </section>
    </>}
  </div>;
}
