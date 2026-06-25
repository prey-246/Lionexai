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
    return apiFetch(`${API_BASE_URL}/api/portfolios/`, { cache: 'no-store' });
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
    return apiFetch(`${API_BASE_URL}/api/portfolios/`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  deletePortfolio: (id: string): Promise<void> => {
    return apiFetch(`${API_BASE_URL}/api/portfolios/${id}`, {
      method: 'DELETE',
    });
  },

  // Phase 4: autonomous allocation transparency
  getAllocations: (id: string): Promise<AllocationItem[]> => {
    return apiFetch(`${API_BASE_URL}/api/portfolios/${id}/allocations`, { cache: 'no-store' });
  },

  getRebalances: (id: string, limit: number = 20): Promise<RebalanceEventItem[]> => {
    return apiFetch(`${API_BASE_URL}/api/portfolios/${id}/rebalances?limit=${limit}`, { cache: 'no-store' });
  },

  getSettlements: (id: string, limit: number = 20): Promise<ClientSettlementItem[]> => {
    return apiFetch(`${API_BASE_URL}/api/portfolios/${id}/settlements?limit=${limit}`, { cache: 'no-store' });
  },
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

  downloadReport: (reportId: string, filename: string = "LionexAI_Report.pdf"): Promise<void> => {
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
      Cookies.set("auth_token", data.access_token, { expires: 1 });
      try {
        const profile = await authAPI.getMe();
        Cookies.set("user_role", profile.role_tier, { expires: 1 });
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
    return apiFetch(`${API_BASE_URL}/api/auth/me`);
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
  getSentimentPulse: (limit: number = 12): Promise<MarketSensitivityScore[]> => {
    return apiFetch(`${API_BASE_URL}/api/intelligence/sentiment?limit=${limit}`, { cache: 'no-store' });
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
  getPoolsSummary: (): Promise<{ total_nav: number; pools: Array<{ id: string; name: string; balance: number; target_allocation_pct: number }> }> => {
    return apiFetch(`${API_BASE_URL}/api/treasury/pools/summary`, { cache: 'no-store' });
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
  },
  getRouting: (limit: number = 50): Promise<any[]> => {
    return apiFetch(`${API_BASE_URL}/api/treasury/routing?limit=${limit}`, { cache: 'no-store' });
  },
  getPoolAnalytics: (): Promise<TreasuryPoolAnalytics[]> => {
    return apiFetch(`${API_BASE_URL}/api/treasury/pools/analytics`, { cache: 'no-store' });
  },
};

export interface TreasuryPoolAnalytics {
  pool_id: string;
  name: string;
  balance: number;
  target_allocation_pct: number;
  contributions: number;
  withdrawals: number;
  net_flow: number;
  transaction_count: number;
}

// --- Phase 4: Multi-Asset Autonomous Fund Manager ---

export interface AssetItem {
  pk_id: number;
  symbol: string;
  display_name: string;
  asset_class: string;
  data_provider: string;
  data_symbol: string;
  execution_venue: string;
  quote_currency: string;
  is_active: boolean;
  is_tradable: boolean;
}

export interface FundUniverseItem {
  symbol: string;
  display_name: string;
  asset_class: string;
  min_weight_pct: number;
  max_weight_pct: number;
}

export interface FundProduct {
  id: string;
  name: string;
  description?: string;
  mandate_id?: string;
  risk_label?: string;
  target_return_label?: string;
  target_weekly_return_pct?: number;
  target_monthly_return_pct?: number;
  actual_weekly_return_pct?: number | null;
  actual_monthly_return_pct?: number | null;
  actual_total_return_pct?: number | null;
  total_aum?: number | null;
  portfolio_count?: number | null;
  data_provenance?: string | null;
  allocation_policy?: Record<string, any>;
  is_active: boolean;
  asset_universe: FundUniverseItem[];
}

export interface AllocationItem {
  symbol: string;
  display_name?: string;
  asset_class?: string;
  target_weight_pct: number;
  current_weight_pct: number;
  updated_at?: string;
}

export interface RebalanceEventItem {
  id: string;
  portfolio_id: number;
  trigger?: string;
  regime?: string;
  global_risk_score?: number;
  decisions?: any;
  created_at: string;
}

export interface ClientSettlementItem {
  id: string;
  portfolio_id: number;
  iso_week_key: string;
  period_start: string;
  period_end: string;
  opening_equity: number;
  period_pnl: number;
  target_return_pct: number;
  client_entitlement: number;
  excess_routed: number;
  shortfall_topup: number;
  uncovered: number;
  status: string;
  breakdown?: Record<string, unknown>;
  created_at: string;
  starting_nav?: number;
  trading_pnl?: number;
  target_yield?: number;
  treasury_routed?: number;
  shortfall_topups?: number;
  lnx_contribution?: number;
}

export interface LNXIndexData {
  nav: number;
  treasury_health: number;
  strategy_performance: number;
  execution_quality: number;
  aum_growth: number;
  composite_index: number;
  computed_at: string;
  weekly_change_pct?: number | null;
  monthly_change_pct?: number | null;
  treasury_nav?: number;
  aum?: number;
  reserve_ratio?: number;
}

export interface GlobalMarketState {
  global_risk_score: number;
  market_regime: string;
  risk_on_off: string;
  asset_ranking?: Array<{ symbol: string; asset_class: string; score: number; momentum_3m: number; vol: number; rank: number }>;
  macro_inputs?: Record<string, any>;
  computed_at: string;
}

export interface MarketRegimeItem {
  scope: string;
  regime: string;
  confidence: number;
  indicators?: Record<string, any>;
  detected_at: string;
}

export const fundsAPI = {
  listFunds: (): Promise<FundProduct[]> => {
    return apiFetch(`${API_BASE_URL}/api/funds/`, { cache: 'no-store' });
  },
  getFund: (id: string): Promise<FundProduct> => {
    return apiFetch(`${API_BASE_URL}/api/funds/${id}`, { cache: 'no-store' });
  },
  invest: (fundId: string, amount: number, portfolioId?: string): Promise<Portfolio> => {
    return apiFetch(`${API_BASE_URL}/api/funds/${fundId}/invest`, {
      method: 'POST',
      body: JSON.stringify({ amount, portfolio_id: portfolioId }),
    });
  },
  getInstitutionalAnalytics: (fundId: string): Promise<Record<string, any>> => {
    return apiFetch(`${API_BASE_URL}/api/funds/${fundId}/institutional`, { cache: 'no-store' });
  },
};

export const validatedAPI = {
  runStrategy: (payload: {
    symbol: string;
    strategy_key: string;
    validation_type?: string;
    initial_capital?: number;
  }) => apiFetch(`${API_BASE_URL}/api/validated/strategy/run`, { method: 'POST', body: JSON.stringify(payload) }),
  listRuns: (strategyKey?: string) =>
    apiFetch(`${API_BASE_URL}/api/validated/strategy/runs${strategyKey ? `?strategy_key=${strategyKey}` : ''}`, { cache: 'no-store' }),
  alphaEvidence: (targetMonthlyPct = 20) =>
    apiFetch(`${API_BASE_URL}/api/validated/alpha/evidence`, {
      method: 'POST',
      body: JSON.stringify({ fund_id: 'ALPHA', target_monthly_pct: targetMonthlyPct }),
    }),
  getGlobalRisk: () => apiFetch(`${API_BASE_URL}/api/validated/global-risk`, { cache: 'no-store' }),
  getPaperSnapshots: (period?: string) =>
    apiFetch(`${API_BASE_URL}/api/validated/paper/snapshots${period ? `?period=${period}` : ''}`, { cache: 'no-store' }),
  getAllocationAlerts: () => apiFetch(`${API_BASE_URL}/api/validated/allocation/alerts`, { cache: 'no-store' }),
  runFundBacktest: (fundId: string, initialCapital = 1_000_000) =>
    apiFetch(`${API_BASE_URL}/api/validated/fund/run`, {
      method: 'POST',
      body: JSON.stringify({ fund_id: fundId, initial_capital: initialCapital, persist: true }),
    }),
  runAllFundBacktests: (initialCapital = 1_000_000) =>
    apiFetch(`${API_BASE_URL}/api/validated/fund/run-all`, {
      method: 'POST',
      body: JSON.stringify({ initial_capital: initialCapital, persist: true }),
    }),
  runOptimization: (payload?: { phase?: string; fund_id?: string; bar_limit?: number; regenerate?: boolean }) =>
    apiFetch(`${API_BASE_URL}/api/validated/optimization/run`, {
      method: 'POST',
      body: JSON.stringify({ phase: 'all', persist: true, regenerate: true, ...payload }),
    }),
  listOptimizationExperiments: (fundId?: string) =>
    apiFetch(`${API_BASE_URL}/api/validated/optimization/experiments${fundId ? `?fund_id=${fundId}` : ''}`, { cache: 'no-store' }),
  getLatestFundBacktest: (fundId: string, includeDemo = false) =>
    apiFetch(`${API_BASE_URL}/api/validated/fund/latest/${fundId}${includeDemo ? '?include_demo=true' : ''}`, { cache: 'no-store' }),
  listFundRuns: (fundId?: string) =>
    apiFetch(`${API_BASE_URL}/api/validated/fund/runs${fundId ? `?fund_id=${fundId}` : ''}`, { cache: 'no-store' }),
};

export const institutionalAPI = {
  getFundAnalyticsV2: (fundId: string) =>
    apiFetch(`${API_BASE_URL}/api/institutional/performance/fund/${fundId}`, { cache: 'no-store' }),
  getLiveValidation: (period?: string) =>
    apiFetch(`${API_BASE_URL}/api/institutional/live-validation/snapshots${period ? `?period=${period}` : ''}`, { cache: 'no-store' }),
  refreshLiveValidation: () =>
    apiFetch(`${API_BASE_URL}/api/institutional/live-validation/refresh`, { method: 'POST' }),
  verifyTreasury: (persist = false) =>
    apiFetch(`${API_BASE_URL}/api/institutional/treasury/verify?persist=${persist}`, { cache: 'no-store' }),
  getLnxAttribution: () =>
    apiFetch(`${API_BASE_URL}/api/institutional/lnx/attribution`, { cache: 'no-store' }),
  getLnxAttributionHistory: (limit = 30) =>
    apiFetch(`${API_BASE_URL}/api/institutional/lnx/attribution/history?limit=${limit}`, { cache: 'no-store' }),
  traceExecution: (tradeId: string) =>
    apiFetch(`${API_BASE_URL}/api/institutional/execution/trace/${tradeId}`, { cache: 'no-store' }),
  getMacroSnapshot: () =>
    apiFetch(`${API_BASE_URL}/api/institutional/macro/snapshot`, { cache: 'no-store' }),
  getAlphaEvidenceFull: (fundId = 'ALPHA', targetMonthlyPct = 20) =>
    apiFetch(`${API_BASE_URL}/api/institutional/alpha/evidence/full`, {
      method: 'POST',
      body: JSON.stringify({ fund_id: fundId, target_monthly_pct: targetMonthlyPct }),
    }),
  generateMonthlyReport: (fundId: string) =>
    apiFetch(`${API_BASE_URL}/api/institutional/reports/monthly-fund`, {
      method: 'POST',
      body: JSON.stringify({ fund_id: fundId }),
    }),
  listReports: (fundId?: string) =>
    apiFetch(`${API_BASE_URL}/api/institutional/reports/institutional${fundId ? `?fund_id=${fundId}` : ''}`, { cache: 'no-store' }),
  exportReportJson: (reportId: string) =>
    downloadBlob(`/api/institutional/reports/institutional/${reportId}/export/json`, `${reportId}.json`),
  exportReportCsv: (reportId: string) =>
    downloadBlob(`/api/institutional/reports/institutional/${reportId}/export/csv`, `${reportId}.csv`),
};

export const assetsAPI = {
  listAssets: (assetClass?: string): Promise<AssetItem[]> => {
    const url = assetClass
      ? `${API_BASE_URL}/api/assets/?asset_class=${encodeURIComponent(assetClass)}`
      : `${API_BASE_URL}/api/assets/`;
    return apiFetch(url, { cache: 'no-store' });
  },
};

export const marketAPI = {
  getGlobalState: (): Promise<GlobalMarketState | null> => {
    return apiFetch(`${API_BASE_URL}/api/market/global-state`, { cache: 'no-store' });
  },
  getRegime: (scope: string = 'GLOBAL', history: number = 1): Promise<MarketRegimeItem[]> => {
    return apiFetch(`${API_BASE_URL}/api/market/regime?scope=${encodeURIComponent(scope)}&history=${history}`, { cache: 'no-store' });
  },
  getAllRegimes: (): Promise<MarketRegimeItem[]> => {
    return apiFetch(`${API_BASE_URL}/api/market/regime/all`, { cache: 'no-store' });
  },
};

export const lnxAPI = {
  getIndex: (): Promise<LNXIndexData> => {
    return apiFetch(`${API_BASE_URL}/api/lnx/index`, { cache: 'no-store' });
  },
  getHistory: (limit: number = 90): Promise<LNXIndexData[]> => {
    return apiFetch(`${API_BASE_URL}/api/lnx/history?limit=${limit}`, { cache: 'no-store' });
  },
};

export const marketIntelligenceAPI = {
  getDashboard: (): Promise<any> => {
    return apiFetch(`${API_BASE_URL}/api/market-intelligence/dashboard`, { cache: 'no-store' });
  },
};