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
    <div className="flex flex-col gap-1.5 p-5">
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-semibold tracking-widest text-gray-400 uppercase font-sans">
          {label}
        </span>
        {Icon && <Icon className="w-4 h-4 text-gray-500" />}
      </div>
      <div className="flex items-baseline gap-3">
        <span className="text-3xl font-bold tracking-tight text-white font-mono">
          {value}
        </span>
        {displayTrend && displayTrendValue && (
          <span className={`text-sm font-medium ${
            displayTrend === 'up' ? 'text-[#10B981]' : displayTrend === 'down' ? 'text-[#EF4444]' : 'text-gray-500'
          }`}>
            {displayTrend === 'up' ? '↗' : displayTrend === 'down' ? '↘' : '→'} {displayTrendValue}
          </span>
        )}
      </div>
    </div>
  );
}