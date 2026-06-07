'use client';

import { PageHeader } from '@/components/ui/PageHeader';
import { UserCog } from 'lucide-react';

export default function UserManagementPage() {
  return (
    <div className="space-y-8">
      <PageHeader title="User Management" subtitle="View, create, and manage user roles and permissions." />
      <div className="flex flex-col items-center justify-center h-64 bg-background-panel-1 border-2 border-dashed border-border-secondary rounded-lg">
        <UserCog className="w-12 h-12 text-text-muted mb-4" />
        <h3 className="text-lg font-semibold text-text-primary">Admin Workspace Under Construction</h3>
        <p className="text-sm text-text-muted">This area will contain tools for user and permission management.</p>
      </div>
    </div>
  );
}
