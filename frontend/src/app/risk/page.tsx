"use client";

import { useState, useEffect } from 'react';
import { portfolioAPI, systemAPI, auditAPI, tradeAPI } from '@/lib/api';
import type { Portfolio, RiskMandate, AuditLog } from '@/lib/types';
import { PageHeader } from '@/components/ui/PageHeader';
import { Loader2, AlertTriangle, ShieldAlert, Unlock, TrendingDown, Gauge, Ban, Wallet } from 'lucide-react';
import MandateBadge from '@/components/ui/MandateBadge';

export default function RiskMonitoring() {
  const [portfolios, setPortfolios] = useState<Portfolio[]>([]);
  const [lockedMandates, setLockedMandates] = useState<RiskMandate[]>([]);
  const [rejections, setRejections] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      const [portfolioData, mandateData, rejectionData] = await Promise.all([
        portfolioAPI.listPortfolios(),
        systemAPI.getMandates(),
        auditAPI.getRiskRejections(20),
      ]);
      setPortfolios(portfolioData || []);
      setLockedMandates((mandateData || []).filter((m: RiskMandate) => m.kill_switch_active));
      setRejections(rejectionData || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleUnlock = async (mandateId: string) => {
    if (confirm(`Are you sure you want to reset the kill switch for mandate "${mandateId}"?`)) {
      try {
        await tradeAPI.resetKillSwitch(mandateId);
        await fetchData(); // Re-fetch all data to update the UI
      } catch (err: any) {
        alert(`Failed to unlock mandate: ${err.message}`);
      }
    }
  };

  if (loading) {
    return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary-gold" /></div>;
  }

  if (error) {
    return <div className="text-center text-danger">{error}</div>;
  }

  const RiskProgressBar = ({ value, limit, label }: { value: number, limit: number, label: string }) => {
    const percentage = limit > 0 ? (value / limit) * 100 : 0;
    let colorClass = 'bg-success';
    if (percentage > 75) {
      colorClass = 'bg-danger';
    } else if (percentage > 50) {
      colorClass = 'bg-warning';
    }
  
    return (
      <div>
        <div className="flex justify-between text-xs mb-1">
          <span className="text-text-muted">{label}</span>
          <span className="font-mono text-text-primary">{value.toFixed(2)}% / {limit.toFixed(2)}%</span>
        </div>
        <div className="w-full bg-background-panel-2 rounded-full h-2">
          <div className={`${colorClass} h-2 rounded-full`} style={{ width: `${Math.min(percentage, 100)}%` }}></div>
        </div>
      </div>
    );
  };

  return (
    <div className="space-y-8">
      <PageHeader title="Risk Monitoring" subtitle="System-wide exposure, drawdown, and risk event overview." />

      {lockedMandates?.length > 0 && (
        <div className="bg-danger/10 border border-danger/30 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-danger mb-4 flex items-center gap-2"><ShieldAlert /> System Halts Active</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {lockedMandates?.map(mandate => (
              <div key={mandate.pk_id} className="bg-background-panel-2 p-4 rounded-md flex justify-between items-center">
                <div>
                  <p className="font-semibold text-text-primary">{mandate.name}</p>
                  <p className="font-mono text-sm text-danger">{mandate.id}</p>
                </div>
                <button onClick={() => handleUnlock(mandate.id)} className="flex items-center gap-2 px-3 py-1.5 bg-danger/20 hover:bg-danger/40 text-danger border border-danger/30 rounded-md text-xs font-semibold transition-colors">
                  <Unlock className="w-4 h-4" />
                  Reset
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div>
        <h3 className="text-lg font-semibold text-text-primary mb-4">Live Portfolio Risk Exposure</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {portfolios?.map(p => (
            <div key={p.id} className="bg-background-panel-1 border border-border-secondary rounded-lg p-4 space-y-4">
              <div className="flex justify-between items-start">
                <div>
                  <p className="font-mono text-primary-gold">{p.id}</p>
                  <MandateBadge mandateId={p.mandate_id} />
                </div>
                <div className="text-right">
                  <p className="text-xs text-text-muted">Capital at Risk</p>
                  <p className="font-mono text-text-primary">${(p.risk_context?.capital_at_risk || 0).toLocaleString()}</p>
                </div>
              </div>
              <RiskProgressBar value={p.risk_context?.current_drawdown_pct || p.current_drawdown_pct || 0} limit={p.risk_context?.max_drawdown_pct || 100} label="Max Drawdown" />
              <RiskProgressBar value={p.risk_context?.exposure_utilization_pct || 0} limit={100} label="Exposure" />
            </div>
          ))}
          {portfolios?.length === 0 && <p className="text-sm text-text-muted text-center p-4 col-span-full">No active portfolios to monitor.</p>}
        </div>
      </div>

      <div>
        <h3 className="text-lg font-semibold text-text-primary mb-4">Recent Trade Rejections</h3>
        <div className="bg-background-panel-1 border border-border-secondary rounded-lg p-4 space-y-3">
          {rejections?.slice(0, 5).map(log => (
            <div key={log.id} className="text-sm flex items-start gap-3 p-2 rounded-md hover:bg-background-panel-2">
              <Ban className="w-4 h-4 text-danger mt-0.5 shrink-0" />
              <div>
                <p className="text-text-primary">{log.description}</p>
                <p className="text-xs text-text-muted font-mono">{new Date(log.timestamp).toLocaleString()}</p>
              </div>
            </div>
          ))}
          {rejections?.length === 0 && <p className="text-sm text-text-muted text-center p-4">No rejections in the log.</p>}
        </div>
      </div>
    </div>
  );
}
