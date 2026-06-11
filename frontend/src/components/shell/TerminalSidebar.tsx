'use client';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { BarChart, Terminal, Shield, History, LogOut, Wallet, FlaskConical, ShieldAlert, Users, Settings, Activity, BrainCircuit, Landmark, Coins, Briefcase, Database } from 'lucide-react';
import clsx from 'clsx';
import Cookies from 'js-cookie';
import { useUser } from '@/contexts/UserContext';

export function TerminalSidebar() {

  const pathname = usePathname();
  const router = useRouter();
  const { user } = useUser();

  const handleLogout = () => {
    Cookies.remove('auth_token');
    Cookies.remove('user_role');
    router.push('/login');
  };

  const role = user?.role_tier || 'client';

  const clientNav = [
    { href: '/dashboard', label: 'My Dashboard', icon: BarChart },
    { href: '/portfolios', label: 'Portfolios', icon: Wallet },
    { href: '/funds', label: 'Lionex Funds', icon: Briefcase },
    { href: '/trade', label: 'Execution Terminal', icon: Terminal },
    { href: '/intelligence', label: 'Intelligence Hub', icon: BrainCircuit },
    { href: '/lnx', label: 'LNX Ecosystem', icon: Coins },
  ];

  const operatorNav = [
    { href: '/', label: 'System Operations', icon: Activity },
    { href: '/audit', label: 'Audit Trail', icon: History },
    { href: '/backtest', label: 'Strategy Engine', icon: FlaskConical },
    { href: '/strategies', label: 'Strategy Registry', icon: Database },
    { href: '/intelligence', label: 'Intelligence Hub', icon: BrainCircuit },
  ];

  const riskNav = [
    { href: '/risk', label: 'Command Center', icon: ShieldAlert },
    { href: '/mandates', label: 'Mandate Contracts', icon: Shield },
    { href: '/intelligence', label: 'Intelligence Hub', icon: BrainCircuit },
  ];

  const adminNav = [
    { href: '/executive', label: 'Executive Summary', icon: BarChart },
    { href: '/treasury', label: 'Treasury NAV', icon: Landmark },
    { href: '/admin/users', label: 'User Management', icon: Users },
    { href: '/admin/settings', label: 'Global Settings', icon: Settings },
  ];

  let navItems: any[] = [];
  let workspaceName = "NEXA Workspace";

  if (role === 'client') {
    navItems = clientNav;
    workspaceName = "Client Workspace";
  } else if (role === 'operator') {
    navItems = operatorNav;
    workspaceName = "System Operations";
  } else if (role === 'risk_manager') {
    navItems = [...riskNav, { href: '/portfolios', label: 'Global Portfolios', icon: Wallet }];
    workspaceName = "Risk Management";
  } else if (role === 'admin') {
    const combined = [...operatorNav, ...riskNav, ...clientNav, ...adminNav];
    navItems = Array.from(new Map(combined.map(item => [item.href, item])).values());
    workspaceName = "Admin Control";
  }

  return (
    <aside className="w-[192px] shrink-0 bg-background-base border-r border-border-default pb-4 flex flex-col justify-between overflow-y-auto">
      <div>
        <div className="mb-6 p-4">
          {/* You can use a base64 string here if you prefer, but standard relative paths point to the public folder */}
          <img 
            src="/logo.png" 
            id="toplogo"
            alt="UnifyX NEXA" 
            className="h-[100px] w-auto mb-2 border-none bg-transparent"
            onError={(e) => { e.currentTarget.style.display = 'none'; }} 
          />
        </div>
        <nav className="flex flex-col space-y-2">
          <div className="font-mono text-[7.5px] tracking-[0.18em] uppercase text-text-muted px-[10px] pt-[10px] pb-[3px]">Navigation</div>
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx("flex items-center gap-3 px-[10px] py-[7px] mx-[8px] my-[1px] rounded-[2px] text-[12px] font-sans transition-colors border", {
                "text-primary-gold bg-system-gBg border-system-gBd": isActive,
                "text-text-secondary hover:bg-background-panel border-transparent hover:text-text-primary": !isActive,
              })}>
              <div className="w-[14px] flex justify-center">
                <item.icon className="w-[11px] h-[11px]" />
              </div>
              <span>{item.label}</span>
            </Link>
          );
        })}
        </nav>
      </div>

      <button onClick={handleLogout} className="flex items-center gap-3 px-[10px] py-[7px] mx-[8px] rounded-[2px] text-[12px] font-sans font-medium text-text-muted hover:bg-background-panel hover:text-text-primary transition-colors border border-transparent">
        <div className="w-[14px] flex justify-center"><LogOut className="w-[11px] h-[11px]" /></div>
        <span>Logout</span>
      </button>
    </aside>
  );
}