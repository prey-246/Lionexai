import { Time } from 'lightweight-charts';

/**
 * Safely converts a value to a finite number, returning a fallback if conversion is not possible.
 */
export function toFiniteNumber(value: any, fallback: number = 0): number {
  const num = Number(value);
  return Number.isFinite(num) ? num : fallback;
}

/**
 * Formats a number as a currency string, returning a placeholder if the value is null/undefined.
 */
export function formatCurrency(value: number | null | undefined, placeholder: string = '$0.00'): string {
  if (value == null) return placeholder;
  return `$${toFiniteNumber(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

/**
 * Formats a number to a fixed number of decimal places, returning a placeholder if the value is null/undefined.
 */
export function formatFixed(value: number | null | undefined, digits: number = 2, placeholder: string = '0.00'): string {
  if (value == null) return placeholder;
  return toFiniteNumber(value).toFixed(digits);
}

/**
 * Safely converts a date string or number into a UNIX timestamp suitable for the charting library.
 */
export function toChartTimestamp(time: number | string | Date): Time {
  if (typeof time === 'number') {
    // If it's already a UNIX timestamp (seconds), use it. If it's ms, convert.
    return time > 10000000000 ? (time / 1000) as Time : time as Time;
  }
  const date = new Date(time);
  return (date.getTime() / 1000) as Time;
}

type EquityPoint = {
  timestamp?: string;
  time?: number;
  equity?: number;
  value?: number;
};

function equityPointMs(point: EquityPoint): number {
  if (point.timestamp) return new Date(point.timestamp).getTime();
  if (point.time != null) return point.time > 1_000_000_000_000 ? point.time : point.time * 1000;
  return 0;
}

function equityPointValue(point: EquityPoint): number {
  return toFiniteNumber(point.equity ?? point.value, 0);
}

/** Total and trailing 7-day return from an equity curve series. */
export function computeEquityReturns(data: EquityPoint[]): {
  totalReturnPct: number | null;
  weeklyReturnPct: number | null;
} {
  if (!data?.length) return { totalReturnPct: null, weeklyReturnPct: null };

  const sorted = [...data]
    .map((p) => ({ ms: equityPointMs(p), value: equityPointValue(p) }))
    .filter((p) => p.ms > 0 && p.value > 0)
    .sort((a, b) => a.ms - b.ms);

  if (sorted.length < 2) return { totalReturnPct: null, weeklyReturnPct: null };

  const first = sorted[0];
  const last = sorted[sorted.length - 1];
  const totalReturnPct = ((last.value - first.value) / first.value) * 100;

  const weekMs = 7 * 24 * 60 * 60 * 1000;
  const targetMs = last.ms - weekMs;
  let baseline = sorted[0];
  for (const point of sorted) {
    if (point.ms <= targetMs) baseline = point;
    else break;
  }
  const weeklyReturnPct =
    baseline.value > 0 ? ((last.value - baseline.value) / baseline.value) * 100 : null;

  return {
    totalReturnPct: Number.isFinite(totalReturnPct) ? totalReturnPct : null,
    weeklyReturnPct:
      weeklyReturnPct != null && Number.isFinite(weeklyReturnPct) ? weeklyReturnPct : null,
  };
}