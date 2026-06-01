export interface RiskMandate {
  id: string;
  name: string;
  max_leverage: number;
  max_drawdown_pct: number;
  daily_loss_limit_pct: number;
  kill_switch_active: boolean;
}

export interface EngineHealth {
  status: string;
  database: string;
  active_mandates: number;
}

export interface Portfolio {
  id: string;
  user_id: string;
  mandate_id: string;
  total_equity: number;
  available_margin: number;
  current_drawdown_pct: number;
}

export interface PortfolioSummary {
  portfolio_count: number;
  total_equity: number;
  total_pnl: number;
  overall_win_rate_pct: number;
  best_performing_portfolio: string | null;
  worst_performing_portfolio: string | null;
}

export interface PortfolioStats {
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate_pct: number;
  total_pnl: number;
  avg_pnl_per_trade: number;
  best_trade_pnl: number;
  worst_trade_pnl: number;
}

export interface Trade {
  id: string;
  portfolio_id: string;
  symbol: string;
  side: string;
  size: number;
  entry_price: number;
  exit_price?: number;
  status: string;
  pnl: number;
  created_at: string;
  closed_at?: string;
}

export interface TradeResponse {
  status: string;
  trade_id: string;
  fill_price: number;
}

export interface ReportGenerate {
  portfolio_id: string;
  report_type: 'WEEKLY' | 'MONTHLY' | 'CUSTOM';
  start_date?: string;
  end_date?: string;
}

export interface Report {
  id: string;
  portfolio_id: string;
  report_type: string;
  period_start: string;
  period_end: string;
  performance_metrics: any;
  risk_metrics: any;
  trades_summary: any;
  created_at: string;
}

export interface RiskEvent {
  id: string;
  portfolio_id: string;
  event_type: string;
  severity: string;
  description: string;
  triggered_at: string;
  resolved: boolean;
}

export interface AuditLog {
  id: string;
  timestamp: string;
  action_type: string;
  description: string;
  metadata_json: any;
}

export interface PaginatedAuditLogs {
  total: number;
  limit: number;
  offset: number;
  logs: AuditLog[];
}

export interface BacktestRequest {
  symbol: string;
  timeframe: string;
  strategy: string;
  initial_capital: number;
  strategy_params?: { [key: string]: any };
}

export interface BacktestMetrics {
  final_capital: number;
  total_return_pct: number;
  max_drawdown_pct: number;
  win_rate_pct: number;
  sharpe_ratio: number;
  total_trades_simulated: number;
}

export interface EquityDataPoint {
  time: number;
  value: number;
}

export interface BacktestResponse {
  status: string;
  symbol: string;
  metrics: BacktestMetrics;
  equity_curve: EquityDataPoint[];
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
}