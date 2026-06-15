'use client';

import { useState, useEffect } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { MetricDisplay } from '@/components/ui/MetricDisplay';
import {
  Loader2, AlertTriangle, HeartPulse, Zap, CheckCircle2, XCircle, Shield,
  Clock, Timer, Server, Activity
} from 'lucide-react';
import { executionHealthAPI } from '@/lib/api';

export default function ExecutionHealthPage() {
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!stats) setLoading(true);
      setError(null);
      try {
        const data = await executionHealthAPI.getStats();
        setStats(data);
      } catch (err: any) {
        setError(err.message || 'An unknown error occurred.');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 30000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-primary-gold" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="card red text-center p-8">
        <AlertTriangle className="w-12 h-12 text-danger mx-auto mb-4" />
        <h3 className="text-xl font-bold text-text-primary mb-2">Failed to Load Stats</h3>
        <p className="text-text-secondary">{error}</p>
      </div>
    );
  }

  if (!stats) return null;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Execution Health Dashboard"
        subtitle="Operational monitoring of exchange connectivity, order flow, risk controls, and execution latency."
      />

      <section>
        <h3 className="font-mono text-[10px] uppercase tracking-wider text-text-muted mb-3">Exchange Status</h3>
        <div className="g4">
          {(stats.exchanges || []).map((ex: any) => (
            <div key={ex.exchange_id} className="card grey p-4">
              <div className="flex items-center gap-2 mb-2">
                <Server className="w-4 h-4 text-primary-gold" />
                <span className="font-serif text-[16px] capitalize">{ex.exchange_id}</span>
              </div>
              <p className={`text-[13px] font-bold ${ex.connected ? 'text-primary-emerald' : 'text-danger'}`}>
                {ex.connected ? 'Connected' : 'Disconnected'}
              </p>
              <p className="text-[11px] text-text-muted mt-1">
                Last heartbeat: {ex.last_heartbeat ? new Date(ex.last_heartbeat).toLocaleString() : 'N/A'}
              </p>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h3 className="font-mono text-[10px] uppercase tracking-wider text-text-muted mb-3">Order Statistics (Today)</h3>
        <div className="g4">
          <MetricDisplay label="Orders Submitted" value={(stats.orders_today?.submitted ?? 0).toString()} icon={Zap} />
          <MetricDisplay label="Orders Filled" value={(stats.orders_today?.filled ?? 0).toString()} icon={CheckCircle2} trend="up" />
          <MetricDisplay label="Orders Rejected" value={(stats.orders_today?.rejected ?? 0).toString()} icon={XCircle} />
          <MetricDisplay label="Orders Cancelled" value={(stats.orders_today?.cancelled ?? 0).toString()} icon={Activity} />
        </div>
      </section>

      <section>
        <h3 className="font-mono text-[10px] uppercase tracking-wider text-text-muted mb-3">Risk Statistics (Today)</h3>
        <div className="g4">
          <MetricDisplay label="Risk-Protected Orders" value={(stats.risk_stats?.risk_rejections ?? 0).toString()} icon={Shield} />
          <MetricDisplay label="AI Rejections" value={(stats.risk_stats?.ai_rejections ?? 0).toString()} icon={AlertTriangle} />
          <MetricDisplay label="Leverage Rejections" value={(stats.risk_stats?.leverage_rejections ?? 0).toString()} icon={XCircle} />
          <MetricDisplay label="Kill Switch Rejections" value={(stats.risk_stats?.kill_switch_rejections ?? 0).toString()} icon={HeartPulse} />
        </div>
      </section>

      <section>
        <h3 className="font-mono text-[10px] uppercase tracking-wider text-text-muted mb-3">System Metrics</h3>
        <div className="g4">
          <MetricDisplay label="Avg Order Latency" value={`${stats.latency?.avg_order_latency_ms ?? stats.avg_placement_latency_ms} ms`} icon={Clock} />
          <MetricDisplay label="Fastest Fill" value={stats.latency?.fastest_fill_ms != null ? `${stats.latency.fastest_fill_ms} ms` : 'N/A'} icon={Timer} />
          <MetricDisplay label="Slowest Fill" value={stats.latency?.slowest_fill_ms != null ? `${stats.latency.slowest_fill_ms} ms` : 'N/A'} icon={Timer} />
          <MetricDisplay label="Execution Fill Rate (1H)" value={`${stats.execution_fill_rate_pct}%`} icon={HeartPulse} trend={stats.execution_fill_rate_pct > 99 ? 'up' : 'down'} />
        </div>
      </section>

      <section>
        <h3 className="font-mono text-[10px] uppercase tracking-wider text-text-muted mb-3">Recent Activity</h3>
        <div className="card grey overflow-x-auto">
          <table className="w-full text-[12px]">
            <thead>
              <tr className="text-text-muted border-b border-border-subtle">
                <th className="text-left p-3">Time</th>
                <th className="text-left p-3">Exchange</th>
                <th className="text-left p-3">Portfolio</th>
                <th className="text-left p-3">Symbol</th>
                <th className="text-left p-3">Action</th>
                <th className="text-left p-3">Result</th>
                <th className="text-left p-3">Latency</th>
              </tr>
            </thead>
            <tbody>
              {(stats.recent_activity || []).map((row: any, i: number) => (
                <tr key={i} className="border-b border-border-subtle/50 hover:bg-background-panel/50">
                  <td className="p-3">{new Date(row.timestamp).toLocaleString()}</td>
                  <td className="p-3 capitalize">{row.exchange || '—'}</td>
                  <td className="p-3">{row.portfolio || '—'}</td>
                  <td className="p-3">{row.symbol || '—'}</td>
                  <td className="p-3 font-mono text-[10px]">{row.action}</td>
                  <td className="p-3">{row.result}</td>
                  <td className="p-3">{row.latency_ms != null ? `${row.latency_ms} ms` : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
