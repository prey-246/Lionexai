/** Coerce API values (null/undefined/strings) to a finite number. */
export function toFiniteNumber(value: unknown, fallback = 0): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

export function formatFixed(value: unknown, digits = 2, fallback = 0): string {
  return toFiniteNumber(value, fallback).toFixed(digits);
}

export function formatCurrency(value: unknown, fallback = 0): string {
  return `$${toFiniteNumber(value, fallback).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}
