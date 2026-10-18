"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { createHealthClient, getCsrf, validateSession, type components } from "@minhaai/contracts";
import styles from "./application-tracker.module.css";

type Language = "ar" | "en";
const states = ["PREPARING", "READY", "SUBMITTED", "UNDER_REVIEW", "ACCEPTED", "REJECTED", "WITHDRAWN"] as const;
type State = typeof states[number];
type Round = components["schemas"]["PublicRound"] & { round_key?: string };
type Deadline = { kind: string; closes_at: string | null; source_timezone: string | null; display_at: string | null; display_timezone: string; eligible: boolean; reason: string; source_version_id: string | null };
type Requirement = { key: string; label: string; status: "MISSING" | "COMPLETE"; version_id: string | null; asset_id: string | null; content_hash: string | null };
type Official = { id: string; status: State; source_url: string; observed_at: string; recorded_at: string; evidence_ref: string; origin: string; verified_official: boolean };
type Application = {
  id: string; scholarship_id: string; title: string; round_key: string; round_snapshot: Round;
  state: State; revision: number; submitted_sequence: number | null; notes: string; requirements_known: boolean;
  requirements: Requirement[]; missing_count: number; allowed_transitions: State[]; official_integration_available: boolean;
  official_reports: Official[]; created_at: string; deadline: Deadline; source_changed: boolean; can_rebase: boolean;
};
type Event = { sequence: number; from_state: State | ""; to_state: State; kind: string; source: "STUDENT_REPORTED"; observed_at: string; recorded_at: string; evidence: string; reason: string; notes_snapshot: string; manifest_snapshot: unknown[]; correction_of_sequence: number | null; student_submission_confirmation: boolean };
type Saved = { id: string; scholarship_id: string; title: string; active: boolean; revision: number };
type VersionOption = { id: string; document_id: string; title: string; language: Language; number: number; content_hash: string };
type FileOption = { asset_id: string; declared_size: number; content_hash: string; mime: string };
type Options = { versions: VersionOption[]; files: FileOption[] };
type Snapshot = { id: string; requirement_key: string; label_snapshot: string; version_id: string | null; document_id: string | null; asset_id: string | null; content_hash: string; submitted_sequence: number };
type Deletion = { id: string; artifact_id: string; reason: string; state: "PENDING_LEGAL_REVIEW"; created_at: string };
type CatalogItem = { id: string; title: string };
type PageMeta = { page: number; page_size: number; total: number };
const client = createHealthClient();
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const hashPattern = /^[a-f0-9]{64}$/;
class RequestFailure extends Error { constructor(public code: string, public status = 0) { super(code); } }
function record(value: unknown): Record<string, unknown> { if (!value || typeof value !== "object" || Array.isArray(value)) throw new RequestFailure("INVALID_RESPONSE"); return value as Record<string, unknown>; }
function text(value: unknown): string { if (typeof value !== "string") throw new RequestFailure("INVALID_RESPONSE"); return value; }
function id(value: unknown): string { const result = text(value); if (!uuid.test(result)) throw new RequestFailure("INVALID_RESPONSE"); return result; }
function hash(value: unknown): string { const result = text(value); if (!hashPattern.test(result)) throw new RequestFailure("INVALID_RESPONSE"); return result; }
function integer(value: unknown, min = 0): number { if (!Number.isSafeInteger(value) || Number(value) < min) throw new RequestFailure("INVALID_RESPONSE"); return Number(value); }
function flag(value: unknown): boolean { if (typeof value !== "boolean") throw new RequestFailure("INVALID_RESPONSE"); return value; }
function instant(value: unknown): string { const result = text(value); if (!/(?:[zZ]|[+-]\d{2}:\d{2})$/.test(result) || !Number.isFinite(Date.parse(result))) throw new RequestFailure("INVALID_RESPONSE"); return result; }
function zone(value: unknown): string { const result = text(value); try { new Intl.DateTimeFormat("en", { timeZone: result }).format(); } catch { throw new RequestFailure("INVALID_RESPONSE"); } return result; }
function state(value: unknown): State { if (!states.includes(value as State)) throw new RequestFailure("INVALID_RESPONSE"); return value as State; }
function nullable<T>(value: unknown, parser: (item: unknown) => T): T | null { return value === null ? null : parser(value); }
function rows(value: unknown): unknown[] { if (!Array.isArray(value)) throw new RequestFailure("INVALID_RESPONSE"); return value; }
function items(value: unknown): unknown[] { return rows(record(value).items); }
function pageMeta(value: unknown): PageMeta { const row = record(value); return { page: integer(row.page, 1), page_size: integer(row.page_size, 1), total: integer(row.total) }; }
function round(value: unknown): Round {
  const row = record(value);
  if (!["UNKNOWN", "ROLLING", "DATE_ONLY", "CONFIRMED"].includes(text(row.kind))) throw new RequestFailure("INVALID_RESPONSE");
  return { kind: row.kind as Round["kind"], label: text(row.label), source_text: text(row.source_text), closes_at: nullable(row.closes_at, instant), deadline_date: nullable(row.deadline_date, text), timezone: nullable(row.timezone, zone), ...(row.round_key === undefined ? {} : { round_key: hash(row.round_key) }) };
}
function deadline(value: unknown): Deadline {
  const row = record(value);
  const result = { kind: text(row.kind), closes_at: nullable(row.closes_at, instant), source_timezone: nullable(row.source_timezone, zone), display_at: nullable(row.display_at, instant), display_timezone: zone(row.display_timezone), eligible: flag(row.eligible), reason: text(row.reason), source_version_id: nullable(row.source_version_id, id) };
  if (result.eligible && (result.kind !== "CONFIRMED" || !result.closes_at || !result.source_timezone || !result.display_at || !result.source_version_id)) throw new RequestFailure("INVALID_RESPONSE");
  return result;
}
function application(value: unknown): Application {
  const row = record(value);
  return {
    id: id(row.id), scholarship_id: id(row.scholarship_id), title: text(row.title), round_key: hash(row.round_key), round_snapshot: round(row.round_snapshot), state: state(row.state), revision: integer(row.revision), submitted_sequence: nullable(row.submitted_sequence, value => integer(value, 1)), notes: text(row.notes), requirements_known: flag(row.requirements_known),
    requirements: rows(row.requirements).map(value => { const item = record(value); if (!["MISSING", "COMPLETE"].includes(text(item.status))) throw new RequestFailure("INVALID_RESPONSE"); return { key: hash(item.key), label: text(item.label), status: item.status as Requirement["status"], version_id: nullable(item.version_id, id), asset_id: nullable(item.asset_id, id), content_hash: nullable(item.content_hash, hash) }; }),
    missing_count: integer(row.missing_count), allowed_transitions: rows(row.allowed_transitions).map(state), official_integration_available: flag(row.official_integration_available),
    official_reports: rows(row.official_reports).map(value => { const item = record(value); return { id: id(item.id), status: state(item.status), source_url: text(item.source_url), observed_at: instant(item.observed_at), recorded_at: instant(item.recorded_at), evidence_ref: text(item.evidence_ref), origin: text(item.origin), verified_official: flag(item.verified_official) }; }), created_at: instant(row.created_at), deadline: deadline(row.deadline), source_changed: flag(row.source_changed), can_rebase: flag(row.can_rebase),
  };
}
function history(value: unknown): Event[] { return items(value).map(value => { const row = record(value); if (row.source !== "STUDENT_REPORTED") throw new RequestFailure("INVALID_RESPONSE"); return { sequence: integer(row.sequence, 1), from_state: row.from_state === "" ? "" : state(row.from_state), to_state: state(row.to_state), kind: text(row.kind), source: row.source, observed_at: instant(row.observed_at), recorded_at: instant(row.recorded_at), evidence: text(row.evidence), reason: text(row.reason), notes_snapshot: text(row.notes_snapshot), manifest_snapshot: rows(row.manifest_snapshot), correction_of_sequence: nullable(row.correction_of_sequence, value => integer(value, 1)), student_submission_confirmation: flag(row.student_submission_confirmation) }; }); }
function saved(value: unknown): Saved { const row = record(value); return { id: id(row.id), scholarship_id: id(row.scholarship_id), title: text(row.title), active: flag(row.active), revision: integer(row.revision) }; }
function options(value: unknown): Options {
  const row = record(value);
  return { versions: rows(row.versions).map(value => { const item = record(value); if (!["ar", "en"].includes(text(item.language))) throw new RequestFailure("INVALID_RESPONSE"); return { id: id(item.id), document_id: id(item.document_id), title: text(item.title), language: item.language as Language, number: integer(item.number, 1), content_hash: hash(item.content_hash) }; }), files: rows(row.files).map(value => { const item = record(value); return { asset_id: id(item.asset_id), declared_size: integer(item.declared_size, 1), content_hash: hash(item.content_hash), mime: text(item.mime) }; }) };
}
function snapshots(value: unknown): Snapshot[] { return items(value).map(value => { const row = record(value); return { id: id(row.id), requirement_key: hash(row.requirement_key), label_snapshot: text(row.label_snapshot), version_id: nullable(row.version_id, id), document_id: nullable(row.document_id, id), asset_id: nullable(row.asset_id, id), content_hash: hash(row.content_hash), submitted_sequence: integer(row.submitted_sequence, 1) }; }); }
function deletions(value: unknown): Deletion[] { return items(value).map(value => { const row = record(value); if (row.state !== "PENDING_LEGAL_REVIEW") throw new RequestFailure("INVALID_RESPONSE"); return { id: id(row.id), artifact_id: id(row.artifact_id), reason: text(row.reason), state: row.state, created_at: instant(row.created_at) }; }); }
function observedInstant(value: string): string {
  const parts = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,3}))?(Z|[+-]\d{2}:\d{2})$/.exec(value);
  if (!parts) throw new RequestFailure("INVALID_OBSERVED_TIME");
  const [year, month, day, hour, minute, second] = parts.slice(1, 7).map(Number);
  const calendar = new Date(0);
  calendar.setUTCFullYear(year, month - 1, day);
  calendar.setUTCHours(hour, minute, second, 0);
  if (year < 1 || calendar.getUTCFullYear() !== year || calendar.getUTCMonth() !== month - 1 || calendar.getUTCDate() !== day || calendar.getUTCHours() !== hour || calendar.getUTCMinutes() !== minute || calendar.getUTCSeconds() !== second) throw new RequestFailure("INVALID_OBSERVED_TIME");
  const parsed = new Date(instant(value));
  if (!Number.isFinite(parsed.getTime()) || parsed.getTime() > Date.now()) throw new RequestFailure("INVALID_OBSERVED_TIME");
  return parsed.toISOString();
}
async function request(path: string, init: RequestInit = {}): Promise<unknown> {
  const response = await fetch(`/api/v1${path}`, { ...init, credentials: "same-origin", cache: "no-store" });
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) throw new RequestFailure(body && typeof body === "object" && "code" in body && typeof body.code === "string" ? body.code : "REQUEST_FAILED", response.status);
  return body;
}

