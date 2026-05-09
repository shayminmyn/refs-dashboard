'use client';

import { DollarSign, TrendingUp, Users, Wallet, ArrowUpRight } from 'lucide-react';
import { formatCurrency, formatNumber } from '@/lib/utils';
import { ExchangeStats } from '@/lib/api';

interface SummaryCardsProps {
  stats: ExchangeStats;
  loading?: boolean;
}

const cards = [
  {
    key: 'totalUsers' as const,
    label: 'Total Referrals',
    icon: Users,
    color: 'text-blue-400',
    bg: 'bg-blue-400/10',
    format: formatNumber,
  },
  {
    key: 'totalDeposit' as const,
    label: 'Total Deposits',
    icon: Wallet,
    color: 'text-emerald-400',
    bg: 'bg-emerald-400/10',
    format: formatCurrency,
  },
  {
    key: 'totalVolume' as const,
    label: 'Trading Volume',
    icon: TrendingUp,
    color: 'text-violet-400',
    bg: 'bg-violet-400/10',
    format: formatCurrency,
  },
  {
    key: 'totalCommission' as const,
    label: 'Commission Earned',
    icon: DollarSign,
    color: 'text-amber-400',
    bg: 'bg-amber-400/10',
    format: formatCurrency,
  },
];

export default function SummaryCards({ stats, loading }: SummaryCardsProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
      {cards.map(({ key, label, icon: Icon, color, bg, format }) => (
        <div key={key} className="bg-card border border-border rounded-xl p-5 hover:border-border/80 transition">
          <div className="flex items-start justify-between mb-4">
            <div className={`w-10 h-10 ${bg} rounded-lg flex items-center justify-center`}>
              <Icon className={`w-5 h-5 ${color}`} />
            </div>
            <ArrowUpRight className="w-4 h-4 text-muted-foreground" />
          </div>
          <div>
            <p className="text-sm text-muted-foreground mb-1">{label}</p>
            {loading ? (
              <div className="h-7 w-32 bg-secondary animate-pulse rounded" />
            ) : (
              <p className="text-2xl font-bold text-foreground">
                {format(stats[key])}
              </p>
            )}
            {key === 'totalUsers' && !loading && (
              <p className="text-xs text-muted-foreground mt-1">
                {formatNumber(stats.activeUsers)} active
              </p>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
