'use client';

import { useState, useEffect } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { MetricDisplay } from '@/components/ui/MetricDisplay';
import { portfolioAPI, treasuryAPI, strategiesAPI, systemAPI, auditAPI } from '@/lib/api';
import { Landmark, Wallet, Database, Activity, ShieldAlert, Coins, TrendingUp, Loader2, Play } from 'lucide-react';

export default function ExecutiveDashboard() {
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState<any>(null);

  useEffect(() => {
    const fetchExecutiveData = async () => {
      try {
        const [
          portfolios,
          pools,
          treasuryTx,
          strategies,
          health,
          riskRejections
        ] = await Promise.all([
          portfolioAPI.listPortfolios(),
          treasuryAPI.getPools(),
          treasuryAPI.getTransactions(1000),
          strategiesAPI.listStrategies(),
          systemAPI.getHealth(),
          auditAPI.getRiskRejections(100)
        ]);

        // Calculate AUM & Treasury
        const platformAUM = portfolios.reduce((sum, p) => sum + (p.total_equity || 0), 0);
        const corporateTreasuryNAV = pools.reduce((sum, p) => sum + (p.balance || 0), 0);
        
        // Calculate LNX NAV
        const reservePool = pools.find(p => p.id === 'RESERVE');
        const lnxNav = (reservePool?.balance || 0) / 100000000;

        // Calculate Yield Generated
        const yieldGenerated = treasuryTx
          .filter(tx => tx.transaction_type === 'YIELD_SWEEP' && tx.amount > 0)
          .reduce((sum, tx) => sum + tx.amount, 0);

        setMetrics({
          platformAUM,
          corporateTreasuryNAV,
          totalStrategies: strategies.length,
          activePortfolios: portfolios.length,
          autonomousTradesToday: health.trades_today,
          riskRejectionsCount: riskRejections.length,
          lnxNav,
          yieldGenerated
        });
      } catch (err) {
        console.error("Failed to fetch executive metrics", err);
      } finally {
        setLoading(false);
      }
    };

    fetchExecutiveData();
  }, []);

  if (loading || !metrics) return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary-gold" /></div>;

  return (
    <div className="space-y-8">
      <PageHeader title="Executive Summary" subtitle="Macro-level snapshot of platform AUM, treasury health, and autonomous execution." />

      {/* Financial Health */}
      <div>
        <h3 className="font-mono text-[10px] uppercase tracking-wider text-text-muted mb-3 pl-1">Capital & Ecosystem Metrics</h3>
        <div className="g4">
          <MetricDisplay label="Platform AUM (Client)" value={`$${metrics.platformAUM.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`} icon={Wallet} />
          <MetricDisplay label="Corporate Treasury NAV" value={`$${metrics.corporateTreasuryNAV.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`} icon={Landmark} />
          <MetricDisplay label="Total Yield Generated" value={`$${metrics.yieldGenerated.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`} icon={TrendingUp} trend="up" />
          <MetricDisplay label="LNX Token NAV" value={`$${metrics.lnxNav.toFixed(4)}`} icon={Coins} trend="up" />
        </div>
      </div>

      {/* Operations & Risk Health */}
      <div>
        <h3 className="font-mono text-[10px] uppercase tracking-wider text-text-muted mb-3 pl-1">Operations & Quantitative Engine</h3>
        <div className="g4">
          <MetricDisplay label="Active Portfolios" value={metrics.activePortfolios} icon={Database} />
          <MetricDisplay label="Strategies in Registry" value={metrics.totalStrategies} icon={Play} />
          <MetricDisplay label="Trades Executed Today" value={metrics.autonomousTradesToday} icon={Activity} />
          <MetricDisplay label="Risk Rejections" value={metrics.riskRejectionsCount} icon={ShieldAlert} trend={metrics.riskRejectionsCount > 0 ? "down" : "neutral"} />
        </div>
      </div>

      <div className="card grey mt-8 p-6 text-center">
        <h2 className="font-serif text-[24px] font-light text-text-primary mb-2">System Operational</h2>
        <p className="font-sans text-[13px] text-text-secondary">
          The UnifyX NEXA ecosystem is fully synchronized. Autonomous engines are active, and risk governance is strictly enforced.
        </p>
      </div>
    </div>
  );
}