'use client';

import { useEffect, useState } from 'react';
import { analyticsAPI } from '@/lib/api/analytics';
import type { PortfolioCompareItem, StrategyAnalytics } from '@/lib/api/analytics';
import { portfolioAPI } from '@/lib/api';
import { PageHeader } from '@/components/ui/PageHeader';
import { Loader2, GitCompare } from 'lucide-react';
import { formatCurrency, formatFixed } from '@/lib/format';
import { SimpleTimeSeriesChart } from '@/components/charts/SimpleTimeSeriesChart';

type Tab = 'portfolios' | 'strategies';

export default function AnalyticsComparePage() {
  const [tab, setTab] = useState<Tab>('portfolios');
  const [portfolios, setPortfolios] = useState<{ id: string }[]>([]);
  const [selectedPortfolios, setSelectedPortfolios] = useState<string[]>([]);
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>([]);
  const [strategyOptions, setStrategyOptions] = useState<StrategyAnalytics[]>([]);
  const [portfolioResults, setPortfolioResults] = useState<PortfolioCompareItem[]>([]);
  const [strategyResults, setStrategyResults] = useState<StrategyAnalytics[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    portfolioAPI.listPortfolios().then(setPortfolios).catch(() => {});
    analyticsAPI.getStrategyAnalytics('AUTONOMOUS').then(setStrategyOptions).catch(() => {});
  }, []);

  const runCompare = async () => {
    setLoading(true);
    try {
      if (tab === 'portfolios' && selectedPortfolios.length >= 2) {
        setPortfolioResults(await analyticsAPI.comparePortfolios(selectedPortfolios));
      } else if (tab === 'strategies' && selectedStrategies.length >= 2) {
        setStrategyResults(await analyticsAPI.compareStrategies(selectedStrategies));
      }
    } catch (err) {
      alert(String(err));
    } finally {
      setLoading(false);
    }
  };

  const togglePortfolio = (id: string) => {
    setSelectedPortfolios(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id].slice(0, 6));
  };

  const toggleStrategy = (name: string) => {
    setSelectedStrategies(prev => prev.includes(name) ? prev.filter(x => x !== name) : [...prev, name].slice(0, 6));
  };

  return (
    <div className="space-y-6">
      <PageHeader title="Analytics Comparison" subtitle="Side-by-side portfolio and strategy performance comparison." />

      <div className="flex gap-2">
        {(['portfolios', 'strategies'] as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-[13px] font-semibold rounded-lg border capitalize transition-colors ${tab === t ? 'bg-system-gBg border-system-gBd text-primary-gold-bright' : 'bg-background-panel border-border-default text-text-secondary hover:text-text-primary'}`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === 'portfolios' ? (
        <div className="space-y-4">
          <p className="text-sm text-text-secondary">Select 2–6 portfolios to compare:</p>
          <div className="flex flex-wrap gap-2">
            {portfolios.map(p => (
              <button
                key={p.id}
                onClick={() => togglePortfolio(p.id)}
                className={`px-3 py-1.5 text-[13px] rounded-lg border transition-colors ${selectedPortfolios.includes(p.id) ? 'border-system-gBd bg-system-gBg text-primary-gold-bright' : 'border-border-default text-text-secondary hover:text-text-primary'}`}
              >
                {p.id}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <p className="text-sm text-text-secondary">Select 2–6 autonomous strategies to compare:</p>
          <div className="flex flex-wrap gap-2">
            {(strategyOptions.length ? strategyOptions : [{ strategy_name: 'No strategies yet' } as StrategyAnalytics]).map(s => (
              s.strategy_name !== 'No strategies yet' ? (
                <button
                  key={s.strategy_name}
                  onClick={() => toggleStrategy(s.strategy_name)}
                  className={`px-3 py-1.5 text-[13px] rounded-lg border transition-colors ${selectedStrategies.includes(s.strategy_name) ? 'border-system-gBd bg-system-gBg text-primary-gold-bright' : 'border-border-default text-text-secondary hover:text-text-primary'}`}
                >
                  {s.strategy_name}
                </button>
              ) : (
                <span key="empty" className="text-text-muted text-sm">Run autonomous trading to populate strategy analytics.</span>
              )
            ))}
          </div>
        </div>
      )}

      <button onClick={runCompare} disabled={loading} className="btn gold flex items-center gap-2">
        {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <GitCompare className="w-4 h-4" />}
        Compare Selected
      </button>

      {portfolioResults.length >= 2 && tab === 'portfolios' && (
        <>
          <div className="overflow-x-auto card p-0">
            <table className="nexa-table w-full">
              <thead>
                <tr>
                  <th>Portfolio</th><th>Equity</th><th>Trades</th><th>Win Rate</th><th>Total P&L</th><th>Drawdown</th>
                </tr>
              </thead>
              <tbody>
                {portfolioResults.map(r => (
                  <tr key={r.portfolio_id}>
                    <td className="font-semibold font-mono text-primary-gold-bright">{r.portfolio_id}</td>
                    <td>{formatCurrency(r.total_equity)}</td>
                    <td>{r.total_trades}</td>
                    <td>{formatFixed(r.win_rate_pct, 1)}%</td>
                    <td className={r.total_pnl >= 0 ? 'text-success' : 'text-danger'}>{formatCurrency(r.total_pnl)}</td>
                    <td>{formatFixed(r.current_drawdown_pct, 1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {portfolioResults.map(r => r.equity_curve.length >= 2 ? (
            <div key={r.portfolio_id} className="card p-4">
              <h3 className="text-[15px] font-semibold mb-3">{r.portfolio_id} Equity Curve</h3>
              <SimpleTimeSeriesChart
                data={r.equity_curve.map(p => ({ time: Math.floor(new Date(p.timestamp).getTime() / 1000), value: p.equity }))}
              />
            </div>
          ) : null)}
        </>
      )}

      {strategyResults.length >= 2 && tab === 'strategies' && (
        <div className="overflow-x-auto card p-0">
          <table className="nexa-table w-full">
            <thead>
              <tr>
                <th>Strategy</th><th>Trades</th><th>Wins</th><th>Losses</th><th>Win Rate</th><th>Total P&L</th><th>Avg P&L</th>
              </tr>
            </thead>
            <tbody>
              {strategyResults.map(r => (
                <tr key={r.strategy_name}>
                  <td className="font-semibold text-primary-gold-bright">{r.strategy_name}</td>
                  <td>{r.total_trades}</td>
                  <td>{r.winning_trades}</td>
                  <td>{r.losing_trades}</td>
                  <td>{formatFixed(r.win_rate_pct, 1)}%</td>
                  <td className={r.total_pnl >= 0 ? 'text-success' : 'text-danger'}>{formatCurrency(r.total_pnl)}</td>
                  <td>{formatCurrency(r.avg_pnl)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
