'use client';

import React, { useState, useEffect } from 'react';
import { supabase } from '../../lib/supabase';
import { AuditLog } from '../../types';
import { 
  History, 
  User, 
  ArrowRight, 
  PlusCircle, 
  AlertCircle, 
  RefreshCw,
  Clock
} from 'lucide-react';
import { format } from 'date-fns';

export default function AuditLogTable() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchLogs();
  }, []);

  async function fetchLogs() {
    try {
      setLoading(true);
      const { data, error } = await (supabase.from('discount_audit_logs') as any)
        .select('*')
        .order('created_at', { ascending: false })
        .limit(50);

      if (error) throw error;
      setLogs(data || []);
    } catch (e: any) {
      console.error('Error fetching audit logs:', e.message);
    } finally {
      setLoading(false);
    }
  }

  const getActionBadge = (action: string) => {
    const styles: Record<string, string> = {
      CREATE: 'bg-blue-100 text-blue-700',
      UPDATE: 'bg-amber-100 text-amber-700',
      APPROVE: 'bg-green-100 text-green-700',
      DISABLE: 'bg-red-100 text-red-700',
      DELETE: 'bg-gray-100 text-gray-700',
    };
    return (
      <span className={`text-[10px] font-black uppercase tracking-widest px-2 py-0.5 rounded-full ${styles[action] || 'bg-gray-100'}`}>
        {action}
      </span>
    );
  };

  if (loading) return <div className="p-8 text-center text-gray-500 animate-pulse font-bold uppercase tracking-widest text-xs">Loading Audit Logs...</div>;

  return (
    <div className="bg-white rounded-2xl border border-border overflow-hidden card-shadow">
      <div className="p-6 border-b border-gray-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
           <History className="h-5 w-5 text-gray-400" />
           <h3 className="font-bold text-gray-900 tracking-tight">Recent Activity</h3>
        </div>
        <button 
          onClick={fetchLogs}
          className="p-2 text-gray-400 hover:text-primary transition-all rounded-lg"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>
      
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead className="bg-gray-50 border-b border-gray-100">
            <tr>
              <th className="px-6 py-3 text-[10px] font-black uppercase tracking-widest text-gray-400">Timestamp</th>
              <th className="px-6 py-3 text-[10px] font-black uppercase tracking-widest text-gray-400">Action</th>
              <th className="px-6 py-3 text-[10px] font-black uppercase tracking-widest text-gray-400">Actor</th>
              <th className="px-6 py-3 text-[10px] font-black uppercase tracking-widest text-gray-400">Change Description</th>
              <th className="px-6 py-3 text-[10px] font-black uppercase tracking-widest text-gray-400">Reason</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {logs.map((log) => (
              <tr key={log.id} className="hover:bg-gray-50/50 transition-colors group">
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center gap-2 text-xs font-bold text-gray-500">
                    <Clock className="h-3.5 w-3.5 text-gray-300" />
                    {format(new Date(log.created_at), 'MMM d, HH:mm:ss')}
                  </div>
                </td>
                <td className="px-6 py-4">
                  {getActionBadge(log.action_type)}
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    <div className="h-6 w-6 rounded-full bg-gray-100 flex items-center justify-center">
                      <User className="h-3 w-3 text-gray-400" />
                    </div>
                    <span className="text-xs font-bold text-gray-700">{log.actor_type || 'System'}</span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    {log.before_payload_json && (
                       <span className="text-xs font-black text-gray-400 line-through">
                          {log.before_payload_json.discount_percent}%
                       </span>
                    )}
                    <ArrowRight className="h-3 w-3 text-gray-300" />
                    <span className="text-sm font-black text-gray-900 bg-gray-100 px-2 py-0.5 rounded">
                       {log.after_payload_json?.discount_percent || '0'}%
                    </span>
                  </div>
                </td>
                <td className="px-6 py-4 max-w-xs">
                  <p className="text-xs text-gray-500 italic truncate" title={log.change_reason || undefined}>
                    {log.change_reason || 'No justification provided'}
                  </p>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {logs.length === 0 && (
          <div className="p-12 text-center">
            <AlertCircle className="h-12 w-12 text-gray-100 mx-auto mb-4" />
            <p className="text-gray-400 font-bold uppercase tracking-widest text-xs">No audit logs recorded yet</p>
          </div>
        )}
      </div>
      
      <div className="p-4 bg-gray-50 border-t border-gray-100">
        <p className="text-[10px] text-gray-400 font-bold text-center uppercase tracking-widest">Showing last 50 transactions</p>
      </div>
    </div>
  );
}
