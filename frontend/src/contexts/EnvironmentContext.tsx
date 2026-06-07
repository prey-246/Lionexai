'use client';

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { systemAPI } from '@/lib/api';

type Environment = 'BACKTEST' | 'PAPER' | 'DEMO' | 'LIVE_DISABLED';

type EnvironmentContextType = {
  environment: Environment;
  isLoading: boolean;
};

const EnvironmentContext = createContext<EnvironmentContextType | undefined>(undefined);

export const EnvironmentProvider = ({ children }: { children: ReactNode }) => {
  const [environment, setEnvironment] = useState<Environment>('PAPER');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    systemAPI.getEnvironmentState().then(state => {
      setEnvironment(state.environment);
      setIsLoading(false);
    }).catch(() => setIsLoading(false));
  }, []);

  return (
    <EnvironmentContext.Provider value={{ environment, isLoading }}>
      {children}
    </EnvironmentContext.Provider>
  );
};

export const useEnvironment = (): EnvironmentContextType => {
  const context = useContext(EnvironmentContext);
  if (context === undefined) {
    throw new Error('useEnvironment must be used within an EnvironmentProvider');
  }
  return context;
};