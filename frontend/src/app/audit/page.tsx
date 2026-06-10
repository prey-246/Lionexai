'use client';

import { useState, useEffect } from 'react';
import { auditAPI } from '@/lib/api';
import type { AuditLog } from '@/lib/types';
import { PageHeader } from '@/components/ui/PageHeader';
import { Loader2 } from 'lucide-react';

const ActionBadge = ({ type }: { type: string }) => {
  let color = 'blue';
  if (type.includes('CREATE')) color = 'teal';
  if (type.includes('UPDATE')) color = 'gold';
  if (type.includes('LOGIN')) color = 'teal';
  if (type.includes('REJECTION') || type.includes('KILL')) color = 'red';

  return <span className={`tag ${color}`}>{type}</span>;
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
          <label htmlFor="action-type-filter" className="font-mono text-[8.5px] uppercase tracking-wider text-text-muted mr-2">Filter by Action:</label>
          <select
            id="action-type-filter"
            value={filterType}
            onChange={handleFilterChange}
            className="border border-border-default rounded-[3px] px-3 py-1.5 font-sans text-[13px] focus:outline-none focus:border-primary-blue transition-colors"
          >
            <option value="">All Actions</option>
            <option value="USER_LOGIN">User Login</option>
            <option value="MANDATE_CREATE">Mandate Create</option>
            <option value="MANDATE_UPDATE">Mandate Update</option>
            <option value="REPORT_GENERATE">Report Generate</option>
            <option value="RISK_REJECTION">Risk Rejection</option>
            <option value="KILL_SWITCH_TRIGGERED">Kill Switch Triggered</option>
            <option value="KILL_SWITCH_RESET">Kill Switch Reset</option>
            <option value="SETTINGS_UPDATE">Settings Update</option>
            <option value="STRATEGY_CREATE">Strategy Create</option>
            <option value="STRATEGY_UPDATE">Strategy Update</option>
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
              className="btn grey"
            >
              Previous
            </button>
            <button
              onClick={() => setCurrentPage(p => p + 1)}
              disabled={currentPage === totalPages || totalPages === 0}
              className="btn grey"
            >
              Next
            </button>
          </div>
        </div>
      </div>

      <div className="card shadow-lg p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="nexa-table">
            <thead>
              <tr>
                <th>Timestamp</th>
                <th>Action Type</th>
                <th>Description</th>
              </tr>
            </thead>
            <tbody>
              {logs?.length > 0 ? (
                logs.map((log) => (
                  <tr key={log.id}>
                    <td className="whitespace-nowrap font-mono">{new Date(log.timestamp).toLocaleString()}</td>
                    <td className="whitespace-nowrap"><ActionBadge type={log.action_type} /></td>
                    <td>{log.description}</td>
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