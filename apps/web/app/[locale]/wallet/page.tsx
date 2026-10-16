import { CatalogShell } from "../../../components/catalog-shell";
import { CreditWallet } from "../../../components/credit-wallet";

export default async function WalletPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  const language = locale === "ar" ? "ar" : "en";
  return <CatalogShell locale={language} path="/wallet" title={language === "ar" ? "رصيد الاستخدام وسجل الحركات" : "Credit wallet and history"}>
    <CreditWallet locale={language} />
  </CatalogShell>;
}
