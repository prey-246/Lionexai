'use client';

import { useState, useEffect } from 'react';
import { portfolioAPI, tradeAPI } from '@/lib/api';
import { Loader2, ShieldAlert, CheckCircle } from 'lucide-react';
import { PageHeader } from '@/components/ui/PageHeader';

export default function ExecutionTerminal() {
  const [portfolio, setPortfolio] = useState<any>(null);
  const [allPortfolios, setAllPortfolios] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState<{type: 'success'|'error', msg: string} | null>(null);

  const [form, setForm] = useState({
    symbol: 'BTC/USDT',
    side: 'BUY',
    size: '' as number | string,
    stop_loss: '' as number | string
  });

  const fetchAllPortfolios = async () => {
    try {
      // Fetch the list of portfolios for the current user
      const portfolios = await portfolioAPI.listPortfolios();
      setAllPortfolios(portfolios);
      if (portfolios.length > 0) {
        // If no portfolio is selected, or the selected one is gone, default to the first.
        if (!portfolio || !portfolios.find(p => p.id === portfolio.id)) {
          setPortfolio(portfolios[0]);
        }
      } else {
        // This user has no portfolios.
        setPortfolio(null);
        setFeedback({ type: 'error', msg: 'No portfolio found for your account. Please create one.' });
      }
    } catch (err: any) {
      setFeedback({ type: 'error', msg: `Failed to fetch portfolio data: ${err.message}` });
    }
  };

  useEffect(() => {
    fetchAllPortfolios();
  }, []);

  const handleExecute = async () => {
    setLoading(true);
    setFeedback(null);
    try {
      if (!portfolio) throw new Error("Portfolio not loaded.");

      const payload = {
        ...form,
        size: Number(form.size) || 0,
        stop_loss: form.stop_loss ? Number(form.stop_loss) : undefined
      };

      if (payload.size <= 0) {
        throw new Error("Order size must be greater than 0");
      }

      // The backend risk engine requires a stop loss for every trade.
      if (!payload.stop_loss) {
        throw new Error("A Stop Loss price is required for all trades.");
      }

      const res = await tradeAPI.executeTrade(portfolio.id, payload);
      setFeedback({ type: 'success', msg: `Order filled at $${res.fill_price.toLocaleString()}` });
      
      // Refresh only the current portfolio's data to avoid resetting the dropdown
      const updatedPortfolio = await portfolioAPI.getPortfolio(portfolio.id);
      setPortfolio(updatedPortfolio);
      // Also update the list in the background
      const updatedList = await portfolioAPI.listPortfolios();
      setAllPortfolios(updatedList);
    } catch (err: any) {
      setFeedback({ type: 'error', msg: `RISK REJECTION: ${err.message}` });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-8">
      <PageHeader
        title="Execution Terminal"
        subtitle="Simulated paper orders passing through the NEXA Risk Gatekeeper"
      />

      <div className="g212 items-start">
        <div className="card blue shadow-lg">
          <h2 className="sec-head mb-6">Order Entry</h2>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block font-mono text-[8.5px] font-bold text-text-muted uppercase tracking-wider mb-1.5">Asset</label>
                <select 
                  className="w-full border border-border-default rounded-[3px] px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-gold" 
                  value={form.symbol} 
                  onChange={(e) => setForm({...form, symbol: e.target.value})}
                >
                  <option value="BTC/USDT" className="bg-background-panel text-text-primary">BTC/USDT</option>
                  <option value="ETH/USDT" className="bg-background-panel text-text-primary">ETH/USDT</option>
                  <option value="DOGE/USDT" className="bg-background-panel text-text-primary">DOGE/USDT (Unapproved)</option>
                </select>
              </div>
              <div>
                <label className="block font-mono text-[8.5px] font-bold text-text-muted uppercase tracking-wider mb-1.5">Side</label>
                <select 
                  className="w-full border border-border-default rounded-[3px] px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-gold"
                  value={form.side} 
                  onChange={(e) => setForm({...form, side: e.target.value})}
                >
                  <option value="BUY" className="bg-background-panel text-text-primary">BUY</option>
                  <option value="SELL" className="bg-background-panel text-text-primary">SELL</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block font-mono text-[8.5px] font-bold text-text-muted uppercase tracking-wider mb-1.5">Quantity</label>
              <input 
                type="number" 
                step="0.1" 
                placeholder="0.00"
                className="w-full border border-border-default rounded-[3px] px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-gold"
                value={form.size} 
                onChange={(e) => {
                  const val = e.target.value;
                  setForm({...form, size: val === '' ? '' : parseFloat(val)});
                }} 
              />
            </div>

            <div>
              <label className="block font-mono text-[8.5px] font-bold text-text-muted uppercase tracking-wider mb-1.5">Stop Loss Price</label>
              <input
                type="number"
                step="0.01"
                placeholder="e.g. 64000.00"
                className="w-full border border-border-default rounded-[3px] px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-gold"
                value={form.stop_loss}
                onChange={(e) => {
                  const val = e.target.value;
                  setForm({...form, stop_loss: val === '' ? '' : parseFloat(val)});
                }}
              />
            </div>

            <button 
              onClick={handleExecute}
              disabled={loading || !form.size}
              className={`btn btn-full mt-4 ${
                form.side === 'BUY' ? 'teal' : 'red'
              }`}
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              {loading ? 'Validating...' : `EXECUTE ${form.side}`}
            </button>
          </div>

          {feedback && (
            <div className={`mt-6 p-4 rounded-[3px] flex items-start gap-3 border ${
              feedback.type === 'error' ? 'bg-system-rBg border-system-rBd text-danger' : 'bg-system-tBg border-system-tBd text-success'
            }`}>
              {feedback.type === 'error' ? <ShieldAlert className="w-5 h-5 shrink-0" /> : <CheckCircle className="w-5 h-5 shrink-0" />}
              <span className="font-sans text-[13px] leading-relaxed">{feedback.msg}</span>
            </div>
          )}
        </div>

        <div className="space-y-4">
          <h2 className="sec-head">Portfolio Status</h2>
          {allPortfolios.length > 1 && (
            <div className="card">
              <label className="block font-mono text-[8.5px] font-bold text-text-muted uppercase tracking-wider mb-2">SELECT PORTFOLIO</label>
              <select
                className="w-full border border-border-default rounded-[3px] px-3 py-2 font-sans text-[13px] focus:outline-none focus:border-primary-gold"
                value={portfolio?.id || ''}
                onChange={(e) => {
                  const selected = allPortfolios.find(p => p.id === e.target.value);
                  setPortfolio(selected || null);
                }}
              >
                {allPortfolios.map(p => <option key={p.id} value={p.id}>{p.id}</option>)}
              </select>
            </div>
          )}
          <div className="card space-y-1 shadow-lg">
            <p className="font-mono text-[8.5px] font-bold uppercase tracking-wider text-text-muted">Total Equity</p>
            <p className="font-serif text-[26px] font-bold text-primary-gold">${portfolio ? portfolio.total_equity.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '0.00'}</p>
          </div>
          <div className="card space-y-1 shadow-lg">
            <p className="font-mono text-[8.5px] font-bold uppercase tracking-wider text-text-muted">Available Margin</p>
            <p className="font-serif text-[26px] font-bold text-text-primary">${portfolio ? portfolio.available_margin.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '0.00'}</p>
          </div>
          <div className="card space-y-1 shadow-lg">
            <p className="font-mono text-[8.5px] font-bold uppercase tracking-wider text-text-muted">Capital At Risk</p>
            <p className="font-serif text-[26px] font-bold text-danger">${portfolio?.risk_context?.capital_at_risk?.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) || '0.00'}</p>
          </div>
          <div className="card space-y-1 shadow-lg">
            <p className="font-mono text-[8.5px] font-bold uppercase tracking-wider text-text-muted">Current Drawdown</p>
            <p className="font-serif text-[26px] font-bold text-danger">{portfolio?.current_drawdown_pct?.toFixed(2) || '0.00'}%</p>
          </div>
          <div className="card space-y-1 shadow-lg">
            <p className="font-mono text-[8.5px] font-bold uppercase tracking-wider text-text-muted">Active Mandate</p>
            <p className="font-mono text-[12px] text-primary-blue font-bold mt-1">{portfolio ? portfolio.mandate_id : 'N/A'}</p>
          </div>
        </div>
      </div>
    </div>
  );
}