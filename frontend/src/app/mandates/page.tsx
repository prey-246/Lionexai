import { PageHeader } from "@/components/ui/PageHeader";
import { systemAPI, RiskMandate } from "@/lib/api";
import { ShieldCheck, ShieldAlert } from "lucide-react";

function MandateTable({ mandates }: { mandates: RiskMandate[] }) {
  return (
    <div className="bg-background-panel-1 border border-border-secondary rounded-lg overflow-hidden">
      <table className="min-w-full divide-y divide-border-secondary">
        <thead className="bg-background-panel-2">
          <tr>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">Mandate ID</th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">Profile Name</th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">Max Leverage</th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">Max Drawdown</th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">Kill Switch</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border-secondary">
          {mandates.map((mandate) => (
            <tr key={mandate.id} className="hover:bg-background-panel-2 transition-colors">
              <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-primary-gold">{mandate.id}</td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-text-primary">{mandate.name}</td>
              <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-text-secondary">{mandate.max_leverage.toFixed(1)}x</td>
              <td className="px-6 py-4 whitespace-nowrap text-sm font-mono text-text-secondary">{mandate.max_drawdown_pct.toFixed(1)}%</td>
              <td className="px-6 py-4 whitespace-nowrap text-sm">
                {mandate.kill_switch_active ? (
                  <span className="flex items-center gap-2 text-status-danger">
                    <ShieldAlert className="w-4 h-4" /> Engaged
                  </span>
                ) : (
                  <span className="flex items-center gap-2 text-status-success">
                    <ShieldCheck className="w-4 h-4" /> Standby
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default async function MandatesPage() {
  const mandates = await systemAPI.getMandates();

  return (
    <div className="space-y-8">
      <PageHeader title="Risk Mandates" subtitle="Manage and review all active risk configurations" />
      <MandateTable mandates={mandates} />
    </div>
  );
}