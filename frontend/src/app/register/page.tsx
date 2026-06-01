'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { authAPI } from '@/lib/api';
import { PageHeader } from '@/components/ui/PageHeader';

export default function RegisterPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsLoading(true);

    const formData = new FormData(event.currentTarget);
    const email = formData.get('email') as string;
    const password = formData.get('password') as string;

    try {
      await authAPI.register({ email, password });
      // On successful registration, redirect to login page with a success message
      router.push('/login?registered=true');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader title="Create Account" subtitle="Join the NEXA platform" />
      <div className="max-w-md mx-auto">
        <form onSubmit={handleSubmit} className="space-y-6 bg-background-panel-1 p-8 rounded-lg border border-border-secondary">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-text-muted">
              Email address
            </label>
            <div className="mt-1">
              <input
                id="email"
                name="email"
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
                autoComplete="new-password"
                required
                className="block w-full px-3 py-2 bg-background-root border border-border-secondary rounded-md shadow-sm placeholder-text-muted focus:outline-none focus:ring-primary-gold focus:border-primary-gold sm:text-sm"
              />
            </div>
          </div>

          {error && <div className="p-3 bg-status-danger/20 border border-status-danger text-status-danger rounded-md text-sm">{error}</div>}

          <div>
            <button type="submit" disabled={isLoading} className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-background-root bg-primary-gold hover:bg-primary-gold/90 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-gold disabled:opacity-50">{isLoading ? 'Registering...' : 'Create Account'}</button>
          </div>
          <p className="text-center text-sm text-text-muted">Already have an account? <Link href="/login" className="font-medium text-primary-gold hover:underline">Sign in</Link></p>
        </form>
      </div>
    </div>
  );
}