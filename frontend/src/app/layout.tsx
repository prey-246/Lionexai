import type { Metadata } from "next";
import "./globals.css";
import { NavBar } from "@/components/ui/NavBar";

export const metadata: Metadata = {
  title: "NEXA Trading Intelligence",
  description: "Institutional Risk Orchestration Platform",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased bg-[#050816] text-white min-h-screen flex flex-col">
        <NavBar />
        <div className="flex-1">
          {children}
        </div>
      </body>
    </html>
  );
}