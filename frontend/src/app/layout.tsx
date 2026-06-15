import type { Metadata } from "next";
import "./globals.css";
import EnvironmentBanner from "@/components/ui/EnvironmentBanner";
import { TerminalSidebar } from "@/components/shell/TerminalSidebar";
import { UserProvider } from "@/contexts/UserContext";

export const metadata: Metadata = {
  title: "NEXA Platform",
  description: "Quantitative Trading Intelligence",
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
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700&family=Roboto+Mono:wght@400;500&family=Merriweather:wght@300;400;700&display=swap" rel="stylesheet" />
      </head>
      <body className="bg-background-base text-text-primary flex flex-col min-h-screen">
        <UserProvider>
          <EnvironmentBanner />
          <div className="flex flex-1 overflow-hidden">
            <TerminalSidebar />
            <main className="flex-1 overflow-y-auto p-4 md:p-8">
              {children}
            </main>
          </div>
        </UserProvider>
      </body>
    </html>
  );
}