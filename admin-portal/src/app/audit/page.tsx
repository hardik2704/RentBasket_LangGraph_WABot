import React from 'react';
import AuditLogTable from '@/components/dashboard/AuditLogTable';
import { History } from 'lucide-react';

export default function AuditLogPage() {
  return (
    <div className="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="h-8 w-8 rounded bg-primary/10 flex items-center justify-center text-primary">
              <History className="h-5 w-5" />
            </div>
            <h2 className="text-2xl font-black text-gray-900 tracking-tight uppercase">Audit Trail</h2>
          </div>
          <p className="text-gray-500 font-medium max-w-xl">
             Every action is recorded. Filter through historical pricing changes to maintain accountability and verify campaign dates.
          </p>
        </div>
      </div>

      <AuditLogTable />
    </div>
  );
}
