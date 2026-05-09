'use client';

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { TimeseriesPoint } from '@/lib/api';
import { formatCurrency } from '@/lib/utils';

interface TimeSeriesChartProps {
  data: TimeseriesPoint[];
  metric: string;
  color?: string;
  loading?: boolean;
}

const metricLabels: Record<string, string> = {
  totalCommission: 'Commission',
  totalDeposit: 'Deposits',
  totalVolume: 'Volume',
};

export default function TimeSeriesChart({ data, metric, color = '#6366f1', loading }: TimeSeriesChartProps) {
  if (loading) {
    return (
      <div className="bg-card border border-border rounded-xl p-5">
        <div className="h-4 w-40 bg-secondary animate-pulse rounded mb-6" />
        <div className="h-48 bg-secondary animate-pulse rounded" />
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-xl p-5">
      <h3 className="text-sm font-semibold text-foreground mb-4">
        {metricLabels[metric] ?? metric} Over Time
      </h3>
      {data.length === 0 ? (
        <div className="h-48 flex items-center justify-center text-muted-foreground text-sm">
          No data available
        </div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={data} margin={{ top: 5, right: 5, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="colorGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor={color} stopOpacity={0.25} />
                <stop offset="95%" stopColor={color} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis
              dataKey="date"
              tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `$${(v as number).toFixed(0)}`}
            />
            <Tooltip
              contentStyle={{
                background: 'hsl(var(--card))',
                border: '1px solid hsl(var(--border))',
                borderRadius: '8px',
                fontSize: '12px',
                color: 'hsl(var(--foreground))',
              }}
              formatter={(v: number) => [formatCurrency(v), metricLabels[metric]]}
            />
            <Area
              type="monotone"
              dataKey="value"
              stroke={color}
              strokeWidth={2}
              fill="url(#colorGrad)"
            />
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
