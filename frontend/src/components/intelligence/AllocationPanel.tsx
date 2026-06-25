'use client';

import { useEffect, useState } from 'react';
import { portfolioAPI, type AllocationItem, type RebalanceEventItem } from '@/lib/api';
import { Loader2, PieChart, History, BrainCircuit } from 'lucide-react';

const CLASS_COLORS: Record<string, string> = {
  CRYPTO: 'bg-primary-gold',
  METAL: 'bg-primary-emerald',
  ENERGY: 'bg-danger',
  EQUITY_INDEX: 'bg-primary-blue',
  FX: 'bg-text-muted',
};

export function AllocationPanel({ portfolioId }: { portfolioId: string }) {
  const [allocations, setAllocations] = useState<AllocationItem[]>([]);
  const [rebalances, setRebalances] = useState<RebalanceEventItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    Promise.all([
      portfolioAPI.getAllocations(portfolioId).catch(() => []),
      portfolioAPI.getRebalances(portfolioId, 5).catch(() => []),
    ])
      .then(([alloc, rebal]) => {
        if (!active) return;
        setAllocations(alloc || []);
        setRebalances(rebal || []);
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [portfolioId]);

  if (loading) {
    return <div className="card flex items-center justify-center h-32"><Loader2 className="w-6 h-6 animate-spin text-primary-gold" /></div>;
  }

  // Not an auto-managed portfolio (or no data yet): render nothing to keep manual portfolios clean.
  if (allocations.length === 0 && rebalances.length === 0) return null;

  const latest = rebalances[0];
  const totalTarget = allocations.reduce((s, a) => s + a.target_weight_pct, 0);
  const cashPct = Math.max(0, 100 - totalTarget);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Target vs actual weights */}
      <div className="lg:col-span-2 card">
        <div className="flex items-center justify-between mb-4 border-b border-border-subtle pb-3">
          <div className="flex items-center gap-2">
            <PieChart className="w-4 h-4 text-primary-gold" />
            <h3 className="font-display text-[15px] font-bold text-text-primary">AI Allocation</h3>
          </div>
          {latest?.regime && (
            <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted">
              Regime: <span className="text-text-secondary font-bold">{latest.regime}</span>
            </span>
          )}
        </div>

        <div className="space-y-3">
          {allocations.map((a) => (
            <div key={a.symbol}>
              <div className="flex items-center justify-between mb-1 gap-2 min-w-0">
                <span className="font-mono text-[12px] text-text-secondary truncate min-w-0">
                  {a.symbol} <span className="text-text-muted">· {a.display_name}</span>
                </span>
                <span className="font-mono text-[11px] tabular-nums text-text-muted shrink-0 whitespace-nowrap">
                  <span className="text-text-primary font-bold">{a.target_weight_pct.toFixed(1)}%</span> target
                  <span className="mx-1">/</span>
                  <span className={(a.current_weight_pct ?? 0) > 100 ? 'text-danger font-bold' : ''}>
                    {a.current_weight_pct.toFixed(1)}% actual
                  </span>
                  {(a.current_weight_pct ?? 0) > 100 && <span className="tag red ml-1">!</span>}
                </span>
              </div>
              <div className="h-2 rounded-full bg-background-base overflow-hidden relative">
                <div className={`h-full rounded-full ${CLASS_COLORS[a.asset_class ?? 'FX'] ?? 'bg-primary-gold'} opacity-50`} style={{ width: `${Math.min(100, a.target_weight_pct)}%` }} />
                <div className={`h-full rounded-full ${CLASS_COLORS[a.asset_class ?? 'FX'] ?? 'bg-primary-gold'} absolute top-0 left-0`} style={{ width: `${Math.min(100, a.current_weight_pct)}%` }} />
              </div>
            </div>
          ))}
          <div className="flex items-center justify-between pt-2 border-t border-border-subtle">
            <span className="font-mono text-[12px] text-text-muted">Cash / Reserve</span>
            <span className="font-mono text-[12px] font-bold text-text-primary tabular-nums">{cashPct.toFixed(1)}%</span>
          </div>
        </div>
      </div>

      {/* Recent rebalance decisions */}
      <div className="lg:col-span-1 card">
        <div className="flex items-center gap-2 mb-4 border-b border-border-subtle pb-3">
          <History className="w-4 h-4 text-primary-gold" />
          <h3 className="font-display text-[15px] font-bold text-text-primary">Rebalance Log</h3>
        </div>
        <div className="flex flex-col gap-3">
          {rebalances.length === 0 && <span className="text-[12px] text-text-muted">No rebalances yet.</span>}
          {rebalances.map((r) => (
            <div key={r.id} className="rounded-lg bg-background-base border border-border-subtle p-2.5">
              <div className="flex items-center justify-between mb-1">
                <span className="font-mono text-[10px] uppercase tracking-wider text-primary-gold-bright flex items-center gap-1">
                  <BrainCircuit className="w-3 h-3" /> {r.trigger || 'REBALANCE'}
                </span>
                <span className="font-mono text-[9px] text-text-muted">{new Date(r.created_at).toLocaleDateString()}</span>
              </div>
              <div className="flex items-center gap-3 text-[11px] font-mono text-text-secondary">
                <span>Regime: <span className="text-text-primary">{r.regime ?? '—'}</span></span>
                {r.global_risk_score != null && <span>Risk: <span className="text-text-primary">{Math.round(r.global_risk_score)}</span></span>}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
