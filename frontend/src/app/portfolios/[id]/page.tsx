'use client';

import { useState, useEffect } from 'react';
import { portfolioAPI } from '@/lib/api';
import type { Portfolio, PortfolioStats, Trade, EquityDataPoint } from '@/lib/types';
import { PageHeader } from '@/components/ui/PageHeader';
import { Loader2, AlertTriangle, Wallet, Activity, TrendingUp, TrendingDown } from 'lucide-react';
import { RiskContextDisplay } from '@/components/ui/RiskContextDisplay';
import { MetricDisplay } from '@/components/ui/MetricDisplay';
import { EquityCurveChart } from '@/components/charts/EquityCurveChart';
import MandateBadge from '@/components/ui/MandateBadge';

export default function PortfolioDetailPage({ params }: { params: { id: string } }) {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [stats, setStats] = useState<PortfolioStats | null>(null);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [equityCurve, setEquityCurve] = useState<EquityDataPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPortfolioData = async () => {
      try {
        setLoading(true);
        const [portfolioData, statsData, tradesData, equityCurveData] = await Promise.all([
          portfolioAPI.getPortfolio(params.id),
          portfolioAPI.getStats(params.id),
          portfolioAPI.getTrades(params.id),
          portfolioAPI.getEquityCurve(params.id),
        ]);
        setPortfolio(portfolioData);
        setStats(statsData);
        setTrades(tradesData);
        setEquityCurve(equityCurveData);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchPortfolioData();
  }, [params.id]);

  if (loading) {
    return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary-gold" /></div>;
  }

  if (error || !portfolio || !stats) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-danger">
        <AlertTriangle className="w-12 h-12 mb-4" />
        <h2 className="text-xl font-semibold">Failed to load portfolio data</h2>
        <p className="text-sm">{error || "Could not fetch portfolio details."}</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader title={`Portfolio: ${portfolio.id}`} subtitle="Detailed performance and risk analysis for this portfolio.">
        <MandateBadge mandateId={portfolio.mandate_id} />
      </PageHeader>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricDisplay label="Total Equity" value={`$${portfolio.total_equity.toLocaleString()}`} icon={Wallet} />
        <MetricDisplay label="Total P&L" value={`$${stats.total_pnl.toLocaleString()}`} trend={stats.total_pnl >= 0 ? 'up' : 'down'} icon={Activity} />
        <MetricDisplay label="Win Rate" value={`${stats.win_rate_pct.toFixed(1)}%`} icon={TrendingUp} />
        <MetricDisplay label="Total Trades" value={stats.total_trades} icon={TrendingUp} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Risk Context */}
        <div className="lg:col-span-1">
          <RiskContextDisplay riskContext={portfolio.risk_context} />
        </div>

        {/* Right Column: Equity Curve */}
        <div className="lg:col-span-2 bg-background-panel-1 border border-border-secondary rounded-lg p-4">
           <h3 className="text-md font-semibold text-text-primary mb-2">Equity Curve</h3>
           <EquityCurveChart data={equityCurve} />
        </div>
      </div>

      {/* Recent Trades Table */}
      <div>
        <h3 className="text-lg font-semibold text-text-primary mb-4">Recent Trades</h3>
        <div className="bg-background-panel-1 border border-border-secondary rounded-lg overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-background-panel-2">
              <tr>
                <th className="px-6 py-3 font-medium text-text-muted">Symbol</th>
                <th className="px-6 py-3 font-medium text-text-muted">Side</th>
                <th className="px-6 py-3 font-medium text-text-muted">Size</th>
                <th className="px-6 py-3 font-medium text-text-muted">Entry Price</th>
                <th className="px-6 py-3 font-medium text-text-muted">P&L</th>
                <th className="px-6 py-3 font-medium text-text-muted">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-secondary">
              {trades.slice(0, 10).map(trade => (
                <tr key={trade.id}>
                  <td className="px-6 py-4 font-mono text-primary-teal">{trade.symbol}</td>
                  <td className={`px-6 py-4 font-semibold ${trade.side === 'BUY' ? 'text-success' : 'text-danger'}`}>{trade.side}</td>
                  <td className="px-6 py-4 font-mono">{trade.size}</td>
                  <td className="px-6 py-4 font-mono">${trade.entry_price.toLocaleString()}</td>
                  <td className={`px-6 py-4 font-mono ${trade.pnl >= 0 ? 'text-success' : 'text-danger'}`}>{trade.pnl.toFixed(2)}</td>
                  <td className="px-6 py-4"><span className="px-2 py-1 text-xs rounded-full bg-gray-700 text-gray-300">{trade.status}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}