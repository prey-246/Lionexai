'use client';

import { useState, useEffect } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { MetricDisplay } from '@/components/ui/MetricDisplay';
import { Loader2, AlertTriangle, ShieldCheck, Download, BarChart2, TrendingUp, TrendingDown, Clock, CheckCircle2 } from 'lucide-react';
import { validationAPI } from '@/lib/api';

export default function ValidationPage() {
  const [summary, setSummary] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const data = await validationAPI.getSummary();
        setSummary(data);
      } catch (err: any) {
        setError(err.message || 'An unknown error occurred.');
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      await validationAPI.downloadReport();
    } catch (err: any) {
      alert(`Failed to download report: ${err.message}`);
    } finally {
      setDownloading(false);
    }
  };

  if (loading) {
    return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary-gold" /></div>;
  }

  if (error) {
    return (
      <div className="card red text-center p-8">
        <AlertTriangle className="w-12 h-12 text-danger mx-auto mb-4" />
        <h3 className="text-xl font-bold text-text-primary mb-2">Failed to Load Validation Data</h3>
        <p className="text-text-secondary">{error}</p>
      </div>
    );
  }

  if (!summary) return null;

  return (
    <div className="space-y-8">
      <PageHeader 
        title="3-Day Validation Framework" 
        subtitle="Continuous platform performance and stability monitoring over a three-day rolling window."
      >
        <button onClick={handleDownload} className="btn gold flex items-center gap-2" disabled={downloading}>
          {downloading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
          Download PDF Report
        </button>
      </PageHeader>

      <section>
        <h3 className="font-mono text-[10px] uppercase tracking-wider text-text-muted mb-3">Aggregated Results (Last 72 Hours)</h3>
        <div className="g4">
          <MetricDisplay label="Total Orders" value={(summary.aggregated.total_orders || 0).toString()} icon={BarChart2} />
          <MetricDisplay label="Orders Filled" value={(summary.aggregated.filled_orders || 0).toString()} icon={CheckCircle2} trend="up" />
          <MetricDisplay label="Risk Rejections" value={(summary.aggregated.rejected_orders || 0).toString()} icon={ShieldCheck} />
          <MetricDisplay label="Avg. Latency" value={`${summary.aggregated.average_latency} ms`} icon={Clock} />
        </div>
        <div className="g4 mt-4">
          <MetricDisplay label="Best Portfolio" value={summary.aggregated.best_portfolio || 'N/A'} icon={TrendingUp} />
          <MetricDisplay label="Worst Portfolio" value={summary.aggregated.worst_portfolio || 'N/A'} icon={TrendingDown} />
        </div>
      </section>

      <section>
        <h3 className="font-mono text-[10px] uppercase tracking-wider text-text-muted mb-3">Daily Performance Breakdown</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {(summary.daily_stats || []).map((day: any) => (
            <div key={day.day} className="card grey p-5">
              <h4 className="font-serif text-[18px] text-text-primary mb-4">{day.day}</h4>
              <div className="space-y-3">
                <div className="flex justify-between items-center text-sm">
                  <span className="text-text-secondary">Trades Executed</span>
                  <span className="font-mono font-bold text-text-primary">{day.trades_executed}</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-text-secondary">Risk Rejections</span>
                  <span className="font-mono font-bold text-text-primary">{day.risk_rejections}</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-text-secondary">Success Rate</span>
                  <span className="font-mono font-bold text-primary-emerald">{day.success_rate}%</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}