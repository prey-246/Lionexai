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
import { formatCurrency, formatFixed, toFiniteNumber } from '@/lib/format';

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
        <MetricDisplay label="Total Equity" value={formatCurrency(toFiniteNumber(portfolio.total_equity))} icon={Wallet} />
        <MetricDisplay label="Total P&L" value={formatCurrency(toFiniteNumber(stats.total_pnl))} trend={toFiniteNumber(stats.total_pnl) >= 0 ? 'up' : 'down'} icon={Activity} />
        <MetricDisplay label="Win Rate" value={`${formatFixed(toFiniteNumber(stats.win_rate_pct), 1)}%`} icon={TrendingUp} />
        <MetricDisplay label="Total Trades" value={String(toFiniteNumber(stats.total_trades, 0))} icon={TrendingUp} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Risk Context */}
        <div className="lg:col-span-1">
          <RiskContextDisplay riskContext={portfolio.risk_context} />
        </div>

        {/* Right Column: Equity Curve */}
        <div className="lg:col-span-2 card">
           <h3 className="text-[15px] font-semibold text-text-primary mb-3">Equity Curve</h3>
           <EquityCurveChart data={equityCurve} />
        </div>
      </div>

      {/* Recent Trades Table */}
      <div>
        <h3 className="sec-head">Recent Trades</h3>
        <div className="card p-0 overflow-x-auto">
          <table className="nexa-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Side</th>
                <th>Size</th>
                <th>Entry Price</th>
                <th>P&L</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {trades.slice(0, 10).map(trade => {
                const pnl = trade.pnl;
                const hasPnl = pnl != null;
                return (
                <tr key={trade.id}>
                  <td className="font-mono font-bold text-primary-emerald-bright">{trade.symbol}</td>
                  <td><span className={`tag ${trade.side === 'BUY' ? 'teal' : 'red'}`}>{trade.side}</span></td>
                  <td className="font-mono">{formatFixed(trade.size, 4, '—')}</td>
                  <td className="font-mono">{formatCurrency(trade.entry_price, '—')}</td>
                  <td className={`font-mono font-bold ${!hasPnl ? 'text-text-secondary' : toFiniteNumber(pnl) >= 0 ? 'text-success' : 'text-danger'}`}>
                    {formatCurrency(pnl, '—')}
                  </td>
                  <td><span className="tag grey">{trade.status}</span></td>
                </tr>
              );})}
              {trades.length === 0 && (
                <tr><td colSpan={6} className="text-center py-8 text-text-muted">No trades yet for this portfolio.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}