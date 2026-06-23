'use client';

import type { PortfolioRiskContext } from '@/lib/types';
import { TrendingUp, TrendingDown, ShieldAlert, Zap, Gauge, Wallet } from 'lucide-react';
import { formatFixed, toFiniteNumber } from '@/lib/format';

interface RiskContextDisplayProps {
  riskContext?: PortfolioRiskContext | null;
}

const RiskMetric = ({ label, value, icon: Icon, className = '' }: { label: string, value: string | number, icon: React.ElementType, className?: string }) => (
  <div className="flex items-center justify-between gap-3 p-3 bg-background-panel border border-border-subtle rounded-lg hover:border-border-default transition-colors">
    <div className="flex items-center gap-2.5 min-w-0">
      <Icon className="w-4 h-4 text-text-muted shrink-0" />
      <span className="text-[13px] text-text-muted truncate">{label}</span>
    </div>
    <span className={`font-mono text-[14px] font-bold tabular-nums shrink-0 ${className || 'text-text-primary'}`}>{value}</span>
  </div>
);

export const RiskContextDisplay = ({ riskContext }: RiskContextDisplayProps) => {
  if (!riskContext || typeof riskContext !== 'object') {
    return (
      <div className="card text-[13px] text-text-muted">
        Risk context unavailable for this portfolio.
      </div>
    );
  }

  const currentDrawdown = toFiniteNumber(
    riskContext.current_drawdown_pct ?? riskContext.current_drawdown,
  );
  const maxDrawdown = toFiniteNumber(
    riskContext.max_drawdown_pct ?? riskContext.max_drawdown,
  );
  const dailyLossLimit = toFiniteNumber(
    riskContext.daily_loss_limit_pct ?? riskContext.daily_loss_limit,
  );
  const leverageLimit = toFiniteNumber(riskContext.leverage_limit ?? riskContext.leverage_used);
  const capitalAtRisk = toFiniteNumber(riskContext.capital_at_risk);
  const exposurePct = toFiniteNumber(riskContext.exposure_utilization_pct);
  
  const isDrawdownHigh = currentDrawdown > (maxDrawdown * 0.75);
  const drawdownColor = currentDrawdown > 0 ? (isDrawdownHigh ? 'text-danger' : 'text-warning') : 'text-success';

  return (
    <div className="card">
      <h3 className="text-[15px] font-semibold text-text-primary mb-4 flex items-center gap-2">
        <ShieldAlert className="w-5 h-5 text-primary-blue" />
        Live Risk Context
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <RiskMetric label="Max Drawdown" value={`${formatFixed(maxDrawdown)}%`} icon={TrendingDown} />
        <RiskMetric label="Current Drawdown" value={`${formatFixed(currentDrawdown)}%`} icon={TrendingDown} className={drawdownColor} />
        <RiskMetric label="Daily Loss Limit" value={`${formatFixed(dailyLossLimit)}%`} icon={TrendingDown} />
        <RiskMetric label="Leverage Limit" value={`${formatFixed(leverageLimit, 1)}x`} icon={TrendingUp} />
        <RiskMetric label="Capital at Risk" value={`$${capitalAtRisk.toLocaleString()}`} icon={Wallet} />
        <RiskMetric label="Exposure" value={`${formatFixed(exposurePct)}%`} icon={Gauge} />
        <RiskMetric label="Kill Switch" value={riskContext.kill_switch_status ? 'ACTIVE' : 'Inactive'} icon={Zap} className={riskContext.kill_switch_status ? 'text-danger' : 'text-success'} />
      </div>
    </div>
  );
};