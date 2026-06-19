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