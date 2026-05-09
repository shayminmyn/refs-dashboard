'use client';

import { useEffect, useState } from 'react';
import { api, SyncLog, Exchange } from '@/lib/api';
import Header from '@/components/layout/Header';
import { formatDate } from '@/lib/utils';
import { CheckCircle2, XCircle, Loader2, RefreshCw } from 'lucide-react';

const STATUS_ICONS: Record<string, React.ReactNode> = {
  success: <CheckCircle2 className="w-4 h-4 text-emerald-400" />,
  failed: <XCircle className="w-4 h-4 text-destructive" />,
  running: <Loader2 className="w-4 h-4 text-blue-400 animate-spin" />,
};

export default function SyncLogsPage() {
  const [logs, setLogs] = useState<SyncLog[]>([]);
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState<string | null>(null);

  async function loadLogs() {
    const [l, ex] = await Promise.all([api.getSyncLogs(), api.getExchanges()]);
    setLogs(l);
    setExchanges(ex);
    setLoading(false);
  }

  useEffect(() => {
    loadLogs();
  }, []);

  async function triggerSync(exchangeId: string) {
    setSyncing(exchangeId);
    try {
      await api.triggerSync(exchangeId);
      await loadLogs();
    } finally {
      setSyncing(null);
    }
  }

  return (
    <>
      <Header title="Sync Logs" subtitle="Scheduled data synchronization history" />
      <div className="flex-1 p-6 space-y-6">
        {/* Manual sync buttons */}
        <div className="bg-card border border-border rounded-xl p-5">
          <h3 className="text-sm font-semibold text-foreground mb-4">Manual Sync</h3>
          <div className="flex flex-wrap gap-3">
            {exchanges.map((ex) => (
              <button
                key={ex.id}
                onClick={() => triggerSync(ex.id)}
                disabled={syncing === ex.id}
                className="flex items-center gap-2 px-4 py-2 bg-secondary hover:bg-accent border border-border rounded-lg text-sm font-medium text-foreground transition disabled:opacity-50"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${syncing === ex.id ? 'animate-spin' : ''}`} />
                Sync {ex.name}
              </button>
            ))}
          </div>
        </div>

        {/* Logs table */}
        <div className="bg-card border border-border rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-border flex items-center justify-between">
            <h3 className="text-sm font-semibold text-foreground">Recent Sync Logs</h3>
            <button
              onClick={loadLogs}
              className="text-xs text-muted-foreground hover:text-foreground transition"
            >
              Refresh
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  {['Exchange', 'Started', 'Finished', 'Status', 'Records', 'Error'].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {loading ? (
                  Array.from({ length: 5 }).map((_, i) => (
                    <tr key={i}>
                      {Array.from({ length: 6 }).map((_, j) => (
                        <td key={j} className="px-4 py-3">
                          <div className="h-4 bg-secondary animate-pulse rounded" />
                        </td>
                      ))}
                    </tr>
                  ))
                ) : logs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-12 text-center text-muted-foreground">
                      No sync logs yet
                    </td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr key={log._id} className="hover:bg-accent/50 transition-colors">
                      <td className="px-4 py-3 font-medium text-foreground capitalize">{log.exchangeId}</td>
                      <td className="px-4 py-3 text-muted-foreground text-xs">{formatDate(log.startedAt)}</td>
                      <td className="px-4 py-3 text-muted-foreground text-xs">
                        {log.finishedAt ? formatDate(log.finishedAt) : '—'}
                      </td>
                      <td className="px-4 py-3">
                        <span className="flex items-center gap-1.5">
                          {STATUS_ICONS[log.status]}
                          <span className="capitalize text-xs">{log.status}</span>
                        </span>
                      </td>
                      <td className="px-4 py-3 text-foreground">{log.recordsUpserted}</td>
                      <td className="px-4 py-3 text-destructive text-xs font-mono max-w-xs truncate">
                        {log.error ?? '—'}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </>
  );
}
