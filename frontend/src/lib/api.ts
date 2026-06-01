const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

export const systemAPI = {
  getHealth: async (): Promise<EngineHealth> => {
    const res = await fetch(`${API_BASE_URL}/health`, { next: { revalidate: 0 } });
    if (!res.ok) throw new Error("Risk Engine Offline");
    return res.json();
  },

  getMandates: async (): Promise<RiskMandate[]> => {
    const res = await fetch(`${API_BASE_URL}/api/mandates`, { cache: 'no-store' });
    if (!res.ok) throw new Error("Failed to fetch risk parameters");
    return res.json();
  },

  getMandate: async (id: string): Promise<RiskMandate> => {
    const res = await fetch(`${API_BASE_URL}/api/mandates/${id}`, { cache: 'no-store' });
    if (!res.ok) throw new Error("Failed to fetch mandate");
    return res.json();
  }
};

export interface BacktestRequest {
  symbol: string;
  timeframe: string;
  strategy: string;
}

export interface BacktestMetrics {
  final_capital: number;
  total_return_pct: number;
  max_drawdown_pct: number;
  win_rate_pct: number;
  sharpe_ratio: number;
  total_trades_simulated: number;
}

export interface BacktestResponse {
  status: string;
  symbol: string;
  metrics: BacktestMetrics;
}

export const quantAPI = {
  runBacktest: async (payload: BacktestRequest): Promise<BacktestResponse> => {
    const res = await fetch(`${API_BASE_URL}/api/backtest/run`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || "Backtest engine failure");
    }
    return res.json();
  }
};

export const portfolioAPI = {
  listPortfolios: async (): Promise<Portfolio[]> => {
    const res = await fetch(`${API_BASE_URL}/api/portfolios`, { cache: 'no-store' });
    if (!res.ok) throw new Error("Failed to fetch portfolios");
    return res.json();
  },

  getPortfolio: async (id: string): Promise<Portfolio> => {
    const res = await fetch(`${API_BASE_URL}/api/portfolios/${id}`, { cache: 'no-store' });
    if (!res.ok) throw new Error("Failed to fetch portfolio");
    return res.json();
  },

  getStats: async (id: string) => {
    const res = await fetch(`${API_BASE_URL}/api/portfolios/${id}/stats`, { cache: 'no-store' });
    if (!res.ok) throw new Error("Failed to fetch stats");
    return res.json();
  },

  getTrades: async (id: string, status?: string) => {
    const url = status ? `${API_BASE_URL}/api/portfolios/${id}/trades?status=${status}` : `${API_BASE_URL}/api/portfolios/${id}/trades`;
    const res = await fetch(url, { cache: 'no-store' });
    if (!res.ok) throw new Error("Failed to fetch trades");
    return res.json();
  },

  getEquityCurve: async (id: string, limit: number = 100) => {
    const res = await fetch(`${API_BASE_URL}/api/portfolios/${id}/equity-curve?limit=${limit}`, { cache: 'no-store' });
    if (!res.ok) throw new Error("Failed to fetch equity curve");
    return res.json();
  },

  getRiskEvents: async (id: string, limit: number = 50) => {
    const res = await fetch(`${API_BASE_URL}/api/portfolios/${id}/risk-events?limit=${limit}`, { cache: 'no-store' });
    if (!res.ok) throw new Error("Failed to fetch risk events");
    return res.json();
  }
};

export const tradeAPI = {
  getPortfolio: async () => {
    const res = await fetch(`${API_BASE_URL}/api/trading/portfolio`, { next: { revalidate: 0 } });
    if (!res.ok) throw new Error("Failed to fetch portfolio");
    return res.json();
  },
  executeTrade: async (payload: { symbol: string, side: string, size: number }) => {
    const res = await fetch(`${API_BASE_URL}/api/trading/execute`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || "Trade execution failed");
    }
    return res.json();
  }
};

export const auditAPI = {
  getLogs: async (actionType?: string, limit: number = 100, offset: number = 0) => {
    const params = new URLSearchParams();
    if (actionType) params.append('action_type', actionType);
    params.append('limit', limit.toString());
    params.append('offset', offset.toString());

    const res = await fetch(`${API_BASE_URL}/api/audit?${params}`, { cache: 'no-store' });
    if (!res.ok) throw new Error("Failed to fetch audit logs");
    return res.json();
  },

  getRiskRejections: async (limit: number = 50) => {
    const res = await fetch(`${API_BASE_URL}/api/audit/events/risk-rejections?limit=${limit}`, { cache: 'no-store' });
    if (!res.ok) throw new Error("Failed to fetch risk rejections");
    return res.json();
  },

  getKillSwitchEvents: async (limit: number = 50) => {
    const res = await fetch(`${API_BASE_URL}/api/audit/events/kill-switch?limit=${limit}`, { cache: 'no-store' });
    if (!res.ok) throw new Error("Failed to fetch kill switch events");
    return res.json();
  }
};

export const reportsAPI = {
  generateReport: async (payload: { portfolio_id: string, report_type: string, start_date?: string, end_date?: string }) => {
    const res = await fetch(`${API_BASE_URL}/api/reports/generate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Failed to generate report");
    return res.json();
  },

  getReports: async (portfolioId: string, reportType?: string, limit: number = 10) => {
    const url = reportType
      ? `${API_BASE_URL}/api/reports/${portfolioId}?report_type=${reportType}&limit=${limit}`
      : `${API_BASE_URL}/api/reports/${portfolioId}?limit=${limit}`;
    const res = await fetch(url, { cache: 'no-store' });
    if (!res.ok) throw new Error("Failed to fetch reports");
    return res.json();
  }
};

export const strategiesAPI = {
  listStrategies: async () => {
    const res = await fetch(`${API_BASE_URL}/api/strategies`, { cache: 'no-store' });
    if (!res.ok) throw new Error("Failed to fetch strategies");
    return res.json();
  },

  getStrategy: async (id: string) => {
    const res = await fetch(`${API_BASE_URL}/api/strategies/${id}`, { cache: 'no-store' });
    if (!res.ok) throw new Error("Failed to fetch strategy");
    return res.json();
  },

  createStrategy: async (payload: any) => {
    const res = await fetch(`${API_BASE_URL}/api/strategies`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Failed to create strategy");
    return res.json();
  },

  updateStrategy: async (id: string, payload: any) => {
    const res = await fetch(`${API_BASE_URL}/api/strategies/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error("Failed to update strategy");
    return res.json();
  }
};