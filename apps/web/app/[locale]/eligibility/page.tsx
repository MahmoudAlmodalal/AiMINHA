import { CatalogShell } from "../../../components/catalog-shell";
import { EligibilityPanel } from "../../../components/eligibility-panel";

export default async function EligibilityPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  const language = locale === "ar" ? "ar" : "en";
  return <CatalogShell locale={language} path="/eligibility" title={language === "ar" ? "ملف الأهلية وفحص الشروط" : "Eligibility profile and rule check"}>
    <EligibilityPanel locale={language} />
  </CatalogShell>;
}
