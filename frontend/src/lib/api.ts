// We will import js-cookie dynamically for client-side execution
import type { RiskMandate, EngineHealth, Portfolio, PortfolioSummary, PortfolioStats, Trade, RiskEvent, AuditLog, PaginatedAuditLogs, BacktestRequest, BacktestResponse, AuthResponse, TradeResponse, EquityDataPoint } from './types';

/**
 * Differentiates between server-side and client-side API calls.
 * In server components, `window` is undefined, so we use the internal Docker network URL.
 * In client components, we use the publicly exposed URL.
 */
const API_BASE_URL = typeof window === 'undefined'
  ? process.env.INTERNAL_API_URL || "http://backend:8000" // For SSR, connects to backend service name
  : process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"; // For CSR, connects to exposed port

// A wrapper for fetch that includes the auth token and handles errors
const apiFetch = async (url: string, options: RequestInit = {}) => {
  const headers: HeadersInit = { ...options.headers };

  // On the client-side, we can access cookies to get the auth token
  if (typeof window !== "undefined") {
    // Dynamically import js-cookie only on the client side
    const Cookies = (await import("js-cookie")).default;
    const token = Cookies.get("auth_token");
    if (token) {
      (headers as { [key: string]: string })['Authorization'] = `Bearer ${token}`;
    }
  } else {
    // On the server-side, we use `next/headers` to get the cookie
    const { cookies } = await import("next/headers");
    const token = cookies().get("auth_token")?.value;
    if (token) {
      (headers as { [key: string]: string })["Authorization"] = `Bearer ${token}`;
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

export const systemAPI = {
  getEnvironmentState: (): Promise<{ environment: 'BACKTEST' | 'PAPER' | 'DEMO' | 'LIVE_DISABLED'}> => {
    return apiFetch(`${API_BASE_URL}/api/system/environment`, { cache: 'no-store' });
  },

  getHealth: async (): Promise<EngineHealth> => {
    const res = await fetch(`${API_BASE_URL}/api/system/health`, { next: { revalidate: 0 } });
    if (!res.ok) throw new Error("Risk Engine Offline");
    return res.json();
  },

  getMandates: (): Promise<RiskMandate[]> => {
    return apiFetch(`${API_BASE_URL}/api/mandates/`, { cache: 'no-store' });
  },

  getMandate: (id: string): Promise<RiskMandate> => {
    return apiFetch(`${API_BASE_URL}/api/mandates/${id}`, { cache: 'no-store' });
  }
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
  getLogs: (actionType?: string, limit: number = 100, offset: number = 0): Promise<PaginatedAuditLogs> => {
    const params = new URLSearchParams();
    if (actionType) params.append('action_type', actionType);
    params.append('limit', limit.toString());
    params.append('offset', offset.toString());

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
  generateReport: (payload: { portfolio_id: string, report_type: string, start_date?: string, end_date?: string }) => {
    return apiFetch(`${API_BASE_URL}/api/reports/generate`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
  },

  getReports: (portfolioId: string, reportType?: string, limit: number = 10) => {
    const url = reportType
      ? `${API_BASE_URL}/api/reports/${portfolioId}?report_type=${reportType}&limit=${limit}`
      : `${API_BASE_URL}/api/reports/${portfolioId}`;
    return apiFetch(url, { cache: 'no-store' });
  },

  downloadReport: async (reportId: string, filename: string = "NEXA_Report.pdf") => {
    const headers: HeadersInit = {};
    if (typeof window !== "undefined") {
      const Cookies = (await import("js-cookie")).default;
      const token = Cookies.get("auth_token");
      if (token) headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch(`${API_BASE_URL}/api/reports/${reportId}/download`, { headers });

    if (!res.ok) {
      const error = await res.json().catch(() => ({ detail: "Failed to download report" }));
      throw new Error(error.detail || "Failed to download report");
    }

    // Convert response to a blob and trigger a simulated browser download
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
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
    window.location.href = '/login';
  }
};