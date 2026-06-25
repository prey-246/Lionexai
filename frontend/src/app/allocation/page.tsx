'use client';

import { useEffect, useState } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { portfolioAPI, marketAPI, type AllocationItem, type GlobalMarketState } from '@/lib/api';
import type { Portfolio } from '@/lib/types';
import { Loader2, PieChart } from 'lucide-react';

export default function AllocationPage() {
  const [loading, setLoading] = useState(true);
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [selectedId, setSelectedId] = useState<string>('');
  const [allocations, setAllocations] = useState<AllocationItem[]>([]);
  const [globalState, setGlobalState] = useState<GlobalMarketState | null>(null);

  useEffect(() => {
    Promise.all([
      portfolioAPI.listPortfolios(),
      marketAPI.getGlobalState().catch(() => null),
    ]).then(([ps, gs]) => {
      const sorted = [...(ps || [])].sort((a: any, b: any) => {
        if (a.auto_managed && !b.auto_managed) return -1;
        if (!a.auto_managed && b.auto_managed) return 1;
        return a.id.localeCompare(b.id);
      });
      const auto = sorted.filter((p: any) => p.auto_managed);
      setPortfolios(auto.length ? auto : sorted);
      const pick = auto.length ? auto[0] : sorted[0];
      if (pick) setSelectedId(pick.id);
      setGlobalState(gs);
    }).finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!selectedId) return;
    portfolioAPI.getAllocations(selectedId).then(setAllocations).catch(() => setAllocations([]));
  }, [selectedId]);

  if (loading) return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary-gold" /></div>;

  return (
    <div className="space-y-8">
      <PageHeader title="Live Allocation" subtitle="Current target weights from the autonomous allocation engine." />

      <div className="card blue p-4 flex flex-wrap items-center gap-4">
        <label className="font-mono text-[11px] uppercase text-text-muted">Portfolio</label>
        <select
          className="border border-border-default rounded-lg px-3 py-2 font-mono text-[13px]"
          value={selectedId}
          onChange={(e) => setSelectedId(e.target.value)}
        >
          {portfolios.map((p) => (
            <option key={p.id} value={p.id}>{p.id}</option>
          ))}
        </select>
        {globalState && (
          <span className="tag grey ml-auto">Regime: {globalState.market_regime} · Risk: {globalState.global_risk_score?.toFixed(0)}</span>
        )}
      </div>

      <div className="card gold p-0 overflow-hidden">
        <div className="p-6 border-b border-border-default flex items-center gap-2">
          <PieChart className="w-4 h-4 text-primary-gold" />
          <h3 className="sec-head mb-0">Target vs Current Weights</h3>
        </div>
        {allocations.length === 0 ? (
          <p className="p-8 text-center text-text-muted font-sans text-[13px]">No allocations yet. Invest in a Lionex Fund to trigger the allocation engine.</p>
        ) : (
          <table className="nexa-table">
            <thead><tr><th>Asset</th><th>Class</th><th>Target %</th><th>Current %</th><th>Drift</th></tr></thead>
            <tbody>
              {allocations.map((a) => {
                const drift = (a.current_weight_pct ?? 0) - a.target_weight_pct;
                return (
                  <tr key={a.symbol}>
                    <td className="font-mono font-bold">{a.symbol}</td>
                    <td><span className="tag grey">{a.asset_class}</span></td>
                    <td className="font-mono">{a.target_weight_pct.toFixed(2)}%</td>
                    <td className="font-mono">{a.current_weight_pct?.toFixed(2) ?? '0.00'}%</td>
                    <td className={`font-mono ${Math.abs(drift) > 2 ? 'text-primary-gold' : 'text-text-secondary'}`}>{drift >= 0 ? '+' : ''}{drift.toFixed(2)}%</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
