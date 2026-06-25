'use client';

import { useEffect, useState } from 'react';
import { portfolioAPI, type ClientSettlementItem } from '@/lib/api';
import { Landmark, Loader2 } from 'lucide-react';
import { formatCurrency } from '@/lib/format';

interface Props {
  portfolioId: string;
  limit?: number;
}

export function SettlementHistoryPanel({ portfolioId, limit = 12 }: Props) {
  const [rows, setRows] = useState<ClientSettlementItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    portfolioAPI.getSettlements(portfolioId, limit)
      .then(setRows)
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, [portfolioId, limit]);

  if (loading) {
    return <div className="card p-6 flex justify-center"><Loader2 className="w-6 h-6 animate-spin text-primary-gold" /></div>;
  }

  if (!rows.length) return null;

  return (
    <div className="card gold p-0 overflow-hidden">
      <div className="p-6 border-b border-border-default flex items-center gap-2">
        <Landmark className="w-4 h-4 text-primary-gold" />
        <h3 className="sec-head mb-0">Weekly Settlement & Treasury Contributions</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="nexa-table">
          <thead>
            <tr>
              <th>Week</th>
              <th>Starting NAV</th>
              <th>Trading P&L</th>
              <th>Target Yield</th>
              <th>Treasury Routed</th>
              <th>Top-ups</th>
              <th>LNX Contrib.</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td className="font-mono text-[11px]">{r.iso_week_key}</td>
                <td className="font-mono">{formatCurrency(r.starting_nav ?? r.opening_equity)}</td>
                <td className={`font-mono font-bold ${(r.trading_pnl ?? r.period_pnl) >= 0 ? 'text-primary-emerald' : 'text-danger'}`}>
                  {formatCurrency(r.trading_pnl ?? r.period_pnl)}
                </td>
                <td className="font-mono text-primary-gold">{formatCurrency(r.target_yield ?? r.client_entitlement)}</td>
                <td className="font-mono">{formatCurrency(r.treasury_routed ?? r.excess_routed)}</td>
                <td className="font-mono">{formatCurrency(r.shortfall_topups ?? r.shortfall_topup)}</td>
                <td className="font-mono">{formatCurrency(r.lnx_contribution ?? 0)}</td>
                <td><span className="tag grey">{r.status}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
