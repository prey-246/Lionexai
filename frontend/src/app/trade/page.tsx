'use client';

import { useState, useEffect } from 'react';
import { GlassCard } from '@/components/ui/GlassCard';
import { MetricDisplay } from '@/components/ui/MetricDisplay';
import { tradeAPI } from '@/lib/api';
import { Target, Loader2, ShieldAlert, CheckCircle } from 'lucide-react';

export default function ExecutionTerminal() {
  const [portfolio, setPortfolio] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<{type: 'success'|'error', msg: string} | null>(null);

  // FIX 1: Allow size to be a string to handle the empty state when backspacing
  const [form, setForm] = useState({
    symbol: 'BTC/USDT',
    side: 'BUY',
    size: 1.5 as number | string 
  });

  const fetchPortfolio = async () => {
    try {
      const data = await tradeAPI.getPortfolio();
      setPortfolio(data);
    } catch (err) {}
  };

  useEffect(() => {
    fetchPortfolio();
  }, []);

  const handleExecute = async () => {
    setLoading(true);
    setFeedback(null);
    try {
      // Cast the string back to a strict number for the Python backend
      const payload = {
        ...form,
        size: Number(form.size) || 0
      };

      if (payload.size <= 0) {
        throw new Error("Order size must be greater than 0");
      }

      const res = await tradeAPI.executeTrade(payload);
      setFeedback({ type: 'success', msg: `Order FILLED at $${res.fill_price.toLocaleString()}` });
      await fetchPortfolio(); // Refresh balances
    } catch (err: any) {
      setFeedback({ type: 'error', msg: `RISK REJECTION: ${err.message}` });
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="p-6 md:p-8 max-w-7xl mx-auto space-y-6">
      <header className="mb-8">
        <h1 className="text-3xl font-semibold tracking-tight text-white flex items-center gap-3">
          <Target className="w-8 h-8 text-[#5EEAD4]" /> 
          Live Execution & Risk Gatekeeper
        </h1>
        <p className="text-gray-400 mt-2 text-sm">Simulated Paper Orders passing through Mandate Validation</p>
      </header>

      {portfolio && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-px bg-white/[0.04] rounded-xl overflow-hidden border border-white/[0.04] mb-8">
          <div className="bg-[#0B1020]">
            <MetricDisplay label="Total Equity" value={`$${portfolio.total_equity.toLocaleString()}`} />
          </div>
          <div className="bg-[#0B1020]">
            <MetricDisplay label="Available Margin" value={`$${portfolio.available_margin.toLocaleString()}`} />
          </div>
          <div className="bg-[#0B1020]">
            <MetricDisplay label="Active Mandate" value={portfolio.mandate_id} />
          </div>
          <div className="bg-[#0B1020]">
            <MetricDisplay label="Max Drawdown Limit" value="10.0%" trend="down" />
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <GlassCard className="p-6">
          <h2 className="font-medium text-white tracking-wide border-b border-white/[0.04] pb-4 mb-6">Order Entry</h2>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-[11px] font-semibold text-gray-400 uppercase tracking-widest mb-1.5">Asset</label>
                <select 
                  className="w-full bg-[#0B1020] border border-white/[0.1] rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-[#5EEAD4]" 
                  value={form.symbol} 
                  onChange={(e) => setForm({...form, symbol: e.target.value})}
                >
                  {/* FIX 2: Explicitly style the <option> tags so they don't default to a white OS background */}
                  <option value="BTC/USDT" className="bg-[#0B1020] text-white">BTC/USDT</option>
                  <option value="ETH/USDT" className="bg-[#0B1020] text-white">ETH/USDT</option>
                  <option value="DOGE/USDT" className="bg-[#0B1020] text-white">DOGE/USDT (Unapproved)</option>
                </select>
              </div>
              <div>
                <label className="block text-[11px] font-semibold text-gray-400 uppercase tracking-widest mb-1.5">Side</label>
                <select 
                  className="w-full bg-[#0B1020] border border-white/[0.1] rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-[#5EEAD4]"
                  value={form.side} 
                  onChange={(e) => setForm({...form, side: e.target.value})}
                >
                  <option value="BUY" className="bg-[#0B1020] text-white">BUY</option>
                  <option value="SELL" className="bg-[#0B1020] text-white">SELL</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-[11px] font-semibold text-gray-400 uppercase tracking-widest mb-1.5">Quantity</label>
              <input 
                type="number" 
                step="0.1" 
                className="w-full bg-[#0B1020] border border-white/[0.1] rounded-lg px-3 py-2.5 text-sm text-white focus:outline-none focus:border-[#5EEAD4]"
                value={form.size} 
                onChange={(e) => {
                  const val = e.target.value;
                  // Handle the empty string cleanly without triggering NaN
                  setForm({...form, size: val === '' ? '' : parseFloat(val)});
                }} 
              />
            </div>

            <button 
              onClick={handleExecute}
              disabled={loading}
              className={`w-full mt-4 py-3 rounded-lg text-sm font-bold tracking-wider uppercase transition-all flex items-center justify-center gap-2 ${
                form.side === 'BUY' ? 'bg-[#10B981]/20 text-[#10B981] hover:bg-[#10B981]/30 border border-[#10B981]/30' 
                : 'bg-[#EF4444]/20 text-[#EF4444] hover:bg-[#EF4444]/30 border border-[#EF4444]/30'
              }`}
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              {loading ? 'Validating...' : `EXECUTE ${form.side}`}
            </button>
          </div>

          {feedback && (
            <div className={`mt-6 p-4 rounded-lg flex items-start gap-3 border ${
              feedback.type === 'error' ? 'bg-[#EF4444]/10 border-[#EF4444]/20 text-[#EF4444]' : 'bg-[#10B981]/10 border-[#10B981]/20 text-[#10B981]'
            }`}>
              {feedback.type === 'error' ? <ShieldAlert className="w-5 h-5 shrink-0" /> : <CheckCircle className="w-5 h-5 shrink-0" />}
              <span className="text-sm font-medium leading-relaxed">{feedback.msg}</span>
            </div>
          )}
        </GlassCard>
      </div>
    </main>
  );
}