import { apiJson, API_BASE_URL } from '../api';

export interface StrategyAnalytics {
  strategy_name: string;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate_pct: number;
  total_pnl: number;
  avg_pnl: number;
}

export interface PortfolioCompareItem {
  portfolio_id: string;
  total_equity: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate_pct: number;
  total_pnl: number;
  current_drawdown_pct: number;
  equity_curve: { timestamp: string; equity: number }[];
}

export interface TradeRecord {
  id: string;
  portfolio_id: string;
  symbol: string;
  side: string;
  quantity: number;
  entry_price: number;
  exit_price: number | null;
  status: string;
  pnl: number | null;
  exchange: string | null;
  execution_latency_ms: number | null;
  strategy_name: string | null;
  rejection_reason: string | null;
  trade_source: string;
  created_at: string;
  closed_at: string | null;
}

export interface PaginatedTrades {
  trades: TradeRecord[];
  total: number;
  limit: number;
  offset: number;
}

export const analyticsAPI = {
  getStrategyAnalytics(tradeSource?: string): Promise<StrategyAnalytics[]> {
    const params = tradeSource ? `?trade_source=${tradeSource}` : '';
    return apiJson(`${API_BASE_URL}/api/analytics/strategies${params}`);
  },

  comparePortfolios(ids: string[]): Promise<PortfolioCompareItem[]> {
    return apiJson(`${API_BASE_URL}/api/analytics/portfolios/compare?ids=${ids.join(',')}`);
  },

  compareStrategies(names: string[], tradeSource = 'AUTONOMOUS'): Promise<StrategyAnalytics[]> {
    const params = new URLSearchParams({ names: names.join(','), trade_source: tradeSource });
    return apiJson(`${API_BASE_URL}/api/analytics/strategies/compare?${params.toString()}`);
  },

  searchTrades(options: {
    portfolio_id?: string;
    symbol?: string;
    strategy_name?: string;
    exchange?: string;
    trade_source?: string;
    status?: string;
    side?: string;
    start_date?: string;
    end_date?: string;
    search?: string;
    skip?: number;
    limit?: number;
  }): Promise<PaginatedTrades> {
    const params = new URLSearchParams();
    Object.entries(options).forEach(([key, value]) => {
      if (value !== undefined && value !== '') params.set(key, String(value));
    });
    return apiJson(`${API_BASE_URL}/api/trades/?${params.toString()}`);
  },
};
