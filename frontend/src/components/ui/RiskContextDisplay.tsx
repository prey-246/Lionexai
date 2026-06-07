'use client';

import type { PortfolioRiskContext } from '@/lib/types';
import { TrendingUp, TrendingDown, ShieldAlert, Zap, Gauge, Wallet } from 'lucide-react';

interface RiskContextDisplayProps {
  riskContext: PortfolioRiskContext;
}

const RiskMetric = ({ label, value, icon: Icon, className = '' }: { label: string, value: string | number, icon: React.ElementType, className?: string }) => (
  <div className="flex items-center justify-between p-3 bg-background-panel-2 rounded-md">
    <div className="flex items-center gap-3">
      <Icon className="w-5 h-5 text-text-muted" />
      <span className="text-sm text-text-muted">{label}</span>
    </div>
    <span className={`font-mono text-sm font-semibold ${className}`}>{value}</span>
  </div>
);

export const RiskContextDisplay = ({ riskContext }: RiskContextDisplayProps) => {
  const currentDrawdown = riskContext.current_drawdown_pct || 0;
  const maxDrawdown = riskContext.max_drawdown_pct || 0;
  
  const isDrawdownHigh = currentDrawdown > (maxDrawdown * 0.75);
  const drawdownColor = currentDrawdown > 0 ? (isDrawdownHigh ? 'text-danger' : 'text-warning') : 'text-success';

  return (
    <div className="bg-background-panel-1 border border-border-secondary rounded-lg p-4">
      <h3 className="text-md font-semibold text-text-primary mb-4 flex items-center gap-2">
        <ShieldAlert className="w-5 h-5 text-primary-blue" />
        Live Risk Context
      </h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <RiskMetric label="Max Drawdown" value={`${maxDrawdown.toFixed(2)}%`} icon={TrendingDown} />
        <RiskMetric label="Current Drawdown" value={`${currentDrawdown.toFixed(2)}%`} icon={TrendingDown} className={drawdownColor} />
        <RiskMetric label="Daily Loss Limit" value={`${(riskContext.daily_loss_limit_pct || 0).toFixed(2)}%`} icon={TrendingDown} />
        <RiskMetric label="Leverage Limit" value={`${(riskContext.leverage_limit || 0).toFixed(1)}x`} icon={TrendingUp} />
        <RiskMetric label="Capital at Risk" value={`$${(riskContext.capital_at_risk || 0).toLocaleString()}`} icon={Wallet} />
        <RiskMetric label="Exposure" value={`${(riskContext.exposure_utilization_pct || 0).toFixed(2)}%`} icon={Gauge} />
        <RiskMetric label="Kill Switch" value={riskContext.kill_switch_status ? 'ACTIVE' : 'Inactive'} icon={Zap} className={riskContext.kill_switch_status ? 'text-danger' : 'text-success'} />
      </div>
    </div>
  );
};