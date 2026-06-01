'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from './GlassCard';
import { Radio, FlaskConical, Target, BarChart3, AlertTriangle, FileText } from 'lucide-react';

export function NavBar() {
  const pathname = usePathname();

  const navItems = [
    { name: 'Operations', path: '/', icon: Radio },
    { name: 'Dashboard', path: '/dashboard', icon: BarChart3 },
    { name: 'Execution', path: '/trade', icon: Target },
    { name: 'Backtest', path: '/backtest', icon: FlaskConical },
    { name: 'Reports', path: '/reports', icon: FileText },
    { name: 'Risk', path: '/risk', icon: AlertTriangle },
  ];

  return (
    <nav className="border-b border-white/[0.04] bg-[#050816]/80 backdrop-blur-md sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-6 md:px-8 h-16 flex items-center gap-8">
        <div className="flex items-center gap-2 mr-4">
          <div className="w-6 h-6 rounded bg-gradient-to-br from-[#5EEAD4] to-[#22D3EE] flex items-center justify-center shadow-glow">
            <span className="text-[#050816] font-bold text-[10px] tracking-tighter">NX</span>
          </div>
          <span className="text-white font-bold tracking-widest text-sm uppercase">UnifyX</span>
        </div>

        <div className="flex gap-1 h-full overflow-x-auto">
          {navItems.map((item) => {
            const isActive = pathname === item.path;
            const Icon = item.icon;
            return (
              <Link
                key={item.path}
                href={item.path}
                className={cn(
                  "flex items-center gap-2 px-4 h-full text-sm font-medium transition-colors border-b-2 whitespace-nowrap",
                  isActive
                    ? "text-white border-[#5EEAD4] bg-white/[0.02]"
                    : "text-gray-400 border-transparent hover:text-gray-200 hover:bg-white/[0.01]"
                )}
              >
                <Icon className="w-4 h-4" />
                {item.name}
              </Link>
            );
          })}
        </div>
      </div>
    </nav>
  );
}



