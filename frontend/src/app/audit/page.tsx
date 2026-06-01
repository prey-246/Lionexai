import { Suspense } from "react";
import { PageHeader } from "@/components/ui/PageHeader";
import { PaginationControls } from "@/components/ui/PaginationControls";
import { FilterControls } from "@/components/ui/FilterControls";
import { auditAPI } from "@/lib/api";
import type { AuditLog } from "@/lib/types";
import { AlertTriangle, ZapOff, Check, FileText, ShieldBan } from "lucide-react";

function formatTimestamp(isoString: string) {
  const date = new Date(isoString);
  return `${date.toLocaleDateString()} ${date.toLocaleTimeString()}`;
}

const actionTypeConfig = {
  RISK_REJECTION: { icon: ShieldBan, color: "text-status-warning", label: "Risk Rejection" },
  KILL_SWITCH_TRIGGERED: { icon: ZapOff, color: "text-status-danger", label: "Kill Switch" },
  TRADE_EXECUTED: { icon: Check, color: "text-status-success", label: "Trade Executed" },
  REPORT_GENERATED: { icon: FileText, color: "text-primary-blue", label: "Report Generated" },
  DEFAULT: { icon: AlertTriangle, color: "text-text-muted", label: "System Event" },
};

function ActionBadge({ type }: { type: string }) {
  const config = actionTypeConfig[type as keyof typeof actionTypeConfig] || actionTypeConfig.DEFAULT;
  const Icon = config.icon;
  return (
    <span className={`inline-flex items-center gap-2 text-xs font-medium ${config.color}`}>
      <Icon className="w-3.5 h-3.5" />
      {config.label}
    </span>
  );
}

function AuditTable({ logs }: { logs: AuditLog[] }) {
  return (
    <div className="bg-background-panel-1 border border-border-secondary rounded-lg overflow-hidden">
      <table className="min-w-full divide-y divide-border-secondary">
        <thead className="bg-background-panel-2">
          <tr>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">Timestamp</th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">Action</th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">Description</th>
            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-text-muted uppercase tracking-wider">Details</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border-secondary">
          {logs.map((log) => (
            <tr key={log.id} className="hover:bg-background-panel-2 transition-colors">
              <td className="px-6 py-4 whitespace-nowrap text-sm text-text-muted font-mono">{formatTimestamp(log.timestamp)}</td>
              <td className="px-6 py-4 whitespace-nowrap text-sm">
                <ActionBadge type={log.action_type} />
              </td>
              <td className="px-6 py-4 text-sm text-text-primary">{log.description}</td>
              <td className="px-6 py-4 text-xs text-text-muted font-mono">
                {log.metadata_json ? (
                  <pre className="bg-background-root p-2 rounded overflow-x-auto">
                    {JSON.stringify(log.metadata_json, null, 2)}
                  </pre>
                ) : (
                  'N/A'
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default async function AuditTrailPage({
  searchParams,
}: {
  searchParams: { [key: string]: string | string[] | undefined };
}) {
  const page = searchParams['page'] ?? '1';
  const filter = searchParams['filter'] as string | undefined;
  const perPage = 20; // Number of items per page
  const offset = (Number(page) - 1) * perPage;

  const actionType = filter === 'ALL' ? undefined : filter;

  // The API returns a paginated object like { total: number, logs: AuditLog[] }
  // We need to access the 'logs' property from the response.
  const response = await auditAPI.getLogs(actionType, perPage, offset).catch(() => ({ total: 0, limit: perPage, offset: 0, logs: [] }));
  const totalLogs = response.total;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Audit Trail"
        subtitle={`Displaying ${response.logs.length} of ${totalLogs} total events ${actionType ? `(filtered by ${actionType})` : ''}`}
      />
      <div className="flex justify-between items-center">
        <FilterControls />
      </div>
      {/* Ensure we pass an array to AuditTable, even if the response is malformed */}
      <AuditTable logs={response.logs || []} />
      <Suspense fallback={<div className="h-12"></div>}>
        <PaginationControls totalItems={totalLogs} perPage={perPage} />
      </Suspense>
    </div>
  );
}