import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import EnvironmentBanner from "@/components/ui/EnvironmentBanner";
import NavBar from "@/components/ui/NavBar";
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
        <body className={`${inter.className} bg-gray-900 text-gray-100 flex flex-col min-h-screen`}>
          <EnvironmentBanner />
          <div className="flex flex-1">
            <NavBar />
            <main className="flex-1 p-8 overflow-y-auto">{children}</main>
          </div>
        </body>
      </UserProvider>
    </html>
  );
}