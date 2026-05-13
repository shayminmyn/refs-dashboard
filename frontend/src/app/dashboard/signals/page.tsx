'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import Header from '@/components/layout/Header';
import DateRangeFilter from '@/components/dashboard/DateRangeFilter';
import type { RangePreset } from '@/lib/dateRange';
import {
  api,
  SignalRow,
  SignalStats,
  SignalsFiltersResponse,
} from '@/lib/api';

const EMPTY_STATS: SignalStats = {
  totalSignals: 0,
  closedTrades: 0,
  wins: 0,
  losses: 0,
  breakeven: 0,
  unsettledR: 0,
  winRate: null,
  totalR: 0,
  avgR: null,
  totalReturnPct: 0,
  totalTargetRrPct: 0,
  tradesWithRiskPct: 0,
  avgReturnPct: null,
};

function fmtDt(iso: string | null | undefined): string {
  if (!iso) return '—';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' });
}

export default function SignalsPage() {
  // Mặc định all time: preset "month/week" dễ ra 0 khi dữ liệu lịch sử nằm ngoài khoảng hiện tại.
  const [preset, setPreset] = useState<RangePreset>('all');
  const [from, setFrom] = useState<string | undefined>(undefined);
  const [to, setTo] = useState<string | undefined>(undefined);

  const [symbol, setSymbol] = useState('');
  const [strategy, setStrategy] = useState('');
  const [timeframe, setTimeframe] = useState('');
  const [status, setStatus] = useState('');

  const [filters, setFilters] = useState<SignalsFiltersResponse>({
    symbols: [],
    strategies: [],
    timeframes: [],
    statuses: [],
  });

  const [stats, setStats] = useState<SignalStats>(EMPTY_STATS);
  const [rows, setRows] = useState<SignalRow[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [total, setTotal] = useState(0);
  const limit = 25;

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const qFrom = preset === 'all' ? undefined : from;
  const qTo = preset === 'all' ? undefined : to;

  const filterParams = useMemo(
    () => ({
      from: qFrom,
      to: qTo,
      symbol: symbol || undefined,
      strategy: strategy || undefined,
      timeframe: timeframe || undefined,
      status: status || undefined,
    }),
    [qFrom, qTo, symbol, strategy, timeframe, status],
  );

  const fpSig = useMemo(
    () =>
      [
        filterParams.from ?? '',
        filterParams.to ?? '',
        filterParams.symbol ?? '',
        filterParams.strategy ?? '',
        filterParams.timeframe ?? '',
        filterParams.status ?? '',
      ].join('|'),
    [
      filterParams.from,
      filterParams.to,
      filterParams.symbol,
      filterParams.strategy,
      filterParams.timeframe,
      filterParams.status,
    ],
  );

  const prevFpSigRef = useRef(fpSig);

  useEffect(() => {
    const sigChanged = prevFpSigRef.current !== fpSig;
    prevFpSigRef.current = fpSig;

    if (sigChanged && page !== 1) {
      setPage(1);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    (async () => {
      try {
        const [f, s, list] = await Promise.all([
          api.getSignalFilters({
            from: filterParams.from,
            to: filterParams.to,
          }),
          api.getSignalStats(filterParams),
          api.getSignals({
            ...filterParams,
            page: String(page),
            limit: String(limit),
            sortDir: 'desc',
          }),
        ]);
        if (cancelled) return;
        setFilters(f);
        setStats(s);
        setRows(list.data);
        setTotalPages(list.pagination.totalPages);
        setTotal(list.pagination.total);
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : 'Error');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [fpSig, page, limit, filterParams]);

  return (
    <>
      <Header
        title="Signal performance"
        subtitle="Theo dõi lệnh từ hệ thống (MongoDB trading.signals)"
      />
      <div className="flex-1 p-6 space-y-6">
        <div className="bg-card border border-border rounded-xl p-4 space-y-4">
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

          <div className="flex flex-wrap gap-3 items-end">
            <FilterSelect
              label="Symbol"
              value={symbol}
              onChange={setSymbol}
              options={filters.symbols}
            />
            <FilterSelect
              label="Strategy"
              value={strategy}
              onChange={setStrategy}
              options={filters.strategies}
            />
            <FilterSelect
              label="Timeframe"
              value={timeframe}
              onChange={setTimeframe}
              options={filters.timeframes}
            />
            <FilterSelect
              label="Status"
              value={status}
              onChange={setStatus}
              options={filters.statuses}
            />
          </div>

          {preset !== 'all' && qFrom && qTo && (
            <p className="text-xs text-muted-foreground">
              Thống kê và bảng theo ngày đóng lệnh (UTC): {qFrom} → {qTo}. Cấu hình field ngày qua{' '}
              <code className="text-[11px]">SIGNAL_FILTER_DATE_FIELDS</code> trên backend.
            </p>
          )}
        </div>

        {error && (
          <div className="rounded-lg border border-destructive/50 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        )}

        <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
          <StatCard label="Signals (filtered)" value={loading ? '…' : String(stats.totalSignals)} />
          <StatCard
            label="Win rate"
            value={
              loading
                ? '…'
                : stats.winRate === null
                  ? '—'
                  : `${(stats.winRate * 100).toFixed(1)}%`
            }
            hint={`${stats.wins}W / ${stats.losses}L`}
          />
          <StatCard
            label="Total R"
            value={loading ? '…' : stats.totalR.toFixed(2)}
            hint={`Avg ${stats.avgR === null ? '—' : stats.avgR.toFixed(2)} (closed)`}
          />
          <StatCard
            label="Σ Return % (risk×R)"
            value={
              loading
                ? '…'
                : `${stats.totalReturnPct.toFixed(2)}%`
            }
            hint={
              stats.tradesWithRiskPct > 0
                ? `Avg/trade ${stats.avgReturnPct === null ? '—' : `${stats.avgReturnPct.toFixed(2)}%`} · ${stats.tradesWithRiskPct} có risk%`
                : 'Thiếu risk_percent trên docs'
            }
          />
          <StatCard
            label="Σ Target % (risk×RR)"
            value={loading ? '…' : `${stats.totalTargetRrPct.toFixed(2)}%`}
            hint="Stack lý thuyết nếu full RR"
          />
          <StatCard
            label="Closed / unsettled R"
            value={loading ? '…' : String(stats.closedTrades)}
            hint={`${stats.unsettledR} chưa gán R`}
          />
        </div>

        <div className="bg-card border border-border rounded-xl overflow-hidden">
          <div className="px-5 py-4 border-b border-border flex flex-wrap items-center justify-between gap-3">
            <h3 className="text-sm font-semibold text-foreground">
              History{' '}
              <span className="font-normal text-muted-foreground">
                ({loading ? '…' : total} rows)
              </span>
            </h3>
            <div className="flex items-center gap-2 text-xs">
              <button
                type="button"
                disabled={page <= 1 || loading}
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                className="px-3 py-1.5 rounded-lg border border-border bg-secondary/80 disabled:opacity-40"
              >
                Prev
              </button>
              <span className="text-muted-foreground tabular-nums">
                {page} / {Math.max(totalPages, 1)}
              </span>
              <button
                type="button"
                disabled={page >= totalPages || loading || totalPages === 0}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1.5 rounded-lg border border-border bg-secondary/80 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="border-b border-border bg-muted/40 text-left text-muted-foreground">
                  <th className="px-4 py-3 font-medium whitespace-nowrap">Closed</th>
                  <th className="px-4 py-3 font-medium whitespace-nowrap">Symbol</th>
                  <th className="px-4 py-3 font-medium whitespace-nowrap">TF</th>
                  <th className="px-4 py-3 font-medium whitespace-nowrap">Strategy</th>
                  <th className="px-4 py-3 font-medium whitespace-nowrap">Status</th>
                  <th className="px-4 py-3 font-medium whitespace-nowrap">Type</th>
                  <th className="px-4 py-3 font-medium whitespace-nowrap">Exit</th>
                  <th className="px-4 py-3 font-medium whitespace-nowrap text-right">Risk %</th>
                  <th className="px-4 py-3 font-medium whitespace-nowrap text-right">RR</th>
                  <th className="px-4 py-3 font-medium whitespace-nowrap text-right">R</th>
                  <th className="px-4 py-3 font-medium min-w-[180px]">Signal key</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {loading && rows.length === 0 ? (
                  <tr>
                    <td colSpan={11} className="px-4 py-8 text-center text-muted-foreground">
                      Loading…
                    </td>
                  </tr>
                ) : rows.length === 0 ? (
                  <tr>
                    <td colSpan={11} className="px-4 py-8 text-center text-muted-foreground">
                      Không có dữ liệu trong khoảng và filter hiện tại.
                    </td>
                  </tr>
                ) : (
                  rows.map((r) => (
                    <tr key={r._id} className="hover:bg-accent/40">
                      <td className="px-4 py-2.5 whitespace-nowrap">{fmtDt(r.closedAt)}</td>
                      <td className="px-4 py-2.5 font-medium">{r.symbol ?? '—'}</td>
                      <td className="px-4 py-2.5">{r.timeframe ?? '—'}</td>
                      <td className="px-4 py-2.5 max-w-[140px] truncate" title={r.strategy ?? ''}>
                        {r.strategy ?? '—'}
                      </td>
                      <td className="px-4 py-2.5">{r.status ?? '—'}</td>
                      <td className="px-4 py-2.5 whitespace-nowrap">{r.orderType ?? '—'}</td>
                      <td className="px-4 py-2.5">{r.exitReason ?? '—'}</td>
                      <td className="px-4 py-2.5 text-right tabular-nums">
                        {r.riskPercent === null ? '—' : r.riskPercent.toFixed(2)}
                      </td>
                      <td className="px-4 py-2.5 text-right tabular-nums">
                        {r.rrRatio === null ? '—' : r.rrRatio.toFixed(2)}
                      </td>
                      <td
                        className={`px-4 py-2.5 text-right tabular-nums font-medium ${
                          r.realizedR === null
                            ? 'text-muted-foreground'
                            : r.realizedR > 0
                              ? 'text-emerald-400'
                              : r.realizedR < 0
                                ? 'text-red-400'
                                : 'text-foreground'
                        }`}
                      >
                        {r.realizedR === null ? '—' : r.realizedR.toFixed(2)}
                      </td>
                      <td className="px-4 py-2.5 text-muted-foreground max-w-[220px] truncate" title={r.signalKey ?? ''}>
                        {r.signalKey ?? '—'}
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

function StatCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <div className="rounded-xl border border-border bg-card px-4 py-3">
      <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="text-lg font-semibold text-foreground mt-1 tabular-nums">{value}</p>
      {hint && <p className="text-[11px] text-muted-foreground mt-0.5">{hint}</p>}
    </div>
  );
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: string[];
}) {
  return (
    <label className="flex flex-col gap-1 text-xs text-muted-foreground min-w-[130px]">
      <span>{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="rounded-md border border-border bg-background px-2 py-1.5 text-xs text-foreground"
      >
        <option value="">All</option>
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </label>
  );
}
