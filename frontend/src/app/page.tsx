'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { portfolioAPI } from '@/lib/api';
import type { Portfolio, PortfolioSummary } from '@/lib/types';
import { PageHeader } from "@/components/ui/PageHeader";
import { MetricDisplay } from '@/components/ui/MetricDisplay';
import { Loader2, AlertTriangle, Wallet, Activity, TrendingUp, ArrowRight, Star, ShieldAlert } from 'lucide-react';

export default function DashboardPage() {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        const [summaryData, portfoliosData] = await Promise.all([
          portfolioAPI.getSummary(),
          portfolioAPI.listPortfolios(),
        ]);
        setSummary(summaryData);
        setPortfolios(portfoliosData);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
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
      <PageHeader title="Global Portfolio Dashboard" subtitle="Aggregate performance overview of all your portfolios" />

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
              <span className="font-mono text-primary-gold">{summary.best_performing_portfolio || 'N/A'}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-text-muted flex items-center gap-2"><TrendingUp className="w-4 h-4 text-danger transform scale-y-[-1]"/>Worst Portfolio</span>
              <span className="font-mono text-danger">{summary.worst_performing_portfolio || 'N/A'}</span>
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
            {portfolios.length > 0 ? portfolios.map(p => (
              <li key={p.id}>
                <Link href={`/portfolios/${p.id}`} className="p-4 flex justify-between items-center hover:bg-white/5 transition-colors group">
                  <div>
                    <p className="font-mono text-primary-gold group-hover:text-primary-teal">{p.id}</p>
                    <p className="text-xs text-text-muted">Mandate: {p.mandate_id} | Equity: ${p.total_equity.toLocaleString()}</p>
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