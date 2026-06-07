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

  let color = 'bg-gray-500/20 text-gray-400 border-gray-500/30';
  let Icon = Shield;

  if (mandate.risk_tier === 'Low') {
    color = 'bg-primary-teal/20 text-primary-teal border-primary-teal/30';
    Icon = Shield;
  } else if (mandate.risk_tier === 'Medium') {
    color = 'bg-primary-blue/20 text-primary-blue border-primary-blue/30';
    Icon = Target;
  } else if (mandate.risk_tier === 'High') {
    color = 'bg-primary-gold/20 text-primary-gold border-primary-gold/30';
    Icon = Zap;
  }

  return (
    <div className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full border text-[10px] font-semibold tracking-wide uppercase ${color}`}>
      <Icon className="w-3 h-3" />
      {mandate.name} ({mandate.risk_tier})
    </div>
  );
};

export default MandateBadge;