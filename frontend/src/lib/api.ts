// We will import js-cookie dynamically for client-side execution
import type { RiskMandate, EngineHealth, Portfolio, PortfolioSummary, PortfolioStats, Trade, RiskEvent, AuditLog, PaginatedAuditLogs, BacktestRequest, BacktestResponse, AuthResponse, TradeResponse, EquityDataPoint, MarketNewsArticle, MarketSensitivityScore, User, GlobalSettings } from './types';

/**
 * Differentiates between server-side and client-side API calls.
 * In server components, `window` is undefined, so we use the internal Docker network URL.
 * In client components, we use the publicly exposed URL.
 */
export const API_BASE_URL = typeof window === 'undefined'
  ? process.env.INTERNAL_API_URL || "http://backend:8000"
  : process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function buildAuthHeaders(options: RequestInit = {}): Promise<HeadersInit> {
  const headers: HeadersInit = { ...(options.headers ?? {}) };
  if (typeof window !== "undefined") {
    const Cookies = (await import("js-cookie")).default;
    const token = Cookies.get("auth_token");
    if (token) (headers as Record<string, string>)['Authorization'] = `Bearer ${token}`;
  } else {
    const { cookies } = await import("next/headers");
    const token = cookies().get("auth_token")?.value;
    if (token) (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  }
  if (options.body && typeof options.body === 'string' && !('Content-Type' in headers)) {
    (headers as Record<string, string>)['Content-Type'] = 'application/json';
  }
  return headers;
}

export const apiFetchRaw = async (url: string, options: RequestInit = {}): Promise<Response> => {
  const headers = await buildAuthHeaders(options);
  const res = await fetch(url, { ...options, headers });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(errorData.detail || "An API error occurred");
  }
  return res;
};

export const apiFetch = async (url: string, options: RequestInit = {}) => {
  const res = await apiFetchRaw(url, options);
  if (res.status === 204) return;
  return res.json();
};

export const apiJson = async <T>(url: string, options: RequestInit = {}): Promise<T> => {
  return apiFetch(url, options);
};

export const downloadBlob = async (path: string, filename: string, options: RequestInit = {}): Promise<void> => {
  const res = await apiFetchRaw(`${API_BASE_URL}${path}`, options);
  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
};

