import { systemAPI } from "@/lib/api";
import { PageHeader } from "@/components/ui/PageHeader";
import { Server, ShieldAlert, Activity, CheckCircle, XCircle } from "lucide-react";

export default async function OperationsDashboard() {
  const health = await systemAPI.getHealth().catch(() => ({
    status: "offline",
    database: "disconnected",
  }));
  const mandates = await systemAPI.getMandates().catch(() => []);
  const isOnline = health.status === "online";
  const isDbConnected = health.database === "connected";

  return (
    <div className="space-y-8">
      <PageHeader
        title="Operations Console"
        subtitle="Institutional Monitoring & Global Risk Parameters"
      />

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-background-panel-1 border border-border-secondary rounded p-4">
          <div className="flex items-center gap-3">
            <Server className="w-4 h-4 text-text-muted" />
            <h3 className="font-mono text-sm text-text-secondary font-bold">ENGINE STATUS</h3>
          </div>
          <p className={`mt-2 text-lg font-bold ${isOnline ? 'text-primary-teal' : 'text-danger'}`}>{isOnline ? 'ONLINE' : 'OFFLINE'}</p>
        </div>
        <div className="bg-background-panel-1 border border-border-secondary rounded p-4">
          <div className="flex items-center gap-3">
            <Activity className="w-4 h-4 text-text-muted" />
            <h3 className="font-mono text-sm text-text-secondary font-bold">DATABASE</h3>
          </div>
          <p className={`mt-2 text-lg font-bold ${isDbConnected ? 'text-primary-teal' : 'text-danger'}`}>{isDbConnected ? 'CONNECTED' : 'DISCONNECTED'}</p>
        </div>
        <div className="bg-background-panel-1 border border-border-secondary rounded p-4">
          <div className="flex items-center gap-3">
            <ShieldAlert className="w-4 h-4 text-text-muted" />
            <h3 className="font-mono text-sm text-text-secondary font-bold">ACTIVE MANDATES</h3>
          </div>
          <p className="mt-2 text-lg font-bold text-primary-gold">{mandates.length}</p>
        </div>
      </div>

      <section className="space-y-4">
        <h2 className="text-lg font-serif font-semibold text-text-primary">Core Risk Engine Rulesets</h2>
        <div className="bg-background-panel-1 border border-border-secondary rounded overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-background-panel-2 text-text-muted uppercase tracking-wider font-mono text-xs border-b border-border-primary">
                <tr>
                  <th className="px-6 py-3 font-bold">Mandate ID</th>
                  <th className="px-6 py-3 font-bold">Profile Name</th>
                  <th className="px-6 py-3 font-bold">Max Leverage</th>
                  <th className="px-6 py-3 font-bold">Max Drawdown</th>
                  <th className="px-6 py-3 font-bold text-center">Circuit Breaker</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-primary">
                {mandates.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="px-6 py-8 text-center text-text-muted font-mono">
                      // NO RISK CONFIGURATIONS LOADED //
                    </td>
                  </tr>
                ) : (
                  mandates.map((m: any) => (
                    <tr key={m.id} className="hover:bg-white/5 transition-colors">
                      <td className="px-6 py-4 font-mono font-bold text-primary-blue">{m.id}</td>
                      <td className="px-6 py-4 text-text-secondary font-sans">{m.name}</td>
                      <td className="px-6 py-4 text-text-muted font-mono">{m.max_leverage.toFixed(1)}x</td>
                      <td className="px-6 py-4 text-danger font-mono font-bold">{m.max_drawdown_pct.toFixed(1)}%</td>
                      <td className="px-6 py-4 text-center">
                        <span className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-sm text-xs font-mono font-bold uppercase ${
                          m.kill_switch_active 
                            ? 'bg-danger/10 text-danger' 
                            : 'bg-primary-teal/10 text-primary-teal'
                        }`}>
                          {m.kill_switch_active ? <XCircle className="w-3 h-3"/> : <CheckCircle className="w-3 h-3"/>}
                          {m.kill_switch_active ? 'Engaged' : 'Standby'}
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
    </div>
  );
}