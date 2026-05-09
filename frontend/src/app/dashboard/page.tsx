'use client';

import { useEffect, useState } from 'react';
import { api, OverviewStats, TimeseriesPoint } from '@/lib/api';
import Header from '@/components/layout/Header';
import SummaryCards from '@/components/dashboard/SummaryCards';
import TimeSeriesChart from '@/components/dashboard/TimeSeriesChart';
import ExchangeBreakdown from '@/components/dashboard/ExchangeBreakdown';
import DateRangeFilter from '@/components/dashboard/DateRangeFilter';
import type { RangePreset } from '@/lib/dateRange';

const EMPTY_STATS: OverviewStats = {
  totals: { totalDeposit: 0, totalVolume: 0, totalCommission: 0, totalUsers: 0, activeUsers: 0 },
  byExchange: [],
};

export default function DashboardPage() {
  const [stats, setStats] = useState<OverviewStats>(EMPTY_STATS);
  const [timeseries, setTimeseries] = useState<TimeseriesPoint[]>([]);
  const [metric, setMetric] = useState('totalCommission');
  const [loading, setLoading] = useState(true);
  const [preset, setPreset] = useState<RangePreset>('all');
  const [from, setFrom] = useState<string | undefined>();
  const [to, setTo] = useState<string | undefined>();

  const qFrom = preset === 'all' ? undefined : from;
  const qTo = preset === 'all' ? undefined : to;

  useEffect(() => {
    setLoading(true);
    Promise.all([
      api.getOverviewStats(qFrom, qTo),
      api.getTimeseries('all', metric, 'day', qFrom, qTo),
    ])
      .then(([s, ts]) => {
        setStats(s);
        setTimeseries(ts);
      })
      .finally(() => setLoading(false));
  }, [metric, qFrom, qTo]);

  return (
    <>
      <Header title="Overview" subtitle="All exchanges combined" />
      <div className="flex-1 p-6 space-y-6">
        <div className="bg-card border border-border rounded-xl p-4 space-y-3">
          <DateRangeFilter
            preset={preset}
            from={from}
            to={to}
            onChange={(next) => {
              setPreset(next.preset);
              setFrom(next.from);
              setTo(next.to);
            }}
          />
          {preset !== 'all' && qFrom && qTo && (
            <p className="text-xs text-muted-foreground">
              KPIs và biểu đồ theo khoảng {qFrom} → {qTo}. Deposit có thể là 0 khi chỉ có dữ liệu hoa hồng theo ngày.
            </p>
          )}
        </div>

        <SummaryCards stats={stats.totals} loading={loading} />

        {/* Exchange breakdown table */}
        {!loading && stats.byExchange.length > 0 && (
          <div className="bg-card border border-border rounded-xl overflow-hidden">
            <div className="px-5 py-4 border-b border-border">
              <h3 className="text-sm font-semibold text-foreground">By Exchange</h3>
            </div>
            <div className="divide-y divide-border">
              {stats.byExchange.map((ex) => (
                <div key={ex.exchangeId} className="px-5 py-3 flex items-center gap-4">
                  <span
                    className="w-2.5 h-2.5 rounded-full shrink-0"
                    style={{ backgroundColor: ex.color }}
                  />
                  <span className="text-sm font-medium text-foreground w-24">{ex.exchangeName}</span>
                  <div className="flex-1 grid grid-cols-4 gap-4 text-sm">
                    <div>
                      <p className="text-xs text-muted-foreground">Users</p>
                      <p className="font-medium text-foreground">{ex.totalUsers}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Deposits</p>
                      <p className="font-medium text-foreground">${ex.totalDeposit.toFixed(2)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Volume</p>
                      <p className="font-medium text-foreground">${ex.totalVolume.toFixed(2)}</p>
                    </div>
                    <div>
                      <p className="text-xs text-muted-foreground">Commission</p>
                      <p className="font-semibold text-amber-400">${ex.totalCommission.toFixed(2)}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2">
            <div className="flex items-center gap-2 mb-3">
              <span className="text-xs font-medium text-muted-foreground">Metric:</span>
              {['totalCommission', 'totalDeposit', 'totalVolume'].map((m) => (
                <button
                  key={m}
                  onClick={() => setMetric(m)}
                  className={`px-3 py-1 text-xs font-medium rounded-full transition ${
                    metric === m
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-secondary text-muted-foreground hover:text-foreground'
                  }`}
                >
                  {m === 'totalCommission' ? 'Commission' : m === 'totalDeposit' ? 'Deposits' : 'Volume'}
                </button>
              ))}
            </div>
            <TimeSeriesChart data={timeseries} metric={metric} loading={loading} />
          </div>
          <ExchangeBreakdown stats={stats} loading={loading} filtered={preset !== 'all'} />
        </div>
      </div>
    </>
  );
}
