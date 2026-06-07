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
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <MetricDisplay label="API Engine" value={health?.status || 'Offline'} icon={Zap} trend={health?.status === 'online' ? 'up' : 'down'} />
        <MetricDisplay label="Database" value={health?.database || 'Offline'} icon={Database} trend={health?.database === 'connected' ? 'up' : 'down'} />
        <MetricDisplay label="Cache (Redis)" value="Connected" icon={Layers} trend="up" />
        <MetricDisplay label="WebSockets" value="Connected" icon={Wifi} trend="up" />
        <MetricDisplay label="Background Jobs" value="Idle" icon={Server} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div>
          <h3 className="text-lg font-semibold text-text-primary mb-4">Recent System Activity</h3>
          <div className="bg-background-panel-1 border border-border-secondary rounded-lg p-4 space-y-3">
            {activity?.length > 0 ? activity.map(log => (
              <div key={log.id} className="text-sm flex items-start gap-3">
                <Clock className="w-4 h-4 text-text-muted mt-0.5 shrink-0" />
                <div>
                  <p className="text-text-primary">{log.description}</p>
                  <p className="text-xs text-text-muted font-mono">{new Date(log.timestamp).toLocaleTimeString()}</p>
                </div>
              </div>
            )) : <p className="text-sm text-text-muted text-center p-4">No recent activity.</p>}
          </div>
        </div>
        <div>
          <h3 className="text-lg font-semibold text-text-primary mb-4">Recent Trade Rejections</h3>
          <div className="bg-background-panel-1 border border-border-secondary rounded-lg p-4 space-y-3">
            {rejections?.length > 0 ? rejections.map(log => (
              <div key={log.id} className="text-sm flex items-start gap-3">
                <Ban className="w-4 h-4 text-danger mt-0.5 shrink-0" />
                <div>
                  <p className="text-text-primary">{log.description}</p>
                  <p className="text-xs text-text-muted font-mono">{new Date(log.timestamp).toLocaleTimeString()}</p>
                </div>
              </div>
            )) : <p className="text-sm text-text-muted text-center p-4">No rejections today.</p>}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-background-panel-1 border border-border-secondary rounded-lg p-6 text-center"><Server className="w-8 h-8 mx-auto text-primary-blue mb-2" /><h4 className="font-semibold text-text-primary">Trades Today</h4><p className="text-2xl font-mono">{health?.trades_today || 0}</p><p className="text-xs text-text-muted">Live Executions</p></div>
        <div className="bg-background-panel-1 border border-border-secondary rounded-lg p-6 text-center"><Users className="w-8 h-8 mx-auto text-primary-teal mb-2" /><h4 className="font-semibold text-text-primary">Registered Users</h4><p className="text-2xl font-mono">{health?.active_users || 0}</p><p className="text-xs text-text-muted">System Accounts</p></div>
      </div>
    </div>
  );
}