import { CatalogShell } from "../../../components/catalog-shell";
import { DocumentWorkspace } from "../../../components/document-workspace";

export default async function DocumentsPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  const language = locale === "ar" ? "ar" : "en";
  return <CatalogShell locale={language} path="/documents" title={language === "ar" ? "ملفاتي ومستنداتي" : "My files and documents"}>
    <DocumentWorkspace locale={language} />
  </CatalogShell>;
}
