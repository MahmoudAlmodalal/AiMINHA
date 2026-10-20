import { CatalogShell } from "../../../components/catalog-shell";
import { SupportDesk } from "../../../components/support-desk";

export default async function SupportPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  const language = locale === "ar" ? "ar" : "en";
  return <CatalogShell locale={language} path="/support" title={language === "ar" ? "الدعم" : "Support"}>
    <SupportDesk locale={language} />
  </CatalogShell>;
}
