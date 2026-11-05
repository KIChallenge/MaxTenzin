import type { Metadata } from "next";
import { Atkinson_Hyperlegible } from "next/font/google";
import "./globals.css";

const atkinson = Atkinson_Hyperlegible({
  variable: "--font-atkinson",
  subsets: ["latin", "latin-ext"],
  weight: ["400", "700"],
});

export const metadata: Metadata = {
  title: "KI-Lotse · Sozialversicherung",
  description: "Persönlicher Navigator durch die österreichische Sozialversicherung (Demo)",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="de">
      <body className={`${atkinson.variable} antialiased`}>{children}</body>
    </html>
  );
}
