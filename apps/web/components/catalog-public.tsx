"use client";

import { useEffect, useState, type FormEvent } from "react";
import { createHealthClient } from "@minhaai/contracts";
import { CatalogFacts, catalogLabel } from "./catalog-presentation";
import type { Funding, PublicScholarship } from "./catalog-types";

const client = createHealthClient();
type Query = {
  q: string; education_level: "" | "BACHELOR" | "MASTER" | "PHD"; discipline: string;
  country: string; language: string; funding: "" | Funding; deadline_before: string;
  sort: "recent" | "relevance" | "deadline";
};
const initialQuery: Query = { q: "", education_level: "", discipline: "", country: "", language: "", funding: "", deadline_before: "", sort: "recent" };

export function CatalogSearch({ locale }: { locale: "ar" | "en" }) {
  const ar = locale === "ar";
  const [query, setQuery] = useState<Query>(initialQuery);
  const [applied, setApplied] = useState<Query>(initialQuery);
  const [page, setPage] = useState(1);
  const [result, setResult] = useState<{ items: PublicScholarship[]; total: number; page_size: number } | null>(null);
  const [busy, setBusy] = useState(true);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    void client.GET("/api/v1/scholarships", { signal: controller.signal, params: { query: {
      q: applied.q || undefined, education_level: applied.education_level || undefined,
      discipline: applied.discipline || undefined, country: applied.country || undefined,
      language: applied.language || undefined, funding: applied.funding || undefined,
      deadline_before: applied.deadline_before || undefined, sort: applied.sort,
      page, page_size: 12, mode: "TEXT",
    } } }).then(response => {
      if (controller.signal.aborted) return;
      if (!response.response.ok || !response.data) throw new Error("CATALOG_UNAVAILABLE");
      setResult(response.data); setFailed(false); setBusy(false);
    }).catch(() => {
      if (controller.signal.aborted) return;
      setResult(null); setFailed(true); setBusy(false);
    });
    return () => controller.abort();
  }, [applied, page]);

  function apply(event?: FormEvent, next = query) {
    event?.preventDefault();
    setBusy(true); setFailed(false); setResult(null); setPage(1); setApplied({ ...next });
  }

  function move(next: number) { setBusy(true); setFailed(false); setResult(null); setPage(next); }

  return <section aria-busy={busy}>
    <p>{ar ? "تصفح مجاني دون حساب. لا تظهر إلا النسخ التي راجعها إنسان وأجاز نشرها من مصدر مأذون." : "Browse freely without an account. Listings appear only after human review of an exact version from a permitted source."}</p>
    <form onSubmit={apply}>
      <label>{ar ? "ابحث في المنح" : "Search scholarships"}
        <input type="search" value={query.q} maxLength={200} onChange={event => setQuery({ ...query, q: event.target.value })} />
      </label>
      <div className="catalog-fields">
        <label>{ar ? "المستوى الدراسي" : "Education level"}<select value={query.education_level} onChange={event => setQuery({ ...query, education_level: event.target.value as Query["education_level"] })}>
          <option value="">{ar ? "كل المستويات" : "All levels"}</option>
          {["BACHELOR", "MASTER", "PHD"].map(value => <option key={value} value={value}>{catalogLabel(value, ar)}</option>)}
        </select></label>
        <label>{ar ? "التمويل" : "Funding"}<select value={query.funding} onChange={event => setQuery({ ...query, funding: event.target.value as Query["funding"] })}>
          <option value="">{ar ? "كل أنواع التمويل" : "All funding"}</option>
          {["FULL", "PARTIAL", "WAIVER", "AID", "UNKNOWN"].map(value => <option key={value} value={value}>{catalogLabel(value, ar)}</option>)}
        </select></label>
        <label>{ar ? "البلد" : "Country"}<input value={query.country} maxLength={80} onChange={event => setQuery({ ...query, country: event.target.value })} /></label>
        <label>{ar ? "التخصص" : "Discipline"}<input value={query.discipline} maxLength={80} onChange={event => setQuery({ ...query, discipline: event.target.value })} /></label>
        <label>{ar ? "اللغة المطلوبة" : "Required language"}<input value={query.language} maxLength={80} onChange={event => setQuery({ ...query, language: event.target.value })} /></label>
        <label>{ar ? "موعد مؤكد حتى نهاية يوم (UTC)" : "Confirmed deadline through date (UTC)"}<input type="date" value={query.deadline_before} onChange={event => setQuery({ ...query, deadline_before: event.target.value })} /></label>
        <label>{ar ? "الترتيب" : "Sort"}<select value={query.sort} onChange={event => setQuery({ ...query, sort: event.target.value as Query["sort"] })}>
          <option value="recent">{ar ? "أحدث النسخ" : "Newest versions"}</option>
          <option value="relevance">{ar ? "صلة النص" : "Text relevance"}</option>
          <option value="deadline">{ar ? "الموعد المؤكد" : "Confirmed deadline"}</option>
        </select></label>
      </div>
      <p>{ar ? "فلتر التاريخ يشمل المواعيد المؤكدة فقط. البحث يطابق النص المعتمد دون تخصيص شخصي." : "The date filter includes confirmed deadlines only. Search matches reviewed text without personalizing results."}</p>
      <div className="catalog-actions">
        <button disabled={busy} type="submit">{ar ? "تطبيق البحث والفلاتر" : "Apply search and filters"}</button>
        <button disabled={busy} type="button" className="secondary" onClick={() => { setQuery(initialQuery); apply(undefined, initialQuery); }}>{ar ? "مسح الفلاتر" : "Clear filters"}</button>
      </div>
    </form>
    <div role={failed ? "alert" : "status"} aria-live="polite">
      {busy ? (ar ? "جارٍ تحميل المنح…" : "Loading scholarships…")
        : failed ? (ar ? "تعذر تحميل المنح. تحقق من الفلاتر وأعد المحاولة." : "Scholarships could not be loaded. Check the filters and try again.")
          : result && (ar ? `${result.total} نتيجة` : `${result.total} results`)}
    </div>
    {failed && <button onClick={() => apply()}>{ar ? "أعد المحاولة" : "Try again"}</button>}
    {result?.items.length === 0 && <p className="catalog-note">{ar ? "لا توجد منح مطابقة. جرّب إزالة بعض الفلاتر، أو عد لاحقًا عند اعتماد فرص جديدة." : "No matching scholarships. Try removing filters, or return after more opportunities are reviewed."}</p>}
    <div className="catalog-grid">
      {result?.items.map(item => <article key={item.id}>
        <h2><a href={`/${locale}/scholarships/${item.id}`}>{item.title}</a></h2>
        <p>{item.summary}</p>
        <CatalogFacts item={item} locale={locale} />
      </article>)}
    </div>
    {result && result.total > result.page_size && <nav className="catalog-pagination" aria-label={ar ? "صفحات النتائج" : "Results pages"}>
      <button disabled={busy || page === 1} onClick={() => move(page - 1)}>{ar ? "السابق" : "Previous"}</button>
      <span>{ar ? "صفحة" : "Page"} {page} / {Math.ceil(result.total / result.page_size)}</span>
      <button disabled={busy || page * result.page_size >= result.total} onClick={() => move(page + 1)}>{ar ? "التالي" : "Next"}</button>
    </nav>}
  </section>;
}

