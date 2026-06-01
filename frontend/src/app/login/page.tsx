'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { authAPI } from '@/lib/api';
import { PageHeader } from '@/components/ui/PageHeader';
import Cookies from 'js-cookie';

// This new component isolates the use of `useSearchParams`
function RegistrationSuccessMessage() {
  const searchParams = useSearchParams();
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (searchParams.get('registered') === 'true') {
      setSuccess('Registration successful! Please sign in.');
    }
  }, [searchParams]);

  if (!success) {
    return null;
  }

  return (
    <div className="p-3 bg-status-success/20 border border-status-success text-status-success rounded-md text-sm">
      {success}
    </div>
  );
}

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsLoading(true);

    const formData = new FormData(event.currentTarget);

    try {
      const data = await authAPI.login(formData);
      // Save the token in a cookie that expires in 1 day
      Cookies.set('auth_token', data.access_token, { expires: 1 });
      // Use window.location to force a full page reload, ensuring the middleware sees the new cookie.
      window.location.href = '/';
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader title="Sign In" subtitle="Access your NEXA risk control panel" />
      <div className="max-w-md mx-auto">
        <form onSubmit={handleSubmit} className="space-y-6 bg-background-panel-1 p-8 rounded-lg border border-border-secondary">
          <Suspense fallback={null}>
            <RegistrationSuccessMessage />
          </Suspense>
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-text-muted">
              Email address
            </label>
            <div className="mt-1">
              <input
                id="username"
                name="username"
                type="email"
                autoComplete="email"
                required
                className="block w-full px-3 py-2 bg-background-root border border-border-secondary rounded-md shadow-sm placeholder-text-muted focus:outline-none focus:ring-primary-gold focus:border-primary-gold sm:text-sm"
              />
            </div>
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-text-muted">
              Password
            </label>
            <div className="mt-1">
              <input
                id="password"
                name="password"
                type="password"
                autoComplete="current-password"
                required
                className="block w-full px-3 py-2 bg-background-root border border-border-secondary rounded-md shadow-sm placeholder-text-muted focus:outline-none focus:ring-primary-gold focus:border-primary-gold sm:text-sm"
              />
            </div>
          </div>

          {error && <div className="p-3 bg-status-danger/20 border border-status-danger text-status-danger rounded-md text-sm">{error}</div>}

          <div>
            <button type="submit" disabled={isLoading} className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-background-root bg-primary-gold hover:bg-primary-gold/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-gold disabled:opacity-50">{isLoading ? 'Signing In...' : 'Sign In'}</button>
          </div>
          <p className="text-center text-sm text-text-muted">Don't have an account? <Link href="/register" className="font-medium text-primary-gold hover:underline">Register here</Link></p>
        </form>
      </div>
    </div>
  );
}