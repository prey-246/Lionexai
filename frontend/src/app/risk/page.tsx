"use client";

import React, { useState, useEffect } from "react";
import { auditAPI, portfolioAPI } from "@/lib/api";
import { AlertTriangle, ShieldAlert, CheckCircle } from "lucide-react";
import { GlassCard } from "@/components/ui/GlassCard";

export default function RiskMonitoring() {
  const [riskEvents, setRiskEvents] = useState<any[]>([]);
  const [rejections, setRejections] = useState<any[]>([]);
  const [killSwitchEvents, setKillSwitchEvents] = useState<any[]>([]);
  const [portfolioId, setPortfolioId] = useState<string>("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const portfolios = await portfolioAPI.listPortfolios();
        if (portfolios.length > 0) {
          setPortfolioId(portfolios[0].id);
          const events = await portfolioAPI.getRiskEvents(portfolios[0].id);
          setRiskEvents(events);
        }

        const rejectionData = await auditAPI.getRiskRejections();
        setRejections(rejectionData);

        const killSwitchData = await auditAPI.getKillSwitchEvents();
        setKillSwitchEvents(killSwitchData);
      } catch (err) {
        console.error("Failed to load risk data", err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 10000);
    return () => clearInterval(interval);
  }, []);

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case "CRITICAL":
        return "bg-red-900/20 border-red-900/30 text-red-300";
      case "WARNING":
        return "bg-yellow-900/20 border-yellow-900/30 text-yellow-300";
      default:
        return "bg-blue-900/20 border-blue-900/30 text-blue-300";
    }
  };

  if (loading) return <div className="p-6 text-center text-gray-400">Loading risk data...</div>;

  return (
    <main className="min-h-screen p-6 md:p-8 max-w-7xl mx-auto space-y-8">
      <header className="border-b border-gray-800 pb-6">
        <h1 className="text-3xl font-semibold tracking-tight text-white flex items-center gap-3">
          <ShieldAlert className="w-8 h-8 text-[#F59E0B]" />
          Risk Monitoring
        </h1>
        <p className="text-gray-400 text-sm mt-1">Real-time risk events & audit trail</p>
      </header>

      {/* CRITICAL ALERTS */}
      <section className="space-y-4">
        <div className="border-b border-gray-800 pb-2">
          <h2 className="text-lg font-medium tracking-tight text-white">Risk Events</h2>
        </div>
        {riskEvents.length === 0 ? (
          <GlassCard className="p-8 text-center text-gray-500">
            <CheckCircle className="w-12 h-12 mx-auto mb-3 text-green-500 opacity-50" />
            No risk events detected
          </GlassCard>
        ) : (
          <div className="space-y-3">
            {riskEvents.slice(0, 10).map((event) => (
              <GlassCard
                key={event.id}
                className={`p-4 border ${getSeverityColor(event.severity)}`}
              >
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5" />
                  <div className="flex-1">
                    <div className="font-semibold">{event.event_type}</div>
                    <div className="text-sm mt-1">{event.description}</div>
                    <div className="text-xs text-gray-500 mt-2">
                      {new Date(event.triggered_at).toLocaleString()}
                    </div>
                  </div>
                  {event.resolved && (
                    <span className="text-xs bg-green-900/20 text-green-300 px-2 py-1 rounded">
                      Resolved
                    </span>
                  )}
                </div>
              </GlassCard>
            ))}
          </div>
        )}
      </section>

      {/* RISK REJECTIONS */}
      <section className="space-y-4">
        <div className="border-b border-gray-800 pb-2">
          <h2 className="text-lg font-medium tracking-tight text-white">Risk Rejections</h2>
        </div>
        {rejections.length === 0 ? (
          <GlassCard className="p-8 text-center text-gray-500">
            No trade rejections
          </GlassCard>
        ) : (
          <GlassCard className="overflow-hidden border border-gray-800 bg-[#0B1020]">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-black/40 text-gray-400 uppercase tracking-wider text-[10px] border-b border-gray-800">
                  <tr>
                    <th className="px-6 py-4 font-medium">Time</th>
                    <th className="px-6 py-4 font-medium">Action</th>
                    <th className="px-6 py-4 font-medium">Reason</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-850">
                  {rejections.slice(0, 10).map((log) => (
                    <tr key={log.id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="px-6 py-4 text-gray-400 text-xs">
                        {new Date(log.timestamp).toLocaleString()}
                      </td>
                      <td className="px-6 py-4 font-mono text-[#EF4444]">RISK_REJECTION</td>
                      <td className="px-6 py-4 text-gray-300 text-sm">{log.description}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </GlassCard>
        )}
      </section>

      {/* KILL SWITCH EVENTS */}
      <section className="space-y-4">
        <div className="border-b border-gray-800 pb-2">
          <h2 className="text-lg font-medium tracking-tight text-white">Kill Switch Events</h2>
        </div>
        {killSwitchEvents.length === 0 ? (
          <GlassCard className="p-8 text-center text-gray-500">
            <CheckCircle className="w-12 h-12 mx-auto mb-3 text-green-500 opacity-50" />
            No kill switch triggered
          </GlassCard>
        ) : (
          <div className="space-y-3">
            {killSwitchEvents.slice(0, 5).map((event) => (
              <GlassCard
                key={event.id}
                className="p-4 border border-red-900/30 bg-red-900/10"
              >
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 shrink-0 mt-0.5 text-red-400" />
                  <div className="flex-1">
                    <div className="font-semibold text-red-300">KILL SWITCH ENGAGED</div>
                    <div className="text-sm text-red-200 mt-1">{event.description}</div>
                    <div className="text-xs text-red-400/70 mt-2">
                      {new Date(event.timestamp).toLocaleString()}
                    </div>
                  </div>
                </div>
              </GlassCard>
            ))}
          </div>
        )}
      </section>
    </main>
  );
}
