import type { Metadata } from "next";
import "./globals.css";
import EnvironmentBanner from "@/components/ui/EnvironmentBanner";
import { TerminalSidebar } from "@/components/shell/TerminalSidebar";
import { UserProvider } from "@/contexts/UserContext";

export const metadata: Metadata = {
  title: "LionexAI | Quantitative Intelligence",
  description: "AI-powered quantitative trading, portfolio intelligence, and automated risk management.",
  icons: { icon: "/logo.png" },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Sora:wght@500;600;700;800&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet" />
      </head>
      <body className="bg-background-base text-text-primary flex flex-col min-h-screen">
        <UserProvider>
          <EnvironmentBanner />
          <div className="flex flex-col md:flex-row flex-1 overflow-hidden">
            <TerminalSidebar />
            <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
              {children}
            </main>
          </div>
        </UserProvider>
      </body>
    </html>
  );
}