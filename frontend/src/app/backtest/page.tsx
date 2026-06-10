'use client';

import { useState, useEffect } from 'react';
import { MetricDisplay } from '@/components/ui/MetricDisplay';
import { quantAPI, systemAPI } from '@/lib/api';
import type { BacktestRequest, BacktestResponse } from '@/lib/types';
import { EquityCurveChart } from '@/components/charts/EquityCurveChart';
import { Play, Loader2, Settings2, BarChart3, FlaskConical } from 'lucide-react';

export default function BacktestTerminal() {
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<BacktestResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    systemAPI.getGlobalSettings()
      .then(settings => {
        setForm(prev => ({
          ...prev,
          commission_pct: settings.default_commission_pct,
          slippage_pct: settings.default_slippage_pct
        }));
      }).catch(console.error);
  }, []);

  const [form, setForm] = useState({
    symbol: 'BTC/USDT',
    timeframe: '1d',
    strategy: 'MA_CROSSOVER',
    initial_capital: 100000,
    commission_pct: 0.1,
    slippage_pct: 0.1,
  });
  
  const [strategyParams, setStrategyParams] = useState({
    short_window: 20,
    long_window: 50,
    rsi_period: 14,
    oversold_level: 30,
    overbought_level: 70,
  });

  const handleParamChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setStrategyParams(prev => ({ ...prev, [name]: Number(value) }));
  };

  const handleRun = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload: BacktestRequest = {
        symbol: form.symbol,
        timeframe: form.timeframe,
        strategy: form.strategy,
        initial_capital: form.initial_capital,
        commission_pct: form.commission_pct,
        slippage_pct: form.slippage_pct,
        strategy_params: {}
      };

      if (form.strategy === 'MA_CROSSOVER') {
        payload.strategy_params = {
            short_window: strategyParams.short_window,
            long_window: strategyParams.long_window,
        };
      } else if (form.strategy === 'RSI_MEAN_REVERSION') {
          payload.strategy_params = {
              rsi_period: strategyParams.rsi_period,
              oversold_level: strategyParams.oversold_level,
              overbought_level: strategyParams.overbought_level,
          };
      }

      const res = await quantAPI.runBacktest(payload);
      setResults(res);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <header className="mb-8">
        <h1 className="font-serif text-[30px] font-light text-text-primary flex items-center gap-3 leading-none">
          <FlaskConical className="w-6 h-6 text-primary-blue" /> 
          Strategy Engine
        </h1>
        <p className="font-serif text-[14px] italic text-text-secondary mt-2">Historical Data Ingestion & Algorithmic Replay</p>
      </header>

      <div className="g12 items-start">
        
        {/* CONFIGURATION PANEL */}
        <div className="space-y-6">
          <div className="card blue shadow-lg p-6">
            <div className="flex items-center gap-2 mb-6 border-b border-border-default pb-4">
              <Settings2 className="w-4 h-4 text-primary-blue" />
              <h2 className="sec-head mb-0">Execution Parameters</h2>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block font-mono text-[8.5px] uppercase tracking-wider text-text-muted mb-1.5">Target Asset</label>
                <select 
                  className="w-full border border-border-default rounded-[3px] px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-blue transition-colors"
                  value={form.symbol}
                  onChange={(e) => setForm({...form, symbol: e.target.value})}
                >
                  <option value="BTC/USDT">BTC/USDT (Binance)</option>
                  <option value="ETH/USDT">ETH/USDT (Binance)</option>
                  <option value="SOL/USDT">SOL/USDT (Binance)</option>
                </select>
              </div>

              <div>
                <label className="block font-mono text-[8.5px] uppercase tracking-wider text-text-muted mb-1.5">Resolution</label>
                <select 
                  className="w-full border border-border-default rounded-[3px] px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-blue transition-colors"
                  value={form.timeframe}
                  onChange={(e) => setForm({...form, timeframe: e.target.value})}
                >
                  <option value="1h">1 Hour (1h)</option>
                  <option value="4h">4 Hour (4h)</option>
                  <option value="1d">1 Day (1d)</option>
                </select>
              </div>

              <div>
                <label className="block font-mono text-[8.5px] uppercase tracking-wider text-text-muted mb-1.5">Initial Capital</label>
                <input 
                  type="number"
                  className="w-full border border-border-default rounded-[3px] px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-blue transition-colors"
                  value={form.initial_capital}
                  onChange={(e) => setForm({...form, initial_capital: Number(e.target.value)})}
                  step={10000}
                  min={1000}
                />
              </div>

              <div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block font-mono text-[8.5px] uppercase tracking-wider text-text-muted mb-1.5">Commission (%)</label>
                    <input 
                      type="number"
                      className="w-full border border-border-default rounded-[3px] px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-blue transition-colors"
                      value={form.commission_pct}
                      onChange={(e) => setForm({...form, commission_pct: Number(e.target.value)})}
                      step={0.01}
                      min={0}
                    />
                  </div>
                  <div>
                    <label className="block font-mono text-[8.5px] uppercase tracking-wider text-text-muted mb-1.5">Slippage (%)</label>
                    <input 
                      type="number"
                      className="w-full border border-border-default rounded-[3px] px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-blue transition-colors"
                      value={form.slippage_pct}
                      onChange={(e) => setForm({...form, slippage_pct: Number(e.target.value)})}
                      step={0.01}
                      min={0}
                    />
                  </div>
                </div>
              </div>

              <div>
                <label className="block font-mono text-[8.5px] uppercase tracking-wider text-text-muted mb-1.5">Algorithm Class</label>
                <select 
                  className="w-full border border-border-default rounded-[3px] px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-blue transition-colors"
                  value={form.strategy}
                  onChange={(e) => setForm({...form, strategy: e.target.value})}
                >
                  <option value="MA_CROSSOVER">Moving Average Crossover (20/50)</option>
                  <option value="RSI_MEAN_REVERSION">RSI Mean Reversion (14/30/70)</option>
                </select>
              </div>

              {/* DYNAMIC STRATEGY PARAMETERS */}
              {form.strategy === 'MA_CROSSOVER' && (
                <div className="grid grid-cols-2 gap-3 pt-4 mt-4 border-t border-border-default">
                  <div>
                    <label className="block font-mono text-[8.5px] uppercase tracking-wider text-text-muted mb-1.5">Short MA</label>
                    <input type="number" name="short_window" value={strategyParams.short_window} onChange={handleParamChange} className="w-full border border-border-default rounded-[3px] px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-blue transition-colors" />
                  </div>
                  <div>
                    <label className="block font-mono text-[8.5px] uppercase tracking-wider text-text-muted mb-1.5">Long MA</label>
                    <input type="number" name="long_window" value={strategyParams.long_window} onChange={handleParamChange} className="w-full border border-border-default rounded-[3px] px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-blue transition-colors" />
                  </div>
                </div>
              )}

              {form.strategy === 'RSI_MEAN_REVERSION' && (
                <div className="space-y-3 pt-4 mt-4 border-t border-border-default">
                   <div>
                    <label className="block font-mono text-[8.5px] uppercase tracking-wider text-text-muted mb-1.5">RSI Period</label>
                    <input type="number" name="rsi_period" value={strategyParams.rsi_period} onChange={handleParamChange} className="w-full border border-border-default rounded-[3px] px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-blue transition-colors" />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block font-mono text-[8.5px] uppercase tracking-wider text-text-muted mb-1.5">Oversold</label>
                      <input type="number" name="oversold_level" value={strategyParams.oversold_level} onChange={handleParamChange} className="w-full border border-border-default rounded-[3px] px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-blue transition-colors" />
                    </div>
                    <div>
                      <label className="block font-mono text-[8.5px] uppercase tracking-wider text-text-muted mb-1.5">Overbought</label>
                      <input type="number" name="overbought_level" value={strategyParams.overbought_level} onChange={handleParamChange} className="w-full border border-border-default rounded-[3px] px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-blue transition-colors" />
                    </div>
                  </div>
                </div>
              )}

              <button 
                onClick={handleRun}
                disabled={loading}
                className="btn blue btn-full mt-4 flex items-center justify-center gap-2 shadow-lg"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                {loading ? 'Compiling Matrix...' : 'Launch Simulation'}
              </button>
            </div>
            
            {error && (
              <div className="mt-6 p-4 rounded-[3px] bg-system-rBg border border-system-rBd text-danger font-sans text-[13px]">
                {error}
              </div>
            )}
          </div>
        </div>

        {/* RESULTS TERMINAL */}
        <div>
          <div className="card gold h-full min-h-[400px] flex flex-col relative shadow-lg p-0 overflow-hidden">
            <div className="p-6 border-b border-border-default flex items-center gap-2 bg-background-base">
              <BarChart3 className="w-5 h-5 text-primary-gold" />
              <span className="sec-head mb-0">Simulation Output Matrix</span>
            </div>
            
            <div className="flex-1 p-8 bg-background-card">
              {!results && !loading && (
                <div className="h-full min-h-[300px] flex flex-col items-center justify-center text-text-muted space-y-4">
                  <FlaskConical className="w-12 h-12 opacity-50" />
                  <p className="font-sans text-[13px]">Awaiting execution parameters...</p>
                </div>
              )}

              {loading && (
                <div className="h-full min-h-[300px] flex flex-col items-center justify-center text-primary-blue space-y-4">
                  <Loader2 className="w-10 h-10 animate-spin" />
                  <p className="font-mono text-[10px] uppercase tracking-widest animate-pulse">Compiling Matrix...</p>
                </div>
              )}

              {results && !loading && (
                <div className="animate-in fade-in duration-500">
                  <div className="g3 pb-6 border-b border-border-default mb-6">
                      <MetricDisplay 
                        label="Gross Return" 
                        value={`${results.metrics.gross_return_pct}%`} 
                        trend={results.metrics.gross_return_pct > 0 ? 'up' : results.metrics.gross_return_pct < 0 ? 'down' : 'neutral'}
                      />
                      <MetricDisplay 
                        label="Net Return (After Fees)" 
                        value={`${results.metrics.net_return_pct}%`} 
                        trend={results.metrics.net_return_pct > 0 ? 'up' : results.metrics.net_return_pct < 0 ? 'down' : 'neutral'}
                      />
                      <MetricDisplay 
                        label="Final Equity" 
                        value={`$${results.metrics.final_capital.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`} 
                      />
                      <MetricDisplay 
                        label="Total Fees Paid" 
                        value={`$${results.metrics.total_fees_paid.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`} 
                        trend="down"
                      />
                      <MetricDisplay 
                        label="Slippage Impact" 
                        value={`$${results.metrics.slippage_impact.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`} 
                        trend="down"
                      />
                      <MetricDisplay 
                        label="Trades Executed" 
                        value={results.metrics.total_trades_simulated} 
                      />
                      <MetricDisplay 
                        label="Win Rate" 
                        value={`${results.metrics.win_rate_pct}%`} 
                      />
                      <MetricDisplay 
                        label="Max Drawdown" 
                        value={`${results.metrics.max_drawdown_pct}%`} 
                        trend="down"
                      />
                      <MetricDisplay 
                        label="Sharpe Ratio" 
                        value={results.metrics.sharpe_ratio} 
                      />
                  </div>

                  <div className="mt-6">
                    <h3 className="sec-head">Equity Curve</h3>
                    <EquityCurveChart data={results.equity_curve} />
                  </div>

                </div>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
}