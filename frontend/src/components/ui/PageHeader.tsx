'use client';

import React from 'react';

interface PageHeaderProps {
  title: string;
  subtitle: string;
  icon?: React.ReactNode;
  children?: React.ReactNode;
}

export const PageHeader = ({ title, subtitle, icon, children }: PageHeaderProps) => {
  return (
    <div className="border-b border-border-secondary pb-5">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4">
          {icon && <div className="shrink-0">{icon}</div>}
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-text-primary">{title}</h2>
            <p className="mt-1 text-sm text-text-muted">{subtitle}</p>
          </div>
        </div>
        {children && <div className="mt-4 md:mt-0">{children}</div>}
      </div>
    </div>
  );
};