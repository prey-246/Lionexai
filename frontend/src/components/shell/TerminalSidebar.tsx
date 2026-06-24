'use client';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useState, useEffect } from 'react';
import { BarChart, Terminal, Shield, History, LogOut, Wallet, FlaskConical, ShieldAlert, Users, Settings, Activity, BrainCircuit, Landmark, Coins, Briefcase, Database, TrendingUp, ShieldCheck, Server, HeartPulse, Search, GitCompare, FileText, Menu, X, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import clsx from 'clsx';
import Cookies from 'js-cookie';
import { useUser } from '@/contexts/UserContext';

const ROLE_LABEL: Record<string, string> = {
  client: 'Client',
  operator: 'Operator',
  risk_manager: 'Risk Manager',
  admin: 'Administrator',
};

export function TerminalSidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user } = useUser();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  // Restore the persisted collapsed state on mount
  useEffect(() => {
    try {
      setCollapsed(localStorage.getItem('lionex_sidebar_collapsed') === '1');
    } catch { /* ignore */ }
  }, []);

  const toggleCollapsed = () => {
    setCollapsed((prev) => {
      const next = !prev;
      try { localStorage.setItem('lionex_sidebar_collapsed', next ? '1' : '0'); } catch { /* ignore */ }
      return next;
    });
  };

  // Close the mobile drawer whenever the route changes
  useEffect(() => {
    setMobileOpen(false);
  }, [pathname]);

  // The shell is hidden on public auth routes for a clean, full-bleed experience
  const isAuthRoute = pathname === '/login' || pathname === '/register';

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
    { href: '/simulator', label: 'Growth Simulator', icon: TrendingUp },
  ];

  const operatorNav = [
    { href: '/', label: 'System Operations', icon: Activity },
    { href: '/audit', label: 'Audit Trail', icon: History },
    { href: '/trade-explorer', label: 'Trade Explorer', icon: Search },
    { href: '/analytics/compare', label: 'Compare Analytics', icon: GitCompare },
    { href: '/backtest', label: 'Strategy Engine', icon: FlaskConical },
    { href: '/strategies', label: 'Strategy Registry', icon: Database },
    { href: '/execution-monitor', label: 'Execution Monitor', icon: Server },
    { href: '/execution-health', label: 'Execution Health', icon: HeartPulse },
    { href: '/validation', label: 'Validation Framework', icon: ShieldCheck },
    { href: '/reports', label: 'Performance Reports', icon: FileText },
    { href: '/intelligence', label: 'Intelligence Hub', icon: BrainCircuit },
  ];

  const riskNav = [
    { href: '/risk', label: 'Command Center', icon: ShieldAlert },
    { href: '/mandates', label: 'Mandate Contracts', icon: Shield },
    { href: '/audit', label: 'Audit Trail', icon: History },
    { href: '/intelligence', label: 'Intelligence Hub', icon: BrainCircuit },
    { href: '/stress-test', label: 'Risk Stress Tests', icon: ShieldCheck },
    { href: '/validation', label: 'Validation Framework', icon: ShieldCheck },
  ];

  const adminNav = [
    { href: '/executive', label: 'Executive Summary', icon: BarChart },
    { href: '/treasury', label: 'Treasury NAV', icon: Landmark },
    { href: '/admin/users', label: 'User Management', icon: Users },
    { href: '/admin/settings', label: 'Global Settings', icon: Settings },
  ];

  let navItems: { href: string; label: string; icon: any }[] = [];
  let workspaceName = 'Workspace';

  if (role === 'client') {
    navItems = clientNav;
    workspaceName = 'Client Workspace';
  } else if (role === 'operator') {
    navItems = operatorNav;
    workspaceName = 'System Operations';
  } else if (role === 'risk_manager') {
    navItems = [...riskNav, { href: '/portfolios', label: 'Global Portfolios', icon: Wallet }];
    workspaceName = 'Risk Management';
  } else if (role === 'admin') {
    const combined = [...adminNav, ...operatorNav, ...riskNav, ...clientNav];
    navItems = Array.from(new Map(combined.map((item) => [item.href, item])).values());
    workspaceName = 'Admin Control';
  }

  const renderSidebar = (isCollapsed: boolean, showCollapseToggle: boolean) => (
    <>
      {/* Brand */}
      <div className={clsx('pt-5 pb-4 border-b border-border-subtle', isCollapsed ? 'px-2' : 'px-4')}>
        <div className={clsx('flex items-center', isCollapsed ? 'justify-center' : 'justify-between gap-2')}>
          <Link href={role === 'client' ? '/dashboard' : '/'} className={clsx('flex items-center group min-w-0', isCollapsed ? '' : 'gap-2.5')} title="LionexAI">
            <img
              src="/logo.png"
              alt="LionexAI"
              className={clsx('w-auto shrink-0 transition-transform duration-300 group-hover:scale-105', isCollapsed ? 'h-9' : 'h-12')}
              style={{ filter: 'drop-shadow(0 0 10px rgba(207,164,59,0.35)) drop-shadow(0 0 18px rgba(15,168,154,0.22))' }}
              onError={(e) => { e.currentTarget.style.display = 'none'; }}
            />
            {!isCollapsed && (
              <div className="leading-tight min-w-0">
                <div className="font-display font-extrabold text-[17px] tracking-tight">
                  <span className="text-text-primary">Lionex</span><span className="text-gradient-gold">AI</span>
                </div>
                <div className="font-mono text-[8.5px] uppercase tracking-[0.16em] text-text-muted truncate">
                  {workspaceName}
                </div>
              </div>
            )}
          </Link>
          {showCollapseToggle && !isCollapsed && (
            <button
              onClick={toggleCollapsed}
              aria-label="Collapse sidebar"
              className="shrink-0 p-1.5 rounded-lg text-text-muted hover:bg-background-panel hover:text-text-primary transition-colors"
            >
              <PanelLeftClose className="w-[18px] h-[18px]" />
            </button>
          )}
        </div>
        {showCollapseToggle && isCollapsed && (
          <button
            onClick={toggleCollapsed}
            aria-label="Expand sidebar"
            className="mt-3 w-full grid place-items-center p-2 rounded-lg text-text-muted hover:bg-background-panel hover:text-text-primary transition-colors"
          >
            <PanelLeftOpen className="w-[18px] h-[18px]" />
          </button>
        )}
        {!isCollapsed && (
          <div className="mt-3 inline-flex items-center gap-1.5 rounded-full bg-system-tBg border border-system-tBd px-2.5 py-1">
            <span className="w-1.5 h-1.5 rounded-full bg-primary-emerald-bright animate-pulse" />
            <span className="font-mono text-[9px] font-bold uppercase tracking-[0.12em] text-primary-emerald-bright">
              {ROLE_LABEL[role] ?? role}
            </span>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className={clsx('flex-1 overflow-y-auto py-3 scrollbar-hide', isCollapsed ? 'px-2' : 'px-2')}>
        {!isCollapsed && <div className="font-mono text-[9px] tracking-[0.18em] uppercase text-text-muted px-3 pb-2">Navigation</div>}
        <div className="flex flex-col gap-0.5">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={isActive ? 'page' : undefined}
                title={isCollapsed ? item.label : undefined}
                className={clsx(
                  'group relative flex items-center rounded-lg text-[13px] font-medium transition-all duration-150',
                  isCollapsed ? 'justify-center px-0 py-2.5' : 'gap-3 px-3 py-2.5',
                  {
                    'text-primary-gold-bright bg-system-gBg': isActive,
                    'text-text-secondary hover:bg-background-panel hover:text-text-primary': !isActive,
                  }
                )}
              >
                {isActive && (
                  <span className="absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-full bg-grad-gold" aria-hidden="true" />
                )}
                <item.icon className={clsx('w-[16px] h-[16px] shrink-0 transition-colors', isActive ? 'text-primary-gold-bright' : 'text-text-muted group-hover:text-text-primary')} />
                {!isCollapsed && <span className="truncate">{item.label}</span>}
              </Link>
            );
          })}
        </div>
      </nav>

      {/* Footer / user + logout */}
      <div className={clsx('border-t border-border-subtle', isCollapsed ? 'p-2' : 'p-3')}>
        {!isCollapsed && user?.email && (
          <div className="px-2 pb-2 min-w-0">
            <div className="font-mono text-[8.5px] uppercase tracking-[0.14em] text-text-muted">Signed in as</div>
            <div className="text-[12px] text-text-secondary truncate" title={user.email}>{user.email}</div>
          </div>
        )}
        <button
          onClick={handleLogout}
          title={isCollapsed ? 'Sign Out' : undefined}
          className={clsx(
            'w-full flex items-center rounded-lg text-[13px] font-medium text-text-muted hover:bg-system-rBg hover:text-danger transition-colors',
            isCollapsed ? 'justify-center py-2.5' : 'gap-3 px-3 py-2.5'
          )}
        >
          <LogOut className="w-[16px] h-[16px] shrink-0" />
          {!isCollapsed && <span>Sign Out</span>}
        </button>
      </div>
    </>
  );

  if (isAuthRoute) return null;

  return (
    <>
      {/* Mobile top bar */}
      <div className="md:hidden sticky top-0 z-40 flex items-center justify-between px-4 h-14 bg-background-base/90 backdrop-blur-md border-b border-border-subtle">
        <Link href={role === 'client' ? '/dashboard' : '/'} className="flex items-center gap-2">
          <img src="/logo.png" alt="LionexAI" className="h-8 w-auto" onError={(e) => { e.currentTarget.style.display = 'none'; }} />
          <span className="font-display font-extrabold text-[15px]"><span className="text-text-primary">Lionex</span><span className="text-gradient-gold">AI</span></span>
        </Link>
        <button
          onClick={() => setMobileOpen(true)}
          aria-label="Open navigation menu"
          className="p-2 rounded-lg text-text-secondary hover:bg-background-panel hover:text-text-primary transition-colors"
        >
          <Menu className="w-5 h-5" />
        </button>
      </div>

      {/* Mobile drawer + overlay */}
      <div
        className={clsx('md:hidden fixed inset-0 z-50 transition-opacity duration-200', mobileOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none')}
        aria-hidden={!mobileOpen}
      >
        <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
        <aside
          className={clsx(
            'absolute left-0 top-0 h-full w-[270px] bg-background-base border-r border-border-default flex flex-col transition-transform duration-300 ease-out',
            mobileOpen ? 'translate-x-0' : '-translate-x-full'
          )}
        >
          <button
            onClick={() => setMobileOpen(false)}
            aria-label="Close navigation menu"
            className="absolute right-3 top-4 z-10 p-1.5 rounded-lg text-text-muted hover:bg-background-panel hover:text-text-primary"
          >
            <X className="w-5 h-5" />
          </button>
          {renderSidebar(false, false)}
        </aside>
      </div>

      {/* Desktop sidebar (collapsible) */}
      <aside
        className={clsx(
          'hidden md:flex shrink-0 bg-background-base border-r border-border-default flex-col h-full overflow-hidden transition-[width] duration-300 ease-out',
          collapsed ? 'w-[72px]' : 'w-[248px]'
        )}
      >
        {renderSidebar(collapsed, true)}
      </aside>
    </>
  );
}
