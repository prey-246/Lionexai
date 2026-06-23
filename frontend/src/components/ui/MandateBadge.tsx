'use client';

import React, { useEffect, useState } from 'react';
import { systemAPI } from '@/lib/api';
import { Shield, Zap, Target } from 'lucide-react';
import type { RiskMandate } from '@/lib/types';

interface MandateBadgeProps {
  mandateId: string | undefined | null;
}

const MandateBadge = ({ mandateId }: MandateBadgeProps) => {
  const [mandate, setMandate] = useState<RiskMandate | null>(null);

  useEffect(() => {
    if (mandateId) {
      systemAPI.getMandate(mandateId)
        .then(data => setMandate(data))
        .catch(err => console.error("Failed to fetch mandate details", err));
    }
  }, [mandateId]);

  if (!mandate) {
    return <span className="text-xs text-text-muted animate-pulse">Loading...</span>;
  }

  let color = 'bg-background-panel text-text-muted border-border-default';
  let Icon = Shield;

  if (mandate.risk_tier === 'Low') {
    color = 'bg-system-tBg text-primary-emerald-bright border-system-tBd';
    Icon = Shield;
  } else if (mandate.risk_tier === 'Medium') {
    color = 'bg-system-bBg text-primary-blue border-system-bBd';
    Icon = Target;
  } else if (mandate.risk_tier === 'High') {
    color = 'bg-system-gBg text-primary-gold-bright border-system-gBd';
    Icon = Zap;
  }

  return (
    <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border text-[10px] font-mono font-bold tracking-wide uppercase ${color}`}>
      <Icon className="w-3 h-3 shrink-0" />
      {mandate.name} ({mandate.risk_tier})
    </div>
  );
};

export default MandateBadge;