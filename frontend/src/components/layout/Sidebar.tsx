'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { TrendingUp, LayoutDashboard, LineChart, LogOut, RefreshCw, Users } from 'lucide-react';
import { cn } from '@/lib/utils';
import { clearToken } from '@/lib/auth';
import { Exchange } from '@/lib/api';

interface SidebarProps {
  exchanges: Exchange[];
}

export default function Sidebar({ exchanges }: SidebarProps) {
  const pathname = usePathname();
  const router = useRouter();

  function handleLogout() {
    clearToken();
    router.push('/login');
  }

  return (
    <aside className="w-60 shrink-0 h-screen sticky top-0 bg-card border-r border-border flex flex-col">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-border">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 bg-primary/10 rounded-lg flex items-center justify-center">
            <TrendingUp className="w-4 h-4 text-primary" />
          </div>
          <div>
            <span className="text-sm font-bold text-foreground">Refs Dashboard</span>
            <p className="text-xs text-muted-foreground">Partner Panel</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto py-4 px-3 space-y-1">
        {/* Overview */}
        <Link
          href="/dashboard"
          className={cn(
            'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
            pathname === '/dashboard'
              ? 'bg-primary/10 text-primary'
              : 'text-muted-foreground hover:text-foreground hover:bg-accent'
          )}
        >
          <LayoutDashboard className="w-4 h-4" />
          Overview
        </Link>

        {/* Community — ngay dưới Overview */}
        <Link
          href="/dashboard/members"
          className={cn(
            'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
            pathname.startsWith('/dashboard/members')
              ? 'bg-primary/10 text-primary'
              : 'text-muted-foreground hover:text-foreground hover:bg-accent'
          )}
        >
          <Users className="w-4 h-4" />
          Community
        </Link>

        <Link
          href="/dashboard/signals"
          className={cn(
            'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
            pathname.startsWith('/dashboard/signals')
              ? 'bg-primary/10 text-primary'
              : 'text-muted-foreground hover:text-foreground hover:bg-accent'
          )}
        >
          <LineChart className="w-4 h-4" />
          Signals
        </Link>

        {/* Exchange divider */}
        <div className="pt-3 pb-1 px-3">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            Exchanges
          </p>
        </div>

        {/* Per-exchange links */}
        {exchanges.map((exchange) => (
          <Link
            key={exchange.id}
            href={`/dashboard/${exchange.id}`}
            className={cn(
              'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
              pathname === `/dashboard/${exchange.id}`
                ? 'bg-primary/10 text-primary'
                : 'text-muted-foreground hover:text-foreground hover:bg-accent'
            )}
          >
            <span
              className="w-2.5 h-2.5 rounded-full shrink-0"
              style={{ backgroundColor: exchange.color }}
            />
            {exchange.name}
          </Link>
        ))}
      </nav>

      {/* Footer */}
      <div className="p-3 border-t border-border space-y-1">
        <Link
          href="/dashboard/sync"
          className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:text-foreground hover:bg-accent transition-colors"
        >
          <RefreshCw className="w-4 h-4" />
          Sync Logs
        </Link>
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
        >
          <LogOut className="w-4 h-4" />
          Logout
        </button>
      </div>
    </aside>
  );
}
