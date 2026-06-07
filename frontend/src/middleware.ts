import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const token = request.cookies.get('auth_token')?.value;
  const role = request.cookies.get('user_role')?.value || 'client'; // Default to client if not set
  const path = request.nextUrl.pathname;

  // 1. Define Public Paths
  const isPublicPath = path === '/login' || path === '/register';

  // 2. Redirect Unauthenticated Users
  if (!token && !isPublicPath) {
    return NextResponse.redirect(new URL('/login', request.url));
  }

  // 3. Smart Routing on Login
  if (token && isPublicPath) {
    if (role === 'admin' || role === 'operator') {
      return NextResponse.redirect(new URL('/', request.url)); // Route to Ops Dashboard
    } else if (role === 'risk_manager') {
      return NextResponse.redirect(new URL('/risk', request.url)); // Route to Risk Dashboard
    } else {
      return NextResponse.redirect(new URL('/dashboard', request.url)); // Route to Client Dashboard
    }
  }

  // 4. RBAC Route Protection
  if (token) {
    // Clients cannot access System Ops (/), Mandates, or Audit pages
    if (role === 'client' && (path === '/' || path.startsWith('/mandates') || path.startsWith('/audit'))) {
      return NextResponse.redirect(new URL('/dashboard', request.url));
    }

    // Risk Managers are restricted to Risk, Reports, Mandates, and Portfolios
    if (role === 'risk_manager' && (path === '/' || path.startsWith('/audit') || path.startsWith('/trade'))) {
      return NextResponse.redirect(new URL('/risk', request.url));
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    '/((?!api|_next/static|_next/image|favicon.ico).*)',
  ],
};