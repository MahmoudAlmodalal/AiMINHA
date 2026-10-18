import { CatalogShell } from "../../../components/catalog-shell";
import { NotificationInbox } from "../../../components/notification-inbox";

export default async function NotificationsPage({ params }: { params: Promise<{ locale: string }> }) {
  const { locale } = await params;
  const language = locale === "ar" ? "ar" : "en";
  return <CatalogShell locale={language} path="/notifications" title={language === "ar" ? "الإشعارات" : "Notifications"}>
    <NotificationInbox locale={language} />
  </CatalogShell>;
}
