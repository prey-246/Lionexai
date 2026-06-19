export interface ChartPoint {
  time: number | string;
  value: number;
}

export interface ExchangeDistribution {
  binance: number;
  bybit: number;
  binance_pct: number;
  bybit_pct: number;
}

export interface ValidationChartData {
  equity_curve?: ChartPoint[];
  cumulative_pnl?: ChartPoint[];
  daily_pnl?: ChartPoint[];
  weekly_pnl?: ChartPoint[];
  monthly_pnl?: ChartPoint[];
  drawdown_series?: ChartPoint[];
  rolling_drawdown?: ChartPoint[];
  daily_trades?: ChartPoint[];
  daily_returns?: ChartPoint[];
  rolling_win_rate?: ChartPoint[];
}

export interface ValidationSnapshot {
  snapshot_key: string;
  snapshot_type: string;
  period: string;
  scope_id?: string | null;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate_pct: number;
  total_pnl: number;
  profit_factor: number | null;
  sharpe_ratio: number | null;
  max_drawdown_pct: number;
  avg_return_pct: number;
  largest_win: number;
  largest_loss: number;
  avg_latency_ms: number;
  fill_rate_pct: number;
  total_orders: number;
  filled_orders: number;
  rejected_orders: number;
  best_portfolio: string | null;
  worst_portfolio: string | null;
  best_strategy: string | null;
  worst_strategy: string | null;
  exchange_distribution: ExchangeDistribution | null;
  chart_data: ValidationChartData | null;
  updated_at: string;
}

export interface ValidationHistoryRecord {
  archive_date: string;
  snapshot_key: string;
  snapshot_type: string;
  period: string;
  scope_id: string | null;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate_pct: number;
  total_pnl: number;
  profit_factor: number | null;
  sharpe_ratio: number | null;
  max_drawdown_pct: number;
  avg_return_pct: number;
  largest_win: number;
  largest_loss: number;
  avg_latency_ms: number;
  fill_rate_pct: number;
  archived_at: string;
}

export interface MetricTimeseriesPoint {
  date: string;
  time: number;
  value: number | null;
}

export interface MetricTimeseries {
  snapshot_key: string;
  metric: string;
  series: MetricTimeseriesPoint[];
}

export interface ValidationDayStat {
  day: string;
  trades_executed: number;
  success_rate: number;
  risk_rejections: number;
}

export interface ValidationSummary {
  daily_stats: ValidationDayStat[];
  aggregated: {
    total_orders: number;
    filled_orders: number;
    rejected_orders: number;
    average_latency: number;
    best_portfolio: string | null;
    worst_portfolio: string | null;
  };
}

export type ValidationPeriod = 'TODAY' | '7D' | '14D' | '30D' | 'ALL';

export type ValidationMetric =
  | 'win_rate_pct'
  | 'max_drawdown_pct'
  | 'total_pnl'
  | 'sharpe_ratio'
  | 'avg_return_pct'
  | 'fill_rate_pct';
