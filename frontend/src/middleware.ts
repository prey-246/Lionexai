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
  return path === prefix || path.startsWith(`${prefix}/`);
}

/** Prefixes this role must not access (redirect to role home). */
const ROLE_BLOCKED: Record<Role, string[]> = {
  client: [
    '/',
    '/audit',
    '/mandates',
    '/executive',
    '/treasury',
    '/admin',
    '/trade-explorer',
    '/analytics',
    '/execution-monitor',
    '/execution-health',
    '/validation',
    '/stress-test',
    '/strategies',
    '/backtest',
    '/reports',
    '/risk',
  ],
  operator: ['/admin', '/executive', '/treasury'],
  risk_manager: [
    '/',
    '/admin',
    '/executive',
    '/treasury',
    '/dashboard',
    '/funds',
    '/lnx',
    '/simulator',
    '/trade',
    '/backtest',
    '/strategies',
    '/execution-monitor',
    '/execution-health',
  ],
  admin: [],
};

function isBlocked(role: Role, path: string): boolean {
  return ROLE_BLOCKED[role].some((prefix) => pathMatches(path, prefix));
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

  if (token && isBlocked(role, path)) {
    return NextResponse.redirect(new URL(defaultRouteFor(role), request.url));
  }

  return NextResponse.next();
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|favicon.ico|logo.png).*)'],
};
