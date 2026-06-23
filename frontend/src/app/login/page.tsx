'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { authAPI } from '@/lib/api';
import Cookies from 'js-cookie';
import { Mail, Lock, Eye, EyeOff, Loader2, CheckCircle2, AlertCircle, ShieldCheck, BrainCircuit, LineChart } from 'lucide-react';

function RegistrationSuccessMessage() {
  const searchParams = useSearchParams();
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (searchParams.get('registered') === 'true') {
      setSuccess('Registration successful. Please sign in.');
    }
  }, [searchParams]);

  if (!success) return null;

  return (
    <div className="flex items-center gap-2 p-3 rounded-lg bg-system-tBg border border-system-tBd text-primary-emerald-bright text-[13px]">
      <CheckCircle2 className="w-4 h-4 shrink-0" />
      {success}
    </div>
  );
}

const FEATURES = [
  { icon: BrainCircuit, title: 'AI Decision Engine', desc: 'Models analyze market conditions continuously.' },
  { icon: LineChart, title: 'Quantitative Strategies', desc: 'Systematic, diversified strategy allocation.' },
  { icon: ShieldCheck, title: 'Risk Intelligence', desc: 'Drawdown management and dynamic controls.' },
];

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setIsLoading(true);

    const formData = new FormData(event.currentTarget);

    try {
      await authAPI.login(formData);
      const role = Cookies.get('user_role') || 'client';
      const destination =
        role === 'admin' || role === 'operator'
          ? '/'
          : role === 'risk_manager'
            ? '/risk'
            : '/dashboard';
      window.location.href = destination;
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-[calc(100vh-3rem)] grid place-items-center">
      <div className="w-full max-w-5xl grid lg:grid-cols-2 rounded-2xl overflow-hidden border border-border-default shadow-glow bg-background-card">
        {/* Brand panel */}
        <div className="relative hidden lg:flex flex-col justify-between p-10 overflow-hidden border-r border-border-subtle">
          <div
            className="absolute inset-0 -z-10"
            style={{
              background:
                'radial-gradient(60% 50% at 20% 15%, rgba(207,164,59,0.16), transparent 60%), radial-gradient(60% 55% at 90% 90%, rgba(15,168,154,0.18), transparent 60%)',
            }}
            aria-hidden="true"
          />
          <div>
            <img
              src="/logo.png"
              alt="LionexAI"
              className="h-16 w-auto"
              style={{ filter: 'drop-shadow(0 0 14px rgba(207,164,59,0.35)) drop-shadow(0 0 26px rgba(15,168,154,0.25))' }}
              onError={(e) => { e.currentTarget.style.display = 'none'; }}
            />
            <h1 className="mt-8 font-display text-[34px] font-extrabold leading-tight text-text-primary">
              AI-Powered Quantitative <span className="text-gradient-gold">Intelligence</span>
            </h1>
            <p className="mt-3 text-[14px] text-text-secondary max-w-sm">
              Institutional-grade algorithmic trading, portfolio intelligence, and automated risk management.
            </p>
          </div>

          <ul className="mt-10 space-y-4">
            {FEATURES.map((f) => (
              <li key={f.title} className="flex items-start gap-3">
                <span className="grid place-items-center w-9 h-9 rounded-lg bg-system-gBg border border-system-gBd text-primary-gold-bright shrink-0">
                  <f.icon className="w-4 h-4" />
                </span>
                <div>
                  <div className="text-[14px] font-semibold text-text-primary">{f.title}</div>
                  <div className="text-[12.5px] text-text-muted">{f.desc}</div>
                </div>
              </li>
            ))}
          </ul>
        </div>

        {/* Form panel */}
        <div className="p-8 sm:p-10 flex flex-col justify-center">
          <div className="lg:hidden mb-6 flex items-center gap-3">
            <img src="/logo.png" alt="LionexAI" className="h-10 w-auto" onError={(e) => { e.currentTarget.style.display = 'none'; }} />
            <span className="font-display font-extrabold text-[18px]"><span className="text-text-primary">Lionex</span><span className="text-gradient-gold">AI</span></span>
          </div>

          <h2 className="font-display text-[24px] font-bold text-text-primary">Welcome back</h2>
          <p className="mt-1 text-[14px] text-text-muted">Sign in to your control panel.</p>

          <form onSubmit={handleSubmit} className="mt-7 space-y-5">
            <Suspense fallback={null}>
              <RegistrationSuccessMessage />
            </Suspense>

            <div>
              <label htmlFor="username" className="block text-[13px] font-medium text-text-secondary mb-1.5">Email address</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted pointer-events-none" />
                <input
                  id="username"
                  name="username"
                  type="email"
                  autoComplete="email"
                  required
                  placeholder="you@institution.com"
                  className="w-full pl-10 pr-3 py-3 text-[14px] rounded-lg"
                />
              </div>
            </div>

            <div>
              <label htmlFor="password" className="block text-[13px] font-medium text-text-secondary mb-1.5">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted pointer-events-none" />
                <input
                  id="password"
                  name="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  placeholder="Enter your password"
                  className="w-full pl-10 pr-11 py-3 text-[14px] rounded-lg"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((s) => !s)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-system-rBg border border-system-rBd text-danger text-[13px]">
                <AlertCircle className="w-4 h-4 shrink-0" />
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="btn primary btn-full disabled:opacity-50"
            >
              {isLoading ? (<><Loader2 className="w-4 h-4 animate-spin" /> Signing In...</>) : 'Sign In'}
            </button>

            <p className="text-center text-[13px] text-text-muted">
              Don&apos;t have an account?{' '}
              <Link href="/register" className="font-semibold text-primary-gold-bright hover:underline">Register here</Link>
            </p>
          </form>
        </div>
      </div>
    </div>
  );
}
