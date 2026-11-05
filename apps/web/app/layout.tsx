import type { Metadata } from "next";
import { cookies } from "next/headers";
import { COOKIE_TEXT } from "@/lib/session";
import "./globals.css";

export const metadata: Metadata = {
  title: "KI-Lotse · Sozialversicherung",
  description: "Persönlicher Navigator durch die österreichische Sozialversicherung (Demo)",
};

export default async function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  const large = (await cookies()).get(COOKIE_TEXT)?.value === "large";
  return (
    <html lang="de" className={large ? "text-large" : undefined}>
      <body className="antialiased">{children}</body>
    </html>
  );
}
