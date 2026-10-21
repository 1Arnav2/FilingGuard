import Link from "next/link";

import { basisName, conditionName, outcomeName } from "@/lib/content";
import { itemsHref } from "@/lib/links";
import type { Basis, Condition, Outcome } from "@/lib/types";

export const OUTCOMES: { key: Outcome; bar: string }[] = [
  { key: "correct", bar: "bg-bar-correct" },
  { key: "missed", bar: "bg-bar-missed" },
  { key: "unsupported", bar: "bg-bar-unsupported" },
];

type Counts = Partial<Record<Outcome, number>>;

export function sameCounts(a: Counts, b: Counts): boolean {
  return OUTCOMES.every((o) => (a[o.key] ?? 0) === (b[o.key] ?? 0));
}

/** Stacked Correct / Missed / Unsupported bar; widths are shares of `n`, labels are the counts. */
export function OutcomeBar({ label, counts, n }: { label: string; counts: Counts; n: number }) {
  const summary = OUTCOMES.map((o) => `${counts[o.key] ?? 0} ${outcomeName(o.key).toLowerCase()}`).join(", ");
  return (
    <div role="img" aria-label={`${label}: ${summary}`} className="flex h-2.5 overflow-hidden rounded-full bg-muted">
      {OUTCOMES.map((o) => {
        const k = counts[o.key] ?? 0;
        return k ? <div key={o.key} className={o.bar} style={{ width: `${(k / n) * 100}%` }} /> : null;
      })}
    </div>
  );
}

/** "197 Correct · 10 Missed · 3 Unsupported", each count a link to those items. */
export function OutcomeCounts({ counts, basis, condition, filters = {} }: {
  counts: Counts;
  basis: Basis;
  condition: Condition;
  filters?: Record<string, string>;
}) {
  return (
    <ul className="flex flex-wrap gap-x-4 gap-y-1 text-sm tabular-nums">
      {OUTCOMES.map((o) => (
        <li key={o.key} className="flex items-center gap-1.5">
          <span aria-hidden="true" className={`size-2 rounded-full ${o.bar}`} />
          <Link
            href={itemsHref({ ...filters, condition, outcome: o.key }, basis)}
            className="inline-flex min-h-11 items-center gap-1 underline decoration-border underline-offset-4 hover:decoration-foreground sm:min-h-0"
          >
            <span className="font-medium">{counts[o.key] ?? 0}</span> {outcomeName(o.key)}
          </Link>
        </li>
      ))}
    </ul>
  );
}

/** The other basis, shown only where it differs. */
export function OtherBasis({ basis, children }: { basis: Basis; children: React.ReactNode }) {
  const other: Basis = basis === "corrected" ? "as_scored" : "corrected";
  return (
    <p className="text-xs text-muted-foreground">
      <span className="font-medium">{basisName(other)}:</span> {children}
    </p>
  );
}

export function ConditionLabel({ condition }: { condition: Condition }) {
  return <span className="text-xs font-medium text-muted-foreground">{conditionName(condition)}</span>;
}
