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
      
      <div className="card shadow-lg p-0 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="nexa-table">
            <thead>
              <tr>
                <th>User ID</th>
                <th>Email</th>
                <th>Status</th>
                <th>Role</th>
              </tr>
            </thead>
            <tbody>
              {users.map((user) => (
                <tr key={user.id}>
                  <td className="font-mono">{user.id}</td>
                  <td className="font-sans font-semibold text-text-primary">{user.email}</td>
                  <td>
                    <span className={`tag ${user.is_active ? 'teal' : 'red'}`}>
                      {user.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td>
                    <select
                      value={user.role_tier}
                      onChange={(e) => handleRoleChange(user.id, e.target.value)}
                      disabled={user.role_tier === 'admin'} // Protect admin role from self-demotion
                      className="w-full border border-border-default rounded-lg px-3 py-2 font-sans text-[13px] bg-background-base focus:outline-none focus:border-primary-gold transition-colors disabled:opacity-50"
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
