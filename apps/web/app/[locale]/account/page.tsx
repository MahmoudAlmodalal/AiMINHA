import { IdentityPanel } from "../../../components/identity-panel";

export default async function AccountPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  const ar = locale === "ar";
  return <>
    <a className="skip" href="#main">{ar ? "انتقل إلى المحتوى" : "Skip to content"}</a>
    <header><a className="brand" href={`/${locale}`}><bdi>MinhaAI</bdi></a>
      <nav aria-label={ar ? "اللغة" : "Language"}>
        <a href={ar ? "/en/account" : "/ar/account"}>{ar ? "English" : "العربية"}</a>
      </nav>
    </header>
    <main id="main" tabIndex={-1}>
      <h1>{ar ? "حسابك وخصوصيتك" : "Your account and privacy"}</h1>
      <IdentityPanel locale={ar ? "ar" : "en"} />
    </main>
  </>;
}
