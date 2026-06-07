'use client';

import { useState, useEffect } from 'react';
import { systemAPI } from '@/lib/api';
import type { RiskMandate } from '@/lib/types';
import { PageHeader } from '@/components/ui/PageHeader';
import { Loader2, ShieldCheck } from 'lucide-react';

export default function MandatesPage() {
  const [mandates, setMandates] = useState<RiskMandate[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    systemAPI.getMandates()
      .then(setMandates)
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary-gold" /></div>;
  }

  if (error) {
    return <div className="text-center text-danger">{error}</div>;
  }

  return (
    <div className="space-y-8">
      <PageHeader title="Risk Mandates" subtitle="View the standardized risk profiles governing portfolios." />

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {mandates.map(mandate => (
          <div key={mandate.id} className="bg-background-panel-1 border border-border-secondary rounded-lg p-6">
            <div className="flex items-center gap-3 mb-4">
              <ShieldCheck className="w-6 h-6 text-primary-blue" />
              <div>
                <h3 className="text-lg font-semibold text-text-primary">{mandate.name}</h3>
                <p className="text-sm font-mono text-primary-gold">{mandate.id}</p>
              </div>
            </div>
            <ul className="space-y-2 text-sm text-text-muted">
              <li className="flex justify-between"><span>Max Leverage:</span> <span className="font-mono">{mandate.max_leverage}x</span></li>
              <li className="flex justify-between"><span>Max Drawdown:</span> <span className="font-mono">{mandate.max_drawdown_pct}%</span></li>
              <li className="flex justify-between"><span>Daily Loss Limit:</span> <span className="font-mono">{mandate.daily_loss_limit_pct}%</span></li>
              <li className="flex justify-between"><span>Kill Switch:</span> <span className={`font-mono ${mandate.kill_switch_active ? 'text-danger' : 'text-success'}`}>{mandate.kill_switch_active ? 'ACTIVE' : 'Inactive'}</span></li>
              <li className="flex justify-between"><span>Status:</span> <span className={`font-mono ${mandate.is_active ? 'text-success' : 'text-text-muted'}`}>{mandate.is_active ? 'Active' : 'Inactive'}</span></li>
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}