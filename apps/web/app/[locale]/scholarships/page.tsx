import { CatalogSearch } from "../../../components/catalog-public";
import { CatalogShell } from "../../../components/catalog-shell";

export default async function ScholarshipsPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  const language = locale === "ar" ? "ar" : "en";
  return <CatalogShell locale={language} path="/scholarships" title={language === "ar" ? "ابحث عن منحة دراسية" : "Find a scholarship"}>
    <CatalogSearch locale={language} />
  </CatalogShell>;
}
