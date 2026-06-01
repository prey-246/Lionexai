import type { Metadata } from "next";
import { Inter, JetBrains_Mono, Cormorant_Garamond } from "next/font/google";
import "./globals.css";
import { AppShell } from "@/components/shell/AppShell";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });
const jetbrains_mono = JetBrains_Mono({ subsets: ["latin"], weight: ["400", "700"], variable: "--font-jetbrains-mono" });
const cormorant_garamond = Cormorant_Garamond({ subsets: ["latin"], weight: ["400", "600", "700"], variable: "--font-cormorant-garamond" });

export const metadata: Metadata = {
  title: "NEXA | Institutional Terminal",
  description: "Institutional Monitoring Console & Global Risk Parameters",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={`${inter.variable} ${jetbrains_mono.variable} ${cormorant_garamond.variable}`}>
      <body>
        <AppShell>
          {children}
        </AppShell>
      </body>
    </html>
  );
}