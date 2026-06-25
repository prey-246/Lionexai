import { LucideIcon, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';

interface MetricDisplayProps {
  label: string;
  value: string | number;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  change?: number;
  icon?: LucideIcon;
  accent?: 'gold' | 'teal' | 'red' | 'blue';
}

export function MetricDisplay({
  label,
  value,
  trend,
  trendValue,
  change,
  icon: Icon,
  accent,
}: MetricDisplayProps) {
  const displayTrend = change !== undefined
    ? change > 0 ? 'up' : change < 0 ? 'down' : 'neutral'
    : trend;

  const displayTrendValue = change !== undefined
    ? `${change > 0 ? '+' : ''}${change.toFixed(2)}%`
    : trendValue;

  const TrendIcon = displayTrend === 'up' ? ArrowUpRight : displayTrend === 'down' ? ArrowDownRight : Minus;
  const trendColor = displayTrend === 'up'
    ? 'text-primary-emerald-bright'
    : displayTrend === 'down'
      ? 'text-danger'
      : 'text-text-muted';

  return (
    <div className={`card ${accent ?? ''} group min-w-0 overflow-hidden`}>
      <div className="flex items-start justify-between gap-3">
        <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-text-muted">
          {label}
        </span>
        {Icon && (
          <span className="shrink-0 grid place-items-center w-8 h-8 rounded-lg bg-background-panel border border-border-subtle text-text-muted group-hover:text-primary-gold-bright transition-colors">
            <Icon className="w-4 h-4" />
          </span>
        )}
      </div>
      <div className="mt-3 flex items-end justify-between gap-3 flex-wrap min-w-0">
        <span className="font-display font-bold text-[clamp(1.125rem,2.5vw,1.875rem)] leading-tight text-text-primary tabular-nums tracking-tight break-all min-w-0">
          {value}
        </span>
        {displayTrend && displayTrendValue && (
          <span className={`inline-flex items-center gap-1 font-mono text-[12px] font-bold ${trendColor}`}>
            <TrendIcon className="w-3.5 h-3.5" />
            {displayTrendValue}
          </span>
        )}
      </div>
    </div>
  );
}
