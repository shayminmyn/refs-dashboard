/** YYYY-MM-DD theo local calendar (đủ cho filter dashboard). */
export function formatYMD(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

export function addDays(d: Date, n: number): Date {
  const x = new Date(d);
  x.setDate(x.getDate() + n);
  return x;
}

export function startOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), 1);
}

/** Thứ Hai của tuần chứa `d` (ISO week-ish, locale đơn giản). */
export function startOfWeekMonday(d: Date): Date {
  const x = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const day = x.getDay(); // 0 Sun .. 6 Sat
  const offset = day === 0 ? -6 : 1 - day;
  x.setDate(x.getDate() + offset);
  return x;
}

export type RangePreset = 'all' | '7d' | '30d' | 'week' | 'month' | 'custom';

export interface DateRangePayload {
  preset: RangePreset;
  from?: string;
  to?: string;
}

export function computePresetRange(preset: Exclude<RangePreset, 'custom'>): { from?: string; to?: string } {
  const today = new Date();
  const to = formatYMD(today);

  switch (preset) {
    case 'all':
      return {};
    case '7d':
      return { from: formatYMD(addDays(today, -6)), to };
    case '30d':
      return { from: formatYMD(addDays(today, -29)), to };
    case 'week':
      return { from: formatYMD(startOfWeekMonday(today)), to };
    case 'month':
      return { from: formatYMD(startOfMonth(today)), to };
    default:
      return {};
  }
}
