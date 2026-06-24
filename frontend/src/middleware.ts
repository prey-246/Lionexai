import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

type Role = 'client' | 'operator' | 'risk_manager' | 'admin';

function normalizeRole(raw: string | undefined): Role {
  if (raw === 'admin' || raw === 'operator' || raw === 'risk_manager' || raw === 'client') {
    return raw;
  }
  return 'client';
}

function defaultRouteFor(role: Role): string {
  switch (role) {
    case 'admin':
    case 'operator':
      return '/';
    case 'risk_manager':
      return '/risk';
    default:
      return '/dashboard';
  }
}

function pathMatches(path: string, prefix: string): boolean {
  if (prefix === '/') return path === '/';
  return path === prefix || path.startsWith(`${prefix}/`);
}

/**
 * Deny-by-default allow-list. Each role may ONLY reach the prefixes listed here,
 * which mirror that role's sidebar navigation exactly. Any route not listed is
 * redirected to the role's home, so new pages are private until explicitly granted.
 * `admin` is granted full access and is handled as a special case below.
 */
const ROLE_ALLOWED: Record<Exclude<Role, 'admin'>, string[]> = {
  client: [
    '/dashboard',
    '/portfolios',
    '/funds',
    '/trade',
    '/intelligence',
    '/lnx',
    '/simulator',
  ],
  operator: [
    '/',
    '/audit',
    '/trade-explorer',
    '/analytics',
    '/backtest',
    '/strategies',
    '/execution-monitor',
    '/execution-health',
    '/validation',
    '/reports',
    '/intelligence',
  ],
  risk_manager: [
    '/risk',
    '/mandates',
    '/audit',
    '/intelligence',
    '/stress-test',
    '/validation',
    '/portfolios',
  ],
};

function isAllowed(role: Role, path: string): boolean {
  if (role === 'admin') return true;
  return ROLE_ALLOWED[role].some((prefix) => pathMatches(path, prefix));
}

export function middleware(request: NextRequest) {
  const token = request.cookies.get('auth_token')?.value;
  const role = normalizeRole(request.cookies.get('user_role')?.value);
  const path = request.nextUrl.pathname;

  const isPublicPath = path === '/login' || path === '/register';

  if (!token && !isPublicPath) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  if (token && isPublicPath) {
    return NextResponse.redirect(new URL(defaultRouteFor(role), request.url));
  }

  if (token && !isAllowed(role, path)) {
    return NextResponse.redirect(new URL(defaultRouteFor(role), request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico|logo.png).*)'],
};
