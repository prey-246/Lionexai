interface MetricDisplayProps {
  label: string;
  value: string | number;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
}

export function MetricDisplay({ label, value, trend, trendValue }: MetricDisplayProps) {
  return (
    <div className="flex flex-col gap-1.5 p-5">
      <span className="text-[11px] font-semibold tracking-widest text-gray-400 uppercase font-sans">
        {label}
      </span>
      <div className="flex items-baseline gap-3">
        <span className="text-3xl font-bold tracking-tight text-white font-mono">
          {value}
        </span>
        {trend && trendValue && (
          <span className={`text-sm font-medium ${
            trend === 'up' ? 'text-[#10B981]' : trend === 'down' ? 'text-[#EF4444]' : 'text-gray-500'
          }`}>
            {trend === 'up' ? '↗' : trend === 'down' ? '↘' : '→'} {trendValue}
          </span>
        )}
      </div>
    </div>
  );
}