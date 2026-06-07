'use client';

import { useState, useEffect } from 'react';
import { PageHeader } from '@/components/ui/PageHeader';
import { UserCog, Loader2 } from 'lucide-react';
import { usersAPI } from '@/lib/api';
import type { User } from '@/lib/types';

export default function UserManagementPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUsers = async () => {
    try {
      setLoading(true);
      const data = await usersAPI.listUsers();
      setUsers(data || []);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleRoleChange = async (userId: string, newRole: string) => {
    try {
      await usersAPI.updateRole(userId, newRole);
      setUsers(users.map(u => u.id === userId ? { ...u, role_tier: newRole } : u));
    } catch (err: any) {
      alert(`Failed to update role: ${err.message}`);
    }
  };

  if (loading) {
    return <div className="flex justify-center items-center h-64"><Loader2 className="w-8 h-8 animate-spin text-primary-gold" /></div>;
  }

  if (error) {
    return <div className="text-center text-danger">{error}</div>;
  }

  return (
    <div className="space-y-8">
      <PageHeader title="User Management" subtitle="View, create, and manage user roles and permissions." />
      
      <div className="bg-background-panel-1 border border-border-secondary rounded-lg overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-background-panel-2">
              <tr>
                <th className="px-6 py-3 font-medium text-text-muted">User ID</th>
                <th className="px-6 py-3 font-medium text-text-muted">Email</th>
                <th className="px-6 py-3 font-medium text-text-muted">Status</th>
                <th className="px-6 py-3 font-medium text-text-muted">Role</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-secondary">
              {users.map((user) => (
                <tr key={user.id} className="hover:bg-white/5 transition-colors">
                  <td className="px-6 py-4 font-mono text-xs text-text-muted">{user.id}</td>
                  <td className="px-6 py-4 font-medium text-text-primary">{user.email}</td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 text-[10px] font-semibold rounded-full uppercase tracking-wider ${user.is_active ? 'bg-success/20 text-success border border-success/30' : 'bg-danger/20 text-danger border border-danger/30'}`}>
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <select
                      value={user.role_tier}
                      onChange={(e) => handleRoleChange(user.id, e.target.value)}
                      disabled={user.role_tier === 'admin'} // Protect admin role from self-demotion
                      className="bg-background-panel-2 border border-border-secondary rounded-md px-3 py-1.5 text-xs font-semibold focus:outline-none focus:border-primary-blue transition-colors disabled:opacity-50"
                    >
                      <option value="client">Client</option>
                      <option value="operator">Operator</option>
                      <option value="risk_manager">Risk Manager</option>
                      {user.role_tier === 'admin' && <option value="admin">Admin</option>}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
