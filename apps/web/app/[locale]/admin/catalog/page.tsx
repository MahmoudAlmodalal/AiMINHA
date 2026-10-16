import { CatalogAdmin } from "../../../../components/catalog-admin";
import { CatalogShell } from "../../../../components/catalog-shell";

export const dynamic = "force-dynamic";

export default async function AdminCatalogPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  const language = locale === "ar" ? "ar" : "en";
  return <CatalogShell locale={language} path="/admin/catalog" title={language === "ar" ? "مراجعة مصادر المنح والكتالوج" : "Catalog and source moderation"}>
    <CatalogAdmin locale={language} />
  </CatalogShell>;
}
