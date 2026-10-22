// Display formatting only: no value shown on the dashboard is computed here.

import type { Rate } from "./types";

export function pct(rate: number | null, digits = 1): string {
  return rate === null ? "—" : `${(rate * 100).toFixed(digits)}%`;
}

export function kn(r: Rate): string {
  return `${r.k}/${r.n}`;
}

export function interval(r: Rate): string {
  return r.wilson95 ? `95% CI ${pct(r.wilson95[0])}–${pct(r.wilson95[1])}` : "";
}

export function seconds(s: number): string {
  return `${s.toFixed(2)} s`;
}

export function usd(x: number, digits = 4): string {
  return `$${x.toFixed(digits)}`;
}

/** A change in a share, in percentage points. */
export function points(change: number): string {
  return `${change > 0 ? "+" : ""}${(change * 100).toFixed(1)} pts`;
}

/** Any evidence value as text: numbers with separators, objects as `key: value` pairs, lists joined. */
export function evidenceText(v: unknown): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "number") return v.toLocaleString("en-US", { maximumFractionDigits: 20 });
  if (Array.isArray(v)) return v.map(evidenceText).join(", ");
  if (typeof v === "object") {
    return Object.entries(v as Record<string, unknown>)
      .map(([k, x]) => `${k}: ${evidenceText(x)}`)
      .join("; ");
  }
  return String(v);
}

/** A whole count with separators. */
export function count(n: number): string {
  return Math.round(n).toLocaleString("en-US");
}

/** A share as a percentage with one decimal; also the Number Ticker's formatter for shares. */
export function share(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

/** A dollar amount: millions with separators at a million and above ($3,770M), whole dollars below. */
export function money(v: number): string {
  const sign = v < 0 ? "-" : "";
  const a = Math.abs(v);
  if (a >= 1e6) return `${sign}$${(a / 1e6).toLocaleString("en-US", { maximumFractionDigits: a < 1e7 ? 1 : 0 })}M`;
  return `${sign}$${a.toLocaleString("en-US", { maximumFractionDigits: 2 })}`;
}
