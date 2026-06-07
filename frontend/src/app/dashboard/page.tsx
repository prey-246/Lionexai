'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { portfolioAPI } from '@/lib/api';
import type { Portfolio, PortfolioSummary } from '@/lib/types';
import { PageHeader } from "@/components/ui/PageHeader";
import { MetricDisplay } from '@/components/ui/MetricDisplay';
import { Loader2, AlertTriangle, Wallet, Activity, TrendingUp, ArrowRight, Star, ShieldAlert } from 'lucide-react';
import MandateBadge from '@/components/ui/MandateBadge';

export default function ClientDashboard() {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [livePrices, setLivePrices] = useState<{[key: string]: number}>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setError(null);
        const [summaryData, portfoliosData] = await Promise.all([
          portfolioAPI.getSummary(),
          portfolioAPI.listPortfolios(),
        ]);
        setSummary(summaryData);
        setPortfolios(portfoliosData || []);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
    
    const wsUrl = (process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000').replace(/^http/, 'ws');
    const marketWs = new WebSocket(`${wsUrl}/api/ws/market`);
    marketWs.onopen = () => {
      marketWs.send(JSON.stringify({ type: 'SUBSCRIBE', symbols: ['BTC/USDT', 'ETH/USDT', 'SOL/USDT'] }));
    };
    marketWs.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'MARKET_TICK') {
        setLivePrices(message.data);
      }
    };

    return () => { marketWs.close(); };
  }, []);

  if (loading) {
    return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin" /></div>;
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-danger">
        <AlertTriangle className="w-12 h-12 mb-4" />
        <h2 className="text-xl font-semibold">Failed to load dashboard</h2>
        <p className="text-sm">{error}</p>
      </div>
    );
  }

  if (!summary) {
    return <div>No summary data available.</div>;
  }

  return (
    <div className="space-y-8">
      <PageHeader title="My Dashboard" subtitle="Aggregate performance overview of all your portfolios" />

      <div className="flex gap-4 overflow-hidden py-1">
        {Object.entries(livePrices || {}).length > 0 ? (
          Object.entries(livePrices || {}).map(([symbol, price]) => (
            <div key={symbol} className="flex items-center gap-2 text-sm font-mono bg-background-panel-2 px-3 py-1.5 rounded-md border border-border-secondary/50 shadow-sm">
              <span className="text-text-muted">{symbol}</span>
              <span className="text-primary-teal font-bold">${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</span>
            </div>
          ))
        ) : (
          <div className="text-sm text-text-muted font-mono animate-pulse flex items-center gap-2">
             <div className="w-2 h-2 bg-text-muted rounded-full animate-ping"></div>
             Connecting to live market feed...
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricDisplay label="Total Equity" value={`$${summary.total_equity.toLocaleString()}`} icon={Wallet} />
        <MetricDisplay label="Total P&L" value={`$${summary.total_pnl.toLocaleString()}`} trend={summary.total_pnl > 0 ? 'up' : 'down'} icon={Activity} />
        <MetricDisplay label="Overall Win Rate" value={`${summary.overall_win_rate_pct}%`} icon={TrendingUp} />
        <MetricDisplay label="Active Portfolios" value={summary.portfolio_count} icon={ShieldAlert} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-background-panel-1 border border-border-secondary rounded-lg p-6">
          <h3 className="text-lg font-semibold text-text-primary mb-4">Top Performers</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-text-muted flex items-center gap-2"><Star className="w-4 h-4 text-primary-gold"/>Best Portfolio</span>
              <span className="font-mono text-primary-gold">{summary.best_performing_id || 'N/A'}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-text-muted flex items-center gap-2"><TrendingUp className="w-4 h-4 text-danger transform scale-y-[-1]"/>Worst Portfolio</span>
              <span className="font-mono text-danger">{summary.worst_performing_id || 'N/A'}</span>
            </div>
          </div>
        </div>
        <div className="bg-background-panel-1 border border-border-secondary rounded-lg p-6">
          <h3 className="text-lg font-semibold text-text-primary mb-4">Quick Actions</h3>
           <div className="flex gap-4">
              <Link href="/portfolios" className="flex-1 text-center bg-primary-blue/10 text-primary-blue border border-primary-blue/20 hover:bg-primary-blue/20 rounded-md p-3 text-sm font-semibold transition-colors">
                Manage Portfolios
              </Link>
              <Link href="/trade" className="flex-1 text-center bg-primary-teal/10 text-primary-teal border border-primary-teal/20 hover:bg-primary-teal/20 rounded-md p-3 text-sm font-semibold transition-colors">
                Go to Terminal
              </Link>
           </div>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-text-primary mb-4">Portfolio List</h3>
        <div className="bg-background-panel-1 border border-border-secondary rounded-lg">
          <ul className="divide-y divide-border-secondary">
            {portfolios?.length > 0 ? portfolios.map(p => (
              <li key={p.id}>
                <Link href={`/portfolios/${p.id}`} className="p-4 flex justify-between items-center hover:bg-white/5 transition-colors group">
                  <div>
                    <p className="font-mono text-primary-gold group-hover:text-primary-teal">{p.id}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <MandateBadge mandateId={p.mandate_id} />
                      <span className="text-xs text-text-muted">|</span>
                      <p className="text-xs text-text-muted">Equity: ${p.total_equity.toLocaleString()}</p>
                    </div>
                  </div>
                  <ArrowRight className="w-4 h-4 text-text-muted group-hover:translate-x-1 transition-transform" />
                </Link>
              </li>
            )) : (
              <li className="p-4 text-center text-text-muted">No portfolios found. Create one in the 'Portfolios' section to get started.</li>
            )}
          </ul>
        </div>
      </div>
    </div>
  );
}