export function CatalogDetail({ locale, scholarshipId }: { locale: "ar" | "en"; scholarshipId: string }) {
  const ar = locale === "ar";
  const [item, setItem] = useState<PublicScholarship | null>(null);
  const [busy, setBusy] = useState(true);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    void client.GET("/api/v1/scholarships/{scholarship_id}", { signal: controller.signal, params: { path: { scholarship_id: scholarshipId } } }).then(response => {
      if (controller.signal.aborted) return;
      if (!response.response.ok || !response.data) throw new Error("CATALOG_UNAVAILABLE");
      setItem(response.data); setFailed(false); setBusy(false);
    }).catch(() => {
      if (controller.signal.aborted) return;
      setItem(null); setFailed(true); setBusy(false);
    });
    return () => controller.abort();
  }, [scholarshipId, attempt]);

  return <section aria-busy={busy}>
    <p><a href={`/${locale}/scholarships`}>{ar ? "العودة إلى المنح" : "Back to scholarships"}</a></p>
    <p role={failed ? "alert" : "status"} aria-live="polite">{busy ? (ar ? "جارٍ تحميل التفاصيل…" : "Loading details…") : failed ? (ar ? "هذه المنحة غير متاحة، أو تعذر تحميلها." : "This scholarship is unavailable, or could not be loaded.") : ""}</p>
    {failed && <button onClick={() => { setBusy(true); setAttempt(value => value + 1); }}>{ar ? "أعد المحاولة" : "Try again"}</button>}
    {item && <article>
      <h2>{item.title}</h2><p>{item.summary}</p>
      <CatalogFacts item={item} locale={locale} detail />
      <p>{ar ? "النسخة المعتمدة: " : "Reviewed version: "}{item.version}</p>
    </article>}
  </section>;
}
