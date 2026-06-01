'use client';

import { TerminalSidebar } from "./TerminalSidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen bg-background-root text-text-secondary font-sans">
      <TerminalSidebar />
      <main className="flex-1 flex flex-col overflow-y-auto">
        <div className="flex-1 p-6 lg:p-8">
          {children}
        </div>
      </main>
    </div>
  );
}