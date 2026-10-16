import type { Metadata } from "next";
import { notFound } from "next/navigation";
import "../globals.css";

export const metadata: Metadata = { title: "MinhaAI | منحة" };
export const dynamicParams = false;

export function generateStaticParams() {
  return [{ locale: "ar" }, { locale: "en" }];
}

export default async function Layout({
  children, params,
}: Readonly<{ children: React.ReactNode; params: Promise<{ locale: string }> }>) {
  const { locale } = await params;
  if (locale !== "ar" && locale !== "en") notFound();
  return (
    <html lang={locale} dir={locale === "ar" ? "rtl" : "ltr"}>
      <body>{children}</body>
    </html>
  );
}
