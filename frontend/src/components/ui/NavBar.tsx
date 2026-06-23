'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, LayoutDashboard, Terminal, BrainCircuit, FileText, Shield, Wallet, FileSliders, LogOut, UserCog, Briefcase, Settings } from 'lucide-react';
import { authAPI } from '@/lib/api';
import { useUser } from '@/contexts/UserContext';

// Define all available routes and the roles permitted to see them
const NAV_LINKS = [
  { href: '/dashboard', label: 'My Dashboard', icon: LayoutDashboard, roles: ['client', 'operator', 'admin'] },
  { href: '/portfolios', label: 'Portfolios', icon: Wallet, roles: ['client', 'operator', 'risk_manager', 'admin'] },
  { href: '/trade', label: 'Terminal', icon: Terminal, roles: ['client', 'operator', 'admin'] },
  { href: '/backtest', label: 'Backtest', icon: BrainCircuit, roles: ['client', 'operator', 'admin'] },
  { href: '/reports', label: 'Reports', icon: FileText, roles: ['client', 'operator', 'risk_manager', 'admin'] },
  { href: '/risk', label: 'Risk Monitoring', icon: Shield, roles: ['client', 'operator', 'risk_manager', 'admin'] },
  { href: '/mandates', label: 'Mandates', icon: FileSliders, roles: ['risk_manager', 'admin'] },
  { href: '/', label: 'System Operations', icon: Home, roles: ['operator', 'admin'] },
  { href: '/audit', label: 'Audit Trail', icon: Briefcase, roles: ['operator', 'admin'] },
  { href: '/admin/users', label: 'User Management', icon: UserCog, roles: ['admin'] },
  { href: '/admin/settings', label: 'Settings', icon: Settings, roles: ['admin'] },
];

const NavBar = () => {
  const pathname = usePathname();
  const { user, isLoading } = useUser();

  const handleLogout = async () => {
    await authAPI.logout();
  };

  const getNavItemsForRole = () => {
    if (!user) return [];
    
    // Filter the links based on the current user's role
    return NAV_LINKS.filter(link => link.roles.includes(user.role_tier));
  };

  const navItems = getNavItemsForRole();

  return (
    <aside className="w-64 bg-background-panel-1 border-r border-border-secondary p-6 flex-col hidden md:flex">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-primary-gold font-serif">LionexAI</h1>
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