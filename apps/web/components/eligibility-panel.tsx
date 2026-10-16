"use client";

import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import { createHealthClient, getCsrf, validateSession, type components } from "@minhaai/contracts";
import type { PublicScholarship } from "./catalog-types";

type Field = components["schemas"]["EligibilityProfileFieldEnum"];
type Degree = components["schemas"]["EducationLevelEnum"];
type Qualification = components["schemas"]["QualificationEnum"];
type Scale = components["schemas"]["ScaleEnum"];
type LanguageLevel = components["schemas"]["LevelEnum"];
type Profile = components["schemas"]["ProfileFactsOutput"];
type ProfileView = components["schemas"]["Profile"];
type Evaluation = components["schemas"]["Evaluation"];
type Draft = {
  nationalities: string; residency_country: string; degree_level: Degree | ""; major: string;
  qualification: Qualification | ""; gpa_value: string; gpa_scale: Scale;
  languages: { language: string; level: LanguageLevel | "" }[]; preferred_countries: string;
  knownEmpty: Field[];
};
const initialDraft: Draft = {
  nationalities: "", residency_country: "", degree_level: "", major: "", qualification: "",
  gpa_value: "", gpa_scale: "UNKNOWN", languages: [{ language: "", level: "" }], preferred_countries: "", knownEmpty: [],
};
const client = createHealthClient();

function toDraft(profile: Profile): Draft {
  return {
    nationalities: profile.nationalities?.join(", ") ?? "", residency_country: profile.residency_country ?? "",
    degree_level: profile.degree_level ?? "", major: profile.major ?? "", qualification: profile.qualification ?? "",
    gpa_value: profile.gpa?.value ?? "", gpa_scale: profile.gpa?.scale ?? "UNKNOWN",
    languages: profile.languages?.length ? profile.languages.map(item => ({ ...item, level: item.level ?? "" })) : [{ language: "", level: "" }],
    preferred_countries: profile.preferred_countries?.join(", ") ?? "",
    knownEmpty: (["nationalities", "languages", "preferred_countries"] as const).filter(field => profile[field]?.length === 0),
  };
}

function countries(value: string): string[] | null {
  if (!value.trim()) return null;
  const items = value.split(/[,،]/).map(item => item.trim().toUpperCase());
  if (items.some(item => !/^[A-Z]{2}$/.test(item))) throw new Error("COUNTRY_CODES");
  return [...new Set(items)];
}

function profileInput(draft: Draft, confirmed: Field[]): Profile {
  const residence = draft.residency_country.trim().toUpperCase();
  if (residence && !/^[A-Z]{2}$/.test(residence)) throw new Error("RESIDENCY_COUNTRY");
  const value = draft.gpa_value.trim().replace(/[٠-٩۰-۹]/g, digit => String("٠١٢٣٤٥٦٧٨٩".includes(digit)
    ? "٠١٢٣٤٥٦٧٨٩".indexOf(digit) : "۰۱۲۳۴۵۶۷۸۹".indexOf(digit))).replace(/٫/g, ".");
  if (value && (!/^\d+(?:\.\d+)?$/.test(value) || !Number.isFinite(Number(value)))) throw new Error("GPA_VALUE");
  const languages = draft.languages.filter(item => item.language.trim()).map(item => {
    if (!/^[a-z]{2}(?:-[a-z]{2})?$/i.test(item.language.trim())) throw new Error("LANGUAGE_CODES");
    const [language, region] = item.language.trim().split("-");
    return { language: region ? `${language.toLowerCase()}-${region.toUpperCase()}` : language.toLowerCase(), level: item.level || null };
  });
  if (languages.some(item => !/^[a-z]{2}(?:-[A-Z]{2})?$/.test(item.language))) throw new Error("LANGUAGE_CODES");
  const profile: Profile = {
    nationalities: draft.knownEmpty.includes("nationalities") ? [] : countries(draft.nationalities), residency_country: residence || null,
    degree_level: draft.degree_level || null, major: draft.major.trim() || null, qualification: draft.qualification || null,
    gpa: value ? { value, scale: draft.gpa_scale } : null, languages: draft.knownEmpty.includes("languages") ? [] : languages.length ? languages : null,
    preferred_countries: draft.knownEmpty.includes("preferred_countries") ? [] : countries(draft.preferred_countries), confirmed_fields: [],
  };
  profile.confirmed_fields = confirmed.filter(field => profile[field] !== null);
  return profile;
}

