'use client';

import { Bell, RefreshCw } from 'lucide-react';

interface HeaderProps {
  title: string;
  subtitle?: string;
  onSync?: () => void;
  syncing?: boolean;
}

export default function Header({ title, subtitle, onSync, syncing }: HeaderProps) {
  return (
    <header className="h-16 border-b border-border bg-card/50 backdrop-blur px-6 flex items-center justify-between sticky top-0 z-10">
      <div>
        <h1 className="text-base font-semibold text-foreground">{title}</h1>
        {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
      </div>

      <div className="flex items-center gap-2">
        {onSync && (
          <button
            onClick={onSync}
            disabled={syncing}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-secondary hover:bg-accent border border-border rounded-lg text-xs font-medium text-foreground transition disabled:opacity-50"
          >
            <RefreshCw className={`w-3 h-3 ${syncing ? 'animate-spin' : ''}`} />
            {syncing ? 'Syncing...' : 'Sync Now'}
          </button>
        )}
        <button className="w-8 h-8 flex items-center justify-center rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition">
          <Bell className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}
