'use client';

import { useEffect, useState } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { MetricDisplay } from '@/components/ui/MetricDisplay';
import { fundsAPI, validatedAPI, marketAPI, type FundProduct, type GlobalMarketState } from '@/lib/api';
import { Loader2, Briefcase, TrendingUp, Shield, AlertTriangle, FlaskConical } from 'lucide-react';
import { formatFixed } from '@/lib/format';

function fmtPct(value: number | null | undefined, digits = 2): string {
  if (value == null || Number.isNaN(value)) return '—';
  return `${formatFixed(value, digits)}%`;
}

function provenanceBadge(p?: string | null) {
  const map: Record<string, string> = {
    DEMO: 'tag red',
    PAPER_LIVE: 'tag teal',
    VALIDATED_HISTORICAL: 'tag blue',
    UNVALIDATED: 'tag gold',
    UNKNOWN: 'tag grey',
  };
  return map[p || 'UNKNOWN'] || 'tag grey';
}

function metricCell(label: string, value: number | null | undefined, isRatio = false) {
  if (value == null) return '—';
  if (isRatio) return formatFixed(value, 2);
  if (String(label).includes('Drawdown')) return fmtPct(value);
  return fmtPct(value);
}

export default function FundPerformancePage() {
  const [loading, setLoading] = useState(true);
  const [funds, setFunds] = useState<FundProduct[]>([]);
  const [analytics, setAnalytics] = useState<Record<string, any>>({});
  const [globalState, setGlobalState] = useState<GlobalMarketState | null>(null);
  const [globalRisk, setGlobalRisk] = useState<any>(null);
  const [runningBacktest, setRunningBacktest] = useState(false);
  const [runningOptimization, setRunningOptimization] = useState(false);
  const [showDemo, setShowDemo] = useState(false);

  const load = () => {
    setLoading(true);
    Promise.all([
      fundsAPI.listFunds(),
      marketAPI.getGlobalState().catch(() => null),
      validatedAPI.getGlobalRisk().catch(() => null),
    ]).then(async ([f, gs, gr]) => {
      setFunds(f);
      setGlobalState(gs);
      setGlobalRisk(gr);
      const inst: Record<string, any> = {};
      await Promise.all(
        f.map(async (fund) => {
          try {
            const v = await validatedAPI.getLatestFundBacktest(fund.id, showDemo).catch(() => null);
            const legacy = await fundsAPI.getInstitutionalAnalytics(fund.id).catch(() => null);
            inst[fund.id] = { ...legacy, validated: v, ...(v || {}) };
          } catch {
            inst[fund.id] = null;
          }
        }),
      );
      setAnalytics(inst);
    }).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [showDemo]);

  const runOptimization = async () => {
    setRunningOptimization(true);
    try {
      await validatedAPI.runOptimization();
      load();
    } catch (e: any) {
      alert(e.message || 'Optimization failed');
    } finally {
      setRunningOptimization(false);
    }
  };

  const runAllBacktests = async () => {
    setRunningBacktest(true);
    try {
      await validatedAPI.runAllFundBacktests();
      load();
    } catch (e: any) {
      alert(e.message || 'Backtest failed');
    } finally {
      setRunningBacktest(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-gold" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Fund Performance"
        subtitle="Historical validated results from market_bars backtests — not seeded demo ledger."
      />

      <div className="card blue p-4 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-primary-blue shrink-0 mt-0.5" />
        <div className="text-[13px] text-text-secondary space-y-2">
          <p>
            All performance metrics shown here use <strong className="text-text-primary">VALIDATED_HISTORICAL</strong> provenance:
            multi-asset fund backtests on real OHLCV from <span className="font-mono">market_bars</span> (Binance, yfinance).
            Seeded demo trades and simulated ledger returns are <strong>not displayed</strong>.
          </p>
          <p className="text-text-muted text-[12px]">
            Treasury routing and LNX index growth are operational metrics — see Treasury and LNX pages for scope notes.
          </p>
        </div>
      </div>

      <div className="flex gap-4 flex-wrap items-center">
        <button className="btn gold flex items-center gap-2" disabled={runningOptimization} onClick={runOptimization}>
          {runningOptimization ? <Loader2 className="w-4 h-4 animate-spin" /> : <FlaskConical className="w-4 h-4" />}
          Run Alpha Optimization Program
        </button>
        <button className="btn outline flex items-center gap-2" disabled={runningBacktest} onClick={runAllBacktests}>
          {runningBacktest ? <Loader2 className="w-4 h-4 animate-spin" /> : <FlaskConical className="w-4 h-4" />}
          Baseline Backtests Only
        </button>
        <label className="flex items-center gap-2 text-[13px] cursor-pointer select-none">
          <input
            type="checkbox"
            checked={showDemo}
            onChange={(e) => setShowDemo(e.target.checked)}
            className="accent-primary-gold"
          />
          <span className={showDemo ? 'text-danger font-semibold' : 'text-text-secondary'}>
            Show demo comparison (admin)
          </span>
        </label>
      </div>

      {showDemo && (
        <div className="card p-3 text-[12px] text-text-secondary border border-system-rBd bg-system-rBg/30">
          <strong className="text-danger">Demo comparison active.</strong> Red column shows operational metrics from seeded client portfolios — not for institutional reporting.
        </div>
      )}

      <div className="g3">
        <MetricDisplay label="Global Risk Score" value={`${globalRisk?.global_risk_score?.toFixed(1) ?? globalState?.global_risk_score?.toFixed(1) ?? '—'}`} icon={Shield} />
        <MetricDisplay label="Market Regime" value={globalState?.market_regime ?? '—'} icon={TrendingUp} />
        <MetricDisplay label="Active Funds" value={funds.length} icon={Briefcase} />
      </div>

      <div className="grid gap-6 md:grid-cols-1 xl:grid-cols-3">
        {funds.map((fund) => {
          const inst = analytics[fund.id] || {};
          const prov = fund.data_provenance || inst.data_provenance || 'UNVALIDATED';
          const v = inst.validated || inst;
          const hasValidated = prov === 'VALIDATED_HISTORICAL' && v?.avg_monthly_return_pct != null;

          return (
            <div key={fund.id} className="card gold p-6 flex flex-col">
              <div className="flex items-start justify-between gap-2">
                <h3 className="font-serif text-[22px] text-text-primary">{fund.name}</h3>
                <span className={provenanceBadge(prov)}>{prov}</span>
              </div>
              <p className="font-sans text-[12px] text-text-muted mt-2 line-clamp-2">{fund.description}</p>

              {!hasValidated && (
                <p className="mt-4 text-[12px] text-warning">
                  No validated backtest yet. Click &quot;Run Historical Fund Backtests&quot; above.
                </p>
              )}

              {hasValidated && v.period_start && (
                <p className="mt-2 text-[11px] font-mono text-text-muted">
                  Period: {new Date(v.period_start).toLocaleDateString()} — {new Date(v.period_end).toLocaleDateString()}
                  {' · '}{v.simulation_days} days · {v.rebalance_count} rebalances
                </p>
              )}

              <div className="mt-6 rounded-lg border border-border-subtle bg-background-panel/50 p-4 overflow-x-auto">
                <div className={`grid ${showDemo ? 'grid-cols-4' : 'grid-cols-3'} gap-2 mb-2 pb-2 border-b border-border-default text-[9px] font-mono uppercase text-text-muted min-w-[280px]`}>
                  <span>Metric</span>
                  <span className="text-right">Target</span>
                  <span className="text-right">Historical</span>
                  {showDemo && <span className="text-right text-danger">Demo Ledger</span>}
                </div>
                {(() => {
                  const demo = v.demo_comparison as Record<string, number | null | undefined> | undefined;
                  const rows: Array<[string, number | null | undefined, number | null | undefined, number | null | undefined, boolean]> = [
                    ['Weekly Return', fund.target_weekly_return_pct, v.avg_weekly_return_pct, demo?.actual_weekly_return_pct ?? null, false],
                    ['Monthly Return', fund.target_monthly_return_pct, v.avg_monthly_return_pct, demo?.actual_monthly_return_pct ?? null, false],
                    ['CAGR', null, v.cagr_pct, null, false],
                    ['Total Return', null, v.total_return_pct, demo?.actual_total_return_pct ?? null, false],
                    ['Sharpe', null, v.sharpe_ratio, null, true],
                    ['Sortino', null, v.sortino_ratio, null, true],
                    ['Max Drawdown', null, v.max_drawdown_pct, null, false],
                    ['Calmar', null, v.calmar_ratio, null, true],
                    ['Win Rate', null, v.win_rate_pct, null, false],
                    ['Profit Factor', null, v.profit_factor, null, true],
                    ['Volatility', null, v.volatility_pct, null, false],
                    ['Yield Delivery', null, v.yield_delivery_pct, null, false],
                  ];
                  return rows.map(([label, target, actual, demoVal, isRatio]) => (
                    <div key={String(label)} className={`grid ${showDemo ? 'grid-cols-4' : 'grid-cols-3'} gap-2 py-2 border-b border-border-subtle last:border-0 text-[13px] min-w-[280px]`}>
                      <span className="text-text-muted">{label}</span>
                      <span className="font-mono text-right">{typeof target === 'number' ? fmtPct(target) : '—'}</span>
                      <span className="font-mono font-bold text-right text-primary-blue">
                        {metricCell(String(label), actual as number | null, isRatio as boolean)}
                      </span>
                      {showDemo && (
                        <span className="font-mono font-bold text-right text-danger">
                          {demoVal != null ? metricCell(String(label), demoVal as number, isRatio as boolean) : '—'}
                        </span>
                      )}
                    </div>
                  ));
                })()}
                {showDemo && (
                  <p className="mt-3 pt-2 border-t border-border-subtle text-[11px] text-text-muted">
                    Demo column: seeded client portfolios only (excludes <span className="font-mono">*-VALIDATED</span> reference).
                    Provenance:{' '}
                    <span className={provenanceBadge((v.demo_comparison as any)?.data_provenance || 'DEMO')}>
                      {(v.demo_comparison as any)?.data_provenance || 'DEMO'}
                    </span>
                    {' · '}{(v.demo_comparison as any)?.portfolio_count ?? 0} demo portfolios ·{' '}
                    AUM ${((v.demo_comparison as any)?.total_aum ?? 0).toLocaleString()}
                  </p>
                )}
              </div>

              {fund.id === 'ALPHA' && v.avg_monthly_return_pct != null && (
                <p className="mt-4 text-[12px] border-t border-border-subtle pt-3">
                  <strong>Alpha 20% monthly target:</strong>{' '}
                  {v.meets_target_monthly || v.alpha_20pct_supported
                    ? 'Met on historical data'
                    : `Not met — actual avg monthly ${fmtPct(v.avg_monthly_return_pct)}`}
                </p>
              )}

              {v.symbols_used?.length > 0 && (
                <div className="mt-4">
                  <span className="font-mono text-[10px] uppercase text-text-muted">Symbols in backtest</span>
                  <div className="flex flex-wrap gap-1.5 mt-2">
                    {v.symbols_used.map((sym: string) => (
                      <span key={sym} className="tag grey font-mono text-[10px]">{sym}</span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
