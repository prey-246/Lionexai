import Cookies from 'js-cookie';

/**
 * Differentiates between server-side and client-side API calls.
 * In server components, `window` is undefined, so we use the internal Docker network URL.
 * In client components, we use the publicly exposed URL.
 */
const API_BASE_URL = typeof window === 'undefined'
  ? process.env.INTERNAL_API_URL || "http://localhost:8000"
  : process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// A wrapper for fetch that includes the auth token and handles errors
const apiFetch = async (url: string, options: RequestInit = {}) => {
  const headers: HeadersInit = { ...options.headers };

  // On the client-side, we can access cookies to get the auth token
  if (typeof window !== 'undefined') {
    const token = Cookies.get('auth_token');
    if (token) {
      (headers as { [key: string]: string })['Authorization'] = `Bearer ${token}`;
    }
  }
  
  // For POST/PUT with a JSON body, ensure Content-Type is set
  if (options.body && typeof options.body === 'string') {
      if (!('Content-Type' in headers)) {
          (headers as { [key: string]: string })['Content-Type'] = 'application/json';
      }
  }

  const res = await fetch(url, {
    ...options,
    headers,
  });

  if (!res.ok) {
    // Try to parse error detail from JSON response, otherwise use status text
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || "An API error occurred");
  }

  // Handle responses that might not have a body (e.g., 204 No Content)
  if (res.status === 204) return;

  return res.json();
};

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

export interface PaginatedAuditLogs {
  total: number;
  limit: number;
  offset: number;
  logs: AuditLog[];
}

export const systemAPI = {
  getHealth: async (): Promise<EngineHealth> => {
    const res = await fetch(`${API_BASE_URL}/api/health`, { next: { revalidate: 0 } });
    if (!res.ok) throw new Error("Risk Engine Offline");
    return res.json();
  },

  getMandates: (): Promise<RiskMandate[]> => {
    return apiFetch(`${API_BASE_URL}/api/mandates`, { cache: 'no-store' });
  },

  getMandate: (id: string): Promise<RiskMandate> => {
    return apiFetch(`${API_BASE_URL}/api/mandates/${id}`, { cache: 'no-store' });
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
  runBacktest: (payload: BacktestRequest): Promise<BacktestResponse> => {
    return apiFetch(`${API_BASE_URL}/api/backtest/run`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }
};

export const portfolioAPI = {
  listPortfolios: (): Promise<Portfolio[]> => {
    return apiFetch(`${API_BASE_URL}/api/portfolios`, { cache: 'no-store' });
  },

  getPortfolio: (id: string): Promise<Portfolio> => {
    return apiFetch(`${API_BASE_URL}/api/portfolios/${id}`, { cache: 'no-store' });
  },

  getStats: (id: string) => {
    return apiFetch(`${API_BASE_URL}/api/portfolios/${id}/stats`, { cache: 'no-store' });
  },

  getTrades: (id: string, status?: string) => {
    const url = status ? `${API_BASE_URL}/api/portfolios/${id}/trades?status=${status}` : `${API_BASE_URL}/api/portfolios/${id}/trades`;
    return apiFetch(url, { cache: 'no-store' });
  },

  getEquityCurve: (id: string, limit: number = 100) => {
    return apiFetch(`${API_BASE_URL}/api/portfolios/${id}/equity-curve?limit=${limit}`, { cache: 'no-store' });
  },

  getRiskEvents: (id: string, limit: number = 50) => {
    return apiFetch(`${API_BASE_URL}/api/portfolios/${id}/risk-events?limit=${limit}`, { cache: 'no-store' });
  }
};

export const tradeAPI = {
  executeTrade: (portfolioId: string, payload: { symbol: string, side: string, size: number, stop_loss?: number }) => {
    return apiFetch(`${API_BASE_URL}/api/trading/${portfolioId}/execute`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  }
};

export const auditAPI = {
  getLogs: (actionType?: string, limit: number = 100, offset: number = 0): Promise<PaginatedAuditLogs> => {
    const params = new URLSearchParams();
    if (actionType) params.append('action_type', actionType);
    params.append('limit', limit.toString());
    params.append('offset', offset.toString());

    return apiFetch(`${API_BASE_URL}/api/audit/?${params}`, { cache: 'no-store' });
  },

  getRiskRejections: (limit: number = 50) => {
    return apiFetch(`${API_BASE_URL}/api/audit/events/risk-rejections?limit=${limit}`, { cache: 'no-store' });
  },

  getKillSwitchEvents: (limit: number = 50) => {
    return apiFetch(`${API_BASE_URL}/api/audit/events/kill-switch?limit=${limit}`, { cache: 'no-store' });
  }
};

export const reportsAPI = {
  generateReport: (payload: { portfolio_id: string, report_type: string, start_date?: string, end_date?: string }) => {
    return apiFetch(`${API_BASE_URL}/api/reports/generate`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  getReports: (portfolioId: string, reportType?: string, limit: number = 10) => {
    const url = reportType
      ? `${API_BASE_URL}/api/reports/${portfolioId}?report_type=${reportType}&limit=${limit}`
      : `${API_BASE_URL}/api/reports/${portfolioId}?limit=${limit}`;
    return apiFetch(url, { cache: 'no-store' });
  }
};

export const strategiesAPI = {
  listStrategies: () => {
    return apiFetch(`${API_BASE_URL}/api/strategies`, { cache: 'no-store' });
  },

  getStrategy: (id: string) => {
    return apiFetch(`${API_BASE_URL}/api/strategies/${id}`, { cache: 'no-store' });
  },

  createStrategy: (payload: any) => {
    return apiFetch(`${API_BASE_URL}/api/strategies`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  updateStrategy: (id: string, payload: any) => {
    return apiFetch(`${API_BASE_URL}/api/strategies/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    });
  }
};

export interface AuthResponse {
  access_token: string;
  token_type: string;
}

export const authAPI = {
  login: async (formData: FormData): Promise<AuthResponse> => {
    const res = await fetch(`${API_BASE_URL}/api/auth/token`, {
      method: "POST",
      body: formData,
    });
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || "Login failed. Please check your credentials.");
    }
    return res.json();
  },

  register: async (payload: { email: string, password: string }): Promise<{ id: string, email: string }> => {
    const res = await fetch(`${API_BASE_URL}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const error = await res.json();
      throw new Error(error.detail || "Registration failed. The email might already be in use.");
    }
    return res.json();
  },
};