'use client';

import { useMemo, useState, useEffect } from 'react';
import { portfolioAPI } from '@/lib/api';
import type { Portfolio, PortfolioStats, Trade } from '@/lib/types';
import { PageHeader } from '@/components/ui/PageHeader';
import { Loader2, AlertTriangle, Wallet, Activity, TrendingUp, Percent } from 'lucide-react';
import { RiskContextDisplay } from '@/components/ui/RiskContextDisplay';
import { MetricDisplay } from '@/components/ui/MetricDisplay';
import { EquityCurveChart } from '@/components/charts/EquityCurveChart';
import { AllocationPanel } from '@/components/intelligence/AllocationPanel';
import { SettlementHistoryPanel } from '@/components/intelligence/SettlementHistoryPanel';
import MandateBadge from '@/components/ui/MandateBadge';
import { computeEquityReturns, formatCurrency, formatFixed, toFiniteNumber } from '@/lib/format';

export default function PortfolioDetailPage({ params }: { params: { id: string } }) {
  const [portfolio, setPortfolio] = useState<Portfolio | null>(null);
  const [stats, setStats] = useState<PortfolioStats | null>(null);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [equityCurve, setEquityCurve] = useState<any[]>([]);
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

  const returns = useMemo(() => computeEquityReturns(equityCurve), [equityCurve]);

  const returnBadgeClass = (value: number | null) => {
    if (value == null) return 'text-text-muted border-border-default bg-background-panel';
    return value >= 0
      ? 'text-primary-emerald border-system-tBd bg-system-tBg'
      : 'text-danger border-system-rBd bg-system-rBg';
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-gold" />
      </div>
    );
  }

  if (error || !portfolio || !stats) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-danger">
        <AlertTriangle className="w-12 h-12 mb-4" />
        <h2 className="text-xl font-semibold">Failed to load portfolio data</h2>
        <p className="text-sm">{error || 'Could not fetch portfolio details.'}</p>
      </div>
    );
  }

  const isValidated = portfolio.id.endsWith('-VALIDATED');

  return (
    <div className="space-y-8 min-w-0">
      <PageHeader
        title={`Portfolio: ${portfolio.id}`}
        subtitle="Detailed performance and risk analysis for this portfolio."
      >
        <MandateBadge mandateId={portfolio.mandate_id} />
        <span
          className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 font-mono text-[12px] font-bold ${returnBadgeClass(returns.totalReturnPct)}`}
        >
          <Percent className="w-3.5 h-3.5" />
          Total Return{' '}
          {returns.totalReturnPct != null ? `${formatFixed(returns.totalReturnPct, 2)}%` : '—'}
        </span>
        <span
          className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 font-mono text-[12px] font-bold ${returnBadgeClass(returns.weeklyReturnPct)}`}
        >
          <TrendingUp className="w-3.5 h-3.5" />
          7D Return{' '}
          {returns.weeklyReturnPct != null ? `${formatFixed(returns.weeklyReturnPct, 2)}%` : '—'}
        </span>
      </PageHeader>

      {(portfolio as { auto_managed?: boolean }).auto_managed !== false && portfolio.id.startsWith('LNX-') && (
        <div className={`card p-4 flex items-start gap-3 text-[13px] text-text-secondary ${isValidated ? 'blue' : ''}`}>
          <AlertTriangle className="w-5 h-5 shrink-0 text-warning" />
          <p>
            {isValidated ? (
              <>
                This is an institutional <strong>VALIDATED_HISTORICAL</strong> reference portfolio (admin@google.com).
                Metrics, allocations, and rebalance history are derived from the validated backtest run on real market bars.
              </>
            ) : (
              <>
                Portfolio equity and trade stats here reflect the <strong>operational ledger</strong> (DEMO when institutionally seeded).
                Fund-level strategy performance on historical market data is validated separately — see{' '}
                <a href="/fund-performance" className="text-primary-gold underline">Fund Performance</a>.
              </>
            )}
          </p>
        </div>
      )}

      <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4 min-w-0">
        <MetricDisplay
          label="Total Equity"
          value={formatCurrency(toFiniteNumber(portfolio.total_equity))}
          icon={Wallet}
        />
        <MetricDisplay
          label="Total P&L"
          value={formatCurrency(toFiniteNumber(stats.total_pnl))}
          trend={toFiniteNumber(stats.total_pnl) >= 0 ? 'up' : 'down'}
          icon={Activity}
        />
        <MetricDisplay
          label="Total Return"
          value={returns.totalReturnPct != null ? `${formatFixed(returns.totalReturnPct, 2)}%` : '—'}
          trend={
            returns.totalReturnPct != null
              ? returns.totalReturnPct >= 0
                ? 'up'
                : 'down'
              : undefined
          }
          icon={Percent}
        />
        <MetricDisplay
          label="7D Return"
          value={returns.weeklyReturnPct != null ? `${formatFixed(returns.weeklyReturnPct, 2)}%` : '—'}
          trend={
            returns.weeklyReturnPct != null
              ? returns.weeklyReturnPct >= 0
                ? 'up'
                : 'down'
              : undefined
          }
          icon={TrendingUp}
        />
        <MetricDisplay
          label="Win Rate"
          value={`${formatFixed(toFiniteNumber(stats.win_rate_pct), 1)}%`}
          icon={TrendingUp}
        />
        <MetricDisplay
          label="Total Trades"
          value={String(toFiniteNumber(stats.total_trades, 0))}
          icon={Activity}
        />
      </div>

      <div className="card min-w-0 overflow-hidden">
        <h3 className="text-[15px] font-semibold text-text-primary mb-3">Equity Curve</h3>
        <EquityCurveChart data={equityCurve} />
      </div>

      <RiskContextDisplay riskContext={portfolio.risk_context} />

      <AllocationPanel portfolioId={params.id} />
      <SettlementHistoryPanel portfolioId={params.id} />

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
              {trades.slice(0, 10).map((trade) => {
                const pnl = trade.pnl;
                const hasPnl = pnl != null;
                return (
                  <tr key={trade.id}>
                    <td className="font-mono font-bold text-primary-emerald-bright">{trade.symbol}</td>
                    <td>
                      <span className={`tag ${trade.side === 'BUY' ? 'teal' : 'red'}`}>{trade.side}</span>
                    </td>
                    <td className="font-mono">{formatFixed(trade.size, 4, '—')}</td>
                    <td className="font-mono">{formatCurrency(trade.entry_price, '—')}</td>
                    <td
                      className={`font-mono font-bold ${!hasPnl ? 'text-text-secondary' : toFiniteNumber(pnl) >= 0 ? 'text-success' : 'text-danger'}`}
                    >
                      {formatCurrency(pnl, '—')}
                    </td>
                    <td>
                      <span className="tag grey">{trade.status}</span>
                    </td>
                  </tr>
                );
              })}
              {trades.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center py-8 text-text-muted">
                    No trades yet for this portfolio.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
