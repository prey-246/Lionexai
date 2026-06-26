'use client';

import { useState, useEffect, useRef } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { MetricDisplay } from '@/components/ui/MetricDisplay';
import { lnxAPI, treasuryAPI, institutionalAPI, type LNXIndexData } from '@/lib/api';
import { createChart, ColorType, Time } from 'lightweight-charts';
import { CHART_TEXT_COLOR } from '@/lib/chartTheme';
import { Coins, Loader2, Shield, TrendingUp, Activity, Lock, HelpCircle } from 'lucide-react';

export default function LNXEcosystemPage() {
  const [loading, setLoading] = useState(true);
  const [index, setIndex] = useState<LNXIndexData | null>(null);
  const [history, setHistory] = useState<LNXIndexData[]>([]);
  const [reserveBalance, setReserveBalance] = useState(0);
  const [attribution, setAttribution] = useState<any>(null);
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<any>(null);

  useEffect(() => {
    Promise.all([
      lnxAPI.getIndex(),
      lnxAPI.getHistory(90),
      treasuryAPI.getPoolsSummary().catch(() => null),
      institutionalAPI.getLnxAttribution().catch(() => null),
    ])
      .then(([idx, hist, summary, attr]) => {
        setIndex(idx);
        setHistory(hist || []);
        setAttribution(attr);
        const reserve = summary?.pools?.find((p) => p.id === 'RESERVE');
        if (reserve?.balance) {
          setReserveBalance(reserve.balance);
        } else if (idx?.treasury_nav && idx?.reserve_ratio) {
          setReserveBalance((idx.treasury_nav * idx.reserve_ratio) / 100);
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!chartRef.current || history.length === 0) return;
    if (chartInstance.current) {
      chartInstance.current.remove();
      chartInstance.current = null;
    }
    const chart = createChart(chartRef.current, {
      layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: CHART_TEXT_COLOR },
      height: 280,
      grid: { vertLines: { visible: false }, horzLines: { color: 'rgba(255,255,255,0.05)' } },
    });
    const series = chart.addAreaSeries({
      lineColor: '#CFA43B',
      topColor: 'rgba(207, 164, 59, 0.35)',
      bottomColor: 'rgba(207, 164, 59, 0)',
    });
    series.setData(
      history.map((h) => ({
        time: h.computed_at.split('T')[0] as Time,
        value: h.composite_index,
      }))
    );
    chart.timeScale().fitContent();
    chartInstance.current = chart;
    return () => chart.remove();
  }, [history]);

  if (loading) return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary-gold" /></div>;

  const composite = index?.composite_index ?? 100;
  const weekly = index?.weekly_change_pct ?? 0;
  const monthly = index?.monthly_change_pct ?? 0;

  return (
    <div className="space-y-8">
      <PageHeader title="LNX Digital Asset" subtitle="Operational ecosystem index — not historical strategy validation." />

      <div className="card blue p-4 flex items-start gap-3 text-[13px] text-text-secondary">
        <HelpCircle className="w-5 h-5 shrink-0 text-primary-blue" />
        <p>
          LNX composite, treasury NAV, and AUM growth reflect <strong>operational platform state</strong> (pools, settlements, demo ledger when seeded).
          Validated fund strategy performance on historical <span className="font-mono">market_bars</span> is on{' '}
          <a href="/fund-performance" className="text-primary-gold underline">Fund Performance</a>.
        </p>
      </div>

      <div className="g4">
        <MetricDisplay label="LNX Composite Index" value={composite.toFixed(2)} icon={Coins} trend={weekly >= 0 ? 'up' : 'down'} />
        <MetricDisplay label="Treasury NAV" value={`$${(index?.treasury_nav ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`} icon={Shield} />
        <MetricDisplay label="Auto-Managed AUM" value={`$${(index?.aum ?? 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}`} icon={Activity} />
        <MetricDisplay label="Reserve Ratio" value={`${(index?.reserve_ratio ?? 0).toFixed(1)}%`} icon={TrendingUp} />
      </div>

      <div className="g4">
        <MetricDisplay label="Weekly Change" value={`${weekly >= 0 ? '+' : ''}${weekly.toFixed(2)}%`} icon={TrendingUp} trend={weekly >= 0 ? 'up' : 'down'} />
        <MetricDisplay label="Monthly Change" value={`${monthly >= 0 ? '+' : ''}${monthly.toFixed(2)}%`} icon={Activity} />
        <MetricDisplay label="Treasury Health" value={`${(index?.treasury_health ?? 0).toFixed(1)}`} icon={Shield} />
        <MetricDisplay label="Strategy Performance" value={`${(index?.strategy_performance ?? 0).toFixed(2)}`} icon={Coins} />
      </div>

      <div className="card gold p-6">
        <h3 className="sec-head">Historical Index Curve</h3>
        <div ref={chartRef} className="w-full" />
      </div>

      <div className="g21">
        <div className="card gold shadow-lg p-6">
          <h3 className="sec-head">Index Components</h3>
          <div className="space-y-3 mt-4">
            <div className="flex justify-between border-b border-border-default pb-2">
              <span className="font-mono text-[10px] text-text-muted uppercase">NAV Component</span>
              <span className="font-mono font-bold">${(index?.nav ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
            </div>
            <div className="flex justify-between border-b border-border-default pb-2">
              <span className="font-mono text-[10px] text-text-muted uppercase">AUM Growth</span>
              <span className="font-mono font-bold">{(index?.aum_growth ?? 0).toLocaleString()}</span>
            </div>
            <div className="flex justify-between border-b border-border-default pb-2">
              <span className="font-mono text-[10px] text-text-muted uppercase">Strategy Performance</span>
              <span className="font-mono font-bold">{(index?.strategy_performance ?? 0).toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="font-mono text-[10px] text-text-muted uppercase">Reserve Backing</span>
              <span className="font-mono font-bold text-primary-emerald">${reserveBalance.toLocaleString(undefined, { minimumFractionDigits: 2 })}</span>
            </div>
          </div>
        </div>
        <div className="card blue shadow-lg p-6">
          <h3 className="sec-head flex items-center gap-2"><HelpCircle className="w-4 h-4" /> LNX Explainability</h3>
          {attribution ? (
            <div className="mt-4 space-y-3 text-[13px]">
              <p className="text-text-secondary">{attribution.explanation}</p>
              <p className="font-mono text-[10px] uppercase text-text-muted">Provenance: {attribution.data_provenance}</p>
              <div className="space-y-2">
                {Object.entries(attribution.attribution || {}).map(([k, v]) => (
                  <div key={k} className="flex justify-between border-b border-border-subtle pb-1">
                    <span className="text-text-muted capitalize">{k.replace(/_/g, ' ')}</span>
                    <span className="font-mono font-bold">{Number(v).toFixed(2)} pts</span>
                  </div>
                ))}
              </div>
              {attribution.dominant_driver && (
                <p className="text-[12px] text-primary-gold">Dominant driver: {String(attribution.dominant_driver).replace(/_/g, ' ')}</p>
              )}
            </div>
          ) : (
            <p className="text-text-muted text-[13px] mt-4">Attribution loading unavailable.</p>
          )}
        </div>
      </div>
    </div>
  );
}
