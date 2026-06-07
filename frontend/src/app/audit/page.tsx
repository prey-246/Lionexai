'use client';

import { useState, useEffect } from 'react';
import { auditAPI } from '@/lib/api';
import type { AuditLog } from '@/lib/types';
import { PageHeader } from '@/components/ui/PageHeader';
import { Loader2 } from 'lucide-react';

const ActionBadge = ({ type }: { type: string }) => {
  let color = 'bg-gray-700 text-gray-300';
  if (type.includes('CREATE')) color = 'bg-green-500/20 text-green-400';
  if (type.includes('UPDATE')) color = 'bg-blue-500/20 text-blue-400';
  if (type.includes('LOGIN')) color = 'bg-cyan-500/20 text-cyan-400';
  if (type.includes('REJECTION') || type.includes('KILL')) color = 'bg-red-500/20 text-red-400';
  if (type.includes('REPORT')) color = 'bg-purple-500/20 text-purple-400';

  return <span className={`px-2 py-1 text-xs font-semibold rounded-full whitespace-nowrap ${color}`}>{type}</span>;
};

export default function AuditTrailPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalLogs, setTotalLogs] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [filterType, setFilterType] = useState('');
  const logsPerPage = 20;

  useEffect(() => {
    setLoading(true);
    const offset = (currentPage - 1) * logsPerPage;
    auditAPI.getLogs(filterType || undefined, logsPerPage, offset)
      .then(data => {
        setLogs(data?.logs || []);
        setTotalLogs(data?.total || 0);
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [currentPage, filterType]);

  const totalPages = Math.ceil(totalLogs / logsPerPage);

  const handleFilterChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setFilterType(e.target.value);
    setCurrentPage(1); // Reset to first page on filter change
  };

  if (loading) {
    return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary-gold" /></div>;
  }

  if (error) {
    return <div className="text-center text-danger">{error}</div>;
  }

  return (
    <div className="space-y-8">
      <PageHeader title="Audit Trail" subtitle="An immutable log of all critical system events and user actions." />
      
      <div className="flex justify-between items-center">
        <div>
          <label htmlFor="action-type-filter" className="text-sm font-medium text-text-muted mr-2">Filter by Action:</label>
          <select
            id="action-type-filter"
            value={filterType}
            onChange={handleFilterChange}
            className="bg-background-panel-2 border border-border-secondary rounded-md px-3 py-1.5 text-sm focus:outline-none focus:border-primary-blue transition-colors"
          >
            <option value="">All Actions</option>
            <option value="USER_LOGIN">User Login</option>
            <option value="MANDATE_CREATE">Mandate Create</option>
            <option value="MANDATE_UPDATE">Mandate Update</option>
            <option value="REPORT_GENERATE">Report Generate</option>
            <option value="RISK_REJECTION">Risk Rejection</option>
            <option value="KILL_SWITCH_TRIGGERED">Kill Switch Triggered</option>
            <option value="KILL_SWITCH_RESET">Kill Switch Reset</option>
          </select>
        </div>
        <div className="flex items-center gap-4">
          <span className="text-sm text-text-muted">
            Page {currentPage} of {totalPages > 0 ? totalPages : 1}
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setCurrentPage(p => p - 1)}
              disabled={currentPage === 1}
              className="px-3 py-1.5 bg-background-panel-2 border border-border-secondary rounded-md text-sm font-semibold hover:bg-gray-700/50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Previous
            </button>
            <button
              onClick={() => setCurrentPage(p => p + 1)}
              disabled={currentPage === totalPages || totalPages === 0}
              className="px-3 py-1.5 bg-background-panel-2 border border-border-secondary rounded-md text-sm font-semibold hover:bg-gray-700/50 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Next
            </button>
          </div>
        </div>
      </div>

      <div className="bg-background-panel-1 border border-border-secondary rounded-lg">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-background-panel-2">
              <tr>
                <th className="px-6 py-3 font-medium text-text-muted">Timestamp</th>
                <th className="px-6 py-3 font-medium text-text-muted">Action Type</th>
                <th className="px-6 py-3 font-medium text-text-muted">Description</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-secondary">
              {logs?.length > 0 ? (
                logs.map((log) => (
                  <tr key={log.id} className="hover:bg-background-panel-2/50">
                    <td className="px-6 py-4 whitespace-nowrap text-text-muted font-mono">{new Date(log.timestamp).toLocaleString()}</td>
                    <td className="px-6 py-4 whitespace-nowrap"><ActionBadge type={log.action_type} /></td>
                    <td className="px-6 py-4 text-text-primary">{log.description}</td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={3} className="px-6 py-8 text-center text-text-muted">No audit logs found matching the criteria.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}