'use client';

import { useEffect, useState } from 'react';
import { api, Exchange, ExchangeStats, TimeseriesPoint } from '@/lib/api';
import Header from '@/components/layout/Header';
import SummaryCards from '@/components/dashboard/SummaryCards';
import TimeSeriesChart from '@/components/dashboard/TimeSeriesChart';
import UsersTable from '@/components/dashboard/UsersTable';
import DateRangeFilter from '@/components/dashboard/DateRangeFilter';
import { useUsers } from '@/hooks/useUsers';
import type { RangePreset } from '@/lib/dateRange';

const EMPTY_STATS: ExchangeStats = {
  totalDeposit: 0,
  totalVolume: 0,
  totalCommission: 0,
  totalUsers: 0,
  activeUsers: 0,
};

export default function ExchangePage({ params }: { params: { exchangeId: string } }) {
  const { exchangeId } = params;

  const [exchange, setExchange] = useState<Exchange | null>(null);
  const [stats, setStats] = useState<ExchangeStats>(EMPTY_STATS);
  const [timeseries, setTimeseries] = useState<TimeseriesPoint[]>([]);
  const [statsLoading, setStatsLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [preset, setPreset] = useState<RangePreset>('all');
  const [from, setFrom] = useState<string | undefined>();
  const [to, setTo] = useState<string | undefined>();

  const qFrom = preset === 'all' ? undefined : from;
  const qTo = preset === 'all' ? undefined : to;

  const { data: users, total, page, totalPages, loading: usersLoading, params: userParams, updateParams } =
    useUsers({
      exchange: exchangeId,
      page: '1',
      limit: '20',
    });

  useEffect(() => {
    updateParams({
      exchange: exchangeId,
      from: qFrom ?? '',
      to: qTo ?? '',
      page: '1',
    });
  }, [exchangeId, qFrom, qTo, updateParams]);

  useEffect(() => {
    setStatsLoading(true);
    Promise.all([
      api.getExchanges(),
      api.getExchangeStats(exchangeId, qFrom, qTo),
      api.getTimeseries(exchangeId, 'totalCommission', 'day', qFrom, qTo),
    ])
      .then(([exchanges, s, ts]) => {
        setExchange(exchanges.find((e) => e.id === exchangeId) ?? null);
        setStats(s);
        setTimeseries(ts);
      })
      .finally(() => setStatsLoading(false));
  }, [exchangeId, qFrom, qTo]);

  async function handleSync() {
    setSyncing(true);
    try {
      await api.triggerSync(exchangeId);
      const [s, ts] = await Promise.all([
        api.getExchangeStats(exchangeId, qFrom, qTo),
        api.getTimeseries(exchangeId, 'totalCommission', 'day', qFrom, qTo),
      ]);
      setStats(s);
      setTimeseries(ts);
      updateParams({ page: '1' });
    } finally {
      setSyncing(false);
    }
  }

  return (
    <>
      <Header
        title={exchange?.name ?? exchangeId}
        subtitle={`Referral activity for ${exchange?.name ?? exchangeId}`}
        onSync={handleSync}
        syncing={syncing}
      />
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
              Thống kê và biểu đồ theo {qFrom} → {qTo}. Bảng users lọc theo ngày đăng ký trong khoảng này.
            </p>
          )}
        </div>

        <SummaryCards stats={stats} loading={statsLoading} />

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2">
            <TimeSeriesChart
              data={timeseries}
              metric="totalCommission"
              color={exchange?.color}
              loading={statsLoading}
            />
          </div>

          {/* Quick stats panel */}
          <div className="bg-card border border-border rounded-xl p-5 space-y-4">
            <h3 className="text-sm font-semibold text-foreground">Quick Stats</h3>
            <div className="space-y-3">
              {[
                { label: 'Active Users', value: `${stats.activeUsers} / ${stats.totalUsers}` },
                {
                  label: 'Avg Deposit / User',
                  value:
                    stats.totalUsers > 0
                      ? `$${(stats.totalDeposit / stats.totalUsers).toFixed(2)}`
                      : '$0.00',
                },
                {
                  label: 'Avg Commission / User',
                  value:
                    stats.totalUsers > 0
                      ? `$${(stats.totalCommission / stats.totalUsers).toFixed(2)}`
                      : '$0.00',
                },
                {
                  label: 'Commission / Volume',
                  value:
                    stats.totalVolume > 0
                      ? `${((stats.totalCommission / stats.totalVolume) * 100).toFixed(3)}%`
                      : '0.000%',
                },
              ].map(({ label, value }) => (
                <div key={label} className="flex items-center justify-between">
                  <span className="text-xs text-muted-foreground">{label}</span>
                  <span className="text-sm font-semibold text-foreground">{value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <UsersTable
          users={users}
          total={total}
          page={page}
          totalPages={totalPages}
          loading={usersLoading}
          onParamsChange={updateParams}
          currentParams={userParams}
        />
      </div>
    </>
  );
}
