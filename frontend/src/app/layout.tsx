import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import EnvironmentBanner from "@/components/ui/EnvironmentBanner";
import { TerminalSidebar } from "@/components/shell/TerminalSidebar";
import { UserProvider } from "@/contexts/UserContext";

const inter = Inter({ subsets: ["latin"] });

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
      <UserProvider>
        <body className={`${inter.className} bg-background-base text-text-primary flex flex-col min-h-screen`}>
          <EnvironmentBanner />
          <div className="flex flex-1 overflow-hidden">
            <TerminalSidebar />
            <main className="flex-1 overflow-y-auto p-4 md:p-8">
              {children}
            </main>
          </div>
        </body>
      </UserProvider>
    </html>
  );
}