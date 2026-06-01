import { systemAPI } from "@/lib/api";
import { Activity, ShieldAlert, Server, Radio } from "lucide-react";

export default async function OperationsDashboard() {
  // Fetch infrastructure variables server-side with fallback safety layers
  const health = await systemAPI.getHealth().catch(() => ({
    status: "offline",
    database: "disconnected",
    active_mandates: 0
  }));
  
  const mandates = await systemAPI.getMandates().catch(() => []);
  const isOnline = health.status === "online";

  return (
    <main className="min-h-screen p-6 md:p-8 max-w-7xl mx-auto space-y-8">
      {/* HUD HEADER */}
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-gray-800 pb-6">
        <div>
          <div className="flex items-center gap-2">
            <Radio className="w-5 h-5 text-[#22D3EE] animate-pulse" />
            <h1 className="text-3xl font-semibold tracking-tight text-white font-sans">NEXA Operations</h1>
          </div>
          <p className="text-gray-400 text-sm mt-1">Institutional Monitoring Console & Global Risk Parameters</p>
        </div>
        
        <div className="flex items-center gap-3 glass-panel px-4 py-2 bg-[#0B1020]">
          <Server className="w-4 h-4 text-gray-400" />
          <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Engine Status:</span>
          <div className="flex items-center gap-2">
            <span className={`relative flex h-2 w-2`}>
              <span className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${isOnline ? 'bg-[#10B981]' : 'bg-[#EF4444]'}`}></span>
              <span className={`relative inline-flex rounded-full h-2 w-2 ${isOnline ? 'bg-[#10B981]' : 'bg-[#EF4444]'}`}></span>
            </span>
            <span className={`text-xs font-bold tracking-widest ${isOnline ? 'text-[#10B981]' : 'text-[#EF4444]'}`}>
              {isOnline ? 'ONLINE' : 'OFFLINE'}
            </span>
          </div>
        </div>
      </header>

      {/* SYSTEM METRICS STATUS MATRIX */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* PORTFOLIO TRACKER */}
        <div className="glass-panel p-6 bg-[#0B1020] relative overflow-hidden group border border-gray-800">
          <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
            <Activity className="w-16 h-16 text-[#5EEAD4]" />
          </div>
          <span className="metric-label">Active Portfolios</span>
          <div className="metric-value mt-2">
            0 <span className="text-xs text-gray-500 font-normal tracking-normal">/ Simulated Base</span>
          </div>
        </div>

        {/* RISK CIRCUIT BREAKER */}
        <div className="glass-panel p-6 bg-[#0B1020] relative overflow-hidden group border border-gray-800">
          <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
            <ShieldAlert className="w-16 h-16 text-[#F59E0B]" />
          </div>
          <span className="metric-label">Kill Switch Breaches (24h)</span>
          <div className="metric-value mt-2 text-white">0</div>
        </div>

        {/* REPOSITORY BACKEND DISK STATUS */}
        <div className="glass-panel p-6 bg-[#0B1020] relative overflow-hidden group border border-gray-800">
          <div className="absolute top-0 right-0 p-4 opacity-5 group-hover:opacity-10 transition-opacity">
            <Server className="w-16 h-16 text-[#22D3EE]" />
          </div>
          <span className="metric-label">Database Status</span>
          <div className="metric-value mt-2 text-sm text-gray-300 font-mono bg-black/40 p-2 rounded border border-gray-850 self-start">
            {health.database.toUpperCase()}
          </div>
        </div>
      </div>

      {/* CORE RISK ENGINE RULESETS */}
      <section className="space-y-4">
        <div className="border-b border-gray-800 pb-2">
          <h2 className="text-lg font-medium tracking-tight text-white">Active Risk Mandates</h2>
        </div>
        <div className="glass-panel overflow-hidden border border-gray-800 bg-[#0B1020]">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-black/40 text-gray-400 uppercase tracking-wider text-[10px] border-b border-gray-800">
                <tr>
                  <th className="px-6 py-4 font-medium">Mandate ID</th>
                  <th className="px-6 py-4 font-medium">Profile Parameters</th>
                  <th className="px-6 py-4 font-medium">Max Leverage Allocation</th>
                  <th className="px-6 py-4 font-medium">Max Drawdown Threshold</th>
                  <th className="px-6 py-4 font-medium text-right">Circuit Breaker</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-850">
                {mandates.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-gray-500 italic">
                      No active risk configurations loaded from infrastructure layer.
                    </td>
                  </tr>
                ) : (
                  mandates.map((m: any) => (
                    <tr key={m.id} className="hover:bg-white/[0.02] transition-colors">
                      <td className="px-6 py-4 font-mono font-bold text-[#22D3EE] text-xs tracking-wider">{m.id}</td>
                      <td className="px-6 py-4 text-gray-200 font-medium">{m.name}</td>
                      <td className="px-6 py-4 text-gray-400 font-mono">{m.max_leverage}x</td>
                      <td className="px-6 py-4 text-[#EF4444] font-mono font-medium">{m.max_drawdown_pct}%</td>
                      <td className="px-6 py-4 text-right">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded text-xs font-semibold uppercase tracking-wider ${
                          m.kill_switch_active 
                            ? 'bg-[#EF4444]/10 text-[#EF4444] border border-[#EF4444]/20' 
                            : 'bg-[#10B981]/10 text-[#10B981] border border-[#10B981]/20'
                        }`}>
                          {m.kill_switch_active ? 'ENGAGED' : 'STANDBY'}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </main>
  );
}