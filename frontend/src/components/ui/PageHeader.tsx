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
    <div className="relative border-b border-border-default pb-5 mb-2">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-4 min-w-0">
          {icon && (
            <div className="shrink-0 grid place-items-center w-11 h-11 rounded-xl bg-system-gBg border border-system-gBd text-primary-gold-bright">
              {icon}
            </div>
          )}
          <div className="min-w-0">
            <h2 className="font-display text-[26px] md:text-[28px] font-bold tracking-tight text-text-primary leading-tight">{title}</h2>
            <p className="mt-1 text-[14px] text-text-muted">{subtitle}</p>
          </div>
        </div>
        {children && <div className="shrink-0 flex flex-wrap items-center gap-3">{children}</div>}
      </div>
    </div>
  );
};