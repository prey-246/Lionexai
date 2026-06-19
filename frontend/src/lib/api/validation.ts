import { apiJson, downloadBlob, API_BASE_URL } from '../api';
import type {
  ValidationSnapshot,
  ValidationSummary,
  ValidationHistoryRecord,
  MetricTimeseries,
  ValidationMetric,
} from '../types/validation';

export const validationAPI = {
  getSnapshots(period: string, snapshotType?: string, scopeId?: string): Promise<ValidationSnapshot[]> {
    const params = new URLSearchParams({ period });
    if (snapshotType) params.set('snapshot_type', snapshotType);
    if (scopeId) params.set('scope_id', scopeId);
    return apiJson(`${API_BASE_URL}/api/validation/snapshots?${params.toString()}`);
  },

  getSnapshotForRange(
    startDate: string,
    endDate: string,
    options?: { portfolioId?: string; strategy?: string },
  ): Promise<ValidationSnapshot> {
    const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
    if (options?.portfolioId) params.set('portfolio_id', options.portfolioId);
    if (options?.strategy) params.set('strategy', options.strategy);
    return apiJson(`${API_BASE_URL}/api/validation/snapshots/range?${params.toString()}`);
  },

  getHistory(options?: {
    snapshotKey?: string;
    snapshotType?: string;
    scopeId?: string;
    period?: string;
    startDate?: string;
    endDate?: string;
    limit?: number;
  }): Promise<ValidationHistoryRecord[]> {
    const params = new URLSearchParams();
    if (options?.snapshotKey) params.set('snapshot_key', options.snapshotKey);
    if (options?.snapshotType) params.set('snapshot_type', options.snapshotType);
    if (options?.scopeId) params.set('scope_id', options.scopeId);
    if (options?.period) params.set('period', options.period);
    if (options?.startDate) params.set('start_date', options.startDate);
    if (options?.endDate) params.set('end_date', options.endDate);
    if (options?.limit) params.set('limit', String(options.limit));
    return apiJson(`${API_BASE_URL}/api/validation/history?${params.toString()}`);
  },

  getMetricTimeseries(
    snapshotKey: string,
    metric: ValidationMetric = 'win_rate_pct',
    startDate?: string,
    endDate?: string,
  ): Promise<MetricTimeseries> {
    const params = new URLSearchParams({ snapshot_key: snapshotKey, metric });
    if (startDate) params.set('start_date', startDate);
    if (endDate) params.set('end_date', endDate);
    return apiJson(`${API_BASE_URL}/api/validation/history/metrics?${params.toString()}`);
  },

  getSummary(): Promise<ValidationSummary> {
    return apiJson(`${API_BASE_URL}/api/validation/summary`);
  },

  refreshSnapshots(): Promise<{ status: string; message: string }> {
    return apiJson(`${API_BASE_URL}/api/validation/snapshots/refresh`, { method: 'POST' });
  },

  downloadReport(period: string = '30D'): Promise<void> {
    const params = new URLSearchParams({ period });
    return downloadBlob(`/api/validation/report/pdf?${params.toString()}`, `nexa_${period.toLowerCase()}_validation_report.pdf`);
  },

  downloadWeeklyReport(): Promise<void> {
    return downloadBlob('/api/validation/report/pdf/weekly', 'nexa_weekly_validation_report.pdf');
  },

  downloadMonthlyReport(): Promise<void> {
    return downloadBlob('/api/validation/report/pdf/monthly', 'nexa_monthly_validation_report.pdf');
  },

  downloadSimulationReport(params: any): Promise<void> {
    return downloadBlob('/api/validation/reports/generate-simulation', 'growth_simulation_report.pdf', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },
};
