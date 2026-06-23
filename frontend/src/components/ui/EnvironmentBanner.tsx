'use client';

import { useEffect, useState } from 'react';
import { usePathname } from 'next/navigation';
import { systemAPI } from '@/lib/api';

type Environment = 'PAPER' | 'BACKTEST' | 'DEMO' | 'LIVE_DISABLED';

const environmentStyles: Record<Environment, { dot: string; text: string; tint: string }> = {
    PAPER: { dot: 'bg-primary-blue', text: 'text-primary-blue', tint: 'bg-system-bBg border-system-bBd' },
    BACKTEST: { dot: 'bg-primary-emerald', text: 'text-primary-emerald', tint: 'bg-system-tBg border-system-tBd' },
    DEMO: { dot: 'bg-warning', text: 'text-warning', tint: 'bg-system-gBg border-system-gBd' },
    LIVE_DISABLED: { dot: 'bg-danger', text: 'text-danger', tint: 'bg-system-rBg border-system-rBd' },
};

const EnvironmentBanner = () => {
    const [environment, setEnvironment] = useState<Environment | null>(null);
    const [error, setError] = useState<string | null>(null);
    const pathname = usePathname();
    const isAuthRoute = pathname === '/login' || pathname === '/register';

    useEffect(() => {
        if (isAuthRoute) return;
        systemAPI.getEnvironmentState()
            .then(data => setEnvironment(data.environment))
            .catch(err => {
                console.error("Failed to fetch environment state:", err);
                setError("Could not determine operating environment.");
            });
    }, [isAuthRoute]);

    if (isAuthRoute) return null;

    if (error) {
        return (
            <div className="w-full text-center py-2 px-4 font-mono text-[11px] tracking-wider text-warning bg-system-gBg border-b border-system-gBd">
                {error}
            </div>
        );
    }

    if (!environment) {
        return <div className="w-full h-[34px] bg-background-card border-b border-border-subtle animate-pulse"></div>;
    }

    const style = environmentStyles[environment];

    return (
        <div className={`w-full flex items-center justify-center gap-2.5 py-2 px-4 sticky top-0 z-50 border-b backdrop-blur-md ${style.tint}`}>
            <span className={`w-2 h-2 rounded-full ${style.dot} animate-pulse`} aria-hidden="true" />
            <span className="font-mono text-[11px] font-bold uppercase tracking-[0.18em] text-text-muted">
                Operating Environment
            </span>
            <span className={`font-mono text-[11px] font-bold uppercase tracking-[0.18em] ${style.text}`}>
                {environment.replace('_', ' ')}
            </span>
        </div>
    );
};

export default EnvironmentBanner;