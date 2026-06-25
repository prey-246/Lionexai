'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { portfolioAPI, intelligenceAPI, fundsAPI, lnxAPI, assetsAPI } from '@/lib/api';
import type { Portfolio, PortfolioSummary, MarketNewsArticle, MarketSensitivityScore } from '@/lib/types';
import { PageHeader } from "@/components/ui/PageHeader";
import { GlobalMarketIntelligence } from "@/components/intelligence/GlobalMarketIntelligence";
import { MetricDisplay } from '@/components/ui/MetricDisplay';
import { Loader2, AlertTriangle, Wallet, Activity, TrendingUp, ArrowRight, Star, ShieldAlert, Newspaper, BrainCircuit, Coins, Landmark, Target } from 'lucide-react';
import MandateBadge from '@/components/ui/MandateBadge';

export default function ClientDashboard() {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [news, setNews] = useState<MarketNewsArticle[]>([]);
  const [sentiments, setSentiments] = useState<{[key: string]: MarketSensitivityScore}>({});
  const [livePrices, setLivePrices] = useState<{[key: string]: number}>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [lnxIndex, setLnxIndex] = useState<number | null>(null);
  const [weeklyTarget, setWeeklyTarget] = useState<number | null>(null);
  const [treasuryContributions, setTreasuryContributions] = useState(0);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setError(null);
        const [summaryData, portfoliosData, newsData, funds, lnx] = await Promise.all([
          portfolioAPI.getSummary(),
          portfolioAPI.listPortfolios(),
          intelligenceAPI.getNews(5),
          fundsAPI.listFunds().catch(() => []),
          lnxAPI.getIndex().catch(() => null),
        ]);

        const assetList = await assetsAPI.listAssets().catch(() => []);
        const symbolsToFetch = (assetList || []).slice(0, 6).map((a) => a.symbol);
        const sentimentResults: {[key: string]: MarketSensitivityScore} = {};
        await Promise.all(symbolsToFetch.map(async (sym) => {
          try {
            const data = await intelligenceAPI.getSentiment(sym);
            sentimentResults[sym] = data;
          } catch (e) { /* optional */ }
        }));

        const autoPortfolios = (portfoliosData || []).filter((p: any) => p.auto_managed);
        let contrib = 0;
        await Promise.all(autoPortfolios.slice(0, 3).map(async (p) => {
          try {
            const stl = await portfolioAPI.getSettlements(p.id, 5);
            contrib += (stl || []).reduce((s, x) => s + (x.excess_routed || 0), 0);
          } catch { /* optional */ }
        }));

        const fundTargets = (funds || []).map((f) => f.target_weekly_return_pct).filter(Boolean) as number[];
        setWeeklyTarget(fundTargets.length ? fundTargets.reduce((a, b) => a + b, 0) / fundTargets.length : null);
        setLnxIndex(lnx?.composite_index ?? null);
        setTreasuryContributions(contrib);
        setSummary(summaryData);
        setPortfolios(portfoliosData || []);
        setNews(newsData || []);
        setSentiments(sentimentResults);
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
      <PageHeader title="My Dashboard" subtitle="Fund performance, weekly yield targets, treasury contributions, and LNX ecosystem growth." />

      <GlobalMarketIntelligence />

      <div className="g4">
        <MetricDisplay label="Total Equity" value={`$${summary.total_equity.toLocaleString()}`} icon={Wallet} />
        <MetricDisplay label="Avg Weekly Target" value={weeklyTarget != null ? `${weeklyTarget.toFixed(2)}%` : '—'} icon={Target} trend="up" />
        <MetricDisplay label="Treasury Contributions" value={`$${treasuryContributions.toLocaleString(undefined, { minimumFractionDigits: 2 })}`} icon={Landmark} />
        <MetricDisplay label="LNX Index" value={lnxIndex?.toFixed(2) ?? '—'} icon={Coins} />
      </div>

      <div className="g4">
        <MetricDisplay label="Total P&L" value={`$${summary.total_pnl.toLocaleString()}`} trend={summary.total_pnl > 0 ? 'up' : 'down'} icon={Activity} />
        <MetricDisplay label="Active Portfolios" value={summary.portfolio_count} icon={ShieldAlert} />
        <Link href="/fund-performance" className="card blue p-4 flex items-center justify-between hover:border-primary-blue transition-colors">
          <span className="font-sans text-[13px]">Fund Performance</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
        <Link href="/allocation" className="card gold p-4 flex items-center justify-between hover:border-primary-gold transition-colors">
          <span className="font-sans text-[13px]">Live Allocation</span>
          <ArrowRight className="w-4 h-4" />
        </Link>
      </div>

      <div className="g21">
        <div className="card gold shadow-lg">
          <h3 className="sec-head">Top Performers</h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="font-mono text-[11px] uppercase tracking-wider text-text-muted flex items-center gap-2"><Star className="w-4 h-4 text-primary-gold"/>BEST PORTFOLIO</span>
              <span className="font-mono text-[14px] font-bold text-primary-gold-bright">{summary.best_performing_id || 'N/A'}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="font-mono text-[11px] uppercase tracking-wider text-text-muted flex items-center gap-2"><TrendingUp className="w-4 h-4 text-danger transform scale-y-[-1]"/>WORST PORTFOLIO</span>
              <span className="font-mono text-[14px] font-bold text-danger">{summary.worst_performing_id || 'N/A'}</span>
            </div>
          </div>
        </div>
        <div className="card blue shadow-lg">
          <h3 className="sec-head">Quick Actions</h3>
           <div className="flex gap-4">
              <Link href="/portfolios" className="flex-1 text-center btn gold btn-full">
                Manage Portfolios
              </Link>
              <Link href="/trade" className="flex-1 text-center btn teal btn-full">
                Go to Terminal
              </Link>
           </div>
        </div>
      </div>

      <div>
        <h3 className="sec-head">Portfolio List</h3>
        <div className="card shadow-lg p-0 overflow-hidden">
          <table className="nexa-table">
            <thead>
              <tr><th>ID</th><th>Mandate</th><th>Equity</th><th>Action</th></tr>
            </thead>
            <tbody>
              {portfolios?.length > 0 ? portfolios.map(p => (
                <tr key={p.id}>
                  <td className="font-mono font-bold text-primary-gold">{p.id}</td>
                  <td><MandateBadge mandateId={p.mandate_id} /></td>
                  <td className="font-mono">${p.total_equity.toLocaleString()}</td>
                  <td><Link href={`/portfolios/${p.id}`} className="btn grey">View</Link></td>
                </tr>
              )) : (
                <tr><td colSpan={4} className="text-center py-4 text-text-muted">No portfolios found.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div>
        <h3 className="sec-head flex items-center gap-2">
          <Newspaper className="w-5 h-5 text-primary-emerald" />
          Live Market Intelligence
        </h3>
        <div className="card shadow-lg p-0 overflow-hidden">
          <ul className="divide-y divide-border-default">
            {news?.length > 0 ? news.map(article => (
              <li key={article.id} className="p-6 hover:bg-white/5 transition-colors">
                <a href={article.url} target="_blank" rel="noopener noreferrer" className="block">
                  <p className="font-sans text-[13px] font-semibold text-text-primary hover:text-primary-emerald transition-colors mb-2">{article.title}</p>
                  <div className="flex items-center gap-3 font-sans text-[12px] text-text-secondary">
                    <span className="tag teal">{article.source}</span>
                    <span>•</span>
                    <span>{new Date(article.published_at).toLocaleString()}</span>
                  </div>
                </a>
              </li>
            )) : (
              <li className="p-8 text-center font-sans text-[13px] text-text-secondary">No recent news available.</li>
            )}
          </ul>
        </div>
      </div>
    </div>
  );
}
