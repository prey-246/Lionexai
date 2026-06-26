'use client';

import { useEffect, useState } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { fundsAPI, validatedAPI, institutionalAPI, type FundProduct } from '@/lib/api';
import { Loader2, FlaskConical, AlertTriangle, Shield, TrendingUp } from 'lucide-react';
import { formatFixed } from '@/lib/format';

function fmtMetric(value: number | null | undefined, digits = 2): string {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return formatFixed(value, digits);
}

const STRATEGIES = [
  'MOMENTUM', 'TREND_FOLLOWING', 'VOL_BREAKOUT', 'RISK_PARITY',
  'CROSS_ASSET_ROTATION', 'MEAN_REVERSION', 'SENTIMENT_OVERLAY',
];

export default function ResearchLabPage() {
  const [loading, setLoading] = useState(true);
  const [funds, setFunds] = useState<FundProduct[]>([]);
  const [runs, setRuns] = useState<any[]>([]);
  const [alphaEvidence, setAlphaEvidence] = useState<any>(null);
  const [globalRisk, setGlobalRisk] = useState<any>(null);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [running, setRunning] = useState(false);
  const [form, setForm] = useState({ symbol: 'BTC/USDT', strategy_key: 'MOMENTUM', validation_type: 'BACKTEST' });

  const load = () => {
    Promise.all([
      fundsAPI.listFunds(),
      validatedAPI.listRuns().catch(() => []),
      validatedAPI.getGlobalRisk().catch(() => null),
      validatedAPI.getAllocationAlerts().catch(() => []),
    ]).then(([f, r, gr, al]) => {
      setFunds(f);
      setRuns(r);
      setGlobalRisk(gr);
      setAlerts(al);
    }).finally(() => setLoading(false));
  };

  useEffect(load, []);

  const runValidation = async () => {
    setRunning(true);
    try {
      await validatedAPI.runStrategy(form);
      load();
    } catch (e: any) {
      alert(e.message || 'Validation failed');
    } finally {
      setRunning(false);
    }
  };

  const runAlphaEvidence = async () => {
    setRunning(true);
    try {
      const ev = await institutionalAPI.getAlphaEvidenceFull('ALPHA', 20);
      setAlphaEvidence(ev);
    } catch (e: any) {
      alert(e.message || 'Alpha evidence failed');
    } finally {
      setRunning(false);
    }
  };

  if (loading) {
    return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary-gold" /></div>;
  }

  return (
    <div className="space-y-8">
      <PageHeader
        title="Strategy Research Lab"
        subtitle="Historical validation on market bars — separate from demo ledger performance. Never mixed with operational metrics."
      />

      <div className="card blue p-4 flex items-start gap-3">
        <AlertTriangle className="w-5 h-5 text-warning shrink-0 mt-0.5" />
        <p className="text-[13px] text-text-secondary">
          Results here use <strong className="text-text-primary">VALIDATED_HISTORICAL</strong> provenance from OHLCV backtests.
          Fund Performance &quot;Actual&quot; columns may show <strong className="text-text-primary">DEMO</strong> data after institutional reset — check the provenance badge.
        </p>
      </div>

      {globalRisk && (
        <div className="card p-4">
          <h3 className="sec-head flex items-center gap-2"><Shield className="w-4 h-4" /> Global Risk Engine</h3>
          <p className="font-mono text-2xl font-bold text-primary-gold">{globalRisk.global_risk_score}/100</p>
          <p className="text-[13px] text-text-muted mt-2">{globalRisk.explanation}</p>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="card gold p-6">
          <h3 className="sec-head flex items-center gap-2"><FlaskConical className="w-4 h-4" /> Run Historical Validation</h3>
          <div className="space-y-3 mt-4">
            <input className="input w-full" value={form.symbol} onChange={(e) => setForm({ ...form, symbol: e.target.value })} placeholder="Symbol e.g. BTC/USDT" />
            <select className="input w-full" value={form.strategy_key} onChange={(e) => setForm({ ...form, strategy_key: e.target.value })}>
              {STRATEGIES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
            <select className="input w-full" value={form.validation_type} onChange={(e) => setForm({ ...form, validation_type: e.target.value })}>
              <option value="BACKTEST">Backtest</option>
              <option value="WALK_FORWARD">Walk-Forward</option>
              <option value="MONTE_CARLO">Monte Carlo</option>
            </select>
            <button className="btn gold btn-full" disabled={running} onClick={runValidation}>
              {running ? 'Running…' : 'Run & Persist'}
            </button>
          </div>
        </div>

        <div className="card p-6">
          <h3 className="sec-head">Alpha 20% Monthly — Evidence Framework</h3>
          <p className="text-[12px] text-text-muted mb-4">Objective test on historical data. Does not fake results.</p>
          <button className="btn blue btn-full mb-4" disabled={running} onClick={runAlphaEvidence}>
            Evaluate ALPHA Fund Target
          </button>
          {alphaEvidence && (
            <div className="text-[13px] space-y-2">
              <p>
                <span className="text-text-muted">Verdict:</span>{' '}
                <span className="font-bold">{alphaEvidence.verdict || alphaEvidence.conclusion}</span>
              </p>
              <p className="text-text-secondary">{alphaEvidence.rationale || alphaEvidence.evidence_summary}</p>
              {alphaEvidence.historical_validation?.disclaimer && (
                <p className="text-[11px] text-text-muted">{alphaEvidence.historical_validation.disclaimer}</p>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="card p-0 overflow-x-auto">
        <h3 className="sec-head px-5 pt-5">Validated Strategy Runs</h3>
        <table className="nexa-table w-full">
          <thead>
            <tr><th>Strategy</th><th>Symbol</th><th>Type</th><th>Monthly %</th><th>CAGR %</th><th>Sharpe</th><th>Max DD</th></tr>
          </thead>
          <tbody>
            {runs.map((r) => (
              <tr key={r.id}>
                <td className="font-mono">{r.strategy_key}</td>
                <td>{r.symbol}</td>
                <td><span className="tag grey">{r.validation_type}</span></td>
                <td className="font-mono">{fmtMetric(r.metrics?.avg_monthly_return_pct)}%</td>
                <td className="font-mono">{fmtMetric(r.metrics?.cagr_pct)}%</td>
                <td className="font-mono">{fmtMetric(r.metrics?.sharpe_ratio)}</td>
                <td className="font-mono">{fmtMetric(r.metrics?.max_drawdown_pct)}%</td>
              </tr>
            ))}
            {runs.length === 0 && <tr><td colSpan={7} className="text-center py-8 text-text-muted">No validated runs yet. Run a backtest above.</td></tr>}
          </tbody>
        </table>
      </div>

      {alerts.length > 0 && (
        <div className="card p-4">
          <h3 className="sec-head flex items-center gap-2"><TrendingUp className="w-4 h-4" /> Allocation Integrity Alerts</h3>
          <ul className="space-y-2 mt-3">
            {alerts.slice(0, 10).map((a) => (
              <li key={a.id} className="text-[12px] border-b border-border-subtle pb-2">
                <span className={`tag ${a.severity === 'CRITICAL' ? 'red' : 'grey'}`}>{a.severity}</span>{' '}
                {a.message}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
