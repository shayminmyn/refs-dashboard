'use client';

import { CalendarRange } from 'lucide-react';
import type { RangePreset } from '@/lib/dateRange';
import { computePresetRange, formatYMD } from '@/lib/dateRange';

export interface DateRangeFilterProps {
  preset: RangePreset;
  from?: string;
  to?: string;
  onChange: (next: { preset: RangePreset; from?: string; to?: string }) => void;
}

const PRESETS: { id: Exclude<RangePreset, 'custom'>; label: string }[] = [
  { id: 'all', label: 'All time' },
  { id: '7d', label: '7 days' },
  { id: 'week', label: 'This week' },
  { id: '30d', label: '30 days' },
  { id: 'month', label: 'This month' },
];

export default function DateRangeFilter({ preset, from, to, onChange }: DateRangeFilterProps) {
  function applyPreset(id: Exclude<RangePreset, 'custom'>) {
    const r = computePresetRange(id);
    onChange({ preset: id, ...r });
  }

  function applyCustom(nextFrom: string, nextTo: string) {
    onChange({ preset: 'custom', from: nextFrom, to: nextTo });
  }

  const today = formatYMD(new Date());

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end">
      <div className="flex items-center gap-2 text-muted-foreground shrink-0">
        <CalendarRange className="w-4 h-4" />
        <span className="text-xs font-medium uppercase tracking-wide">Date range</span>
      </div>

      <div className="flex flex-wrap gap-2">
        {PRESETS.map(({ id, label }) => (
          <button
            key={id}
            type="button"
            onClick={() => applyPreset(id)}
            className={`px-3 py-1.5 text-xs font-medium rounded-lg border transition ${
              preset === id
                ? 'bg-primary text-primary-foreground border-primary'
                : 'bg-secondary/80 text-muted-foreground border-border hover:text-foreground hover:border-border'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <span>From</span>
          <input
            type="date"
            max={to ?? today}
            value={from ?? ''}
            onChange={(e) => {
              const nf = e.target.value;
              applyCustom(nf, to ?? nf);
            }}
            className="rounded-md border border-border bg-background px-2 py-1 text-xs text-foreground"
          />
        </label>
        <label className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <span>To</span>
          <input
            type="date"
            min={from}
            max={today}
            value={to ?? ''}
            onChange={(e) => {
              const nt = e.target.value;
              applyCustom(from ?? nt, nt);
            }}
            className="rounded-md border border-border bg-background px-2 py-1 text-xs text-foreground"
          />
        </label>
      </div>
    </div>
  );
}
