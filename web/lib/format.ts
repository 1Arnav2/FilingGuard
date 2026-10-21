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