export function EligibilityPanel({ locale }: { locale: "ar" | "en" }) {
  const ar = locale === "ar";
  const [access, setAccess] = useState<"loading" | "ready" | "denied" | "unavailable">("loading");
  const [view, setView] = useState<ProfileView | null>(null);
  const [etag, setEtag] = useState("");
  const [draft, setDraft] = useState<Draft>(initialDraft);
  const [confirmed, setConfirmed] = useState<Field[]>([]);
  const [dirty, setDirty] = useState(false);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const [scholarships, setScholarships] = useState<PublicScholarship[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [selection, setSelection] = useState("");
  const [evaluation, setEvaluation] = useState<Evaluation | null>(null);
  const pageSize = 20;
  const labels: Record<Field, string> = ar ? {
    nationalities: "الجنسيات", residency_country: "بلد الإقامة", degree_level: "المستوى الدراسي المطلوب",
    major: "التخصص", qualification: "المؤهل المكتمل", gpa: "المعدل وسلمه", languages: "اللغات ومستوياتها", preferred_countries: "بلدان الدراسة المفضلة",
  } : {
    nationalities: "Nationalities", residency_country: "Country of residence", degree_level: "Desired degree level",
    major: "Major", qualification: "Completed qualification", gpa: "GPA and scale", languages: "Languages and levels", preferred_countries: "Preferred study countries",
  };
  const choiceLabels: Record<string, string> = ar ? {
    BACHELOR: "بكالوريوس", MASTER: "ماجستير", PHD: "دكتوراه", SECONDARY: "ثانوية", DIPLOMA: "دبلوم", OTHER: "آخر",
    PERCENT_100: "من 100", GPA_4_0: "من 4", GPA_5_0: "من 5", UNKNOWN: "سلم غير معروف",
    ELIGIBLE: "مستوفٍ للشروط المراجعة", INELIGIBLE: "غير مستوفٍ لشرط ملزم", INSUFFICIENT_INFORMATION: "معلومات غير كافية",
    PASS: "مستوفى", FAIL: "غير مستوفى", ACADEMIC: "أكاديمي", FIELD: "التخصص", NATIONALITY_RESIDENCY: "الجنسية والإقامة", LANGUAGE: "اللغة", INTEREST: "الاهتمامات",
  } : {
    BACHELOR: "Bachelor's", MASTER: "Master's", PHD: "PhD", SECONDARY: "Secondary school", DIPLOMA: "Diploma", OTHER: "Other",
    PERCENT_100: "Out of 100", GPA_4_0: "Out of 4", GPA_5_0: "Out of 5", UNKNOWN: "Unknown scale",
    ELIGIBLE: "Eligible for the reviewed rules", INELIGIBLE: "Ineligible: a mandatory condition failed", INSUFFICIENT_INFORMATION: "Insufficient information",
    PASS: "Pass", FAIL: "Fail", ACADEMIC: "Academic", FIELD: "Field", NATIONALITY_RESIDENCY: "Nationality and residency", LANGUAGE: "Language", INTEREST: "Interest",
  };
  const unknown = ar ? "غير مُدخل / غير معروف" : "Not provided / unknown";
  const percent = (basisPoints: number) => new Intl.NumberFormat(locale, { style: "percent", maximumFractionDigits: 2 }).format(basisPoints / 10000);

  function explanation(code: string) {
    const messages: Record<string, [string, string]> = {
      REQUIREMENT_UNKNOWN: ["المعلومة المطلوبة في شرط المنحة غير كافية للحسم.", "The scholarship requirement has insufficient information for a decision."],
      REQUIREMENT_UNVERIFIED: ["هذا الشرط لم يُراجع ويُعتمد، لذلك لا يُعد مستوفى.", "This requirement has not been reviewed and approved, so it cannot count as satisfied."],
      PROFILE_UNKNOWN: ["لم تُدخل المعلومة اللازمة في ملفك.", "Your profile does not provide the required fact."],
      PROFILE_UNCONFIRMED: ["تحتاج هذه المعلومة إلى مراجعتك وتأكيدك قبل استخدامها.", "This fact needs your review and confirmation before it can be used."],
      GPA_SCALE_UNKNOWN: ["سلم معدل الطالب أو شرط المعدل غير معروف؛ لا نخمن السلم.", "The student's or requirement's GPA scale is unknown; no scale is guessed."],
      GPA_SCALE_MISMATCH: ["السلمان مختلفان، ولا توجد معادلة تكافؤ معتمدة بينهما.", "The GPA scales differ and no approved equivalence is available."],
      GPA_VALUE_INVALID: ["قيمة المعدل غير صالحة ضمن سلمها المحدد.", "The GPA value is invalid for its declared scale."],
      GPA_MEETS_MINIMUM: ["المعدل المُدخل يستوفي الحد الأدنى على السلم نفسه.", "The reported GPA meets the minimum on the same scale."],
      GPA_BELOW_MINIMUM: ["المعدل المُدخل أقل من الحد الأدنى على السلم نفسه.", "The reported GPA is below the minimum on the same scale."],
      LANGUAGE_NOT_DECLARED: ["اللغة المطلوبة غير موجودة في قائمة اللغات التي أكدت اكتمالها.", "The required language is absent from the language list you confirmed as complete."],
      LANGUAGE_LEVEL_UNKNOWN: ["مستوى اللغة المطلوبة غير مُدخل أو غير معروف.", "The required language's level is missing or unknown."],
      LANGUAGE_MEETS_MINIMUM: ["مستوى اللغة المُدخل يستوفي الحد الأدنى المحدد.", "The reported language level meets the specified minimum."],
      LANGUAGE_BELOW_MINIMUM: ["مستوى اللغة المُدخل أقل من الحد الأدنى المحدد.", "The reported language level is below the specified minimum."],
      MATCH: ["تتوافق إفادتك المؤكدة مع القيم المقبولة في الشرط المراجع.", "Your confirmed self-report matches the accepted values in the reviewed requirement."],
      NO_MATCH: ["لا تتوافق إفادتك المؤكدة مع القيم المقبولة في الشرط المراجع.", "Your confirmed self-report does not match the accepted values in the reviewed requirement."],
      UNSUPPORTED_RULE: ["لا يستطيع محرك القواعد الحالي حسم هذا النوع من الشروط.", "The current rule engine cannot determine this type of requirement."],
      FIT_IS_NOT_ADMISSION_PROBABILITY: ["الملاءمة ليست احتمال قبول أو ضمانًا له.", "Fit is not an acceptance probability or guarantee."],
      STUDENT_CONFIRMED_IS_SELF_REPORTED: ["الحقائق التي أكدها الطالب إفادة ذاتية وليست مؤهلات متحققًا منها مستقلًا.", "Student-confirmed facts are self-reported, not independently verified credentials."],
      WEIGHTS_UNCALIBRATED: ["هذه الأوزان أولية وتحتاج معايرة ميدانية.", "These initial weights require field calibration."],
      NO_CROSS_SCALE_GPA_EQUIVALENCE: ["لا يفترض الفحص تكافؤ معدلات من سلالم مختلفة.", "The check does not assume equivalence between different GPA scales."],
      INSUFFICIENT_VERIFIED_COVERAGE: ["تغطية الأدلة أقل من الحد المطلوب لعرض درجة ملاءمة.", "Evidence coverage is below the threshold required to show a fit score."],
      SOURCE_STALE: ["معلومات المصدر قديمة وتحتاج إعادة تحقق؛ لا تُعد شروطها مستوفاة تلقائيًا.", "The source information is stale and needs reverification; its requirements do not count as automatically satisfied."],
      SOURCE_UNKNOWN: ["حداثة معلومات المصدر غير معروفة؛ راجع الجهة الرسمية لإعادة التحقق.", "The source information's freshness is unknown; check the official provider for reverification."],
      VERIFIED_RULES_AND_CONFIRMED_DECLARATIONS: ["شروط مراجعة وإفادات أكدها الطالب متاحة لهذا المجال.", "Reviewed requirements and student-confirmed declarations are available for this domain."],
      NO_RULE_EVIDENCE: ["لا يوجد شرط مراجع لهذا المجال؛ لا نفترضه مستوفى.", "This domain has no reviewed requirement; it is not assumed satisfied."],
      UNRESOLVED_RULE_EVIDENCE: ["بعض أدلة هذا المجال غير محسومة؛ لا تدخل في التغطية.", "Some evidence in this domain remains unresolved and does not count toward coverage."],
    };
    return messages[code]?.[ar ? 0 : 1] ?? (ar ? "راجع الأدلة والمعلومات المطلوبة؛ لا توجد معلومات كافية لتفسير إضافي معتمد." : "Review the evidence and required facts; no further verified explanation is available.");
  }

  function clearPrivate() {
    setView(null); setDraft(initialDraft); setConfirmed([]); setEvaluation(null); setEtag(""); setDirty(false);
    setScholarships([]); setSelection(""); setTotal(0); setPage(1);
  }

  function errorMessage(code: string) {
    const messages: Record<string, [string, string]> = {
      COUNTRY_CODES: ["استخدم رموز بلدان من حرفين، وافصل المتعدد بفاصلة، مثل PS, JO.", "Use two-letter country codes, separated by commas for multiple countries, such as PS, JO."],
      RESIDENCY_COUNTRY: ["أدخل رمز بلد إقامة واحدًا فقط من حرفين، أو اتركه غير معروف.", "Enter exactly one two-letter residence country code, or leave it unknown."],
      LANGUAGE_CODES: ["أدخل رمز لغة من حرفين، مثل ar أو en، مع منطقة اختيارية مثل en-US.", "Enter a two-letter language code, such as ar or en, with an optional region such as en-US."],
      GPA_VALUE: ["أدخل معدلًا رقميًا صالحًا، أو اتركه غير مُدخل. لا نحول السلم تلقائيًا.", "Enter a valid numeric GPA, or leave it unknown. Scales are never converted automatically."],
      PROFILE_CHANGED: ["تغير إصدار ملفك. أعد تحميله وراجع بياناتك قبل الحفظ أو الفحص.", "Your profile version changed. Reload and review it before saving or checking."],
      STALE_REVISION: ["تغير إصدار الملف. أعد تحميله قبل الحفظ، ثم راجع تأكيداتك.", "The profile revision changed. Reload before saving, then review your confirmations."],
      CATALOG_VERSION_UNAVAILABLE: ["نسخة المنحة لم تعد متاحة للفحص. أعد تحميل الصفحة واختر منحة منشورة حاليًا.", "The scholarship version is no longer available for checking. Reload and select a currently published scholarship."],
      EVALUATION_STALE: ["تغيرت أدلة الفحص. أعد تحميل الملف والمنحة وأجرِ فحصًا جديدًا.", "The evidence changed. Reload the profile and scholarship and run a new check."],
      RATE_LIMITED: ["طلبات كثيرة. حاول لاحقًا.", "Too many requests. Try later."],
    };
    return messages[code]?.[ar ? 0 : 1] ?? (ar ? "تعذر إتمام الطلب. تحقق من المدخلات وحاول مجددًا. لم تُستنتج بيانات ناقصة." : "The request could not be completed. Check your inputs and try again. Missing facts have not been inferred.");
  }

  useEffect(() => {
    const controller = new AbortController();
    void (async () => {
      try {
        const session = await client.GET("/api/v1/session", { signal: controller.signal });
        if (controller.signal.aborted) return;
        if (!session.response.ok || !session.data || validateSession(session.data).roles[0] !== "STUDENT") {
          clearPrivate(); setAccess("denied"); return;
        }
        const profile = await client.GET("/api/v1/profile", { signal: controller.signal });
        if (controller.signal.aborted) return;
        if ([401, 403].includes(profile.response.status)) { clearPrivate(); setAccess("denied"); return; }
        if (!profile.response.ok || !profile.data || !profile.response.headers.get("ETag")) throw new Error();
        setView(profile.data); setEtag(profile.response.headers.get("ETag")!);
        setDraft(toDraft(profile.data.profile)); setConfirmed(profile.data.profile.confirmed_fields); setDirty(false); setAccess("ready");
      } catch {
        if (!controller.signal.aborted) { clearPrivate(); setAccess("unavailable"); }
      }
    })();
    return () => controller.abort();
  }, [attempt]);

  useEffect(() => {
    if (access !== "ready") return;
    const controller = new AbortController();
    void client.GET("/api/v1/scholarships", { signal: controller.signal, params: { query: { page, page_size: pageSize, sort: "recent", mode: "TEXT" } } }).then(response => {
      if (controller.signal.aborted) return;
      if (!response.response.ok || !response.data) throw new Error();
      setScholarships(response.data.items); setTotal(response.data.total);
    }).catch(() => {
      if (!controller.signal.aborted) { setScholarships([]); setFailed(true); setMessage(ar ? "تعذر تحميل المنح؛ أعد تحميل الصفحة للمحاولة مجددًا." : "Scholarships could not be loaded. Reload the page to try again."); }
    });
    return () => controller.abort();
  }, [access, page, ar]);

  function edit(field: Field, changes: Partial<Draft>) {
    setDraft(current => ({ ...current, knownEmpty: current.knownEmpty.filter(item => item !== field), ...changes })); setConfirmed(current => current.filter(item => item !== field));
    setDirty(true); setEvaluation(null); setMessage("");
  }

  function hasValue(field: Field) {
    if (draft.knownEmpty.includes(field)) return true;
    if (field === "gpa") return Boolean(draft.gpa_value.trim());
    if (field === "languages") return draft.languages.some(item => item.language.trim());
    return Boolean(draft[field].trim());
  }

  function fieldset(field: Field, children: ReactNode) {
    const list = ["nationalities", "languages", "preferred_countries"].includes(field);
    return <fieldset><legend>{labels[field]}</legend>
      {list && <label className="confirm"><input type="checkbox" checked={draft.knownEmpty.includes(field)} disabled={busy} onChange={event => {
        const blanks: Partial<Draft> = field === "languages" ? { languages: [{ language: "", level: "" }] } : { [field]: "" };
        edit(field, { ...blanks, knownEmpty: event.target.checked ? [...draft.knownEmpty.filter(item => item !== field), field] : draft.knownEmpty.filter(item => item !== field) });
      }} />{ar ? "أصرّح صراحة بأن هذه القائمة لا تحتوي أي عناصر" : "I explicitly declare that this list has no entries"}</label>}
      {draft.knownEmpty.includes(field) ? <p>{ar ? "قائمة فارغة مُصرّح بها؛ تختلف عن معلومة غير معروفة. أزل الاختيار لإدخال عناصر أو العودة إلى غير معروف." : "An explicitly empty list is different from unknown. Clear this option to add entries or return to unknown."}</p> : children}
      <label className="confirm"><input type="checkbox" checked={confirmed.includes(field)} disabled={busy || !hasValue(field)}
        onChange={event => { setConfirmed(current => event.target.checked ? [...current.filter(item => item !== field), field] : current.filter(item => item !== field)); setDirty(true); setEvaluation(null); }} />
        {list ? (ar ? "راجعت وأؤكد أن هذه القائمة كاملة حسب إفادتي" : "I reviewed and confirm this is my complete self-reported list")
          : (ar ? "راجعت هذا الحقل وأؤكد أنه إفادتي" : "I reviewed this field and confirm it as my self-report")}</label>
      {!hasValue(field) && <p className="eligibility-unknown">{unknown}</p>}
    </fieldset>;
  }

  async function run(action: () => Promise<void>) {
    setBusy(true); setFailed(false); setMessage("");
    try { await action(); }
    catch (error) { setFailed(true); setMessage(errorMessage(error instanceof Error ? error.message : "")); }
    finally { setBusy(false); }
  }

  function checkAccess(response: Response) {
    if ([401, 403].includes(response.status)) { clearPrivate(); setAccess("denied"); throw new Error("ACCESS_DENIED"); }
  }

  async function save(event: FormEvent) {
    event.preventDefault();
    await run(async () => {
      const body = profileInput(draft, confirmed);
      const response = await client.PUT("/api/v1/profile", { body, params: { header: {
        "X-CSRFToken": await getCsrf(client), "Idempotency-Key": crypto.randomUUID(), "If-Match": etag,
      } } });
      checkAccess(response.response);
      if (!response.response.ok || !response.data) throw new Error(response.error?.code);
      const nextEtag = response.response.headers.get("ETag");
      if (!nextEtag) throw new Error();
      setView(response.data); setEtag(nextEtag); setDraft(toDraft(response.data.profile)); setConfirmed(response.data.profile.confirmed_fields);
      setDirty(false); setEvaluation(null); setMessage(ar ? "حُفظ إصدار جديد. التأكيد إفادتك، وليس تحققًا مستقلًا من المؤهلات." : "New version saved. Confirmation is your self-report, not independent credential verification.");
    });
  }

  async function evaluate(event: FormEvent) {
    event.preventDefault(); setEvaluation(null);
    await run(async () => {
      const scholarship = scholarships.find(item => item.id === selection);
      if (!view?.version_id || !scholarship || dirty) throw new Error();
      const response = await client.POST("/api/v1/eligibility/evaluations", { body: {
        profile_version_id: view.version_id, scholarship_id: scholarship.id, scholarship_version_id: scholarship.version_id,
      }, params: { header: { "X-CSRFToken": await getCsrf(client), "Idempotency-Key": crypto.randomUUID() } } });
      checkAccess(response.response);
      if (!response.response.ok || !response.data) throw new Error(response.error?.code);
      setEvaluation(response.data); setMessage(ar ? "اكتمل فحص الشروط. راجع الأدلة والقيود أدناه." : "Rule check completed. Review the evidence and limitations below.");
    });
  }

  function reload() { clearPrivate(); setAccess("loading"); setMessage(""); setAttempt(value => value + 1); }

  return <section className="eligibility" aria-busy={access === "loading" || busy}>
    <p>{ar ? "احفظ الحقائق التي تعرفها فقط. الحقول الفارغة تبقى غير معروفة؛ ولا يعني نقص المعلومات رفضك أو استيفاءك للشروط." : "Save only facts you know. Blank fields stay unknown; missing information means neither failure nor satisfaction of a condition."}</p>
    {access === "loading" && <p role="status">{ar ? "جارٍ التحقق من الوصول…" : "Checking access…"}</p>}
    {access === "denied" && <p className="catalog-warning">{ar ? "هذه الميزة لحساب طالب مؤكد البريد وبالغ. سجّل الدخول أو أكمل التحقق أولًا." : "This feature requires a verified adult student account. Sign in or complete verification first."} <a href={`/${locale}/account`}>{ar ? "الحساب والتحقق" : "Account and verification"}</a></p>}
    {access === "unavailable" && <p role="alert">{ar ? "تعذر تحميل ملفك. حاول مجددًا." : "Your profile could not be loaded. Try again."}</p>}
    {access !== "loading" && <button type="button" disabled={busy} onClick={reload}>{ar ? "إعادة تحميل الملف والمنح" : "Reload profile and scholarships"}</button>}
    {access === "ready" && view && <>
      <p className="catalog-note">{ar ? "هذا إدخال يدوي خاص بك. مراجعتك تؤكد إفادتك فقط؛ ليست تحققًا من مستنداتك. يبقى كل حقل غير مؤكد مجهولًا في الفحص. لا تُرسل بياناتك إلى مزود ذكاء اصطناعي لهذا الفحص." : "This is your private manual profile. Your review confirms a self-report, not document verification. Unconfirmed fields stay unknown in the check. This check does not send your data to an AI provider."}</p>
      <form onSubmit={save}>
        <h2>{ar ? "ملفك الأكاديمي" : "Your academic profile"}</h2>
        <p>{ar ? "الإصدار الحالي: " : "Current revision: "}{view.revision}. {ar ? "أدخل رموز البلدان واللغات من حرفين، وفق ما تعرفه. يمكن تحديد منطقة للغة مثل en-US. اترك غير المعروف فارغًا." : "Enter two-letter country and language codes you know. Language regions such as en-US are supported. Leave unknown facts blank."}</p>
        <div className="eligibility-fields">
          {fieldset("nationalities", <label>{ar ? "رموز الجنسيات، مفصولة بفاصلة" : "Nationality codes, separated by commas"}<input value={draft.nationalities} placeholder="PS, JO" maxLength={100} disabled={busy} onChange={event => edit("nationalities", { nationalities: event.target.value })} /></label>)}
          {fieldset("residency_country", <label>{ar ? "رمز بلد الإقامة" : "Residence country code"}<input value={draft.residency_country} placeholder="PS" maxLength={2} disabled={busy} onChange={event => edit("residency_country", { residency_country: event.target.value })} /></label>)}
          {fieldset("degree_level", <label>{labels.degree_level}<select value={draft.degree_level} disabled={busy} onChange={event => edit("degree_level", { degree_level: event.target.value as Draft["degree_level"] })}>
            <option value="">{unknown}</option>{(["BACHELOR", "MASTER", "PHD"] as Degree[]).map(value => <option key={value} value={value}>{choiceLabels[value]}</option>)}
          </select></label>)}
          {fieldset("major", <label>{labels.major}<input value={draft.major} maxLength={120} disabled={busy} onChange={event => edit("major", { major: event.target.value })} /></label>)}
          {fieldset("qualification", <label>{labels.qualification}<select value={draft.qualification} disabled={busy} onChange={event => edit("qualification", { qualification: event.target.value as Draft["qualification"] })}>
            <option value="">{unknown}</option>{(["SECONDARY", "DIPLOMA", "BACHELOR", "MASTER", "PHD", "OTHER"] as Qualification[]).map(value => <option key={value} value={value}>{choiceLabels[value]}</option>)}
          </select></label>)}
          {fieldset("gpa", <><label>{ar ? "المعدل كما في إفادتك" : "GPA as reported"}<input inputMode="decimal" value={draft.gpa_value} maxLength={12} disabled={busy} onChange={event => edit("gpa", { gpa_value: event.target.value })} /></label>
            <label>{ar ? "سلم المعدل" : "GPA scale"}<select value={draft.gpa_scale} disabled={busy} onChange={event => edit("gpa", { gpa_scale: event.target.value as Scale })}>
              {(["UNKNOWN", "PERCENT_100", "GPA_4_0", "GPA_5_0"] as Scale[]).map(value => <option key={value} value={value}>{choiceLabels[value]}</option>)}
            </select></label><p>{ar ? "لا نحول بين السلالم. السلم غير المعروف أو المختلف عن الشرط لا يكفي للمقارنة." : "Scales are not converted. An unknown scale, or one different from the requirement, cannot support a comparison."}</p></>)}
          {fieldset("languages", <>{draft.languages.map((item, index) => <div key={index} className="eligibility-language">
            <label>{ar ? `رمز اللغة ${index + 1}` : `Language code ${index + 1}`}<input value={item.language} placeholder="en" maxLength={5} disabled={busy} onChange={event => edit("languages", { languages: draft.languages.map((language, position) => position === index ? { ...language, language: event.target.value } : language) })} /></label>
            <label>{ar ? "المستوى حسب CEFR" : "CEFR level"}<select value={item.level} disabled={busy} onChange={event => edit("languages", { languages: draft.languages.map((language, position) => position === index ? { ...language, level: event.target.value as LanguageLevel | "" } : language) })}>
              <option value="">{unknown}</option>{["A1", "A2", "B1", "B2", "C1", "C2"].map(value => <option key={value}>{value}</option>)}
            </select></label>
            {draft.languages.length > 1 && <button type="button" disabled={busy} onClick={() => edit("languages", { languages: draft.languages.filter((_, position) => position !== index) })}>{ar ? `إزالة اللغة ${index + 1}` : `Remove language ${index + 1}`}</button>}
          </div>)}<button type="button" disabled={busy || draft.languages.length >= 10} onClick={() => edit("languages", { languages: [...draft.languages, { language: "", level: "" }] })}>{ar ? "إضافة لغة" : "Add language"}</button>
          <p>{ar ? "المستوى إفادة ذاتية، ولا يمثل شهادة لغة معتمدة." : "The level is self-reported and does not represent a verified language certificate."}</p></>)}
          {fieldset("preferred_countries", <label>{ar ? "رموز بلدان الدراسة، مفصولة بفاصلة" : "Study country codes, separated by commas"}<input value={draft.preferred_countries} placeholder="DE, FR" maxLength={150} disabled={busy} onChange={event => edit("preferred_countries", { preferred_countries: event.target.value })} /></label>)}
        </div>
        <button type="submit" disabled={busy}>{busy ? (ar ? "جارٍ الحفظ أو الفحص…" : "Saving or checking…") : (ar ? "حفظ إصدار الملف" : "Save profile version")}</button>
      </form>
      <form onSubmit={evaluate}>
        <h2>{ar ? "فحص شروط منحة" : "Check scholarship requirements"}</h2>
        <p>{ar ? "الفحص حتمي ومستقل عن أي درجة ملاءمة. فشل شرط ملزم يبقي النتيجة غير مستوفاة، مهما ارتفعت الدرجة." : "The rule check is deterministic and separate from fit. A mandatory failure keeps the result ineligible regardless of the score."}</p>
        <label>{ar ? "اختر منحة منشورة" : "Choose a published scholarship"}<select value={selection} disabled={busy || scholarships.length === 0} required onChange={event => { setSelection(event.target.value); setEvaluation(null); }}>
          <option value="">{ar ? "اختر منحة" : "Choose a scholarship"}</option>{scholarships.map(item => <option key={item.id} value={item.id}>{item.title} · {ar ? "إصدار" : "version"} {item.version}</option>)}
        </select></label>
        {scholarships.length === 0 && <p>{ar ? "لا توجد منح منشورة متاحة في هذه الصفحة. لا تُنشأ فرص تجريبية على أنها حقيقية." : "No published scholarships are available on this page. Synthetic opportunities are not presented as real."}</p>}
        {total > pageSize && <nav aria-label={ar ? "صفحات المنح للاختيار" : "Scholarship selection pages"}>
          <button type="button" disabled={busy || page === 1} onClick={() => { setPage(value => value - 1); setScholarships([]); setSelection(""); setEvaluation(null); }}>{ar ? "السابق" : "Previous"}</button>
          <span>{ar ? "صفحة" : "Page"} {page} / {Math.ceil(total / pageSize)}</span>
          <button type="button" disabled={busy || page * pageSize >= total} onClick={() => { setPage(value => value + 1); setScholarships([]); setSelection(""); setEvaluation(null); }}>{ar ? "التالي" : "Next"}</button>
        </nav>}
        {dirty && <p className="catalog-warning">{ar ? "لديك تغييرات غير محفوظة. احفظ ملفك أولًا لتقييم الإصدار الصحيح." : "You have unsaved changes. Save your profile first to evaluate the correct version."}</p>}
        {!view.version_id && <p>{ar ? "احفظ إصدارًا من ملفك أولًا. يمكنك ترك ما لا تعرفه فارغًا." : "Save a profile version first. You may leave unknown facts blank."}</p>}
        <button type="submit" disabled={busy || dirty || !view.version_id || !selection}>{ar ? "فحص الشروط دون ذكاء اصطناعي" : "Check rules without AI"}</button>
      </form>
      {evaluation && <section className="eligibility-result" aria-labelledby="eligibility-result-title">
        <h2 id="eligibility-result-title">{choiceLabels[evaluation.result.status]}</h2>
        <p className="catalog-warning">{ar ? "هذه ملاءمة استرشادية للشروط المراجعة، وليست احتمال قبول أو ضمانًا له. لا تغير الدرجة نتيجة الشروط الملزمة. تحقق من المصدر الرسمي قبل اتخاذ قرار." : "This is indicative fit against reviewed requirements, not an acceptance probability or guarantee. The score cannot change mandatory-rule outcomes. Check the official source before making a decision."}</p>
        <p>{ar ? "تغطية الأدلة المؤكدة: " : "Confirmed evidence coverage: "}<strong>{percent(evaluation.result.coverage_bps)}</strong></p>
        {evaluation.result.fit_status === "AVAILABLE" && evaluation.result.fit_score_bps !== null && evaluation.result.coverage_bps >= 7000
          ? <p>{ar ? "درجة الملاءمة الحتمية الاسترشادية: " : "Indicative deterministic fit score: "}<strong>{new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(evaluation.result.fit_score_bps / 100)} / 100</strong></p>
          : <p>{ar ? "لا تُعرض درجة ملاءمة: تغطية الأدلة أقل من 70% أو المعلومات غير كافية." : "No fit score is shown: evidence coverage is below 70% or information is insufficient."}</p>}
        <p>{ar ? "الأوزان أولية وغير معايرة ميدانيًا. نسبة التغطية ليست نسبة ثقة أو نجاح." : "Weights are initial and have not been calibrated in the field. Coverage is not a confidence or success rate."}</p>
        <p><a href={`/${locale}/scholarships/${evaluation.scholarship_id}`}>{ar ? "راجع المنحة ومصدرها الرسمي" : "Review the scholarship and its official source"}</a></p>
        <h3>{ar ? "مساهمات الملاءمة" : "Fit contributions"}</h3>
        <p>{ar ? "تُحسب مساهمة كل مجال من وزنه الأصلي. تُعاد موازنة الدرجة النهائية على مجموع الأوزان ذات الأدلة الكافية فقط." : "Each domain contribution uses its original weight. The final score is normalized over the weights with sufficient evidence."}</p>
        <ul>{evaluation.result.domains.map(domain => <li key={domain.domain}>
          {choiceLabels[domain.domain] ?? domain.domain} · {ar ? "الوزن" : "weight"} {percent(domain.weight_bps)} · {domain.covered && domain.contribution_bps !== null
            ? (ar ? `مساهمة ${new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(domain.contribution_bps / 100)} نقطة` : `contribution ${new Intl.NumberFormat(locale, { maximumFractionDigits: 2 }).format(domain.contribution_bps / 100)} points`)
            : (ar ? "أدلة غير كافية" : "Insufficient evidence")}. {explanation(domain.reason_code)}
        </li>)}</ul>
        <h3>{ar ? "كل شرط ودليله" : "Each rule and its evidence"}</h3>
        {evaluation.result.rules.length === 0 && <p>{ar ? "لا توجد مجموعة شروط منظمة معتمدة لهذه النسخة. لا نستخرج شروطًا ملزمة بالتخمين من النص." : "This version has no approved structured rule set. Mandatory conditions are not guessed from prose."}</p>}
        {evaluation.result.rules.map(rule => <article key={rule.key}>
          <h4>{labels[rule.field as Field] ?? rule.field} · {rule.result === "UNKNOWN" ? (ar ? "غير محسوم" : "Undetermined") : choiceLabels[rule.result]}</h4>
          <p>{rule.mandatory ? (ar ? "شرط ملزم" : "Mandatory condition") : (ar ? "معلومة للملاءمة" : "Fit evidence")}</p>
          <dl><dt>{ar ? "المطلوب" : "Requirement"}</dt><dd>{rule.expected_display}</dd>
            <dt>{ar ? "بيانات ملفك" : "Your profile fact"}</dt><dd>{rule.actual_display ?? unknown}</dd>
            <dt>{ar ? "دليل الشرط من المصدر" : "Requirement source evidence"}</dt><dd>{rule.evidence.source_text || (ar ? "دليل غير متاح" : "Evidence unavailable")}</dd>
            <dt>{ar ? "مراجعة حقل الملف" : "Profile field review"}</dt><dd>{rule.evidence.profile_confirmed ? (ar ? "إفادة طالب مؤكدة منه؛ غير متحقق منها مستقلًا" : "Student-confirmed self-report; not independently verified") : (ar ? "غير مؤكد؛ يبقى غير محسوم" : "Unconfirmed; stays undetermined")}</dd>
            <dt>{ar ? "مرجع الشرط" : "Criterion reference"}</dt><dd>{rule.evidence.criterion_index + 1}</dd>
          </dl>
          <p>{explanation(rule.reason_code)}</p>
        </article>)}
        {evaluation.result.missing_fields.length > 0 && <><h3>{ar ? "معلومات ناقصة" : "Missing information"}</h3><ul>{evaluation.result.missing_fields.map(field => <li key={field}>{labels[field as Field] ?? field}</li>)}</ul></>}
        {evaluation.result.limitations.length > 0 && <><h3>{ar ? "القيود" : "Limitations"}</h3><ul>{evaluation.result.limitations.map(limitation => <li key={limitation}>{explanation(limitation)}</li>)}</ul></>}
        <details><summary>{ar ? "مراجع الإصدارات المستخدمة" : "Versions used in this check"}</summary><dl>
          <dt>{ar ? "وقت الفحص UTC" : "Checked at UTC"}</dt><dd><bdi>{evaluation.evaluated_at}</bdi></dd>
          <dt>{ar ? "إصدار الملف" : "Profile version"}</dt><dd><bdi>{evaluation.profile_version_id}</bdi></dd>
          <dt>{ar ? "إصدار المنحة" : "Scholarship version"}</dt><dd><bdi>{evaluation.scholarship_version_id}</bdi></dd>
          <dt>{ar ? "مجموعة القواعد" : "Rule set"}</dt><dd><bdi>{evaluation.rule_set_id ?? (ar ? "غير متاحة" : "Unavailable")}</bdi></dd>
          <dt>{ar ? "سياسة الأوزان" : "Weight policy"}</dt><dd><bdi>{evaluation.policy_version}</bdi></dd>
          <dt>{ar ? "إصدار المحرك" : "Engine version"}</dt><dd><bdi>{evaluation.engine_version}</bdi></dd>
          <dt>{ar ? "إصدار الأوزان" : "Weight version"}</dt><dd><bdi>{evaluation.weight_version}</bdi></dd>
        </dl></details>
      </section>}
    </>}
    <p role={failed ? "alert" : "status"} aria-live="polite">{message}</p>
  </section>;
}
