'use client';

import { useState, useEffect } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { MetricDisplay } from '@/components/ui/MetricDisplay';
import { Loader2, AlertTriangle, Download, CheckCircle2, Calendar, BarChart3 } from 'lucide-react';
import { validationAPI } from '@/lib/api';

export default function ValidationPage() {
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    validationAPI.getSummary()
      .then(setSummary)
      .catch((err: any) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      await validationAPI.downloadReport();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setDownloading(false);
    }
  };

  if (loading) {
    return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary-gold" /></div>;
  }

  if (error && !summary) {
    return (
      <div className="card red text-center p-8">
        <AlertTriangle className="w-12 h-12 text-danger mx-auto mb-4" />
        <p className="text-text-secondary">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-8 pb-10">
      <PageHeader
        title="Three-Day Validation Framework"
        subtitle="Continuous platform performance tracking across order execution, risk controls, and exchange uptime."
      />

      <div className="flex justify-end">
        <button
          onClick={handleDownload}
          disabled={downloading}
          className="flex items-center gap-2 px-4 py-2 bg-primary-gold/10 border border-primary-gold text-primary-gold rounded-[3px] text-[13px] hover:bg-primary-gold/20 disabled:opacity-50"
        >
          {downloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
          Download Validation Report (PDF)
        </button>
      </div>

      <section>
        <h3 className="font-mono text-[10px] uppercase tracking-wider text-text-muted mb-3">Daily Performance</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {(summary?.days || []).map((day: any) => (
            <div key={day.day} className="card grey p-5 space-y-3">
              <div className="flex items-center gap-2">
                <Calendar className="w-4 h-4 text-primary-gold" />
                <h4 className="font-serif text-[16px]">Day {day.day}</h4>
                <span className="text-[11px] text-text-muted ml-auto">{day.label}</span>
              </div>
              <MetricDisplay label="Trades Executed" value={day.trades_executed} icon={BarChart3} />
              <MetricDisplay label="Success Rate" value={`${day.success_rate_pct}%`} icon={CheckCircle2} />
              <MetricDisplay label="Risk Rejections" value={day.risk_rejections} icon={AlertTriangle} />
            </div>
          ))}
        </div>
      </section>

      <section>
        <h3 className="font-mono text-[10px] uppercase tracking-wider text-text-muted mb-3">Aggregated Results (3 Days)</h3>
        <div className="g4">
          <MetricDisplay label="Total Orders" value={summary?.total_orders ?? 0} icon={BarChart3} />
          <MetricDisplay label="Filled Orders" value={summary?.filled_orders ?? 0} icon={CheckCircle2} trend="up" />
          <MetricDisplay label="Rejected Orders" value={summary?.rejected_orders ?? 0} icon={AlertTriangle} />
          <MetricDisplay label="Average Latency" value={`${summary?.average_latency_ms ?? 0} ms`} icon={Calendar} />
        </div>
        <div className="g4 mt-4">
          <MetricDisplay label="Best Portfolio" value={summary?.best_portfolio || 'N/A'} icon={CheckCircle2} />
          <MetricDisplay label="Worst Portfolio" value={summary?.worst_portfolio || 'N/A'} icon={AlertTriangle} />
          <MetricDisplay label="Exchange Uptime" value={`${summary?.exchange_uptime_pct ?? 100}%`} icon={CheckCircle2} />
        </div>
      </section>

      <div className="flex items-start gap-3 bg-primary-blue/5 border border-primary-blue/20 p-4 rounded-[3px]">
        <AlertTriangle className="w-5 h-5 text-primary-blue mt-0.5 shrink-0" />
        <p className="font-sans text-[12px] text-text-secondary leading-relaxed">
          Validation metrics are derived from audit trail events, exchange execution logs, and risk engine outcomes.
          Reports include order statistics, execution history, risk events, exchange uptime, and performance summary.
        </p>
      </div>
    </div>
  );
}
