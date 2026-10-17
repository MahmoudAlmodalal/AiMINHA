import type { ReactNode } from "react";

export function CatalogShell({ locale, title, path, children }: {
  locale: "ar" | "en"; title: string; path: string; children: ReactNode;
}) {
  const ar = locale === "ar";
  return <>
    <a className="skip" href="#main">{ar ? "انتقل إلى المحتوى" : "Skip to content"}</a>
    <header>
      <a className="brand" href={`/${locale}`}><bdi>MinhaAI</bdi></a>
      <nav aria-label={ar ? "التنقل" : "Navigation"}>
        <a href={`/${locale}/scholarships`}>{ar ? "المنح الدراسية" : "Scholarships"}</a>
        <a href={`/${locale}/documents`}>{ar ? "ملفاتي ومستنداتي" : "Files and documents"}</a>
        <a href={`/${locale}/account`}>{ar ? "الحساب" : "Account"}</a>
        <a href={`/${ar ? "en" : "ar"}${path}`} lang={ar ? "en" : "ar"} hrefLang={ar ? "en" : "ar"}>
          {ar ? "English" : "العربية"}
        </a>
      </nav>
    </header>
    <main className="catalog-main" id="main" tabIndex={-1}>
      <h1>{title}</h1>
      {children}
    </main>
  </>;
}
