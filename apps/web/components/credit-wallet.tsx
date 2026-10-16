"use client";

import { useEffect, useState } from "react";
import { createHealthClient, validateSession, type components } from "@minhaai/contracts";

type Wallet = components["schemas"]["Wallet"];
type CreditEntries = components["schemas"]["CreditEntries"];
type CreditOperations = components["schemas"]["CreditOperations"];
type CreditOperation = components["schemas"]["CreditOperation"];
type CreditService = CreditOperation["service"];
type CreditState = CreditOperation["state"];
type Page<T> = { items: T[]; total: number; page: number; page_size: number };
const client = createHealthClient();
const pageSize = 10;

export function CreditWallet({ locale }: { locale: "ar" | "en" }) {
  const ar = locale === "ar";
  const [access, setAccess] = useState<"loading" | "ready" | "denied" | "unavailable">("loading");
  const [wallet, setWallet] = useState<Wallet | null>(null);
  const [entries, setEntries] = useState<CreditEntries | null>(null);
  const [operations, setOperations] = useState<CreditOperations | null>(null);
  const [entryPage, setEntryPage] = useState(1);
  const [operationPage, setOperationPage] = useState(1);
  const [attempt, setAttempt] = useState(0);
  const count = (value: number) => new Intl.NumberFormat(locale).format(value);
  const credits = (value: number) => `${count(value)} ${ar ? "رصيد استخدام" : "Credits"}`;
  const dateTime = (value: string) => new Intl.DateTimeFormat(locale, {
    dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Hebron",
  }).format(new Date(value));
  const services: Record<CreditService, string> = ar ? {
    MATCHING_AI: "شرح المطابقة بالذكاء الاصطناعي", CV_EXTRACTION: "استخراج بيانات السيرة الذاتية", DOCUMENT_NEW: "إنشاء مستند جديد",
  } : {
    MATCHING_AI: "AI matching explanation", CV_EXTRACTION: "CV extraction", DOCUMENT_NEW: "New document",
  };
  const stateLabels: Record<CreditState, string> = ar ? {
    RESERVED: "محجوزة", RUNNING: "قيد التنفيذ", RECONCILING: "قيد المطابقة والتحقق", SETTLED: "خُصمت مرة واحدة", RELEASED: "حُرّر الحجز",
  } : {
    RESERVED: "Reserved", RUNNING: "Running", RECONCILING: "Reconciling", SETTLED: "Settled once", RELEASED: "Reservation released",
  };
  const stateExplanations: Record<CreditState, string> = ar ? {
    RESERVED: "الرصيد محجوز، ولم يحدث خصم نهائي بعد.",
    RUNNING: "الرصيد محجوز أثناء التنفيذ. لا يعني بدء العملية نجاح المخرج.",
    RECONCILING: "نتيجة العملية غير محسومة. يبقى الحجز حتى التحقق؛ مرور الوقت لا يحرر الرصيد تلقائيًا.",
    SETTLED: "تم اعتماد مخرج صالح ومحفوظ قبل الخصم النهائي.",
    RELEASED: "حُرّر الحجز بعد ثبوت الفشل، من دون خصم نهائي لهذه العملية.",
  } : {
    RESERVED: "Credits are held. No final debit has been posted.",
    RUNNING: "Credits remain held during execution. Starting an operation does not mean its output succeeded.",
    RECONCILING: "The outcome is uncertain. Credits remain held until verified; elapsed time does not automatically release them.",
    SETTLED: "A valid saved output was accepted before the final debit.",
    RELEASED: "The reservation was released after a proven failure, without a final debit for this operation.",
  };

  useEffect(() => {
    const controller = new AbortController();
    function clearPrivate() { setWallet(null); setEntries(null); setOperations(null); }
    void (async () => {
      clearPrivate(); setAccess("loading");
      try {
        const session = await client.GET("/api/v1/session", { signal: controller.signal });
        if (controller.signal.aborted) return;
        if ([401, 403].includes(session.response.status)) { setAccess("denied"); return; }
        if (!session.response.ok || !session.data) throw new Error();
        if (validateSession(session.data).roles[0] !== "STUDENT") { setAccess("denied"); return; }
        const [balance, history, progress] = await Promise.all([
          client.GET("/api/v1/wallet", { signal: controller.signal }),
          client.GET("/api/v1/wallet/entries", { signal: controller.signal, params: { query: { page: entryPage, page_size: pageSize } } }),
          client.GET("/api/v1/operations", { signal: controller.signal, params: { query: { page: operationPage, page_size: pageSize } } }),
        ]);
        if (controller.signal.aborted) return;
        if ([balance, history, progress].some(result => [401, 403].includes(result.response.status))) {
          clearPrivate(); setAccess("denied"); return;
        }
        if (!balance.response.ok || !balance.data || !history.response.ok || !history.data || !progress.response.ok || !progress.data) throw new Error();
        setWallet(balance.data); setEntries(history.data); setOperations(progress.data); setAccess("ready");
      } catch {
        if (!controller.signal.aborted) { clearPrivate(); setAccess("unavailable"); }
      }
    })();
    return () => controller.abort();
  }, [entryPage, operationPage, attempt]);

  function paginate<T>(page: Page<T>, move: (value: number) => void, label: string) {
    return <nav className="credit-pagination" aria-label={label}>
      <button type="button" disabled={page.page <= 1} onClick={() => move(page.page - 1)}>{ar ? "السابق" : "Previous"}</button>
      <span>{ar ? `الصفحة ${count(page.page)} · ${count(page.total)} سجلًا إجمالًا` : `Page ${count(page.page)} · ${count(page.total)} records in total`}</span>
      <button type="button" disabled={page.page * page.page_size >= page.total} onClick={() => move(page.page + 1)}>{ar ? "التالي" : "Next"}</button>
    </nav>;
  }

  return <section className="credit-wallet" aria-label={ar ? "رصيدك وسجل الاستخدام" : "Your Credits and usage history"} aria-busy={access === "loading"}>
    <p className="catalog-note">{ar
      ? "الرصيد وحدات استخدام داخلية، وليس نقودًا. الشراء غير متاح في التجربة. التصفح وفحص الأهلية بالقواعد مجانيان."
      : "Credits are internal usage units, not money. Purchases are unavailable during beta. Browsing and rules-based eligibility are free."}</p>
    {access === "loading" && <p role="status">{ar ? "جارٍ التحقق وتحميل الرصيد…" : "Verifying access and loading your wallet…"}</p>}
    {access === "denied" && <p role="alert">{ar
      ? "يلزم حساب طالب بالغ ومؤكد البريد لعرض رصيدك."
      : "A verified adult student account is required to view your own wallet."} {" "}<a href={`/${locale}/account`}>{ar ? "إدارة الحساب والدخول" : "Sign in or manage your account"}</a></p>}
    {access === "unavailable" && <p role="alert">{ar
      ? "تعذر تحميل الرصيد. لا يمكن استنتاج أن رصيدك صفر أو أن الحجز تحرر. حاول التحديث."
      : "Your wallet could not be loaded. This does not mean your balance is zero or that a hold was released. Try refreshing."}</p>}
    <button type="button" disabled={access === "loading"} onClick={() => setAttempt(value => value + 1)}>{ar ? "تحديث البيانات" : "Refresh data"}</button>
    {access === "ready" && wallet && entries && operations && <>
      <section aria-labelledby="credit-balance-title">
        <h2 id="credit-balance-title">{ar ? "الرصيد الحالي" : "Current balance"}</h2>
        <dl className="credit-balances">
          <div><dt>{ar ? "المتاح للإنفاق" : "Available to spend"}</dt><dd>{credits(wallet.available_balance)}</dd></div>
          <div><dt>{ar ? "المحجوز" : "Reserved"}</dt><dd>{credits(wallet.reserved_balance)}</dd></div>
          <div><dt>{ar ? "صافي الرصيد المثبت" : "Posted balance"}</dt><dd>{credits(wallet.posted_balance)}</dd></div>
        </dl>
        <p>{ar
          ? "المتاح هو صافي الرصيد المثبت ناقص المحجوز. لا تجمعهما كرصيد إضافي؛ الحجز ليس خصمًا نهائيًا."
          : "Available Credits equal the posted balance minus reservations. Do not add these balances together; a reservation is not a final debit."}</p>
        <p>{wallet.signup_grant.awarded && wallet.signup_grant.amount !== null ? (ar
          ? `مُنحت ${credits(wallet.signup_grant.amount)} مرة واحدة بعد تفعيل حسابك المؤهل.`
          : `Your eligible activation received a once-only grant of ${credits(wallet.signup_grant.amount)}.`) : (ar
          ? "لا توجد منحة تفعيل مسجلة في البيانات الحالية."
          : "No activation grant is recorded in the current data.")}
          {wallet.signup_grant.awarded_at && <> {ar ? "وقت المنحة: " : "Granted: "}<time dateTime={wallet.signup_grant.awarded_at}>{dateTime(wallet.signup_grant.awarded_at)}</time>.</>}
        </p>
        <p>{ar
          ? "لا تنتهي صلاحية الرصيد لمجرد مرور الوقت أثناء نشاط الحساب. طلب حذف الحساب يوقف الاستخدام ويجمّد الرصيد وفق سياسة الاستعادة."
          : "Credits do not expire just because time passes while your account is active. Account deletion disables usage and freezes Credits under the recovery policy."}</p>
      </section>

      <section aria-labelledby="credit-limits-title">
        <h2 id="credit-limits-title">{ar ? "حدود الاستخدام اليومي" : "Daily usage limits"}</h2>
        <p className="catalog-warning">{ar
          ? "الحد اليومي سقف إنفاق، وليس تعبئة رصيد. بدء يوم جديد لا يضيف أي رصيد."
          : "The daily limit caps spending; it is not a refill. A new day does not add Credits."}</p>
        <p>{ar ? "اليوم المحاسبي: " : "Accounting day: "}<bdi dir="ltr">{wallet.daily.day} · {wallet.daily.timezone}</bdi></p>
        <dl>
          <dt>{ar ? "حد إنفاقك اليومي" : "Your daily spending cap"}</dt><dd>{credits(wallet.daily.cap)}</dd>
          <dt>{ar ? "خُصم لهذا اليوم" : "Settled for this day"}</dt><dd>{credits(wallet.daily.spent)}</dd>
          <dt>{ar ? "محجوز لهذا اليوم" : "Reserved for this day"}</dt><dd>{credits(wallet.daily.reserved)}</dd>
          <dt>{ar ? "المتبقي ضمن الحد اليومي" : "Remaining daily allowance"}</dt><dd>{credits(wallet.daily.remaining)}</dd>
          <dt>{ar ? "عمليات الذكاء الاصطناعي المقبولة عالميًا" : "Global AI operations admitted"}</dt>
          <dd>{count(wallet.global_daily.admitted_operations)} / {count(wallet.global_daily.cap)} · {ar ? "المتبقي" : "remaining"}: {count(wallet.global_daily.remaining)}</dd>
        </dl>
        <p>{ar ? "فترة الحد العالمي: " : "Global limit period: "}<bdi dir="ltr">{wallet.global_daily.day} · {wallet.global_daily.timezone}</bdi></p>
        <p>{ar
          ? "الحجوزات تحتسب ضمن السقف لمنع تجاوزه بطلبات متزامنة. تحرر الحجز المثبت لا يمنح رصيدًا جديدًا. الحد العالمي ليس ضمانًا لتوافر الذكاء الاصطناعي."
          : "Reservations count toward the cap to prevent concurrent requests from exceeding it. A confirmed release does not grant new Credits. The global cap does not guarantee AI availability."}</p>
      </section>

      <section aria-labelledby="credit-policy-title">
        <h2 id="credit-policy-title">{ar ? "السياسة والأسعار الداخلية الحالية" : "Current policy and internal prices"}</h2>
        <p>{ar ? "إصدار السياسة: " : "Policy version: "}{count(wallet.policy.version)}. {ar
          ? "تسري تغييرات الأسعار على العمليات الجديدة؛ تحتفظ العملية السابقة بسعرها وإصدارها المسجلين."
          : "Price changes apply to new operations; earlier operations retain their captured price and version."}</p>
        <dl>
          {(Object.keys(services) as CreditService[]).map(service => <div className="credit-description-row" key={service}><dt>{services[service]}</dt><dd>{credits(wallet.policy.prices[service])}</dd></div>)}
          <div className="credit-description-row"><dt>{ar ? "منحة التفعيل للطلاب الجدد" : "Activation grant for new students"}</dt><dd>{credits(wallet.policy.signup_grant)} · {ar ? "مرة واحدة" : "once only"}</dd></div>
        </dl>
        <p>{ar
          ? "مجاني: التصفح والفلاتر، فحص الأهلية بالقواعد، التحرير اليدوي، إعادة تصدير نسخة المستند نفسها، وإضافة المتصفح. ذكر هذه الخدمات لا يعني تفعيل جميعها حاليًا."
          : "Free: browsing and filters, rules-based eligibility, manual edits, re-exporting the same document version, and the browser extension. Listing a service does not mean it is currently available."}</p>
        <p className="catalog-note">{ar
          ? "تنفيذ خدمات الذكاء الاصطناعي غير متاح حاليًا. عرض السعر لا يبدأ عملية ولا يحجز رصيدًا."
          : "AI service execution is currently unavailable. Viewing these prices does not start an operation or reserve Credits."}</p>
      </section>

      <section aria-labelledby="credit-operations-title">
        <h2 id="credit-operations-title">{ar ? "حالة العمليات" : "Operation status"}</h2>
        <p>{ar
          ? `علامة متابعة الحجز بعد ${count(wallet.policy.reserve_minutes)} دقيقة. هدف التحقق والمطابقة ${count(wallet.policy.reconciliation_target_hours)} ساعة؛ ليس ضمانًا ولا إذنًا لخصم أو تحرير تلقائي.`
          : `Reservation follow-up marker: ${count(wallet.policy.reserve_minutes)} minutes. Reconciliation target: ${count(wallet.policy.reconciliation_target_hours)} hours; this is not a guarantee or permission for an automatic debit or release.`}</p>
        {operations.total === 0 ? <p>{ar ? "لا توجد عمليات مسجلة. لا يبدأ عرض هذه الصفحة أي عملية." : "No operations are recorded. Viewing this page does not start one."}</p>
          : <ol className="credit-history">{operations.items.map(operation => <li key={operation.id}><article>
            <h3>{services[operation.service]} · <span className="catalog-badge">{stateLabels[operation.state]}</span></h3>
            <p>{stateExplanations[operation.state]}</p>
            {operation.resolution_overdue && <p className="catalog-warning">{ar
              ? "تجاوزت العملية هدف المتابعة. لا يعني ذلك ثبوت الفشل أو تحرير الحجز."
              : "This operation is past its review target. This does not prove failure or release the reservation."}</p>}
            <dl>
              <dt>{ar ? "معرّف العملية" : "Operation ID"}</dt><dd><bdi dir="ltr">{operation.id}</bdi></dd>
              <dt>{ar ? "السعر المسجل" : "Captured price"}</dt><dd>{credits(operation.price)}</dd>
              <dt>{ar ? "إصدار السياسة" : "Policy version"}</dt><dd>{count(operation.policy_version)}</dd>
              <dt>{ar ? "اليوم المحاسبي المسجل" : "Captured accounting day"}</dt><dd><bdi dir="ltr">{operation.captured_day}</bdi></dd>
              <dt>{ar ? "تاريخ الإنشاء" : "Created"}</dt><dd><time dateTime={operation.created_at}>{dateTime(operation.created_at)}</time></dd>
              <dt>{ar ? "علامة متابعة الحجز" : "Reservation follow-up marker"}</dt><dd><time dateTime={operation.reserve_until}>{dateTime(operation.reserve_until)}</time></dd>
              {operation.reconciliation_started_at && <><dt>{ar ? "بدء المطابقة" : "Reconciliation started"}</dt><dd><time dateTime={operation.reconciliation_started_at}>{dateTime(operation.reconciliation_started_at)}</time></dd></>}
              {operation.resolution_due_at && <><dt>{ar ? "هدف المتابعة" : "Review target"}</dt><dd><time dateTime={operation.resolution_due_at}>{dateTime(operation.resolution_due_at)}</time></dd></>}
            </dl>
          </article></li>)}</ol>}
        {operations.total > 0 && paginate(operations, setOperationPage, ar ? "صفحات العمليات" : "Operation pages")}
      </section>

      <section aria-labelledby="credit-ledger-title">
        <h2 id="credit-ledger-title">{ar ? "سجل الحركات المثبتة" : "Posted ledger history"}</h2>
        <p>{ar ? "يحتوي السجل على المنحة والخصم النهائي؛ تظل الحجوزات ضمن حالات العمليات أعلاه. الأوقات بتوقيت Asia/Hebron." : "The ledger records the grant and final debits; reservations appear in operation status above. All times use Asia/Hebron."}</p>
        {entries.total === 0 ? <p>{ar ? "لا توجد حركات مثبتة في السجل. لا يُستنتج من ذلك عدم وجود حجوزات." : "No ledger entries are posted. This does not imply that no reservations exist."}</p>
          : <ol className="credit-history">{entries.items.map(entry => <li key={entry.id}><article>
            <h3>{entry.kind === "SIGNUP_GRANT" ? (ar ? "منحة التفعيل مرة واحدة" : "Once-only activation grant") : (ar ? "خصم بعد اعتماد مخرج محفوظ" : "Debit after accepting saved output")}</h3>
            <p className="credit-amount"><bdi dir="ltr">{new Intl.NumberFormat(locale, { signDisplay: "always" }).format(entry.amount)}</bdi> {ar ? "رصيد استخدام" : "Credits"}</p>
            <dl>
              <dt>{ar ? "معرّف الحركة" : "Entry ID"}</dt><dd><bdi dir="ltr">{entry.id}</bdi></dd>
              <dt>{ar ? "التاريخ" : "Date"}</dt><dd><time dateTime={entry.created_at}>{dateTime(entry.created_at)}</time></dd>
              <dt>{ar ? "إصدار السياسة" : "Policy version"}</dt><dd>{count(entry.policy_version)}</dd>
              {entry.operation_id && <><dt>{ar ? "معرّف العملية المرتبطة" : "Linked operation ID"}</dt><dd><bdi dir="ltr">{entry.operation_id}</bdi></dd></>}
            </dl>
          </article></li>)}</ol>}
        {entries.total > 0 && paginate(entries, setEntryPage, ar ? "صفحات سجل الحركات" : "Ledger pages")}
      </section>
    </>}
  </section>;
}
