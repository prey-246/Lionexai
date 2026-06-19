'use client';

import { useEffect, useState } from 'react';
import { analyticsAPI } from '@/lib/api/analytics';
import type { TradeRecord } from '@/lib/api/analytics';
import { portfolioAPI } from '@/lib/api';
import { PageHeader } from '@/components/ui/PageHeader';
import { Loader2, Search, Filter } from 'lucide-react';
import { formatCurrency, formatFixed } from '@/lib/format';

export default function TradeExplorerPage() {
  const [trades, setTrades] = useState<TradeRecord[]>([]);
  const [portfolios, setPortfolios] = useState<{ id: string }[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const limit = 25;

  const [filters, setFilters] = useState({
    search: '',
    portfolio_id: '',
    symbol: '',
    strategy_name: '',
    exchange: '',
    trade_source: '',
    status: '',
    side: '',
  });

  useEffect(() => {
    portfolioAPI.listPortfolios().then(setPortfolios).catch(() => {});
  }, []);

  useEffect(() => {
    const fetchTrades = async () => {
      setLoading(true);
      try {
        const res = await analyticsAPI.searchTrades({
          ...filters,
          portfolio_id: filters.portfolio_id || undefined,
          trade_source: filters.trade_source || undefined,
          status: filters.status || undefined,
          exchange: filters.exchange || undefined,
          side: filters.side || undefined,
          skip: (page - 1) * limit,
          limit,
        });
        setTrades(res.trades);
        setTotal(res.total);
      } catch (err) {
        console.error(err);
        setTrades([]);
        setTotal(0);
      } finally {
        setLoading(false);
      }
    };
    fetchTrades();
  }, [filters, page]);

  const totalPages = Math.max(1, Math.ceil(total / limit));

  return (
    <div className="space-y-6">
      <PageHeader
        title="Trade Explorer"
        subtitle="Search and filter historical trades across portfolios, strategies, and exchanges."
      />

      <div className="bg-background-panel-1 border border-border-secondary rounded-lg p-4 grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-3">
        <div className="md:col-span-2 relative">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-text-muted" />
          <input
            placeholder="Search symbol, strategy, trade ID..."
            className="w-full pl-9 pr-3 py-2 text-sm bg-background-panel-2 border border-border-secondary rounded-md"
            value={filters.search}
            onChange={e => { setFilters(f => ({ ...f, search: e.target.value })); setPage(1); }}
          />
        </div>
        <select
          className="text-sm bg-background-panel-2 border border-border-secondary rounded-md px-3 py-2"
          value={filters.portfolio_id}
          onChange={e => { setFilters(f => ({ ...f, portfolio_id: e.target.value })); setPage(1); }}
        >
          <option value="">All Portfolios</option>
          {portfolios.map(p => <option key={p.id} value={p.id}>{p.id}</option>)}
        </select>
        <select
          className="text-sm bg-background-panel-2 border border-border-secondary rounded-md px-3 py-2"
          value={filters.trade_source}
          onChange={e => { setFilters(f => ({ ...f, trade_source: e.target.value })); setPage(1); }}
        >
          <option value="">All Sources</option>
          <option value="AUTONOMOUS">Autonomous</option>
          <option value="MANUAL">Manual</option>
          <option value="SEED">Seed</option>
        </select>
        <input
          placeholder="Symbol"
          className="text-sm bg-background-panel-2 border border-border-secondary rounded-md px-3 py-2"
          value={filters.symbol}
          onChange={e => { setFilters(f => ({ ...f, symbol: e.target.value })); setPage(1); }}
        />
        <input
          placeholder="Strategy"
          className="text-sm bg-background-panel-2 border border-border-secondary rounded-md px-3 py-2"
          value={filters.strategy_name}
          onChange={e => { setFilters(f => ({ ...f, strategy_name: e.target.value })); setPage(1); }}
        />
        <select
          className="text-sm bg-background-panel-2 border border-border-secondary rounded-md px-3 py-2"
          value={filters.exchange}
          onChange={e => { setFilters(f => ({ ...f, exchange: e.target.value })); setPage(1); }}
        >
          <option value="">All Exchanges</option>
          <option value="binance">Binance</option>
          <option value="bybit">Bybit</option>
        </select>
        <select
          className="text-sm bg-background-panel-2 border border-border-secondary rounded-md px-3 py-2"
          value={filters.status}
          onChange={e => { setFilters(f => ({ ...f, status: e.target.value })); setPage(1); }}
        >
          <option value="">All Statuses</option>
          <option value="OPEN">Open</option>
          <option value="CLOSED">Closed</option>
          <option value="REJECTED">Rejected</option>
        </select>
      </div>

      <div className="flex items-center justify-between text-sm text-text-secondary">
        <span className="flex items-center gap-2"><Filter className="w-4 h-4" /> {total} trades found</span>
        <div className="flex gap-2">
          <button disabled={page <= 1} onClick={() => setPage(p => p - 1)} className="btn grey">Previous</button>
          <span>Page {page} / {totalPages}</span>
          <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)} className="btn grey">Next</button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-16"><Loader2 className="w-8 h-8 animate-spin text-primary-gold" /></div>
      ) : (
        <div className="overflow-x-auto bg-background-panel-1 border border-border-secondary rounded-lg">
          <table className="nexa-table w-full text-sm">
            <thead>
              <tr>
                <th>Time</th><th>Portfolio</th><th>Symbol</th><th>Side</th><th>Status</th>
                <th>Source</th><th>Exchange</th><th>Strategy</th><th>P&L</th><th>Latency</th>
              </tr>
            </thead>
            <tbody>
              {trades.length === 0 ? (
                <tr><td colSpan={10} className="text-center py-8 text-text-muted">No trades match your filters.</td></tr>
              ) : trades.map(t => (
                <tr key={t.id}>
                  <td className="font-mono whitespace-nowrap">{new Date(t.created_at).toLocaleString()}</td>
                  <td>{t.portfolio_id}</td>
                  <td className="font-semibold">{t.symbol}</td>
                  <td>{t.side}</td>
                  <td>{t.status}</td>
                  <td>{t.trade_source}</td>
                  <td>{t.exchange ?? '—'}</td>
                  <td>{t.strategy_name ?? '—'}</td>
                  <td className={t.pnl != null && t.pnl >= 0 ? 'text-success' : 'text-danger'}>
                    {t.pnl != null ? formatCurrency(t.pnl) : '—'}
                  </td>
                  <td>{t.execution_latency_ms != null ? `${formatFixed(t.execution_latency_ms, 0)} ms` : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
