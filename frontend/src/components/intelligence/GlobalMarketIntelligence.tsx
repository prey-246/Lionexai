'use client';

import { useEffect, useState } from 'react';
import { marketAPI, type GlobalMarketState } from '@/lib/api';
import { Activity, Gauge, TrendingUp, TrendingDown, Minus, Loader2, BrainCircuit } from 'lucide-react';

const REGIME_STYLES: Record<string, { label: string; cls: string }> = {
  BULL: { label: 'Bull', cls: 'text-primary-emerald-bright bg-system-tBg border-system-tBd' },
  BEAR: { label: 'Bear', cls: 'text-danger bg-system-rBg border-system-rBd' },
  SIDEWAYS: { label: 'Sideways', cls: 'text-text-secondary bg-background-panel border-border-default' },
  CRISIS: { label: 'Crisis', cls: 'text-danger bg-system-rBg border-system-rBd animate-pulse' },
};

function riskColor(score: number) {
  if (score >= 60) return 'text-danger';
  if (score <= 40) return 'text-primary-emerald-bright';
  return 'text-primary-gold-bright';
}

function riskTrack(score: number) {
  if (score >= 60) return 'bg-danger';
  if (score <= 40) return 'bg-primary-emerald';
  return 'bg-primary-gold';
}

export function GlobalMarketIntelligence({ compact = false }: { compact?: boolean }) {
  const [state, setState] = useState<GlobalMarketState | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    marketAPI.getGlobalState()
      .then((s) => { if (active) setState(s); })
      .catch(() => { if (active) setState(null); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

  if (loading) {
    return (
      <div className="card flex items-center justify-center h-40">
        <Loader2 className="w-6 h-6 animate-spin text-primary-gold" />
      </div>
    );
  }

  if (!state) {
    return (
      <div className="card">
        <div className="flex items-center gap-2 mb-2">
          <BrainCircuit className="w-4 h-4 text-primary-gold" />
          <h3 className="font-display text-[15px] font-bold text-text-primary">Global Market Intelligence</h3>
        </div>
        <p className="text-[13px] text-text-muted">Market intelligence is warming up. Check back shortly.</p>
      </div>
    );
  }

  const regime = REGIME_STYLES[state.market_regime] ?? REGIME_STYLES.SIDEWAYS;
  const score = Math.round(state.global_risk_score);
  const riskOn = state.risk_on_off;
  const ranking = (state.asset_ranking ?? []).slice(0, compact ? 3 : 5);

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4 border-b border-border-subtle pb-3">
        <div className="flex items-center gap-2">
          <BrainCircuit className="w-4 h-4 text-primary-gold" />
          <h3 className="font-display text-[15px] font-bold text-text-primary">Global Market Intelligence</h3>
        </div>
        <span className="font-mono text-[9px] uppercase tracking-[0.14em] text-text-muted">
          {new Date(state.computed_at).toLocaleString()}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Risk gauge */}
        <div className="sm:col-span-1">
          <div className="flex items-center gap-1.5 mb-1.5">
            <Gauge className="w-3.5 h-3.5 text-text-muted" />
            <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted">Global Risk Score</span>
          </div>
          <div className={`font-display text-[34px] font-extrabold leading-none tabular-nums ${riskColor(score)}`}>{score}<span className="text-[15px] text-text-muted font-bold">/100</span></div>
          <div className="mt-2 h-2 rounded-full bg-background-base overflow-hidden">
            <div className={`h-full rounded-full ${riskTrack(score)} transition-all duration-500`} style={{ width: `${score}%` }} />
          </div>
        </div>

        {/* Regime + risk on/off */}
        <div className="sm:col-span-1 flex flex-col gap-3 justify-center">
          <div>
            <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted block mb-1.5">Market Regime</span>
            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border font-mono text-[11px] font-bold uppercase tracking-wider ${regime.cls}`}>
              <Activity className="w-3 h-3" /> {regime.label}
            </span>
          </div>
          <div>
            <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted block mb-1.5">Risk Posture</span>
            <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border font-mono text-[11px] font-bold uppercase tracking-wider ${
              riskOn === 'RISK_ON' ? 'text-primary-emerald-bright bg-system-tBg border-system-tBd'
              : riskOn === 'RISK_OFF' ? 'text-danger bg-system-rBg border-system-rBd'
              : 'text-text-secondary bg-background-panel border-border-default'
            }`}>
              {riskOn === 'RISK_ON' ? <TrendingUp className="w-3 h-3" /> : riskOn === 'RISK_OFF' ? <TrendingDown className="w-3 h-3" /> : <Minus className="w-3 h-3" />}
              {riskOn.replace('_', '-')}
            </span>
          </div>
        </div>

        {/* Asset ranking */}
        <div className="sm:col-span-1">
          <span className="font-mono text-[10px] uppercase tracking-[0.14em] text-text-muted block mb-2">Top Ranked Assets</span>
          <div className="flex flex-col gap-1.5">
            {ranking.length === 0 && <span className="text-[12px] text-text-muted">No ranking yet.</span>}
            {ranking.map((a) => (
              <div key={a.symbol} className="flex items-center justify-between">
                <span className="font-mono text-[12px] text-text-secondary truncate">
                  <span className="text-text-muted mr-1.5">{a.rank}.</span>{a.symbol}
                </span>
                <span className={`font-mono text-[11px] tabular-nums ${a.momentum_3m >= 0 ? 'text-primary-emerald-bright' : 'text-danger'}`}>
                  {(a.momentum_3m * 100).toFixed(1)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
