'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import { portfolioAPI } from '@/lib/api';
import type { Portfolio, PortfolioStats, EquityDataPoint, Trade } from '@/lib/types';
import { PageHeader } from '@/components/ui/PageHeader';
import { MetricDisplay } from '@/components/ui/MetricDisplay';
import { EquityCurveChart } from '@/components/charts/EquityCurveChart';
import { Loader2, AlertTriangle, Wallet, Activity, TrendingUp, TrendingDown, Check, X } from 'lucide-react';

function formatTimestamp(isoString: string) {
  const date = new Date(isoString);
  return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
}

export default function PortfolioDetailPage() {
  const params = useParams();
  const id = params.id as string;

  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [stats, setStats] = useState<PortfolioStats | null>(null);
  const [equityCurve, setEquityCurve] = useState<EquityDataPoint[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;

    const fetchAllData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [portfolioData, statsData, equityCurveData, tradesData] = await Promise.all([
          portfolioAPI.getPortfolio(id),
          portfolioAPI.getStats(id),
          portfolioAPI.getEquityCurve(id),
          portfolioAPI.getTrades(id, 'CLOSED'),
        ]);
        setPortfolio(portfolioData);
        setStats(statsData);
        setEquityCurve(equityCurveData);
        setTrades(tradesData);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchAllData();
  }, [id]);

  if (loading) {
    return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin" /></div>;
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-danger">
        <AlertTriangle className="w-12 h-12 mb-4" />
        <h2 className="text-xl font-semibold">Failed to load portfolio data</h2>
        <p className="text-sm">{error}</p>
      </div>
    );
  }

  if (!portfolio || !stats) {
    return <div>Portfolio not found.</div>;
  }

  return (
    <div className="space-y-8">
      <PageHeader title={portfolio.id} subtitle="Portfolio Analytics Dashboard" />

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricDisplay label="Total Equity" value={`$${portfolio.total_equity.toLocaleString()}`} icon={Wallet} />
        <MetricDisplay label="Total P&L" value={`$${stats.total_pnl.toLocaleString()}`} trend={stats.total_pnl > 0 ? 'up' : 'down'} icon={Activity} />
        <MetricDisplay label="Win Rate" value={`${stats.win_rate_pct}%`} icon={TrendingUp} />
        <MetricDisplay label="Total Trades" value={stats.total_trades} icon={TrendingDown} />
      </div>

      <div className="bg-background-panel-1 border border-border-secondary rounded-lg p-6">
        <h3 className="text-lg font-semibold text-text-primary mb-4">Equity Curve</h3>
        <EquityCurveChart data={equityCurve} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div>
          <h3 className="text-lg font-semibold text-text-primary mb-4">Performance Statistics</h3>
          <div className="bg-background-panel-1 border border-border-secondary rounded-lg">
            <dl className="divide-y divide-border-secondary">
              <div className="px-4 py-3 grid grid-cols-2 gap-4"><dt className="text-sm text-text-muted">Avg. P&L / Trade</dt><dd className="text-sm text-text-primary text-right font-mono">${stats.avg_pnl_per_trade.toLocaleString()}</dd></div>
              <div className="px-4 py-3 grid grid-cols-2 gap-4"><dt className="text-sm text-text-muted">Winning Trades</dt><dd className="text-sm text-status-success text-right font-mono">{stats.winning_trades}</dd></div>
              <div className="px-4 py-3 grid grid-cols-2 gap-4"><dt className="text-sm text-text-muted">Losing Trades</dt><dd className="text-sm text-status-danger text-right font-mono">{stats.losing_trades}</dd></div>
              <div className="px-4 py-3 grid grid-cols-2 gap-4"><dt className="text-sm text-text-muted">Best Trade</dt><dd className="text-sm text-status-success text-right font-mono">+${stats.best_trade_pnl.toLocaleString()}</dd></div>
              <div className="px-4 py-3 grid grid-cols-2 gap-4"><dt className="text-sm text-text-muted">Worst Trade</dt><dd className="text-sm text-status-danger text-right font-mono">-${Math.abs(stats.worst_trade_pnl).toLocaleString()}</dd></div>
            </dl>
          </div>
        </div>
        <div>
          <h3 className="text-lg font-semibold text-text-primary mb-4">Recent Trades</h3>
          <div className="bg-background-panel-1 border border-border-secondary rounded-lg max-h-96 overflow-y-auto">
            <table className="min-w-full divide-y divide-border-secondary text-sm">
              <thead className="bg-background-panel-2 sticky top-0">
                <tr>
                  <th className="px-4 py-2 text-left text-xs font-medium text-text-muted uppercase tracking-wider">Symbol</th>
                  <th className="px-4 py-2 text-left text-xs font-medium text-text-muted uppercase tracking-wider">Side</th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-text-muted uppercase tracking-wider">P&L</th>
                  <th className="px-4 py-2 text-right text-xs font-medium text-text-muted uppercase tracking-wider">Closed At</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-secondary">
                {trades.slice(0, 20).map(trade => (
                  <tr key={trade.id}>
                    <td className="px-4 py-3 font-mono text-primary-blue">{trade.symbol}</td>
                    <td className={`px-4 py-3 font-semibold ${trade.side === 'BUY' ? 'text-status-success' : 'text-status-danger'}`}>{trade.side}</td>
                    <td className={`px-4 py-3 text-right font-mono ${trade.pnl > 0 ? 'text-status-success' : 'text-status-danger'}`}>
                      {trade.pnl > 0 ? '+' : ''}${trade.pnl.toFixed(2)}
                    </td>
                    <td className="px-4 py-3 text-right text-text-muted font-mono text-xs">{trade.closed_at ? formatTimestamp(trade.closed_at) : 'N/A'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
