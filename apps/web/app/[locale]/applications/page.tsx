import { CatalogShell } from "../../../components/catalog-shell";
import { ApplicationTracker } from "../../../components/application-tracker";

export default async function ApplicationsPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  const language = locale === "ar" ? "ar" : "en";
  return <CatalogShell locale={language} path="/applications" title={language === "ar" ? "طلباتي والمنح المحفوظة" : "My applications and saved scholarships"}>
    <ApplicationTracker locale={language} />
  </CatalogShell>;
}
