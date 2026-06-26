'use client';

import { useState, useRef, useEffect } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { MetricDisplay } from '@/components/ui/MetricDisplay';
import { quantAPI, strategiesAPI } from '@/lib/api';
import { FlaskConical, Play, TrendingUp, AlertTriangle, Activity, Settings2, BarChart3, Database, History, Save, Loader2 } from 'lucide-react';
import type { BacktestResponse } from '@/lib/types';
import { createChart, ColorType } from 'lightweight-charts';
import { CHART_TEXT_COLOR } from '@/lib/chartTheme';

export default function StrategyEnginePage() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BacktestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const chartContainerRef = useRef<HTMLDivElement>(null);
  
  const [isSaveModalOpen, setIsSaveModalOpen] = useState(false);
  const [saveForm, setSaveForm] = useState({ name: '', description: '' });
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    symbol: 'BTC/USDT',
    timeframe: '1d',
    strategy: 'ma_crossover',
    initial_capital: 100000,
    fast_ma: 10,
    slow_ma: 50,
    rsi_period: 14,
    rsi_overbought: 70,
    rsi_oversold: 30,
  });

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await quantAPI.runBacktest({
        symbol: form.symbol,
        timeframe: form.timeframe,
        strategy: form.strategy,
        initial_capital: form.initial_capital,
        strategy_params: form.strategy === 'ma_crossover' ? {
          fast_ma: form.fast_ma,
          slow_ma: form.slow_ma
        } : {
          rsi_period: form.rsi_period,
          rsi_overbought: form.rsi_overbought,
          rsi_oversold: form.rsi_oversold
        }
      });
      setResult(res);
    } catch (err: any) {
      setError(err.message || 'Backtest failed to execute. Ensure historical data is backfilled.');
    } finally {
      setLoading(false);
    }
  };

  const handleSaveStrategy = async () => {
    setSaving(true);
    try {
      const strategy_params = form.strategy === 'ma_crossover' ? {
        fast_ma: form.fast_ma,
        slow_ma: form.slow_ma
      } : {
        rsi_period: form.rsi_period,
        rsi_overbought: form.rsi_overbought,
        rsi_oversold: form.rsi_oversold
      };

      await strategiesAPI.createStrategy({
        id: saveForm.name.toUpperCase().replace(/\s+/g, '_'),
        name: saveForm.name,
        description: saveForm.description,
        strategy_type: form.strategy,
        parameters: strategy_params,
      });
      alert(`Strategy saved successfully to the Registry!`);
      setIsSaveModalOpen(false);
      setSaveForm({ name: '', description: '' });
    } catch (err: any) {
      alert(err.message || 'Failed to save strategy.');
    } finally {
      setSaving(false);
    }
  };

  useEffect(() => {
    if (!result || !result.equity_curve || result.equity_curve.length === 0 || !chartContainerRef.current) return;

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth });
      }
    };

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: CHART_TEXT_COLOR,
        fontFamily: "'JetBrains Mono', monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.04)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.05)' },
      },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false, timeVisible: true },
      crosshair: {
        vertLine: { color: 'rgba(30, 214, 166, 0.4)', labelBackgroundColor: '#1ED6A6' },
        horzLine: { color: 'rgba(30, 214, 166, 0.4)', labelBackgroundColor: '#1ED6A6' },
      },
      height: 192,
    });

    const areaSeries = chart.addAreaSeries({
      lineColor: '#1ED6A6',
      topColor: 'rgba(30, 214, 166, 0.35)',
      bottomColor: 'rgba(30, 214, 166, 0.0)',
      lineWidth: 2,
      priceLineVisible: false,
    });

    const dataMap = new Map<number, number>();
    
    result.equity_curve.forEach((point: any) => {
      const rawTime = point.timestamp || point.time || point.date;
      const timeKey = typeof rawTime === 'string' ? Math.floor(new Date(rawTime).getTime() / 1000) : Math.floor(rawTime);
      dataMap.set(timeKey, point.equity ?? point.value ?? 0);
    });

    const chartData = Array.from(dataMap.entries())
      .map(([time, value]) => ({ time: time as any, value }))
      .sort((a, b) => (a.time as number) - (b.time as number));

    if (chartData.length === 1) {
      chartData.push({ time: (chartData[0].time as number + 86400) as any, value: chartData[0].value });
    }

    if (chartData.length > 0) {
      areaSeries.setData(chartData);
      chart.timeScale().fitContent();
    }

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [result]);

  return (
    <div className="space-y-8">
      <PageHeader title="Strategy Engine" subtitle="Advanced quantitative backtesting and algorithmic simulation environment." />

      <div className="g21">
        {/* Configuration Panel */}
        <div className="card grey shadow-lg">
          <div className="flex items-center gap-2 mb-6 border-b border-border-default pb-4">
            <Settings2 className="w-5 h-5 text-text-primary" />
            <h3 className="sec-head mb-0">Strategy Parameters</h3>
          </div>

          <div className="space-y-5">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1.5">Asset Pair</label>
                <select className="w-full border border-border-default rounded-lg px-3 py-2 font-sans text-[13px] bg-background-base text-text-primary focus:border-primary-gold focus:outline-none" value={form.symbol} onChange={e => setForm({...form, symbol: e.target.value})}>
                  <option value="BTC/USDT">BTC/USDT</option>
                  <option value="ETH/USDT">ETH/USDT</option>
                  <option value="SOL/USDT">SOL/USDT</option>
                </select>
              </div>
              <div>
                <label className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1.5">Timeframe</label>
                <select className="w-full border border-border-default rounded-lg px-3 py-2 font-sans text-[13px] bg-background-base text-text-primary focus:border-primary-gold focus:outline-none" value={form.timeframe} onChange={e => setForm({...form, timeframe: e.target.value})}>
                  <option value="1d">1 Day (1d)</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1.5">Strategy Algorithm</label>
              <select className="w-full border border-border-default rounded-lg px-3 py-2 font-sans text-[13px] bg-background-base text-text-primary focus:border-primary-gold focus:outline-none" value={form.strategy} onChange={e => setForm({...form, strategy: e.target.value})}>
                <option value="ma_crossover">Moving Average Crossover</option>
                <option value="mean_reversion">Mean Reversion (RSI)</option>
              </select>
            </div>

            {form.strategy === 'ma_crossover' && (
              <div className="grid grid-cols-2 gap-4 pt-4 border-t border-border-subtle">
                <div>
                  <label className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1.5">Fast MA Period</label>
                  <input type="number" min="1" className="w-full border border-border-default rounded-lg px-3 py-2 font-sans text-[13px] bg-background-base text-text-primary focus:border-primary-gold focus:outline-none" value={form.fast_ma} onChange={e => setForm({...form, fast_ma: Number(e.target.value)})} />
                </div>
                <div>
                  <label className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1.5">Slow MA Period</label>
                  <input type="number" min="2" className="w-full border border-border-default rounded-lg px-3 py-2 font-sans text-[13px] bg-background-base text-text-primary focus:border-primary-gold focus:outline-none" value={form.slow_ma} onChange={e => setForm({...form, slow_ma: Number(e.target.value)})} />
                </div>
              </div>
            )}

            {form.strategy === 'mean_reversion' && (
              <div className="grid grid-cols-3 gap-4 pt-4 border-t border-border-subtle">
                <div>
                  <label className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1.5">RSI Period</label>
                  <input type="number" min="1" className="w-full border border-border-default rounded-lg px-3 py-2 font-sans text-[13px] bg-background-base text-text-primary focus:border-primary-gold focus:outline-none" value={form.rsi_period} onChange={e => setForm({...form, rsi_period: Number(e.target.value)})} />
                </div>
                <div>
                  <label className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1.5">Overbought</label>
                  <input type="number" min="50" max="100" className="w-full border border-border-default rounded-lg px-3 py-2 font-sans text-[13px] bg-background-base text-text-primary focus:border-primary-gold focus:outline-none" value={form.rsi_overbought} onChange={e => setForm({...form, rsi_overbought: Number(e.target.value)})} />
                </div>
                <div>
                  <label className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1.5">Oversold</label>
                  <input type="number" min="0" max="50" className="w-full border border-border-default rounded-lg px-3 py-2 font-sans text-[13px] bg-background-base text-text-primary focus:border-primary-gold focus:outline-none" value={form.rsi_oversold} onChange={e => setForm({...form, rsi_oversold: Number(e.target.value)})} />
                </div>
              </div>
            )}

            <div>
              <label className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1.5">Initial Capital ($)</label>
              <input type="number" step="1000" className="w-full border border-border-default rounded-lg px-3 py-2 font-sans text-[13px] bg-background-base text-text-primary focus:border-primary-gold focus:outline-none" value={form.initial_capital} onChange={e => setForm({...form, initial_capital: Number(e.target.value)})} />
            </div>

            <button onClick={handleRun} disabled={loading} className="btn gold btn-full mt-6 flex justify-center items-center gap-2">
              {loading ? <Activity className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              Execute Simulation
            </button>
            
            {error && (
              <div className="mt-4 p-3 bg-red-900/20 border border-danger/50 rounded-lg text-danger text-[12px] font-sans flex gap-2">
                <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                <p>{error}</p>
              </div>
            )}
          </div>
        </div>

        {/* Results Panel */}
        <div className="card blue shadow-lg min-h-[500px] flex flex-col">
          <div className="flex items-center justify-between mb-6 border-b border-border-default pb-4">
            <div className="flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-primary-blue" />
              <h3 className="sec-head mb-0">Simulation Results</h3>
            </div>
            {result && !loading && (
              <button onClick={() => setIsSaveModalOpen(true)} className="btn gold flex items-center gap-2 py-1.5 px-3 text-[11px]">
                <Save className="w-3 h-3" /> Save Strategy
              </button>
            )}
          </div>

          {!result && !loading && (
            <div className="flex-1 flex flex-col items-center justify-center text-text-muted opacity-50">
              <Database className="w-12 h-12 mb-4" />
              <p className="font-sans text-[14px]">Ready to run backtest.</p>
              <p className="font-mono text-[10px] uppercase tracking-wider mt-1">Awaiting Strategy Execution</p>
            </div>
          )}

          {loading && (
            <div className="flex-1 flex flex-col items-center justify-center text-primary-gold">
              <FlaskConical className="w-12 h-12 mb-4 animate-pulse" />
              <p className="font-sans text-[14px] animate-pulse">Running quantitative simulation...</p>
            </div>
          )}

          {result && !loading && (
            <div className="space-y-6">
              <div className="grid grid-cols-2 gap-4">
                <MetricDisplay label="Net Return" value={`${result.metrics.net_return_pct}%`} trend={result.metrics.net_return_pct >= 0 ? 'up' : 'down'} icon={TrendingUp} />
                <MetricDisplay label="Win Rate" value={`${result.metrics.win_rate_pct}%`} icon={Activity} />
                <MetricDisplay label="Max Drawdown" value={`-${result.metrics.max_drawdown_pct}%`} icon={AlertTriangle} trend="down" />
                <MetricDisplay label="Sharpe Ratio" value={result.metrics.sharpe_ratio} icon={BarChart3} />
              </div>

              <div className="grid grid-cols-3 gap-4 border-t border-border-default pt-6">
                <div>
                  <span className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1">Final Capital</span>
                  <span className="font-sans font-bold text-text-primary">${result.metrics.final_capital.toLocaleString()}</span>
                </div>
                <div>
                  <span className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1">Total Trades</span>
                  <span className="font-sans font-bold text-text-primary">{result.metrics.total_trades_simulated}</span>
                </div>
                <div>
                  <span className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1">Fees & Slippage</span>
                  <span className="font-sans font-bold text-danger">${(result.metrics.total_fees_paid + result.metrics.slippage_impact).toLocaleString(undefined, {minimumFractionDigits: 2})}</span>
                </div>
              </div>

              <div className="mt-8 pt-6 border-t border-border-default">
                <span className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-4">Equity Curve (NAV)</span>
                <div className="h-48 bg-background-base border border-border-subtle rounded-lg overflow-hidden flex items-center justify-center relative">
                   {result.equity_curve && result.equity_curve.length > 0 ? (
                     <div ref={chartContainerRef} className="w-full h-full" />
                   ) : (
                     <div className="text-center">
                       <TrendingUp className="w-8 h-8 text-primary-emerald opacity-50 mx-auto mb-2" />
                       <span className="font-mono text-[10px] text-text-muted uppercase">No curve data returned.</span>
                     </div>
                   )}
                </div>
              </div>

              {(result as any).trades && (result as any).trades.length > 0 && (
                <div className="mt-8 pt-6 border-t border-border-default">
                  <div className="flex items-center gap-2 mb-4">
                    <History className="w-4 h-4 text-primary-gold" />
                    <span className="block font-mono text-[11px] uppercase tracking-wider text-text-muted">Simulated Trade History</span>
                  </div>
                  <div className="overflow-x-auto max-h-[300px] overflow-y-auto">
                    <table className="nexa-table">
                      <thead>
                        <tr><th>Time</th><th>Side</th><th>Price</th><th>P&L</th></tr>
                      </thead>
                      <tbody>
                        {(result as any).trades.map((trade: any, i: number) => (
                          <tr key={i}>
                            <td className="font-mono whitespace-nowrap text-[10px]">{new Date(trade.timestamp).toLocaleString(undefined, {month: 'short', day:'numeric', hour:'2-digit', minute:'2-digit'})}</td>
                            <td><span className={`tag ${trade.side === 'BUY' ? 'teal' : 'red'}`}>{trade.side}</span></td>
                            <td className="font-mono">${trade.price.toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                            <td className={`font-mono font-bold ${trade.pnl > 0 ? 'text-primary-emerald' : trade.pnl < 0 ? 'text-danger' : 'text-text-muted'}`}>
                              {trade.pnl ? `${trade.pnl > 0 ? '+' : ''}$${trade.pnl.toLocaleString(undefined, {minimumFractionDigits: 2})}` : '-'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Promote to Registry Modal Overlay */}
      {isSaveModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 px-4">
           <div className="card gold w-full max-w-lg shadow-2xl">
              <h3 className="font-display text-[22px] font-bold text-text-primary mb-6">Promote To Strategy Registry</h3>
              <p className="font-sans text-[13px] text-text-secondary mb-6">Save this winning backtest to the Strategy Registry for future paper-trading or live assignment.</p>
              <div className="space-y-4">
                <div>
                  <label className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1.5">Strategy Name</label>
                  <input type="text" className="w-full border border-border-default rounded-lg px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-gold" value={saveForm.name} onChange={e => setSaveForm({...saveForm, name: e.target.value})} placeholder="e.g. BTC MA Crossover Optimal" />
                </div>
                <div>
                  <label className="block font-mono text-[11px] uppercase tracking-wider text-text-muted mb-1.5">Description</label>
                  <input type="text" className="w-full border border-border-default rounded-lg px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-gold" value={saveForm.description} onChange={e => setSaveForm({...saveForm, description: e.target.value})} placeholder="e.g. Optimized for 1D timeframe in bull markets" />
                </div>
              </div>
              <div className="flex justify-end gap-3 mt-8 pt-4 border-t border-border-default">
                 <button onClick={() => setIsSaveModalOpen(false)} className="btn grey">Cancel</button>
                 <button onClick={handleSaveStrategy} className="btn teal" disabled={saving || !saveForm.name}>{saving ? <Loader2 className="w-4 h-4 animate-spin mr-1"/> : null} Save to Registry</button>
              </div>
           </div>
        </div>
      )}
    </div>
  );
}