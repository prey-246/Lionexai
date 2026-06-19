'use client';

import { useState, useEffect, useMemo } from 'react';
import { validationAPI } from '@/lib/api/validation';
import type { ValidationSnapshot, ValidationSummary, ValidationPeriod, MetricTimeseries } from '@/lib/types/validation';
import { PageHeader } from '@/components/ui/PageHeader';
import { MetricDisplay } from '@/components/ui/MetricDisplay';
import {
  Loader2, AlertTriangle, BarChart, TrendingUp, TrendingDown, Zap, Clock, Target,
  Download, CheckCircle, XCircle, Activity, Layers, ArrowUpRight, ArrowDownRight,
} from 'lucide-react';
import { formatCurrency, formatFixed, toFiniteNumber } from '@/lib/format';
import { HistogramChart } from '@/components/charts/HistogramChart';
import { SimpleTimeSeriesChart } from '@/components/charts/SimpleTimeSeriesChart';

const PERIOD_LABELS: Record<ValidationPeriod, string> = {
  TODAY: 'Today',
  '7D': 'Last 7 Days',
  '14D': 'Last 14 Days',
  '30D': 'Last 30 Days',
  ALL: 'All Time',
};

export default function LongTermValidationPage() {
  const [snapshot, setSnapshot] = useState<ValidationSnapshot | null>(null);
  const [summary, setSummary] = useState<ValidationSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [downloading, setDownloading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedPeriod, setSelectedPeriod] = useState<ValidationPeriod>('30D');
  const [historicalWinRate, setHistoricalWinRate] = useState<MetricTimeseries | null>(null);
  const [historicalDrawdown, setHistoricalDrawdown] = useState<MetricTimeseries | null>(null);

  const historySnapshotKey = useMemo(() => `GLOBAL_${selectedPeriod}`, [selectedPeriod]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setError(null);
        const [snapshots, summaryData] = await Promise.all([
          validationAPI.getSnapshots(selectedPeriod),
          validationAPI.getSummary(),
        ]);
        setSummary(summaryData);

        let globalSnapshot = snapshots.find(s => s.snapshot_type === 'GLOBAL');
        if (!globalSnapshot) {
          await validationAPI.refreshSnapshots();
          const refreshed = await validationAPI.getSnapshots(selectedPeriod);
          globalSnapshot = refreshed.find(s => s.snapshot_type === 'GLOBAL');
        }
        if (globalSnapshot) {
          setSnapshot(globalSnapshot);
        } else {
          setError(`No GLOBAL snapshot found for period: ${selectedPeriod}. Run paper trading to build history.`);
          setSnapshot(null);
        }
      } catch (err: unknown) {
        const message = err instanceof Error ? err.message : 'Failed to fetch validation data.';
        setError(message);
        setSnapshot(null);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [selectedPeriod]);

  useEffect(() => {
    const fetchHistoricalMetrics = async () => {
      try {
        const [winRate, drawdown] = await Promise.all([
          validationAPI.getMetricTimeseries(historySnapshotKey, 'win_rate_pct'),
          validationAPI.getMetricTimeseries(historySnapshotKey, 'max_drawdown_pct'),
        ]);
        setHistoricalWinRate(winRate.series.length >= 2 ? winRate : null);
        setHistoricalDrawdown(drawdown.series.length >= 2 ? drawdown : null);
      } catch {
        setHistoricalWinRate(null);
        setHistoricalDrawdown(null);
      }
    };
    fetchHistoricalMetrics();
  }, [historySnapshotKey]);

  const handleDownloadPdf = async (period: string = selectedPeriod) => {
    try {
      setDownloading(true);
      await validationAPI.downloadReport(period);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'PDF download failed.';
      setError(message);
    } finally {
      setDownloading(false);
    }
  };

  const renderPeriodLabel = () => PERIOD_LABELS[selectedPeriod];

  const renderCoreMetrics = () => {
    if (loading) {
      return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary-gold" /></div>;
    }
    if (error || !snapshot) {
      return (
        <div className="flex flex-col items-center justify-center h-64 text-danger bg-background-panel-1 border border-border-secondary rounded-lg p-4">
          <AlertTriangle className="w-12 h-12 mb-4" />
          <h2 className="text-xl font-semibold">Failed to load validation data</h2>
          <p className="text-sm text-center">{error || 'Could not fetch snapshot details.'}</p>
        </div>
      );
    }
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
        <MetricDisplay label="Total P&L" value={formatCurrency(snapshot.total_pnl)} trend={toFiniteNumber(snapshot.total_pnl) >= 0 ? 'up' : 'down'} icon={BarChart} />
        <MetricDisplay label="Win Rate" value={`${formatFixed(snapshot.win_rate_pct, 1)}%`} icon={TrendingUp} />
        <MetricDisplay label="Profit Factor" value={formatFixed(snapshot.profit_factor, 2)} icon={TrendingUp} />
        <MetricDisplay label="Sharpe Ratio" value={formatFixed(snapshot.sharpe_ratio, 2)} icon={TrendingUp} />
        <MetricDisplay label="Avg Return" value={`${formatFixed(snapshot.avg_return_pct, 2)}%`} icon={TrendingUp} />
        <MetricDisplay label="Max Drawdown" value={`${formatFixed(snapshot.max_drawdown_pct, 1)}%`} icon={TrendingDown} />
        <MetricDisplay label="Total Trades" value={String(toFiniteNumber(snapshot.total_trades))} icon={Zap} />
        <MetricDisplay label="Avg Latency" value={`${formatFixed(snapshot.avg_latency_ms, 0)} ms`} icon={Clock} />
        <MetricDisplay label="Fill Rate" value={`${formatFixed(snapshot.fill_rate_pct, 1)}%`} icon={Target} />
        <MetricDisplay label="Winning Trades" value={String(snapshot.winning_trades)} icon={CheckCircle} />
        <MetricDisplay label="Losing Trades" value={String(snapshot.losing_trades)} icon={XCircle} />
        <MetricDisplay label="Largest Win" value={formatCurrency(snapshot.largest_win)} trend="up" icon={ArrowUpRight} />
        <MetricDisplay label="Largest Loss" value={formatCurrency(snapshot.largest_loss)} trend="down" icon={ArrowDownRight} />
      </div>
    );
  };

  const renderOrderAndRankingMetrics = () => {
    if (loading || !snapshot) return null;
    const exchange = snapshot.exchange_distribution;

    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mt-4">
        <div className="bg-background-panel-1 border border-border-secondary rounded-lg p-4">
          <h3 className="text-sm font-semibold text-text-secondary mb-3 flex items-center gap-2">
            <Activity className="w-4 h-4" /> Order Flow
          </h3>
          <div className="grid grid-cols-3 gap-2 text-center">
            <div>
              <p className="text-xs text-text-secondary">Total</p>
              <p className="text-lg font-bold text-text-primary">{snapshot.total_orders}</p>
            </div>
            <div>
              <p className="text-xs text-text-secondary">Filled</p>
              <p className="text-lg font-bold text-success">{snapshot.filled_orders}</p>
            </div>
            <div>
              <p className="text-xs text-text-secondary">Rejected</p>
              <p className="text-lg font-bold text-danger">{snapshot.rejected_orders}</p>
            </div>
          </div>
        </div>

        <div className="bg-background-panel-1 border border-border-secondary rounded-lg p-4">
          <h3 className="text-sm font-semibold text-text-secondary mb-3 flex items-center gap-2">
            <Layers className="w-4 h-4" /> Best / Worst
          </h3>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between">
              <dt className="text-text-secondary">Best Portfolio</dt>
              <dd className="font-medium text-success">{snapshot.best_portfolio ?? '—'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-text-secondary">Worst Portfolio</dt>
              <dd className="font-medium text-danger">{snapshot.worst_portfolio ?? '—'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-text-secondary">Best Strategy</dt>
              <dd className="font-medium text-success">{snapshot.best_strategy ?? '—'}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-text-secondary">Worst Strategy</dt>
              <dd className="font-medium text-danger">{snapshot.worst_strategy ?? '—'}</dd>
            </div>
          </dl>
        </div>

        <div className="bg-background-panel-1 border border-border-secondary rounded-lg p-4">
          <h3 className="text-sm font-semibold text-text-secondary mb-3">Exchange Distribution</h3>
          {exchange ? (
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span>Binance</span>
                  <span>{exchange.binance_pct}% ({exchange.binance})</span>
                </div>
                <div className="h-2 bg-background-panel-2 rounded-full overflow-hidden">
                  <div className="h-full bg-primary-gold" style={{ width: `${exchange.binance_pct}%` }} />
                </div>
              </div>
              <div>
                <div className="flex justify-between text-sm mb-1">
                  <span>Bybit</span>
                  <span>{exchange.bybit_pct}% ({exchange.bybit})</span>
                </div>
                <div className="h-2 bg-background-panel-2 rounded-full overflow-hidden">
                  <div className="h-full bg-blue-500" style={{ width: `${exchange.bybit_pct}%` }} />
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-text-secondary">No exchange data yet.</p>
          )}
        </div>
      </div>
    );
  };

  const renderLegacySummary = () => {
    if (!summary) return null;

    return (
      <div className="bg-background-panel-1 border border-border-secondary rounded-lg p-4 mt-8">
        <h3 className="text-md font-semibold text-text-primary mb-4">3-Day Execution Summary</h3>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-text-secondary border-b border-border-secondary">
                <th className="text-left py-2 pr-4">Day</th>
                <th className="text-right py-2 px-4">Trades Executed</th>
                <th className="text-right py-2 px-4">Success Rate</th>
                <th className="text-right py-2 pl-4">Risk Rejections</th>
              </tr>
            </thead>
            <tbody>
              {summary.daily_stats.map(stat => (
                <tr key={stat.day} className="border-b border-border-secondary/50">
                  <td className="py-2 pr-4">{stat.day}</td>
                  <td className="text-right py-2 px-4">{stat.trades_executed}</td>
                  <td className="text-right py-2 px-4">{formatFixed(stat.success_rate, 1)}%</td>
                  <td className="text-right py-2 pl-4">{stat.risk_rejections}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mt-4 pt-4 border-t border-border-secondary text-sm">
          <div>
            <p className="text-text-secondary">Total Orders (3D)</p>
            <p className="font-semibold">{summary.aggregated.total_orders}</p>
          </div>
          <div>
            <p className="text-text-secondary">Filled</p>
            <p className="font-semibold text-success">{summary.aggregated.filled_orders}</p>
          </div>
          <div>
            <p className="text-text-secondary">Rejected</p>
            <p className="font-semibold text-danger">{summary.aggregated.rejected_orders}</p>
          </div>
          <div>
            <p className="text-text-secondary">Avg Latency</p>
            <p className="font-semibold">{formatFixed(summary.aggregated.average_latency, 0)} ms</p>
          </div>
          <div>
            <p className="text-text-secondary">Best / Worst PF</p>
            <p className="font-semibold">{summary.aggregated.best_portfolio ?? '—'} / {summary.aggregated.worst_portfolio ?? '—'}</p>
          </div>
        </div>
      </div>
    );
  };

  const renderCharts = () => {
    if (loading || error || !snapshot?.chart_data) return null;

    const {
      cumulative_pnl, equity_curve, daily_pnl, weekly_pnl, monthly_pnl,
      drawdown_series, rolling_drawdown, daily_trades, daily_returns, rolling_win_rate,
    } = snapshot.chart_data;
    const pnlSeries = cumulative_pnl?.length ? cumulative_pnl : equity_curve;
    const periodLabel = renderPeriodLabel();

    return (
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mt-8">
        {pnlSeries && pnlSeries.length >= 2 ? (
          <div className="bg-background-panel-1 border border-border-secondary rounded-lg p-4">
            <h3 className="text-md font-semibold text-text-primary mb-2">Cumulative P&L ({periodLabel})</h3>
            <SimpleTimeSeriesChart data={pnlSeries} />
          </div>
        ) : null}
        {daily_pnl && daily_pnl.length >= 1 ? (
          <div className="bg-background-panel-1 border border-border-secondary rounded-lg p-4">
            <h3 className="text-md font-semibold text-text-primary mb-2">Daily P&L</h3>
            <HistogramChart data={daily_pnl} />
          </div>
        ) : null}
        {daily_trades && daily_trades.length >= 1 ? (
          <div className="bg-background-panel-1 border border-border-secondary rounded-lg p-4">
            <h3 className="text-md font-semibold text-text-primary mb-2">Daily Trades</h3>
            <HistogramChart data={daily_trades} />
          </div>
        ) : null}
        {daily_returns && daily_returns.length >= 2 ? (
          <div className="bg-background-panel-1 border border-border-secondary rounded-lg p-4">
            <h3 className="text-md font-semibold text-text-primary mb-2">Daily Returns (%)</h3>
            <SimpleTimeSeriesChart data={daily_returns} />
          </div>
        ) : null}
        {rolling_win_rate && rolling_win_rate.length >= 2 ? (
          <div className="bg-background-panel-1 border border-border-secondary rounded-lg p-4">
            <h3 className="text-md font-semibold text-text-primary mb-2">Rolling Win Rate (7D)</h3>
            <SimpleTimeSeriesChart data={rolling_win_rate} lineColor="#22c55e" />
          </div>
        ) : null}
        {weekly_pnl && weekly_pnl.length >= 1 ? (
          <div className="bg-background-panel-1 border border-border-secondary rounded-lg p-4">
            <h3 className="text-md font-semibold text-text-primary mb-2">Weekly P&L</h3>
            <HistogramChart data={weekly_pnl} />
          </div>
        ) : null}
        {monthly_pnl && monthly_pnl.length >= 1 ? (
          <div className="bg-background-panel-1 border border-border-secondary rounded-lg p-4">
            <h3 className="text-md font-semibold text-text-primary mb-2">Monthly P&L</h3>
            <HistogramChart data={monthly_pnl} />
          </div>
        ) : null}
        {drawdown_series && drawdown_series.length >= 2 ? (
          <div className="bg-background-panel-1 border border-border-secondary rounded-lg p-4">
            <h3 className="text-md font-semibold text-text-primary mb-2">Drawdown (%)</h3>
            <SimpleTimeSeriesChart data={drawdown_series} lineColor="#ef4444" />
          </div>
        ) : null}
        {rolling_drawdown && rolling_drawdown.length >= 2 ? (
          <div className="bg-background-panel-1 border border-border-secondary rounded-lg p-4">
            <h3 className="text-md font-semibold text-text-primary mb-2">Rolling Drawdown (7D)</h3>
            <SimpleTimeSeriesChart data={rolling_drawdown} lineColor="#f97316" />
          </div>
        ) : null}
        {historicalWinRate && historicalWinRate.series.length >= 2 ? (
          <div className="bg-background-panel-1 border border-border-secondary rounded-lg p-4">
            <h3 className="text-md font-semibold text-text-primary mb-2">Historical Win Rate (Daily Archive)</h3>
            <SimpleTimeSeriesChart
              data={historicalWinRate.series.map(p => ({ time: p.time, value: p.value ?? 0 }))}
              lineColor="#22c55e"
            />
          </div>
        ) : null}
        {historicalDrawdown && historicalDrawdown.series.length >= 2 ? (
          <div className="bg-background-panel-1 border border-border-secondary rounded-lg p-4">
            <h3 className="text-md font-semibold text-text-primary mb-2">Historical Max Drawdown (Daily Archive)</h3>
            <SimpleTimeSeriesChart
              data={historicalDrawdown.series.map(p => ({ time: p.time, value: p.value ?? 0 }))}
              lineColor="#ef4444"
            />
          </div>
        ) : null}
      </div>
    );
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <PageHeader
          title="Long-Term Validation"
          subtitle="Continuous performance monitoring of the live paper trading environment."
        />
        <div className="flex flex-wrap gap-2 shrink-0">
          <button
            onClick={() => handleDownloadPdf(selectedPeriod)}
            disabled={downloading || loading}
            className="flex items-center gap-2 px-4 py-2 text-sm font-semibold rounded-md bg-primary-gold text-background-dark hover:opacity-90 disabled:opacity-50 transition-opacity"
          >
            {downloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            PDF ({PERIOD_LABELS[selectedPeriod]})
          </button>
          <button
            onClick={() => handleDownloadPdf('7D')}
            disabled={downloading || loading}
            className="flex items-center gap-2 px-3 py-2 text-sm font-semibold rounded-md bg-background-panel-2 text-text-secondary border border-border-secondary hover:bg-border-secondary disabled:opacity-50 transition-colors"
          >
            Weekly PDF
          </button>
          <button
            onClick={() => handleDownloadPdf('30D')}
            disabled={downloading || loading}
            className="flex items-center gap-2 px-3 py-2 text-sm font-semibold rounded-md bg-background-panel-2 text-text-secondary border border-border-secondary hover:bg-border-secondary disabled:opacity-50 transition-colors"
          >
            Monthly PDF
          </button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {(['TODAY', '7D', '14D', '30D', 'ALL'] as ValidationPeriod[]).map(period => (
          <button
            key={period}
            onClick={() => setSelectedPeriod(period)}
            className={`px-4 py-2 text-sm font-semibold rounded-md transition-colors ${
              selectedPeriod === period
                ? 'bg-primary-gold text-background-dark'
                : 'bg-background-panel-2 text-text-secondary hover:bg-border-secondary'
            }`}
          >
            {PERIOD_LABELS[period]}
          </button>
        ))}
      </div>

      {renderCoreMetrics()}
      {renderOrderAndRankingMetrics()}
      {renderCharts()}
      {renderLegacySummary()}
    </div>
  );
}
