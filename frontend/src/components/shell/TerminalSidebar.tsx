'use client';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { BarChart, Terminal, Shield, FileText, History, LogOut } from 'lucide-react';
import clsx from 'clsx';
import Cookies from 'js-cookie';

export function TerminalSidebar() {
  const navItems = [
    { href: '/', label: 'Dashboard', icon: BarChart },
    { href: '/trade', label: 'Terminal', icon: Terminal },
    { href: '/mandates', label: 'Mandates', icon: Shield },
    { href: '/reports', label: 'Reports', icon: FileText },
    { href: '/audit', label: 'Audit Trail', icon: History },
  ];

  const pathname = usePathname();
  const router = useRouter();

  const handleLogout = () => {
    Cookies.remove('auth_token');
    router.push('/login');
  };

  return (
    <aside className="w-64 bg-background-panel-1 border-r border-border-secondary p-4 flex flex-col justify-between">
      <div>
        <div className="mb-8">
          <h1 className="text-2xl font-bold font-serif text-primary-gold">NEXA</h1>
          <p className="text-xs text-text-muted">Risk Control</p>
        </div>
        <nav className="flex flex-col space-y-2">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx("flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium transition-colors", {
                "bg-background-panel-2 text-text-primary": isActive,
                "text-text-muted hover:bg-background-panel-2 hover:text-text-primary": !isActive,
              })}>
              <item.icon className="w-4 h-4" />
              <span>{item.label}</span>
            </Link>
          );
        })}
        </nav>
      </div>

      <button onClick={handleLogout} className="flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium text-text-muted hover:bg-background-panel-2 hover:text-text-primary transition-colors">
        <LogOut className="w-4 h-4" />
        <span>Logout</span>
      </button>
    </aside>
  );
}