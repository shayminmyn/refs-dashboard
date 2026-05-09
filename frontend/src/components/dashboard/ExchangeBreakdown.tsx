'use client';

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { OverviewStats } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';

interface ExchangeBreakdownProps {
  stats: OverviewStats;
  loading?: boolean;
  /** Đang lọc theo khoảng ngày (không phải all-time). */
  filtered?: boolean;
}

export default function ExchangeBreakdown({ stats, loading, filtered }: ExchangeBreakdownProps) {
  if (loading) {
    return (
      <div className="bg-card border border-border rounded-xl p-5">
        <div className="h-4 w-48 bg-secondary animate-pulse rounded mb-6" />
        <div className="h-48 bg-secondary animate-pulse rounded" />
      </div>
    );
  }

  const data = stats.byExchange.map((e) => ({
    name: e.exchangeName,
    value: e.totalCommission,
    color: e.color,
  }));

  return (
    <div className="bg-card border border-border rounded-xl p-5">
      <h3 className="text-sm font-semibold text-foreground mb-4">
        Commission by Exchange
        {filtered && (
          <span className="font-normal text-muted-foreground"> · selected period</span>
        )}
      </h3>
      {data.length === 0 || data.every((d) => d.value === 0) ? (
        <div className="h-48 flex items-center justify-center text-muted-foreground text-sm">
          No data available
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={55}
              outerRadius={80}
              paddingAngle={3}
              dataKey="value"
            >
              {data.map((entry, index) => (
                <Cell key={index} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip
              contentStyle={{
                background: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '8px',
                fontSize: '12px',
                color: 'hsl(var(--foreground))',
              }}
              formatter={(v: number) => [formatCurrency(v), 'Commission']}
            />
            <Legend
              iconSize={8}
              iconType="circle"
              wrapperStyle={{ fontSize: '12px', color: 'hsl(var(--muted-foreground))' }}
            />
          </PieChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