export const systemAPI = {
  getEnvironmentState: (): Promise<{ environment: 'BACKTEST' | 'PAPER' | 'DEMO' | 'LIVE_DISABLED'}> => {
    return apiFetch(`${API_BASE_URL}/api/system/environment`, { cache: 'no-store' });
  },

  getGlobalSettings: (): Promise<GlobalSettings> => {
    return apiFetch(`${API_BASE_URL}/api/system/settings`, { cache: 'no-store' });
  },

  updateGlobalSettings: (payload: Partial<GlobalSettings>): Promise<GlobalSettings> => {
    return apiFetch(`${API_BASE_URL}/api/system/settings`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  },

  getHealth: async (): Promise<EngineHealth> => {
    const res = await fetch(`${API_BASE_URL}/api/system/health`, { next: { revalidate: 0 } });
    if (!res.ok) throw new Error("Risk Engine Offline");
    return res.json();
  },

  getBackgroundTaskStatuses: (): Promise<any[]> => {
    return apiFetch(`${API_BASE_URL}/api/system/background-tasks`, { cache: 'no-store' });
  },

  getMandates: (): Promise<RiskMandate[]> => {
    return apiFetch(`${API_BASE_URL}/api/mandates/`, { cache: 'no-store' });
  },

  getMandate: (id: string): Promise<RiskMandate> => {
    return apiFetch(`${API_BASE_URL}/api/mandates/${id}`, { cache: 'no-store' });
  },

  getMandateHistory: (id: string): Promise<RiskMandate[]> => {
    return apiFetch(`${API_BASE_URL}/api/mandates/${id}/history`, { cache: 'no-store' });
  },

  updateMandate: (pkId: number, payload: Partial<RiskMandate>): Promise<RiskMandate> => {
    return apiFetch(`${API_BASE_URL}/api/mandates/${pkId}`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    });
  },

  activateMandate: (pkId: number): Promise<RiskMandate> => {
    return apiFetch(`${API_BASE_URL}/api/mandates/${pkId}/activate`, { method: 'POST' });
  },

  deactivateMandate: (pkId: number): Promise<RiskMandate> => {
    return apiFetch(`${API_BASE_URL}/api/mandates/${pkId}/deactivate`, { method: 'POST' });
  }
};

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

  getSummary: (): Promise<PortfolioSummary> => {
    return apiFetch(`${API_BASE_URL}/api/portfolios/summary`, { cache: 'no-store' });
  },

  getStats: (id: string): Promise<PortfolioStats> => {
    return apiFetch(`${API_BASE_URL}/api/portfolios/${id}/stats`, { cache: 'no-store' });
  },

  getTrades: (id: string, status?: string): Promise<Trade[]> => {
    const url = status ? `${API_BASE_URL}/api/portfolios/${id}/trades?status=${status}` : `${API_BASE_URL}/api/portfolios/${id}/trades`;
    return apiFetch(url, { cache: 'no-store' });
  },

  getEquityCurve: (id: string, limit: number = 100): Promise<EquityDataPoint[]> => {
    return apiFetch(`${API_BASE_URL}/api/portfolios/${id}/equity-curve?limit=${limit}`, { cache: 'no-store' });
  },

  getRiskEvents: (id: string, limit: number = 50): Promise<RiskEvent[]> => {
    return apiFetch(`${API_BASE_URL}/api/portfolios/${id}/risk-events?limit=${limit}`, { cache: 'no-store' });
  },

  createPortfolio: (payload: { id: string, mandate_pk_id: string, total_equity: number }): Promise<Portfolio> => {
    return apiFetch(`${API_BASE_URL}/api/portfolios`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  deletePortfolio: (id: string): Promise<void> => {
    return apiFetch(`${API_BASE_URL}/api/portfolios/${id}`, {
      method: 'DELETE',
    });
  }
};

export const tradeAPI = {
  executeTrade: (portfolioId: string, payload: { symbol: string, side: string, size: number, stop_loss?: number }): Promise<TradeResponse> => {
    return apiFetch(`${API_BASE_URL}/api/trading/${portfolioId}/execute`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },
  
  resetKillSwitch: (mandateId: string) => {
    return apiFetch(`${API_BASE_URL}/api/trading/mandates/${mandateId}/reset`, {
      method: "POST",
    });
  }
};

export const auditAPI = {
  getLogs: (
    actionType?: string,
    limit: number = 100,
    offset: number = 0,
    options?: { exchange?: string; start_date?: string; end_date?: string; search?: string },
  ): Promise<PaginatedAuditLogs> => {
    const params = new URLSearchParams();
    if (actionType) params.append('action_type', actionType);
    if (options?.exchange) params.append('exchange', options.exchange);
    if (options?.start_date) params.append('start_date', options.start_date);
    if (options?.end_date) params.append('end_date', options.end_date);
    if (options?.search) params.append('search', options.search);
    params.append('limit', limit.toString());
    params.append('skip', offset.toString());

    return apiFetch(`${API_BASE_URL}/api/audit/?${params}`, { cache: 'no-store' });
  },

  getRiskRejections: async (limit: number = 50): Promise<AuditLog[]> => {
    const res = await auditAPI.getLogs('RISK_REJECTION', limit);
    return res.logs;
  },

  getKillSwitchEvents: async (limit: number = 50): Promise<AuditLog[]> => {
    const res = await auditAPI.getLogs('KILL_SWITCH_TRIGGERED', limit);
    return res.logs;
  }
};

export const reportsAPI = {
  generateReport: (payload: { portfolio_id: string, report_type: string, start_date?: string, end_date?: string }): Promise<any> => {
    return apiJson(`${API_BASE_URL}/api/reports/generate`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  getReports: (portfolioId: string, reportType?: string, limit: number = 10): Promise<any> => {
    const url = reportType
      ? `${API_BASE_URL}/api/reports/${portfolioId}?report_type=${reportType}&limit=${limit}`
      : `${API_BASE_URL}/api/reports/${portfolioId}`;
    return apiFetch(url, { cache: 'no-store' });
  },

  downloadReport: (reportId: string, filename: string = "NEXA_Report.pdf"): Promise<void> => {
    return downloadBlob(`/api/reports/${reportId}/download`, filename);
  }
};

export const strategiesAPI = {
  listStrategies: (): Promise<any[]> => {
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

export const authAPI = {
  login: async (formData: FormData): Promise<AuthResponse> => {
    const data: AuthResponse = await apiFetch(`${API_BASE_URL}/api/auth/token`, {
      method: "POST",
      body: formData,
    });
    
    // Automatically set tokens and fetch role so the middleware knows who we are
    if (typeof window !== "undefined") {
      const Cookies = (await import("js-cookie")).default;
      Cookies.set("auth_token", data.access_token);
      try {
        const profile = await authAPI.getMe();
        Cookies.set("user_role", profile.role_tier);
      } catch (e) {
        console.error("Could not fetch user role during login", e);
      }
    }
    
    return data;
  },

  register: async (payload: { email: string, password: string }): Promise<{ id: string, email: string }> => {
    return apiJson(`${API_BASE_URL}/api/auth/register`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  getMe: async (): Promise<{ id: string, email: string, role_tier: 'client' | 'operator' | 'risk_manager' | 'admin' }> => {
    return apiFetch(`${API_BASE_URL}/api/users/me`);
  },

  logout: async (): Promise<void> => {
    // Call the backend logout endpoint to create an audit log.
    // We wrap this in a try/catch so that the client-side logout proceeds even if the API call fails.
    try {
      await apiFetch(`${API_BASE_URL}/api/auth/logout`, { method: 'POST' });
    } catch (error) {
      console.error("Logout API call failed, proceeding with client-side logout:", error);
    }
    // Dynamically import js-cookie only on the client side
    const Cookies = (await import("js-cookie")).default;
    Cookies.remove('auth_token');
    Cookies.remove('user_role');
    window.location.href = '/login';
  }
};

export const intelligenceAPI = {
  getNews: (limit: number = 5): Promise<MarketNewsArticle[]> => {
    return apiFetch(`${API_BASE_URL}/api/intelligence/news?limit=${limit}`, { cache: 'no-store' });
  },
  getSentiment: (symbol: string): Promise<MarketSensitivityScore> => {
    return apiFetch(`${API_BASE_URL}/api/intelligence/sentiment/${encodeURIComponent(symbol)}`, { cache: 'no-store' });
  },
  getEconomicEvents: (limit: number = 10): Promise<any[]> => {
    return apiFetch(`${API_BASE_URL}/api/intelligence/events?limit=${limit}`, { cache: 'no-store' });
  }
};

export const exchangeAPI = {
  getStatus: (exchangeId: string): Promise<any> => {
    return apiFetch(`${API_BASE_URL}/api/exchange/${exchangeId}/status`, { cache: 'no-store' });
  },
  getHeartbeat: (exchangeId: string): Promise<any> => {
    return apiFetch(`${API_BASE_URL}/api/exchange/${exchangeId}/heartbeat`, { cache: 'no-store' });
  },
  cancelOrder: (exchangeId: string, orderId: string, symbol: string): Promise<any> => {
    return apiFetch(`${API_BASE_URL}/api/exchange/${exchangeId}/orders/${orderId}`, {
      method: 'DELETE',
      body: JSON.stringify({ symbol }), // CCXT cancel_order often requires the symbol
    });
  }
};

export const executionHealthAPI = {
  getStats: (): Promise<any> => {
    return apiFetch(`${API_BASE_URL}/api/execution/health-stats`, { cache: 'no-store' });
  },
};

export const stressTestAPI = {
  runScenario: (scenarioId: string): Promise<any> => {
    return apiFetch(`${API_BASE_URL}/api/stress-test/${scenarioId}/run`, { method: 'POST' });
  },
};

export const usersAPI = {
  listUsers: (): Promise<User[]> => {
    return apiFetch(`${API_BASE_URL}/api/users`, { cache: 'no-store' });
  },
  updateRole: (userId: string, role_tier: string): Promise<User> => {
    return apiFetch(`${API_BASE_URL}/api/users/${userId}/role`, {
      method: 'PUT',
      body: JSON.stringify({ role_tier }),
    });
  }
};

export const treasuryAPI = {
  getPools: (): Promise<any[]> => {
    return apiFetch(`${API_BASE_URL}/api/treasury/pools`, { cache: 'no-store' });
  },
  getTransactions: (limit: number = 50): Promise<any[]> => {
    return apiFetch(`${API_BASE_URL}/api/treasury/transactions?limit=${limit}`, { cache: 'no-store' });
  },
  seedTreasury: (): Promise<any[]> => {
    return apiFetch(`${API_BASE_URL}/api/treasury/seed`, { method: 'POST' });
  },
  transferFunds: (payload: { source_pool_id: string, target_pool_id: string, amount: number, description: string }): Promise<any> => {
    return apiFetch(`${API_BASE_URL}/api/treasury/transfer`, {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  },
  sweepYield: (): Promise<any> => {
    return apiFetch(`${API_BASE_URL}/api/treasury/sweep`, { method: 'POST' });
  }
};