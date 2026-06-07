'use client';

import { useEffect, useState } from 'react';
import { systemAPI } from '@/lib/api';

type Environment = 'PAPER' | 'BACKTEST' | 'DEMO' | 'LIVE_DISABLED';

const environmentStyles: Record<Environment, { bg: string; text: string }> = {
    PAPER: { bg: 'bg-blue-600', text: 'text-white' },
    BACKTEST: { bg: 'bg-green-600', text: 'text-white' },
    DEMO: { bg: 'bg-orange-500', text: 'text-white' },
    LIVE_DISABLED: { bg: 'bg-red-700', text: 'text-white' },
};

const EnvironmentBanner = () => {
    const [environment, setEnvironment] = useState<Environment | null>(null);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        systemAPI.getEnvironmentState()
            .then(data => setEnvironment(data.environment))
            .catch(err => {
                console.error("Failed to fetch environment state:", err);
                setError("Could not determine operating environment.");
            });
    }, []);

    if (error) {
        return <div className="w-full text-center p-2 font-bold bg-yellow-500 text-black">{error}</div>;
    }

    if (!environment) {
        return <div className="w-full p-2 h-[40px] bg-gray-800 animate-pulse"></div>;
    }

    const style = environmentStyles[environment];

    return (
        <div className={`w-full text-center p-2 font-bold ${style.bg} ${style.text} sticky top-0 z-50`}>
            OPERATING ENVIRONMENT: {environment}
        </div>
    );
};

export default EnvironmentBanner;