'use client';

import { useState, useEffect } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { MetricDisplay } from '@/components/ui/MetricDisplay';
import { portfolioAPI, treasuryAPI, strategiesAPI, systemAPI, auditAPI, executionHealthAPI, exchangeAPI } from '@/lib/api';
import { Landmark, Wallet, Database, Activity, ShieldAlert, Coins, TrendingUp, Loader2, Play, Bot, Cpu, Target, HeartPulse, Server, Power } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

export default function ExecutiveDashboard() {
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState<any>(null);
  const [taskStatuses, setTaskStatuses] = useState<any[]>([]);

  useEffect(() => {
    const fetchExecutiveData = async () => {
      try {
        const [
          portfolios,
          pools,
          treasuryTx,
          strategies,
          legacyHealth, // Renaming to avoid conflict
          riskRejections,
          execHealth,
          exchangeStatus,
          taskStatusesData
        ] = await Promise.all([
          portfolioAPI.listPortfolios(),
          treasuryAPI.getPools(),
          treasuryAPI.getTransactions(1000),
          strategiesAPI.listStrategies(),
          systemAPI.getHealth(), // This provides trades_today
          auditAPI.getRiskRejections(100),
          executionHealthAPI.getStats(),
          exchangeAPI.getStatus('binance'), // Primary exchange for health check
          systemAPI.getBackgroundTaskStatuses()
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

        // Calculate Autonomous Metrics
        const autonomousStrategies = strategies.filter((s: any) => s.is_active && s.parameters?.assigned_portfolio_id);
        const autonomousPortfolioIds = new Set(autonomousStrategies.map((s: any) => s.parameters.assigned_portfolio_id));
        const autonomousAUM = portfolios
          .filter((p: any) => autonomousPortfolioIds.has(p.id))
          .reduce((sum: number, p: any) => sum + (p.total_equity || 0), 0);

        setMetrics({
          platformAUM,
          corporateTreasuryNAV,
          totalStrategies: strategies.length,
          activePortfolios: portfolios.length,
          autonomousTradesToday: legacyHealth.trades_today,
          riskRejectionsCount: riskRejections.length,
          lnxNav,
          yieldGenerated,
          autonomousAUM,
          autonomousStrategiesCount: autonomousStrategies.length,
          executionFillRate: execHealth.execution_fill_rate_pct,
          avgExecutionLatency: execHealth.avg_placement_latency_ms,
          primaryExchangeStatus: exchangeStatus.status,
          strategySuccessRate: Math.round(execHealth.execution_fill_rate_pct || 0),
        });

        setTaskStatuses(taskStatusesData || []);
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
        <h3 className="sec-head pl-1">Capital & Ecosystem Metrics</h3>
        <div className="g4">
          <MetricDisplay label="Platform AUM (Client)" value={`$${metrics.platformAUM.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`} icon={Wallet} />
          <MetricDisplay label="Corporate Treasury NAV" value={`$${metrics.corporateTreasuryNAV.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`} icon={Landmark} />
          <MetricDisplay label="Total Yield Generated" value={`$${metrics.yieldGenerated.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`} icon={TrendingUp} trend="up" />
          <MetricDisplay label="LNX Token NAV" value={`$${metrics.lnxNav.toFixed(4)}`} icon={Coins} trend="up" />
        </div>
      </div>

      {/* Autonomous Execution & Quant Engine */}
      <div>
        <h3 className="sec-head pl-1">Autonomous Execution Engine</h3>
        <div className="g4">
          <MetricDisplay label="Autonomous AUM" value={`$${metrics.autonomousAUM.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`} icon={Bot} />
          <MetricDisplay label="Active Auto-Strategies" value={metrics.autonomousStrategiesCount} icon={Cpu} />
          <MetricDisplay label="Autonomous Trades Today" value={metrics.autonomousTradesToday} icon={Activity} />
          <MetricDisplay label="Execution Success Rate" value={`${metrics.strategySuccessRate}%`} icon={Target} trend="up" />
        </div>
      </div>

      {/* Execution & Exchange Health */}
      <div>
        <h3 className="sec-head pl-1">Execution & Exchange Health</h3>
        <div className="g4">
          <MetricDisplay label="Execution Fill Rate (1H)" value={`${metrics.executionFillRate}%`} icon={HeartPulse} trend="up" />
          <MetricDisplay label="Avg. Execution Latency" value={`${metrics.avgExecutionLatency} ms`} icon={Cpu} />
          <MetricDisplay label="Primary Exchange Status" value={metrics.primaryExchangeStatus} icon={Server} trend={metrics.primaryExchangeStatus === 'OPERATIONAL' ? 'up' : 'down'} />
        </div>
      </div>

      {/* System Status */}
      <div>
        <h3 className="sec-head pl-1">Background System Status</h3>
        <div className="card p-5">
          <div className="space-y-3">
            {taskStatuses.map((task: any) => (
              <div key={task.name} className="flex justify-between items-center text-sm border-b border-border-subtle pb-2 last:border-b-0">
                <div className="flex items-center gap-3">
                  <Power className="w-4 h-4 text-primary-emerald" />
                  <span className="font-sans text-text-primary">{task.name}</span>
                </div>
                <div className="flex items-center gap-4">
                  <span className="font-mono text-[11px] text-text-muted">{formatDistanceToNow(new Date(task.last_run), { addSuffix: true })}</span>
                  <span className={`tag ${task.status === 'OPERATIONAL' ? 'teal' : 'red'}`}>{task.status}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Operations & Risk Health */}
      <div>
        <h3 className="sec-head pl-1">System Operations & Governance</h3>
        <div className="g4">
          <MetricDisplay label="Active Portfolios" value={metrics.activePortfolios} icon={Database} />
          <MetricDisplay label="Strategies in Registry" value={metrics.totalStrategies} icon={Play} />
          <MetricDisplay label="Risk Rejections" value={metrics.riskRejectionsCount} icon={ShieldAlert} trend={metrics.riskRejectionsCount > 0 ? "down" : "neutral"} />
        </div>
      </div>

      <div className="card gold mt-8 p-6 text-center">
        <h2 className="font-display text-[24px] font-bold text-text-primary mb-2">System Operational</h2>
        <p className="font-sans text-[13px] text-text-secondary">
          The LionexAI ecosystem is fully synchronized. Autonomous engines are active, and risk governance is strictly enforced.
        </p>
      </div>
    </div>
  );
}