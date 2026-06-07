'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, LayoutDashboard, Terminal, BrainCircuit, FileText, Shield, Wallet, FileSliders, LogOut, UserCog, Briefcase, Settings } from 'lucide-react';
import { authAPI } from '@/lib/api';
import { useUser } from '@/contexts/UserContext';

const navSections = {
  client: [
    { href: '/dashboard', label: 'My Dashboard', icon: LayoutDashboard },
    { href: '/portfolios', label: 'Portfolios', icon: Wallet },
    { href: '/backtest', label: 'Backtest', icon: BrainCircuit },
    { href: '/reports', label: 'Reports', icon: FileText },
    { href: '/risk', label: 'Risk Monitoring', icon: Shield },
  ],
  operator: [
    { href: '/', label: 'System Operations', icon: Home },
    { href: '/audit', label: 'Audit Trail', icon: Briefcase },
  ],
  risk: [
    { href: '/mandates', label: 'Mandates', icon: FileSliders },
    { href: '/audit', label: 'Audit Trail', icon: Briefcase }, // Also for risk
  ],
  admin: [
    { href: '/admin/users', label: 'User Management', icon: UserCog },
    { href: '/admin/settings', label: 'Settings', icon: Settings },
  ],
  // Terminal is a special case, available to clients, operators, and admins
  terminal: { href: '/trade', label: 'Terminal', icon: Terminal, roles: ['client', 'operator', 'admin'] }
};


const NavBar = () => {
  const pathname = usePathname();
  const { user, isLoading } = useUser();

  const handleLogout = async () => {
    await authAPI.logout();
  };

  const getNavItemsForRole = () => {
    if (!user) return [];
    
    let items: { href: string; label: string; icon: React.ElementType; }[] = [];
    
    switch (user.role_tier) {
      case 'admin':
        items = [...navSections.client, navSections.terminal, ...navSections.operator, ...navSections.risk, ...navSections.admin];
        break;
      case 'operator':
        items = [...navSections.client, navSections.terminal, ...navSections.operator];
        break;
      case 'risk_manager':
        items = [...navSections.client, ...navSections.risk];
        break;
      case 'client':
      default:
        items = [...navSections.client, navSections.terminal];
        break;
    }
    // Remove duplicates
    return items.filter((item, index, self) => index === self.findIndex((t) => t.href === item.href));
  };

  const navItems = getNavItemsForRole();

  return (
    <aside className="w-64 bg-background-panel-1 border-r border-border-secondary p-6 flex-col hidden md:flex">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-primary-gold font-serif">NEXA</h1>
        <p className="text-xs text-text-muted font-mono">QUANT PLATFORM</p>
      </div>
      <nav className="flex flex-col space-y-2">
        <div className="flex-grow">
          {isLoading && <div className="text-sm text-text-muted">Loading...</div>}
          {!isLoading && !user && <div className="text-sm text-text-muted">Not logged in.</div>}
          
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-3 px-4 py-2.5 rounded-md text-sm font-medium transition-colors ${
                  isActive ? 'bg-primary-gold/10 text-primary-gold' : 'text-text-muted hover:bg-gray-700/50 hover:text-text-primary'
                }`}
              >
                <item.icon className="w-5 h-5" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>
      <div className="mt-auto">
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-3 px-4 py-2.5 rounded-md text-sm font-medium transition-colors text-text-muted hover:bg-danger/10 hover:text-danger"
        >
          <LogOut className="w-5 h-5" />
          <span>Sign Out</span>
        </button>
      </div>
    </aside>
  );
};

export default NavBar;