export function ApplicationTracker({ locale }: { locale: Language }) {
  const ar = locale === "ar";
  const [access, setAccess] = useState<"loading" | "ready" | "denied" | "unavailable">("loading");
  const [applications, setApplications] = useState<Application[]>([]), [savedRows, setSavedRows] = useState<Saved[]>([]);
  const [counts, setCounts] = useState<Record<State, number> | null>(null);
  const [applicationPage, setApplicationPage] = useState(1), [savedPage, setSavedPage] = useState(1);
  const [applicationPageMeta, setApplicationPageMeta] = useState<PageMeta | null>(null), [savedPageMeta, setSavedPageMeta] = useState<PageMeta | null>(null);
  const [selected, setSelected] = useState<Application | null>(null), [events, setEvents] = useState<Event[]>([]);
  const [artifactOptions, setArtifactOptions] = useState<Options>({ versions: [], files: [] }), [submitted, setSubmitted] = useState<Snapshot[]>([]), [deletionRows, setDeletionRows] = useState<Deletion[]>([]);
  const [catalog, setCatalog] = useState<CatalogItem[]>([]), [query, setQuery] = useState(""), [catalogMore, setCatalogMore] = useState(false), [catalogSearched, setCatalogSearched] = useState(false);
  const [scholarshipId, setScholarshipId] = useState(""), [rounds, setRounds] = useState<Round[]>([]), [roundKey, setRoundKey] = useState("");
  const [notes, setNotes] = useState(""), [choices, setChoices] = useState<Record<string, string>>({});
  const [nextState, setNextState] = useState<State | "">(""), [observed, setObserved] = useState(""), [evidence, setEvidence] = useState(""), [confirmed, setConfirmed] = useState(false), [rebaseConfirmed, setRebaseConfirmed] = useState(false);
  const [deletionArtifact, setDeletionArtifact] = useState(""), [deletionReason, setDeletionReason] = useState("");
  const [preview, setPreview] = useState<{ title: string; content: string; language: Language } | null>(null);
  const [busy, setBusy] = useState(false), [stale, setStale] = useState(false), [attempt, setAttempt] = useState(0);
  const [message, setMessage] = useState(""), [failed, setFailed] = useState(false), [deviceTimezone, setDeviceTimezone] = useState("UTC");
  const keys = useRef(new Map<string, string>()), detailHeading = useRef<HTMLHeadingElement>(null);
  const count = (value: number) => new Intl.NumberFormat(locale).format(value);
  const labels: Record<State, string> = ar ? { PREPARING: "قيد التجهيز", READY: "جاهز للتقديم", SUBMITTED: "تم التقديم — بإفادة الطالب", UNDER_REVIEW: "قيد المراجعة — بإفادة الطالب", ACCEPTED: "مقبول — بإفادة الطالب", REJECTED: "مرفوض — بإفادة الطالب", WITHDRAWN: "منسحب" } : { PREPARING: "Preparing", READY: "Ready to apply", SUBMITTED: "Submitted — student reported", UNDER_REVIEW: "Under review — student reported", ACCEPTED: "Accepted — student reported", REJECTED: "Rejected — student reported", WITHDRAWN: "Withdrawn" };
  const eventLabels: Record<string, string> = ar ? { CREATED: "إنشاء الطلب", TRANSITION: "تسجيل حالة", NOTES: "تحديث الملاحظات", ARTIFACT: "تحديث المرفقات", CORRECTION: "تصحيح مدقق", REBASE: "مراجعة المصدر والمتطلبات" } : { CREATED: "Application created", TRANSITION: "Status recorded", NOTES: "Notes updated", ARTIFACT: "Attachments updated", CORRECTION: "Audited correction", REBASE: "Source and requirements reviewed" };
  const date = (value: string, timezone = selected?.deadline.display_timezone ?? deviceTimezone) => new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short", timeZone: timezone }).format(new Date(value));
  const dirty = selected !== null && notes !== selected.notes;
  const clearDetail = useCallback(() => { setSelected(null); setEvents([]); setArtifactOptions({ versions: [], files: [] }); setSubmitted([]); setDeletionRows([]); setNotes(""); setChoices({}); setPreview(null); setNextState(""); setObserved(""); setEvidence(""); setConfirmed(false); setRebaseConfirmed(false); setDeletionArtifact(""); setDeletionReason(""); }, []);
  const clearPrivate = useCallback(() => { clearDetail(); setApplications([]); setSavedRows([]); setCounts(null); setApplicationPageMeta(null); setSavedPageMeta(null); setRounds([]); setRoundKey(""); setScholarshipId(""); keys.current.clear(); }, [clearDetail]);
  const report = useCallback((error: unknown) => {
    if (error instanceof RequestFailure && [401, 403].includes(error.status)) { clearPrivate(); setAccess("denied"); return; }
    setFailed(true);
    if (error instanceof RequestFailure && [409, 412, 428].includes(error.status)) { setStale(true); setMessage(ar ? "تغيّر الطلب أو توجد نسخة لهذه الجولة. احتفظ بملاحظاتك، ثم حدّث وراجع السجل قبل إعادة المحاولة." : "The application changed, or this round already has a record. Keep your notes, then refresh and review the history before retrying."); }
    else if (error instanceof RequestFailure && error.code === "ROUND_IDENTITY_UNAVAILABLE") setMessage(ar ? "هوية الجولة تحتاج مراجعة المصدر. لا ننشئ جولة بالتخمين." : "Round identity needs source review. A round cannot be invented.");
    else setMessage(ar ? "تعذر إتمام الطلب. لا نفترض أنه حُفظ؛ بقيت مدخلاتك الحالية. حدّث السجل للتحقق ثم أعد المحاولة." : "The request could not be completed. Saving was not assumed; your current input remains. Refresh the history to check, then retry.");
  }, [ar, clearPrivate]);
  async function run(action: () => Promise<void>) { setBusy(true); setMessage(""); setFailed(false); try { await action(); } catch (error) { report(error); } finally { setBusy(false); } }
  async function mutate(path: string, method: string, body: unknown, revision?: number) {
    const encoded = body === undefined ? undefined : JSON.stringify(body), fingerprint = `${method}:${path}:${revision ?? ""}:${encoded ?? ""}`;
    let key = keys.current.get(fingerprint); if (!key) { key = crypto.randomUUID(); keys.current.set(fingerprint, key); }
    const result = await request(path, { method, headers: { "Content-Type": "application/json", "X-CSRFToken": await getCsrf(client), "Idempotency-Key": key, ...(revision === undefined ? {} : { "If-Match": `"${revision}"` }) }, ...(encoded === undefined ? {} : { body: encoded }) });
    keys.current.delete(fingerprint);
    return result;
  }
  async function loadSummary(applicationPage: number, savedPage: number, signal?: AbortSignal) {
    const [list, savedList] = await Promise.all([request(`/applications?page=${applicationPage}&page_size=20`, { signal }), request(`/saved-scholarships?page=${savedPage}&page_size=20`, { signal })]);
    const data = record(list), totals = record(data.counts), parsedCounts = Object.fromEntries(states.map(key => [key, integer(totals[key])])) as Record<State, number>;
    return { applications: items(list).map(application), savedRows: items(savedList).map(saved), counts: parsedCounts, applicationPageMeta: pageMeta(list), savedPageMeta: pageMeta(savedList) };
  }
  async function detail(id: string, signal?: AbortSignal) {
    const [app, timeline, choices, frozen, requests] = await Promise.all([request(`/applications/${id}`, { signal }), request(`/applications/${id}/history`, { signal }), request(`/applications/${id}/artifact-options`, { signal }), request(`/applications/${id}/submitted-artifacts`, { signal }), request(`/applications/${id}/artifact-deletion-requests`, { signal })]);
    return { app: application(app), timeline: history(timeline), choices: options(choices), frozen: snapshots(frozen), requests: deletions(requests) };
  }
  const showDetail = useCallback((result: Awaited<ReturnType<typeof detail>>) => {
    setSelected(result.app); setNotes(result.app.notes); setEvents(result.timeline); setArtifactOptions(result.choices); setSubmitted(result.frozen); setDeletionRows(result.requests);
    setChoices(Object.fromEntries(result.app.requirements.map(row => [row.key, row.version_id ? `version:${row.version_id}` : row.asset_id ? `file:${row.asset_id}` : ""])));
    setPreview(null); setNextState(""); setObserved(""); setEvidence(""); setConfirmed(false); setRebaseConfirmed(false); setStale(false); setDeletionArtifact(""); setDeletionReason("");
  }, []);
  async function refreshDetail(id: string) { const [result, summary] = await Promise.all([detail(id), loadSummary(applicationPage, savedPage)]); showDetail(result); setApplications(summary.applications); setSavedRows(summary.savedRows); setCounts(summary.counts); setApplicationPageMeta(summary.applicationPageMeta); setSavedPageMeta(summary.savedPageMeta); }
  function discard(): boolean { return !dirty || window.confirm(ar ? "توجد ملاحظات غير محفوظة. هل تريد تركها وتحميل البيانات؟" : "You have unsaved notes. Discard them and load the data?"); }
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
        const summary = await loadSummary(applicationPage, savedPage, controller.signal);
        const params = new URLSearchParams(window.location.search), applicationId = params.get("application"), scholarship = params.get("scholarship");
        const result = applicationId && uuid.test(applicationId) ? await detail(applicationId, controller.signal) : null;
        if (controller.signal.aborted) return;
        clearDetail(); setApplications(summary.applications); setSavedRows(summary.savedRows); setCounts(summary.counts); setApplicationPageMeta(summary.applicationPageMeta); setSavedPageMeta(summary.savedPageMeta); setStale(false); setDeviceTimezone(Intl.DateTimeFormat().resolvedOptions().timeZone);
        if (result) showDetail(result);
        if (scholarship && uuid.test(scholarship)) setScholarshipId(scholarship);
        setAccess("ready");
      } catch (error) { if (!controller.signal.aborted) { clearPrivate(); setAccess(error instanceof RequestFailure && [401, 403].includes(error.status) ? "denied" : "unavailable"); } }
    })();
    return () => controller.abort();
  }, [attempt, applicationPage, savedPage, clearDetail, clearPrivate, showDetail]);
  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => { event.preventDefault(); event.returnValue = ""; };
    window.addEventListener("beforeunload", warn); return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  useEffect(() => {
    if (!scholarshipId || access !== "ready") return;
    const controller = new AbortController();
    void (async () => {
      setRounds([]); setRoundKey("");
      try {
        const data = record(await request(`/applications/round-options?scholarship_id=${id(scholarshipId)}`, { signal: controller.signal }));
        const result = rows(data.items).map(round);
        if (controller.signal.aborted) return;
        if (result.some(row => !row.round_key)) throw new RequestFailure("INVALID_RESPONSE");
        setRounds(result); setRoundKey(result[0]?.round_key ?? "");
      } catch (error) { if (!controller.signal.aborted) report(error); }
    })();
    return () => controller.abort();
  }, [scholarshipId, access, report]);

  async function search(event: FormEvent) {
    event.preventDefault();
    await run(async () => {
      const response = await client.GET("/api/v1/scholarships", { params: { query: { q: query || undefined, mode: "TEXT", page: 1, page_size: 20, sort: "recent" } } });
      if (!response.response.ok || !response.data) throw new RequestFailure("CATALOG_UNAVAILABLE", response.response.status);
      setCatalog(response.data.items.map(row => ({ id: id(row.id), title: text(row.title) }))); setCatalogMore(response.data.total > response.data.items.length); setCatalogSearched(true);
    });
  }
  async function toggleSaved(scholarship: string) {
    await run(async () => {
      const current = savedRows.find(row => row.scholarship_id === scholarship && row.active);
      saved(await mutate(current ? `/saved-scholarships/${scholarship}` : "/saved-scholarships", current ? "DELETE" : "POST", current ? undefined : { scholarship_id: scholarship }, current?.revision));
      const list = await request(`/saved-scholarships?page=${savedPage}&page_size=20`);
      setSavedRows(items(list).map(saved)); setSavedPageMeta(pageMeta(list));
      setMessage(ar ? "حُدثت المنح المحفوظة. سجل الطلب مستقل ويبقى محفوظًا." : "Saved scholarships updated. Application records remain separate and preserved.");
    });
  }
  async function create(event: FormEvent) {
    event.preventDefault(); if (!scholarshipId || !roundKey || !discard()) return;
    await run(async () => { const result = application(await mutate("/applications", "POST", { scholarship_id: scholarshipId, round_key: roundKey })); await refreshDetail(result.id); setMessage(ar ? "أُنشئ سجل مستقل لهذه الجولة. لم يُقدّم أي طلب خارجي." : "A separate record was created for this round. No external application was submitted."); detailHeading.current?.focus(); });
  }
  async function select(id: string) {
    if (!discard()) return;
    await run(async () => { clearDetail(); showDetail(await detail(id)); window.history.replaceState(null, "", `?application=${id}`); window.setTimeout(() => detailHeading.current?.focus(), 0); });
  }
  async function saveNotes(event: FormEvent) {
    event.preventDefault(); if (!selected) return;
    await run(async () => { await mutate(`/applications/${selected.id}/notes`, "PUT", { notes }, selected.revision); await refreshDetail(selected.id); setMessage(ar ? "حُفظت الملاحظات مع سجل تدقيق." : "Notes saved with an audit event."); });
  }
  async function attach(requirement: Requirement, clear = false) {
    if (!selected || !discard()) return;
    const choice = choices[requirement.key], version = artifactOptions.versions.find(row => `version:${row.id}` === choice), file = artifactOptions.files.find(row => `file:${row.asset_id}` === choice);
    if (!clear && !version && !file) return;
    await run(async () => {
      await mutate(`/applications/${selected.id}/requirements/${requirement.key}/artifact`, "PUT", clear ? { clear: true } : { version_id: version?.id ?? null, asset_id: file?.asset_id ?? null, content_hash: version?.content_hash ?? file?.content_hash, clear: false }, selected.revision);
      await refreshDetail(selected.id); setMessage(ar ? "حُدث المرفق المحدد. عند تأكيد التقديم تُحفظ نسخة ثابتة منه." : "The exact attachment was updated. Submission confirmation freezes its evidence.");
    });
  }
  async function transition(event: FormEvent) {
    event.preventDefault(); if (!selected || !nextState || !observed || !discard()) return;
    let observedAt: string;
    try { observedAt = observedInstant(observed); } catch { setFailed(true); setMessage(ar ? "اختر وقت ملاحظة صالحًا لا يقع في المستقبل." : "Choose a valid observation time that is not in the future."); return; }
    await run(async () => { await mutate(`/applications/${selected.id}/transitions`, "POST", { to_state: nextState, observed_at: observedAt, evidence, confirm_external_submission: nextState === "SUBMITTED" && confirmed }, selected.revision); await refreshDetail(selected.id); setMessage(ar ? "سُجلت إفادتك ووقت ملاحظتها دون ادعاء تحقق رسمي." : "Your report and its observation time were recorded without claiming official verification."); });
  }
  async function rebase(event: FormEvent) {
    event.preventDefault(); if (!selected || !rebaseConfirmed || !discard()) return;
    await run(async () => { await mutate(`/applications/${selected.id}/rebase`, "POST", { confirm: true }, selected.revision); await refreshDetail(selected.id); setMessage(ar ? "سُجلت مراجعة المصدر وحُملت المتطلبات الحالية. أُزيلت اختيارات المرفقات القديمة؛ أعد مراجعتها. بقي تاريخ الطلب محفوظًا." : "Source review was recorded and current requirements loaded. Old attachment selections were cleared; review them again. Application history remains preserved."); });
  }
  async function readVersion(documentId: string, versionId: string, expectedHash: string) {
    const value = items(await request(`/documents/${documentId}/versions`)).map(record).find(row => row.id === versionId);
    if (!value || hash(value.content_hash) !== expectedHash || !["ar", "en"].includes(text(value.language))) throw new RequestFailure("INVALID_RESPONSE");
    setPreview({ title: text(value.title), content: text(value.content), language: value.language as Language });
  }
  async function download(assetId: string) {
    const grant = record(await request(`/files/${id(assetId)}/access-grants`, { method: "POST", headers: { "Content-Type": "application/json", "X-CSRFToken": await getCsrf(client) }, body: "{}" }));
    const token = text(grant.token); if (!token) throw new RequestFailure("INVALID_RESPONSE");
    const response = await fetch(`/api/v1/files/${assetId}/content`, { cache: "no-store", credentials: "same-origin", headers: { "X-File-Access-Grant": token } });
    if (!response.ok) throw new RequestFailure("DOWNLOAD_UNAVAILABLE", response.status);
    const mime = response.headers.get("Content-Type")?.split(";")[0], extensions: Record<string, string> = { "application/pdf": "pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx", "image/png": "png", "image/jpeg": "jpg" };
    if (!mime || !extensions[mime]) throw new RequestFailure("INVALID_RESPONSE");
    const blob = await response.blob(); if (!blob.size) throw new RequestFailure("INVALID_RESPONSE");
    const url = URL.createObjectURL(blob), anchor = document.createElement("a"); anchor.href = url; anchor.download = `submitted-${assetId}.${extensions[mime]}`; anchor.click(); window.setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  async function requestDeletion(event: FormEvent) {
    event.preventDefault(); if (!selected || !deletionArtifact) return;
    await run(async () => { await mutate(`/applications/${selected.id}/artifact-deletion-requests`, "POST", { artifact_id: deletionArtifact, reason: deletionReason }); setDeletionRows(deletions(await request(`/applications/${selected.id}/artifact-deletion-requests`))); setDeletionReason(""); setMessage(ar ? "سُجل طلب مراجعة الحذف. لم يُحذف الدليل؛ التنفيذ يحتاج مراجعة قانونية مستقلة." : "Deletion review was requested. Evidence was not erased; execution needs a separate legal review."); });
  }
  function paginate(meta: PageMeta, move: (page: number) => void, label: string) {
    return <nav className={styles.actions} aria-label={label}>
      <button type="button" disabled={busy || meta.page <= 1} onClick={() => { if (discard()) move(meta.page - 1); }}>{ar ? "السابق" : "Previous"}</button>
      <span>{ar ? "الصفحة " : "Page "}{count(meta.page)} · {count(meta.total)} {ar ? "سجلًا إجمالًا" : "records in total"}</span>
      <button type="button" disabled={busy || meta.page * meta.page_size >= meta.total} onClick={() => { if (discard()) move(meta.page + 1); }}>{ar ? "التالي" : "Next"}</button>
    </nav>;
  }

  return <div className={styles.tracker} aria-busy={access === "loading" || busy}>
    <p className="catalog-note">{ar ? "هذا سجل خاص لتجهيز طلباتك وإفاداتك. أنت تقدّم على بوابة الجهة المانحة، ثم تؤكد التقديم هنا بنفسك. لا يتصل هذا السجل بخدمة حالة رسمية حاليًا." : "This private tracker records preparation and your own reports. Submit on the sponsor portal yourself, then explicitly confirm it here. An official status integration is currently unavailable."}</p>
    {access === "loading" && <p role="status">{ar ? "جارٍ التحقق وتحميل طلباتك…" : "Verifying access and loading your applications…"}</p>}
    {access === "denied" && <p role="alert">{ar ? "يلزم حساب طالب بالغ ومؤكد البريد لعرض طلباتك الخاصة." : "A verified adult student account is required to view your private applications."} <a href={`/${locale}/account`}>{ar ? "الدخول وإدارة الحساب" : "Sign in or manage account"}</a></p>}
    {access === "unavailable" && <p role="alert">{ar ? "تعذر تحميل الطلبات. لا يعني ذلك أن سجلّك فارغ أو أن طلبًا أُرسل." : "Applications could not be loaded. This does not mean your history is empty or an application was submitted."}</p>}
    <div className={styles.actions}><button type="button" disabled={access === "loading" || busy} onClick={() => { if (discard()) { setMessage(""); setAttempt(value => value + 1); } }}>{ar ? "تحديث البيانات والسجل" : "Refresh data and history"}</button><a href={`/${locale}/notifications`}>{ar ? "الإشعارات وتوقيت العرض" : "Notifications and display timezone"}</a><a href={`/${locale}/documents`}>{ar ? "مكتبة الملفات والتحرير اليدوي" : "Files and manual document editing"}</a></div>
    <div className={styles.status} role={failed ? "alert" : "status"}>{message}</div>
    {access === "ready" && <>
      <section aria-labelledby="application-list-heading"><h2 id="application-list-heading">{ar ? "طلباتي — حالات بإفادتي" : "My applications — student-reported states"}</h2>
        {counts && <ul className={styles.counts} aria-label={ar ? "أعداد الطلبات المسجلة حسب الحالة" : "Recorded application counts by state"}>{states.map(key => <li key={key}>{labels[key]}: {count(counts[key])}</li>)}</ul>}
        {applications.length === 0 ? <p>{ar ? "لا توجد طلبات محفوظة. ابحث عن منحة منشورة واختر جولة لإنشاء سجل تجهيز." : "There are no saved applications. Find a published scholarship and choose a round to start preparing."}</p> : <ul className={styles.cards}>{applications.map(row => <li key={row.id}>
          <h3>{row.title}</h3><p>{labels[row.state]} · {row.round_snapshot.label || (ar ? "جولة غير مسماة في المصدر" : "Round unnamed by source")}</p>
          <button type="button" disabled={busy} aria-pressed={selected?.id === row.id} onClick={() => void select(row.id)}>{ar ? "فتح سجل الطلب" : "Open application record"}</button>
        </li>)}</ul>}
        {applicationPageMeta && paginate(applicationPageMeta, setApplicationPage, ar ? "صفحات طلباتي" : "Application pages")}
      </section>
      <section aria-labelledby="saved-scholarships-heading"><h2 id="saved-scholarships-heading">{ar ? "المنح المحفوظة" : "Saved scholarships"}</h2>
        {savedRows.filter(row => row.active).length === 0 ? <p>{ar ? "لا توجد منح محفوظة حاليًا." : "There are no currently saved scholarships."}</p> : <ul className={styles.cards}>{savedRows.filter(row => row.active).map(row => <li key={row.id}>
          <h3>{row.title}</h3><div className={styles.actions}><a href={`/${locale}/scholarships/${row.scholarship_id}`}>{ar ? "تفاصيل المنحة الحالية" : "Current scholarship details"}</a><button type="button" disabled={busy} onClick={() => setScholarshipId(row.scholarship_id)}>{ar ? "اختيار جولة للتجهيز" : "Choose a round to prepare"}</button><button type="button" disabled={busy || stale} onClick={() => void toggleSaved(row.scholarship_id)}>{ar ? "إلغاء حفظ المنحة" : "Unsave scholarship"}</button></div>
        </li>)}</ul>}
        {savedPageMeta && paginate(savedPageMeta, setSavedPage, ar ? "صفحات المنح المحفوظة" : "Saved scholarship pages")}
        <form onSubmit={search}><fieldset disabled={busy}><label htmlFor="tracker-scholarship-search">{ar ? "ابحث في المنح المنشورة" : "Search published scholarships"}<input id="tracker-scholarship-search" type="search" maxLength={200} value={query} onChange={event => setQuery(event.target.value)} /></label><button type="submit">{ar ? "بحث" : "Search"}</button></fieldset></form>
        {catalogSearched && catalog.length === 0 && <p>{ar ? "لا توجد نتائج منشورة لهذا البحث." : "No published results match this search."}</p>}
        {catalog.length > 0 && <ul className={styles.cards}>{catalog.map(row => <li key={row.id}><h3>{row.title}</h3><div className={styles.actions}><a href={`/${locale}/scholarships/${row.id}`}>{ar ? "تفاصيل المنحة" : "Scholarship details"}</a><button type="button" disabled={busy || stale} onClick={() => void toggleSaved(row.id)}>{savedRows.some(item => item.scholarship_id === row.id && item.active) ? (ar ? "إلغاء الحفظ" : "Unsave") : (ar ? "حفظ المنحة" : "Save scholarship")}</button><button type="button" disabled={busy} onClick={() => setScholarshipId(row.id)}>{ar ? "اختيار هذه المنحة" : "Choose this scholarship"}</button></div></li>)}</ul>}
        {catalogMore && <p>{ar ? "تُعرض أول 20 نتيجة. حدّد البحث للوصول إلى منحتك." : "The first 20 results are shown. Refine your search to find your scholarship."}</p>}
        {scholarshipId && <form onSubmit={create}><fieldset disabled={busy || !rounds.length || stale}><h3>{ar ? "إنشاء سجل لجولة منشورة" : "Create a record for a published round"}</h3><a href={`/${locale}/scholarships/${scholarshipId}`}>{ar ? "راجع المنحة والمصدر قبل الاختيار" : "Review the scholarship and source before choosing"}</a>
          <label htmlFor="application-round">{ar ? "الجولة المعتمدة في المصدر" : "Source-reviewed round"}<select id="application-round" required value={roundKey} onChange={event => setRoundKey(event.target.value)}>{rounds.map(row => <option key={row.round_key} value={row.round_key}>{row.label || (ar ? "جولة غير مسماة" : "Unnamed round")} · {row.kind === "CONFIRMED" ? (ar ? "موعد مؤكد" : "Confirmed deadline") : row.kind === "DATE_ONLY" ? (ar ? "تاريخ دون وقت مؤكد" : "Date without confirmed time") : row.kind === "ROLLING" ? (ar ? "تقديم مستمر" : "Rolling") : (ar ? "موعد غير معروف" : "Unknown deadline")}</option>)}</select></label>
          <p>{ar ? "كل جولة مصدرية جديدة تحتاج سجلًا جديدًا. لا يُعاد تعيين سجل جولة قديمة أو محو تاريخها." : "Each new sourced round uses a new record. An old round is never reset or silently overwritten."}</p><button type="submit">{ar ? "بدء التجهيز لهذه الجولة" : "Start preparing this round"}</button>
        </fieldset>{rounds.length === 0 && <p role="status">{ar ? "الجولات المعتمدة غير محمّلة. لا يمكن إنشاء طلب حتى تتوفر." : "Reviewed rounds are not loaded. An application cannot be created until they are available."}</p>}</form>}
      </section>
      {selected && <section className={styles.detail} aria-labelledby="application-detail-heading"><h2 id="application-detail-heading" tabIndex={-1} ref={detailHeading}>{selected.title} — {labels[selected.state]}</h2>
        <p>{ar ? "المصدر: إفادة الطالب. راجع وقت الملاحظة ووقت التسجيل بشكل منفصل في السجل أدناه." : "Source: student report. Observation time and recording time are shown separately in the history below."}</p>
        <p>{ar ? "الجولة المسجلة: " : "Recorded round: "}{selected.round_snapshot.label || (ar ? "غير مسماة" : "Unnamed")} · <bdi dir="ltr">{selected.round_key}</bdi></p>
        <a href={`/${locale}/scholarships/${selected.scholarship_id}`}>{ar ? "مراجعة المنحة الحالية ورابط الجهة المانحة" : "Review the current scholarship and sponsor portal link"}</a>
        {selected.source_changed && <div className="catalog-warning"><p>{ar ? "تغيّرت نسخة المصدر منذ تجهيز هذا الطلب. راجع المعلومات الجديدة؛ لا تُستخدم المتطلبات القديمة لإعلان الجاهزية أو تأكيد التقديم." : "The source version changed after this application was prepared. Review the new information; old requirements cannot authorize readiness or submission."}</p>{selected.can_rebase && <form onSubmit={rebase}><fieldset disabled={busy || stale}><label className={styles.confirm}><input type="checkbox" required checked={rebaseConfirmed} onChange={event => setRebaseConfirmed(event.target.checked)} />{ar ? "راجعت المصدر الحالي لهذه الجولة وأوافق على تحميل متطلباته وإزالة اختيارات المرفقات القديمة. سيبقى السجل السابق محفوظًا." : "I reviewed the current source for this round and agree to load its requirements and clear old attachment selections. The previous history will be preserved."}</label><button type="submit" disabled={!rebaseConfirmed}>{ar ? "تسجيل المراجعة وتحديث متطلبات التجهيز" : "Record review and update preparation requirements"}</button></fieldset></form>}</div>}
        <h3>{ar ? "الموعد الحالي المؤكد" : "Current confirmed deadline"}</h3>
        {selected.deadline.eligible && selected.deadline.closes_at && selected.deadline.source_timezone ? <>
          <p>{ar ? "بتوقيت العرض الخاص بك: " : "In your display timezone: "}<time dateTime={selected.deadline.closes_at}>{date(selected.deadline.closes_at)}</time> · <bdi dir="ltr">{selected.deadline.display_timezone}</bdi></p>
          <p>{ar ? "بتوقيت الجهة المانحة: " : "In the sponsor timezone: "}<time dateTime={selected.deadline.closes_at}>{date(selected.deadline.closes_at, selected.deadline.source_timezone)}</time> · <bdi dir="ltr">{selected.deadline.source_timezone}</bdi></p>
          <p>{ar ? "يُعرض الموعد الذي تحقق منه الخادم من المصدر المنشور الحالي؛ لا يمثل وقت فتح الصفحة تذكيرًا جديدًا." : "The server verified this date against the current published source. Opening this page does not create a new reminder."}</p>
        </> : <p className="catalog-warning">{ar ? "لا يوجد موعد مستقبلي مؤكد ومؤهل للتذكير حاليًا. الموعد المجهول أو المستمر أو التاريخ دون وقت أو المصدر القديم لا يملك عدادًا أو تذكيرًا مُفترضًا." : "There is no confirmed future deadline eligible for reminders right now. Unknown, rolling, date-only or outdated information has no invented countdown or reminder."}</p>}
        <h3>{ar ? "المتطلبات والمرفقات المحددة" : "Requirements and exact attachments"}</h3>
        {!selected.requirements_known && <p className="catalog-warning">{ar ? "قائمة المتطلبات غير مؤكدة؛ القائمة الفارغة لا تعني الجاهزية. راجع المصدر. لا يمكن اعتماد «جاهز» بقائمة مجهولة." : "The requirements checklist is unconfirmed; an empty list does not mean readiness. Check the source. An unknown checklist cannot be marked Ready."}</p>}
        <p>{ar ? "المتطلبات الناقصة المسجلة: " : "Recorded missing requirements: "}{count(selected.missing_count)}. {ar ? "نختار نسخة معتمدة بعينها أو ملفًا اجتاز الفحص؛ لا يُرسل شيء إلى AI." : "Choose an exact approved version or a scanned accepted upload. No attachment is sent to AI."}</p>
        <ul className={styles.cards}>{selected.requirements.map(requirement => <li key={requirement.key}><h4>{requirement.label}</h4><p>{requirement.status === "COMPLETE" ? (ar ? "مرفق محدد" : "Exact attachment selected") : (ar ? "مرفق ناقص" : "Missing attachment")}</p>
          {requirement.content_hash && <p className={styles.hash}><bdi dir="ltr">SHA-256: {requirement.content_hash}</bdi></p>}
          {selected.submitted_sequence === null ? <fieldset disabled={busy || stale}><label htmlFor={`artifact-${requirement.key}`}>{ar ? "النسخة أو الملف" : "Version or upload"}<select id={`artifact-${requirement.key}`} value={choices[requirement.key] ?? ""} onChange={event => setChoices({ ...choices, [requirement.key]: event.target.value })}>
            <option value="">{ar ? "اختر مرفقًا محددًا" : "Choose an exact attachment"}</option>
            <optgroup label={ar ? "نسخ مستندات معتمدة" : "Approved document versions"}>{artifactOptions.versions.map(row => <option key={row.id} value={`version:${row.id}`}>{row.title} · {ar ? "نسخة" : "version"} {row.number} · {row.language}</option>)}</optgroup>
            <optgroup label={ar ? "ملفات مقبولة بعد الفحص" : "Accepted scanned uploads"}>{artifactOptions.files.map(row => <option key={row.asset_id} value={`file:${row.asset_id}`}>{row.mime} · {count(row.declared_size)} {ar ? "بايت" : "bytes"} · {row.asset_id}</option>)}</optgroup>
          </select></label><div className={styles.actions}><button type="button" disabled={!choices[requirement.key]} onClick={() => void attach(requirement)}>{ar ? "حفظ المرفق المحدد" : "Save exact attachment"}</button><button type="button" disabled={!requirement.content_hash} onClick={() => void attach(requirement, true)}>{ar ? "إزالة الاختيار" : "Clear selection"}</button></div></fieldset> : <p>{ar ? "المرفق المقدم ثابت. تعديل المستند الرئيسي لا يغيّر هذا الدليل." : "Submitted evidence is frozen. Editing the master document does not change it."}</p>}
        </li>)}</ul>
        <form onSubmit={saveNotes}><fieldset disabled={busy || stale}><label htmlFor="application-notes">{ar ? "ملاحظاتي الخاصة" : "My private notes"}<textarea id="application-notes" maxLength={5000} value={notes} onChange={event => setNotes(event.target.value)} /></label><p>{count(notes.length)} / {count(5000)}</p><button type="submit" disabled={!dirty}>{ar ? "حفظ الملاحظات" : "Save notes"}</button></fieldset></form>
        <form onSubmit={transition}><fieldset disabled={busy || stale || selected.allowed_transitions.length === 0}><h3>{ar ? "تسجيل حالة بإفادتي" : "Record a student-reported state"}</h3>
          <label htmlFor="application-next-state">{ar ? "الانتقال المسموح" : "Allowed transition"}<select id="application-next-state" required value={nextState} onChange={event => { setNextState(event.target.value as State | ""); setConfirmed(false); }}><option value="">{ar ? "اختر الحالة التالية" : "Choose the next state"}</option>{selected.allowed_transitions.map(value => <option key={value} value={value}>{labels[value]}</option>)}</select></label>
          <label htmlFor="application-observed">{ar ? "وقت ملاحظتك للحالة مع فرق التوقيت" : "When you observed the status, including its UTC offset"}<input id="application-observed" type="text" dir="ltr" required maxLength={40} value={observed} onChange={event => setObserved(event.target.value)} placeholder="2026-10-17T09:00:00+03:00" aria-describedby="observed-timezone" /></label><p id="observed-timezone">{ar ? "اكتب تاريخًا ووقتًا بصيغة ISO مع Z لتوقيت UTC أو فرق صريح مثل +03:00 حتى لا نخمن ساعة مبهمة. وقت التسجيل منفصل عن وقت الملاحظة." : "Use an ISO date and time with Z for UTC or an explicit offset such as +03:00, so an ambiguous hour is not guessed. Recording time is separate from observation time."}</p>
          <label htmlFor="application-evidence">{ar ? "وصف مصدر إفادتك" : "Describe the source of your report"}<textarea id="application-evidence" required maxLength={1000} value={evidence} onChange={event => setEvidence(event.target.value)} placeholder={ar ? "مثل: رسالة من الجهة المانحة أو الحالة التي رأيتها في حسابي على بوابتها" : "For example: a sponsor message or the status I saw in my portal account"} /></label>
          {nextState === "SUBMITTED" && <label className={styles.confirm}><input type="checkbox" required checked={confirmed} onChange={event => setConfirmed(event.target.checked)} />{ar ? "أؤكد أنني أرسلت الطلب بالفعل بنفسي على البوابة الخارجية، وأن المرفقات المحددة هي النسخ التي قدّمتها. هذا الإجراء يسجل إفادتي ويحفظ دليلًا ثابتًا." : "I confirm that I already submitted the application myself on the external portal and that these are the exact attachments I submitted. This action records my report and freezes the evidence."}</label>}
          <p>{ar ? "فتح الرابط أو تجهيز الملفات لا يثبت التقديم. لا يعيد هذا الإجراء تعيين السجل أو يرسل طلبًا خارجيًا." : "Opening a link or preparing files does not prove submission. This action does not reset history or submit an external application."}</p><button type="submit" disabled={!nextState || (nextState === "SUBMITTED" && !confirmed)}>{nextState === "SUBMITTED" ? (ar ? "سجّل إفادتي: قدّمت على البوابة الخارجية" : "Record my report: I submitted on the external portal") : (ar ? "تسجيل الحالة بإفادتي" : "Record my reported state")}</button>
        </fieldset>{selected.allowed_transitions.length === 0 && <p>{ar ? "لا توجد انتقالات عادية متاحة لهذه الحالة. احتُفظ بالسجل؛ التقديم لجولة جديدة يحتاج سجل جولة جديدة." : "No ordinary transitions are available for this state. History is preserved; a new round needs a new application record."}</p>}</form>
        <section aria-labelledby="application-official-heading"><h3 id="application-official-heading">{ar ? "المصدر الرسمي — سجل مستقل" : "Official source — separate record"}</h3><p>{ar ? "التكامل الرسمي المباشر غير متاح. لا تتحول إفادتك إلى حالة رسمية، ولا يكتب مصدر آخر فوقها بصمت." : "Live official integration is unavailable. Your report does not become an official status, and another source cannot silently overwrite it."}</p>
          {selected.official_reports.length === 0 ? <p>{ar ? "لا توجد إفادة رسمية متحققة مسجلة." : "No verified official status report is recorded."}</p> : <ul className={styles.cards}>{selected.official_reports.map(row => <li key={row.id}><p>{row.verified_official ? (ar ? "إفادة رسمية متحققة: " : "Verified official report: ") : (ar ? "إفادة مصدر منفصلة غير متحققة رسميًا: " : "Separate source report, not officially verified: ")}{labels[row.status].split(" — ")[0]}</p><p>{ar ? "المصدر: " : "Source: "}<bdi>{row.source_url}</bdi></p><p>{ar ? "لوحظت: " : "Observed: "}<time dateTime={row.observed_at}>{date(row.observed_at)}</time> · {ar ? "سُجلت: " : "Recorded: "}<time dateTime={row.recorded_at}>{date(row.recorded_at)}</time></p></li>)}</ul>}
        </section>
        <section aria-labelledby="submitted-evidence-heading"><h3 id="submitted-evidence-heading">{ar ? "المرفقات المقدمة الثابتة" : "Frozen submitted evidence"}</h3>
          {submitted.length === 0 ? <p>{ar ? "لم تُحفظ مرفقات تقديم ثابتة لهذا السجل بعد." : "No frozen submitted attachments have been saved for this record yet."}</p> : <ul className={styles.cards}>{submitted.map(row => <li key={row.id}><h4>{row.label_snapshot}</h4><p>{ar ? "مرتبط بحدث تقديم رقم " : "Bound to submission event "}{count(row.submitted_sequence)}</p><p className={styles.hash}><bdi dir="ltr">SHA-256: {row.content_hash}</bdi></p><div className={styles.actions}>
            {row.version_id && row.document_id && <button type="button" disabled={busy} onClick={() => void run(() => readVersion(row.document_id!, row.version_id!, row.content_hash))}>{ar ? "قراءة النسخة المقدمة" : "Read the submitted version"}</button>}
            {row.asset_id && <button type="button" disabled={busy} onClick={() => void run(() => download(row.asset_id!))}>{ar ? "تنزيل الملف المقدم بترخيص مؤقت" : "Download submitted file with temporary access"}</button>}
          </div></li>)}</ul>}
          {preview && <div className={styles.preview} lang={preview.language} dir={preview.language === "ar" ? "rtl" : "ltr"}><h4>{preview.title}</h4><p>{preview.content}</p><button type="button" onClick={() => setPreview(null)}>{ar ? "إغلاق المعاينة" : "Close preview"}</button></div>}
          {submitted.length > 0 && <details><summary>{ar ? "طلب مراجعة حذف دليل مقدم" : "Request review of submitted evidence deletion"}</summary><p className="catalog-warning">{ar ? "هذا مسار مستقل عن التحرير. يسجل طلب مراجعة قانونية ولا يحذف الدليل تلقائيًا أو يعد بإمكانية محوه فورًا." : "This is separate from editing. It records a request for legal review and does not automatically erase evidence or promise immediate erasure."}</p>
            <form onSubmit={requestDeletion}><fieldset disabled={busy}><label htmlFor="deletion-artifact">{ar ? "الدليل المقصود" : "Evidence to review"}<select id="deletion-artifact" required value={deletionArtifact} onChange={event => setDeletionArtifact(event.target.value)}><option value="">{ar ? "اختر دليلًا" : "Choose evidence"}</option>{submitted.map(row => <option key={row.id} value={row.id}>{row.label_snapshot}</option>)}</select></label><label htmlFor="deletion-reason">{ar ? "سبب طلب المراجعة" : "Reason for review"}<textarea id="deletion-reason" required maxLength={1000} value={deletionReason} onChange={event => setDeletionReason(event.target.value)} /></label><button type="submit">{ar ? "تسجيل طلب مراجعة الحذف" : "Request deletion review"}</button></fieldset></form>
            <ul>{deletionRows.map(row => <li key={row.id}>{ar ? "بانتظار المراجعة القانونية" : "Pending legal review"} · <time dateTime={row.created_at}>{date(row.created_at)}</time><p>{row.reason}</p></li>)}</ul>
          </details>}
        </section>
        <section aria-labelledby="application-history-heading"><h3 id="application-history-heading">{ar ? "السجل الزمني غير القابل للاستبدال" : "Append-only history"}</h3><ol className={styles.history}>{events.map(event => <li key={event.sequence}><p><strong>{count(event.sequence)} · {event.from_state ? `${labels[event.from_state]} → ` : ""}{labels[event.to_state]}</strong></p><p>{ar ? "المصدر: إفادة الطالب" : "Source: student report"} · <span>{eventLabels[event.kind] ?? (ar ? "نشاط مسجل" : "Recorded activity")}</span></p><dl><dt>{ar ? "وقت الملاحظة" : "Observed time"}</dt><dd><time dateTime={event.observed_at}>{date(event.observed_at)}</time></dd><dt>{ar ? "وقت التسجيل" : "Recorded time"}</dt><dd><time dateTime={event.recorded_at}>{date(event.recorded_at)}</time></dd><dt>{ar ? "الدليل أو المصدر الموصوف" : "Described evidence or source"}</dt><dd>{event.evidence || (ar ? "لم يُذكر" : "Not provided")}</dd></dl>{event.reason && <p>{event.reason}</p>}{event.student_submission_confirmation && <p>{ar ? "سُجل تأكيد الطالب الصريح بالتقديم الخارجي." : "Explicit student confirmation of external submission was recorded."}</p>}{event.correction_of_sequence !== null && <p>{ar ? "تصحيح مدقق لحدث رقم " : "Audited correction of event "}{count(event.correction_of_sequence)}</p>}<details><summary>{ar ? "الملاحظات وحجم قائمة المرفقات وقت الحدث" : "Notes and attachment count captured at this event"}</summary><p className={styles.record}>{event.notes_snapshot || (ar ? "لا توجد ملاحظات وقت الحدث." : "No notes were recorded at this event.")}</p><p>{ar ? "عدد المرفقات في اللقطة: " : "Attachments in captured manifest: "}{count(event.manifest_snapshot.length)}</p></details></li>)}</ol></section>
      </section>}
    </>}
  </div>;
}
