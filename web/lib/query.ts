// Filtering, sorting and paging of the item list, in the page. A port of `items()` in
// src/filingguard/api/routes.py; tests/test_static_site.py checks both give the same pages.

import type { Basis, Condition, ItemPage, ItemRow, ItemSource } from "./types";

export type ItemQuery = Record<string, string | number | undefined>;

const OUTCOME_RANK: Record<string, number> = { correct: 0, missed: 1, unsupported: 2 };
const VERDICT_RANK: Record<string, number> = { pass: 0, flag: 1, block: 2 };
// Outcomes and verdicts sort by severity, not alphabetically; ties break on the item ID.
const SORT_KEYS: Record<string, (r: ItemRow) => string | number> = {
  id: (r) => r.id,
  company: (r) => r.company,
  attack_type: (r) => r.attack_type,
  baseline: (r) => OUTCOME_RANK[r.baseline.outcome],
  verdict: (r) => VERDICT_RANK[r.verdict],
  treatment: (r) => OUTCOME_RANK[r.treatment.outcome],
};
const FLAGS = ["corrected", "unparseable", "handchecked"] as const;

/** One list row on one basis. */
export function toRow(item: ItemSource, basis: Basis): ItemRow {
  const { outcomes, ...rest } = item;
  return { ...rest, baseline: outcomes[basis].baseline, treatment: outcomes[basis].treatment };
}

function text(q: ItemQuery, key: string): string {
  const v = q[key];
  return v === undefined ? "" : String(v);
}

function bounded(v: string, fallback: number, max: number): number {
  const n = Number.parseInt(v, 10);
  return Number.isFinite(n) && n >= 1 ? Math.min(n, max) : fallback;
}

function compare(a: string | number, b: string | number): number {
  return a < b ? -1 : a > b ? 1 : 0;
}

/** The items, filtered and sorted; `outcome` and `label` apply to `condition` on `basis`. */
export function queryItems(items: ItemSource[], q: ItemQuery = {}): ItemPage {
  const basis: Basis = text(q, "basis") === "as_scored" ? "as_scored" : "corrected";
  const condition: Condition = text(q, "condition") === "baseline" ? "baseline" : "treatment";
  let rows = items.map((item) => toRow(item, basis));
  const needle = text(q, "q").trim().toLowerCase();
  if (needle) rows = rows.filter((r) => r.id.toLowerCase().includes(needle) || r.company.toLowerCase().includes(needle));
  for (const flag of FLAGS) {
    const v = text(q, flag);
    if (v === "true" || v === "false") rows = rows.filter((r) => r[flag] === (v === "true"));
  }
  const attackType = text(q, "attack_type");
  if (attackType) rows = rows.filter((r) => r.attack_type === attackType);
  const verdict = text(q, "verdict");
  if (verdict) rows = rows.filter((r) => r.verdict === verdict);
  const outcome = text(q, "outcome");
  if (outcome) rows = rows.filter((r) => r[condition].outcome === outcome);
  const label = text(q, "label");
  if (label) rows = rows.filter((r) => r[condition].label === label);
  const key = SORT_KEYS[text(q, "sort")] ?? SORT_KEYS.id;
  const sign = text(q, "order") === "desc" ? -1 : 1;
  rows.sort((a, b) => sign * (compare(key(a), key(b)) || compare(a.id, b.id)));
  const page = bounded(text(q, "page"), 1, Number.MAX_SAFE_INTEGER);
  const pageSize = bounded(text(q, "page_size"), 50, 500);
  const start = (page - 1) * pageSize;
  return { total: rows.length, page, page_size: pageSize, basis, items: rows.slice(start, start + pageSize) };
}
