import { notFound } from "next/navigation";
import { CatalogDetail } from "../../../../components/catalog-public";
import { CatalogShell } from "../../../../components/catalog-shell";

export const dynamic = "force-dynamic";
export const dynamicParams = true;

export default async function ScholarshipPage({ params }: { params: Promise<{ locale: string; id: string }> }) {
  const { locale, id } = await params;
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(id)) notFound();
  const language = locale === "ar" ? "ar" : "en";
  return <CatalogShell locale={language} path={`/scholarships/${id}`} title={language === "ar" ? "تفاصيل المنحة" : "Scholarship details"}>
    <CatalogDetail locale={language} scholarshipId={id} />
  </CatalogShell>;
}
