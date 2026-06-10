import { LucideIcon } from 'lucide-react';

interface MetricDisplayProps {
  label: string;
  value: string | number;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  change?: number;
  icon?: LucideIcon;
}

export function MetricDisplay({
  label,
  value,
  trend,
  trendValue,
  change,
  icon: Icon
}: MetricDisplayProps) {
  const displayTrend = change !== undefined
    ? change > 0 ? 'up' : change < 0 ? 'down' : 'neutral'
    : trend;

  const displayTrendValue = change !== undefined
    ? `${change > 0 ? '+' : ''}${change.toFixed(2)}%`
    : trendValue;

  return (
    <div className="card flex flex-col gap-1.5" style={{ padding: '14px 16px' }}>
      <div className="flex items-center justify-between">
        <span className="font-mono text-[8.5px] uppercase tracking-wider text-text-muted">
          {label}
        </span>
        {Icon && <Icon className="w-4 h-4 text-text-muted" />}
      </div>
      <div className="flex items-baseline gap-3">
        <span className="font-serif text-[26px] font-bold text-text-primary">
          {value}
        </span>
        {displayTrend && displayTrendValue && (
          <span className={`tag ${displayTrend === 'up' ? 'teal' : displayTrend === 'down' ? 'red' : 'grey'}`}>
            {displayTrend === 'up' ? '↗' : displayTrend === 'down' ? '↘' : '→'} {displayTrendValue}
          </span>
        )}
      </div>
    </div>
  );
}