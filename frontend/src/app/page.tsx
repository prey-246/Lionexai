'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { systemAPI, auditAPI } from '@/lib/api';
import type { EngineHealth, AuditLog } from '@/lib/types';
import { PageHeader } from "@/components/ui/PageHeader";
import { MetricDisplay } from '@/components/ui/MetricDisplay';
import { Loader2, AlertTriangle, Zap, Database, Layers, Wifi, Server, Clock, Ban, Users } from 'lucide-react';

export default function DashboardPage() {
  const [health, setHealth] = useState<EngineHealth | null>(null);
  const [activity, setActivity] = useState<AuditLog[]>([]);
  const [rejections, setRejections] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        const [healthData, activityData, rejectionData] = await Promise.all([
          systemAPI.getHealth(),
          auditAPI.getLogs(undefined, 5), // Get recent general activity
          auditAPI.getRiskRejections(5)    // Get recent rejections
        ]);
        setHealth(healthData);
        setActivity(activityData?.logs || []);
        setRejections(rejectionData || []);
      } catch (err: any) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };
    fetchDashboardData();
  }, []);

  if (loading) {
    return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary-gold" /></div>;
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-danger">
        <AlertTriangle className="w-12 h-12 mb-4" />
        <h2 className="text-xl font-semibold">Failed to load system status</h2>
        <p className="text-sm">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <PageHeader title="System Operations" subtitle="Live status of all platform infrastructure and services." />
      <div className="g4">
        <MetricDisplay label="API Engine" value={health?.status || 'Offline'} icon={Zap} trend={health?.status === 'online' ? 'up' : 'down'} />
        <MetricDisplay label="Database" value={health?.database || 'Offline'} icon={Database} trend={health?.database === 'connected' ? 'up' : 'down'} />
        <MetricDisplay label="Cache (Redis)" value="Connected" icon={Layers} trend="up" />
        <MetricDisplay label="WebSockets" value="Connected" icon={Wifi} trend="up" />
        <MetricDisplay label="Background Jobs" value="Idle" icon={Server} />
      </div>

      <div className="g21">
        <div>
          <h3 className="sec-head">Recent System Activity</h3>
          <div className="card space-y-1">
            {activity?.length > 0 ? activity.map(log => (
              <div key={log.id} className="flex items-start gap-3 py-3 border-b border-border-subtle last:border-0">
                <span className="grid place-items-center w-8 h-8 rounded-lg bg-background-panel border border-border-subtle text-text-muted shrink-0">
                  <Clock className="w-4 h-4" />
                </span>
                <div className="min-w-0">
                  <p className="font-sans text-[13px] text-text-primary">{log.description}</p>
                  <p className="font-mono text-[11px] text-text-muted mt-1">{new Date(log.timestamp).toLocaleTimeString()}</p>
                </div>
              </div>
            )) : <p className="font-sans text-[13px] text-text-muted text-center py-8">No recent activity.</p>}
          </div>
        </div>
        <div>
          <h3 className="sec-head">Recent Trade Rejections</h3>
          <div className="card red space-y-1">
            {rejections?.length > 0 ? rejections.map(log => (
              <div key={log.id} className="flex items-start gap-3 py-3 border-b border-border-subtle last:border-0">
                <span className="grid place-items-center w-8 h-8 rounded-lg bg-system-rBg border border-system-rBd text-danger shrink-0">
                  <Ban className="w-4 h-4" />
                </span>
                <div className="min-w-0">
                  <p className="font-sans text-[13px] text-danger">{log.description}</p>
                  <p className="font-mono text-[11px] text-text-muted mt-1">{new Date(log.timestamp).toLocaleTimeString()}</p>
                </div>
              </div>
            )) : <p className="font-sans text-[13px] text-text-muted text-center py-8">No rejections today.</p>}
          </div>
        </div>
      </div>

      <div className="g21">
        <div className="card blue flex items-center gap-5">
          <span className="grid place-items-center w-14 h-14 rounded-xl bg-system-bBg border border-system-bBd text-primary-blue shrink-0">
            <Server className="w-7 h-7" />
          </span>
          <div>
            <h4 className="font-mono text-[11px] uppercase tracking-[0.12em] text-text-muted mb-1">Trades Today</h4>
            <p className="font-display text-[32px] leading-none font-bold text-text-primary tabular-nums">{health?.trades_today || 0}</p>
          </div>
        </div>
        <div className="card teal flex items-center gap-5">
          <span className="grid place-items-center w-14 h-14 rounded-xl bg-system-tBg border border-system-tBd text-primary-emerald-bright shrink-0">
            <Users className="w-7 h-7" />
          </span>
          <div>
            <h4 className="font-mono text-[11px] uppercase tracking-[0.12em] text-text-muted mb-1">Registered Users</h4>
            <p className="font-display text-[32px] leading-none font-bold text-text-primary tabular-nums">{health?.active_users || 0}</p>
          </div>
        </div>
      </div>
    </div>
  );
}