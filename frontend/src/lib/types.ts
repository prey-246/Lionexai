import { Time } from "lightweight-charts";

export interface RiskMandate {
  pk_id: number;
  id: string;
  name: string;
  description: string;
  risk_tier: string;
  max_position_size_pct: number;
  max_portfolio_exposure_pct: number;
  max_leverage: number;
  daily_loss_limit_pct: number;
  max_drawdown_pct: number;
  max_open_positions: number;
  restricted_assets_enabled: boolean;
  kill_switch_enabled: boolean;
  allowed_assets: string[];
  is_active: boolean;
  kill_switch_active: boolean;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface PortfolioRiskContext {
  mandate_name?: string;
  risk_tier?: string;
  daily_loss_limit?: number;
  max_drawdown?: number;
  current_drawdown?: number;
  capital_at_risk?: number;
  exposure_used?: number;
  leverage_used?: number;
  kill_switch_status?: boolean;
  mandate_id?: string;
  daily_loss_limit_pct?: number;
  max_drawdown_pct?: number;
  current_drawdown_pct?: number;
  leverage_limit?: number;
  exposure_utilization_pct?: number;
}

export interface Portfolio {
  id: string;
  user_id: string;
  mandate_id: string;
  mandate_pk_id: number;
  total_equity: number;
  available_margin: number;
  current_drawdown_pct: number;
  risk_context: PortfolioRiskContext;
}

// Other types can be added here as needed
export interface EngineHealth {
  status: string;
  database: string;
  active_mandates: number;
  timestamp: string;
}

export interface PortfolioSummary {
  portfolio_count: number;
  total_equity: number;
  total_pnl: number;
  overall_win_rate_pct: number;
  best_performing_id: string;
  worst_performing_id: string;
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
  portfolio_id: number;
  symbol: string;
  side: 'BUY' | 'SELL';
  size: number;
  entry_price: number;
  exit_price?: number;
  status: 'OPEN' | 'CLOSED' | 'REJECTED';
  pnl: number;
  created_at: string;
  closed_at?: string;
}

export interface RiskEvent {
  id: string;
  portfolio_id: number;
  event_type: string;
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
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
  logs: AuditLog[];
  total: number;
  limit: number;
  offset: number;
}

export interface BacktestRequest {
  symbol: string;
  timeframe: string;
  strategy: string;
  initial_capital: number;
  commission_pct?: number;
  slippage_pct?: number;
  strategy_params?: {
    [key: string]: any;
  };
}

export interface BacktestMetrics {
  final_capital: number;
  total_return_pct: number;
  gross_return_pct: number;
  net_return_pct: number;
  total_fees_paid: number;
  slippage_impact: number;
  max_drawdown_pct: number;
  win_rate_pct: number;
  sharpe_ratio: number;
  total_trades_simulated: number;
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
export interface TradeResponse {
  status: string;
  trade_id: string;
  fill_price: number;
}
export interface EquityDataPoint { time: Time, value: number }

export interface Report {
  id: string;
  portfolio_id: number;
  report_type: 'WEEKLY' | 'MONTHLY';
  period_start: string;
  period_end: string;
  performance_metrics: {
    total_return_pct: number;
    total_pnl: number;
    winning_trades: number;
    losing_trades: number;
    win_rate_pct: number;
  };
  created_at: string;
}

export interface ReportGenerate {
  portfolio_id: string;
  report_type: 'WEEKLY' | 'MONTHLY';
}

export interface MarketNewsArticle {
  id: string;
  title: string;
  source: string;
  url?: string;
  content?: string;
  published_at: string;
  created_at: string;
}

export interface MarketSensitivityScore {
  id: string;
  symbol: string;
  score: number;
  contributing_factors?: Record<string, any>;
  timestamp: string;
}

export interface User {
  id: string;
  email: string;
  is_active: boolean;
  role_tier: 'client' | 'operator' | 'risk_manager' | 'admin' | string;
}