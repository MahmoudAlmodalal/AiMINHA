import { HealthStatus } from "../../components/health-status";

export default async function Page({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  const ar = locale === "ar";
  return (
    <>
      <a className="skip" href="#main">{ar ? "انتقل إلى المحتوى" : "Skip to content"}</a>
      <header>
        <span className="brand"><bdi>MinhaAI</bdi></span>
        <nav aria-label={ar ? "اللغة" : "Language"}>
          <a href={`/${locale}/scholarships`}>{ar ? "المنح الدراسية" : "Scholarships"}</a>{" · "}
          <a href={`/${locale}/account`}>{ar ? "الحساب والخصوصية" : "Account and privacy"}</a>{" · "}
          <a href={ar ? "/en" : "/ar"} lang={ar ? "en" : "ar"} hrefLang={ar ? "en" : "ar"}>
            {ar ? "English" : "العربية"}
          </a>
        </nav>
      </header>
      <main id="main" tabIndex={-1}>
        <p className="eyebrow">{ar ? "قيد الإعداد" : "In development"}</p>
        <h1>{ar ? "مساحة جديدة لرحلتك الدراسية" : "A new space for your scholarship journey"}</h1>
        <p>{ar
          ? "نعمل على إعداد منحة. ستتوفر خدمات الطلاب في مراحل لاحقة."
          : "MinhaAI is being prepared. Student services will be available in later phases."}</p>
        <HealthStatus locale={ar ? "ar" : "en"} />
      </main>
    </>
  );
}
