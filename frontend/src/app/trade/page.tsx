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

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
        <div className="lg:col-span-2 bg-background-panel-1 border border-border-secondary rounded p-6">
          <h2 className="font-mono text-base font-bold text-text-primary border-b border-border-primary pb-3 mb-6">ORDER ENTRY</h2>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-mono font-bold text-text-muted uppercase tracking-wider mb-1.5">Asset</label>
                <select 
                  className="w-full bg-background-panel-2 border border-border-primary rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-primary-gold" 
                  value={form.symbol} 
                  onChange={(e) => setForm({...form, symbol: e.target.value})}
                >
                  <option value="BTC/USDT" className="bg-background-panel-2 text-text-primary">BTC/USDT</option>
                  <option value="ETH/USDT" className="bg-background-panel-2 text-text-primary">ETH/USDT</option>
                  <option value="DOGE/USDT" className="bg-background-panel-2 text-text-primary">DOGE/USDT (Unapproved)</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-mono font-bold text-text-muted uppercase tracking-wider mb-1.5">Side</label>
                <select 
                  className="w-full bg-background-panel-2 border border-border-primary rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-primary-gold"
                  value={form.side} 
                  onChange={(e) => setForm({...form, side: e.target.value})}
                >
                  <option value="BUY" className="bg-background-panel-2 text-text-primary">BUY</option>
                  <option value="SELL" className="bg-background-panel-2 text-text-primary">SELL</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-mono font-bold text-text-muted uppercase tracking-wider mb-1.5">Quantity</label>
              <input 
                type="number" 
                step="0.1" 
                placeholder="0.00"
                className="w-full bg-background-panel-2 border border-border-primary rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-primary-gold"
                value={form.size} 
                onChange={(e) => {
                  const val = e.target.value;
                  setForm({...form, size: val === '' ? '' : parseFloat(val)});
                }} 
              />
            </div>

            <div>
              <label className="block text-xs font-mono font-bold text-text-muted uppercase tracking-wider mb-1.5">Stop Loss Price</label>
              <input
                type="number"
                step="0.01"
                placeholder="e.g. 64000.00"
                className="w-full bg-background-panel-2 border border-border-primary rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-primary-gold"
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
              className={`w-full mt-2 py-3 rounded text-sm font-mono font-bold tracking-wider uppercase transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed ${
                form.side === 'BUY' ? 'bg-primary-teal/20 text-primary-teal hover:bg-primary-teal/30 border border-primary-teal/30' 
                : 'bg-danger/20 text-danger hover:bg-danger/30 border border-danger/30'
              }`}
            >
              {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              {loading ? 'Validating...' : `EXECUTE ${form.side}`}
            </button>
          </div>

          {feedback && (
            <div className={`mt-6 p-4 rounded flex items-start gap-3 border ${
              feedback.type === 'error' ? 'bg-danger/10 border-danger/20 text-danger' : 'bg-primary-teal/10 border-primary-teal/20 text-primary-teal'
            }`}>
              {feedback.type === 'error' ? <ShieldAlert className="w-5 h-5 shrink-0" /> : <CheckCircle className="w-5 h-5 shrink-0" />}
              <span className="text-sm font-mono leading-relaxed">{feedback.msg}</span>
            </div>
          )}
        </div>

        <div className="space-y-4">
          <h2 className="font-mono text-base font-bold text-text-primary">PORTFOLIO STATUS</h2>
          {allPortfolios.length > 1 && (
            <div className="bg-background-panel-1 border border-border-secondary rounded p-4">
              <label className="block text-xs font-mono text-text-muted mb-1.5">SELECT PORTFOLIO</label>
              <select
                className="w-full bg-background-panel-2 border border-border-primary rounded px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-primary-gold"
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
          <div className="bg-background-panel-1 border border-border-secondary rounded p-4 space-y-1">
            <p className="text-xs font-mono text-text-muted">TOTAL EQUITY</p>
            <p className="text-2xl font-serif text-primary-gold font-semibold">${portfolio ? portfolio.total_equity.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '0.00'}</p>
          </div>
          <div className="bg-background-panel-1 border border-border-secondary rounded p-4 space-y-1">
            <p className="text-xs font-mono text-text-muted">AVAILABLE MARGIN</p>
            <p className="text-2xl font-serif text-text-primary font-semibold">${portfolio ? portfolio.available_margin.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) : '0.00'}</p>
          </div>
          <div className="bg-background-panel-1 border border-border-secondary rounded p-4 space-y-1">
            <p className="text-xs font-mono text-text-muted">ACTIVE MANDATE</p>
            <p className="text-lg font-mono text-primary-blue font-bold">{portfolio ? portfolio.mandate_id : 'N/A'}</p>
          </div>
        </div>
      </div>
    </div>
  );
}