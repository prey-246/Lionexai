'use client';

import { useState, useEffect } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { MetricDisplay } from '@/components/ui/MetricDisplay';
import { auditAPI, portfolioAPI } from '@/lib/api';
import { ShieldAlert, Loader2, Activity } from 'lucide-react';
import type { AuditLog, Portfolio } from '@/lib/types';

export default function RiskCommandCenter() {
  const [loading, setLoading] = useState(true);
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [rejections, setRejections] = useState<AuditLog[]>([]);
  const [killSwitches, setKillSwitches] = useState<AuditLog[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [ports, rejs, kills] = await Promise.all([
          portfolioAPI.listPortfolios(),
          auditAPI.getRiskRejections(10),
          auditAPI.getKillSwitchEvents(5)
        ]);
        setPortfolios(ports);
        setRejections(rejs);
        setKillSwitches(kills);
      } catch (err) {
        console.error("Failed to load risk data", err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading) return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary-gold" /></div>;

  const activeExposure = portfolios.reduce((acc, p) => acc + ((p as any).risk_context?.exposure_used || 0), 0);
  const maxDrawdown = portfolios.reduce((acc, p) => Math.max(acc, p.current_drawdown_pct || 0), 0);
  const activeKills = portfolios.filter(p => (p as any).risk_context?.kill_switch_status).length;

  return (
    <div className="space-y-8">
      <PageHeader title="Risk Command Center" subtitle="Institutional-grade risk governance and system-wide visibility." />

      <div className="g4">
        <MetricDisplay label="System Exposure" value={`$${activeExposure.toLocaleString(undefined, {minimumFractionDigits: 2})}`} icon={Activity} />
        <MetricDisplay label="Max Drawdown" value={`${maxDrawdown.toFixed(2)}%`} trend={maxDrawdown > 0 ? 'down' : 'neutral'} />
        <MetricDisplay label="Recent Rejections" value={rejections.length} trend={rejections.length > 0 ? 'down' : 'neutral'} />
        <MetricDisplay label="Active Kill Switches" value={activeKills} trend={activeKills > 0 ? 'down' : 'neutral'} icon={ShieldAlert} />
      </div>

      <div className="g21">
        <div className="card red shadow-lg p-0 overflow-hidden">
          <div className="p-4 border-b border-border-default bg-background-base">
            <h3 className="sec-head mb-0">Recent Trade Rejections</h3>
          </div>
          <table className="nexa-table">
            <thead><tr><th>Time</th><th>Reason</th></tr></thead>
            <tbody>
              {rejections.length > 0 ? rejections.map(log => (
                <tr key={log.id}>
                  <td className="whitespace-nowrap font-mono">{new Date(log.timestamp).toLocaleTimeString()}</td>
                  <td className="text-danger">{log.description}</td>
                </tr>
              )) : (
                <tr><td colSpan={2} className="text-center py-4 text-text-muted">No recent rejections.</td></tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="card gold shadow-lg p-0 overflow-hidden">
          <div className="p-4 border-b border-border-default bg-background-base">
            <h3 className="sec-head mb-0">Kill Switch Audit</h3>
          </div>
          <table className="nexa-table">
            <thead><tr><th>Time</th><th>Event Detail</th></tr></thead>
            <tbody>
              {killSwitches.length > 0 ? killSwitches.map(log => (
                <tr key={log.id}>
                  <td className="whitespace-nowrap font-mono">{new Date(log.timestamp).toLocaleTimeString()}</td>
                  <td className="text-primary-gold">{log.description}</td>
                </tr>
              )) : (
                <tr><td colSpan={2} className="text-center py-4 text-text-muted">No kill switch events detected.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}