import type { PublicScholarship, Round } from "./catalog-types";

export function safeCatalogUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" && !url.username && !url.password ? url.href : null;
  } catch { return null; }
}

export function catalogTime(value: string | null, locale: "ar" | "en", timeZone = "UTC"): string {
  if (!value || !Number.isFinite(Date.parse(value))) return locale === "ar" ? "غير معروف" : "Unknown";
  try {
    return new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short", timeZone }).format(new Date(value));
  } catch { return value; }
}

export function catalogLabel(value: string, ar: boolean): string {
  const labels: Record<string, [string, string]> = {
    FULL: ["تمويل كامل", "Full funding"], PARTIAL: ["تمويل جزئي", "Partial funding"],
    WAIVER: ["إعفاء من الرسوم", "Tuition waiver"], AID: ["مساعدة مالية", "Financial aid"],
    UNKNOWN: ["غير معروف", "Unknown"], CURRENT: ["تم التحقق حديثًا", "Recently verified"],
    STALE: ["تحتاج إعادة تحقق", "Needs reverification"],
    BACHELOR: ["بكالوريوس", "Bachelor’s"], MASTER: ["ماجستير", "Master’s"], PHD: ["دكتوراه", "PhD"],
    DRAFT: ["مسودة", "Draft"], PUBLISHED: ["منشورة", "Published"], REVERIFY: ["إعادة تحقق", "Reverify"],
    SUSPENDED: ["معلقة", "Suspended"], ARCHIVED: ["مؤرشفة", "Archived"], REJECTED: ["مرفوضة", "Rejected"],
    UNVERIFIED: ["إذن غير متحقق", "Unverified permission"], APPROVED: ["معتمد", "Approved"],
    BLOCKED: ["محظور", "Blocked"], REVOKED: ["إذن ملغى", "Revoked permission"],
  };
  return labels[value]?.[ar ? 0 : 1] ?? value;
}

export function CatalogRound({ round, locale }: { round: Round; locale: "ar" | "en" }) {
  const ar = locale === "ar";
  return <li>
    {round.label && <strong>{round.label}: </strong>}
    {round.kind === "CONFIRMED" && round.closes_at && round.timezone
      ? <><bdi>{catalogTime(round.closes_at, locale, round.timezone)}</bdi> · <bdi>{round.timezone}</bdi></>
      : round.kind === "DATE_ONLY" && round.deadline_date
        ? <><bdi>{round.deadline_date}</bdi> — {ar ? "تاريخ فقط؛ ساعة الإغلاق غير مؤكدة" : "Date only; closing time is unconfirmed"}</>
        : round.kind === "ROLLING"
          ? (ar ? "التقديم مستمر بحسب المصدر؛ لا موعد إغلاق مؤكد" : "Rolling according to the source; no confirmed closing instant")
          : (ar ? "الموعد غير معروف أو غير مؤكد" : "Deadline unknown or unconfirmed")}
    {round.source_text && <p>{ar ? "النص الوارد من المصدر: " : "Source wording: "}{round.source_text}</p>}
  </li>;
}

export function CatalogFacts({ item, locale, detail = false }: {
  item: PublicScholarship; locale: "ar" | "en"; detail?: boolean;
}) {
  const ar = locale === "ar";
  const unknown = ar ? "غير معروف" : "Unknown";
  const source = safeCatalogUrl(item.source.url);
  const submission = safeCatalogUrl(item.submission_url);
  const terms = (values: string[]) => values.length ? values.map(value => catalogLabel(value, ar)).join(ar ? "، " : ", ") : unknown;
  return <>
    <p><span className="catalog-badge">{catalogLabel(item.funding, ar)}</span><span className="catalog-badge">{catalogLabel(item.freshness, ar)}</span></p>
    {item.freshness !== "CURRENT" && <p className="catalog-warning">{ar ? "قد تكون المعلومات قديمة أو غير متحققة؛ راجع الجهة المانحة قبل الاعتماد عليها." : "Information may be stale or unverified. Confirm it with the provider before relying on it."}</p>}
    <dl>
      <dt>{ar ? "الجهة المانحة" : "Provider"}</dt><dd>{item.provider || unknown}</dd>
      <dt>{ar ? "المستوى" : "Education level"}</dt><dd>{terms(item.education_levels)}</dd>
      {detail && <>
        <dt>{ar ? "التخصصات" : "Disciplines"}</dt><dd>{terms(item.disciplines)}</dd>
        <dt>{ar ? "البلدان" : "Countries"}</dt><dd>{terms(item.countries)}</dd>
        <dt>{ar ? "اللغات" : "Languages"}</dt><dd>{terms(item.languages)}</dd>
      </>}
      <dt>{ar ? "المصدر" : "Source"}</dt><dd className="catalog-source">{source ? <a href={source} target="_blank" rel="noopener noreferrer">{item.source.name}</a> : item.source.name}</dd>
      <dt>{ar ? "فحص المصدر UTC" : "Source checked UTC"}</dt><dd><bdi>{catalogTime(item.source_checked_at, locale)}</bdi></dd>
      <dt>{ar ? "آخر اعتماد UTC" : "Last reviewed UTC"}</dt><dd><bdi>{catalogTime(item.verified_at, locale)}</bdi></dd>
    </dl>
    <h3>{ar ? "المواعيد والجولات" : "Deadlines and rounds"}</h3>
    {item.rounds.length ? <ul className="catalog-list">{item.rounds.map((round, i) => <CatalogRound key={i} round={round} locale={locale} />)}</ul> : <p>{ar ? "الموعد غير معروف" : "Deadline unknown"}</p>}
    {!item.reminder_eligible && <p>{ar ? "لا يوجد موعد مؤكد صالح للتذكيرات. لا يُنشأ تذكير من تاريخ مجهول أو قديم." : "No confirmed deadline is eligible for reminders. An unknown or stale date does not create a reminder."}</p>}
    {detail && <>
      <h2>{ar ? "معايير الجهة المانحة" : "Provider criteria"}</h2>
      {item.criteria.length ? <ul>{item.criteria.map((value, i) => <li key={i}>{value}</li>)}</ul> : <p>{unknown}</p>}
      <h2>{ar ? "المستندات المطلوبة" : "Required documents"}</h2>
      {item.required_documents.length ? <ul>{item.required_documents.map((value, i) => <li key={i}>{value}</li>)}</ul> : <p>{unknown}</p>}
      {submission ? <p><a href={submission} target="_blank" rel="noopener noreferrer">{ar ? "افتح رابط التقديم لدى الجهة المانحة" : "Open the provider’s application page"}</a></p> : <p>{ar ? "رابط تقديم موثوق غير متاح." : "A trusted application link is unavailable."}</p>}
      <p className="catalog-note">{ar ? "هذه معلومات منشورة من المصدر وليست ضمانًا للأهلية أو القبول. التقديم يتم لدى الجهة المانحة." : "This catalog summarizes source information and does not guarantee eligibility or admission. Apply with the provider."}</p>
    </>}
  </>;
}
