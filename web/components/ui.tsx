// Small shared pieces for every page. Values are shown as the API returns them; only formatting here.

import { interval, kn, pct } from "@/lib/format";
import type { Outcome, Rate, Summary } from "@/lib/types";

const STATUS_STYLE: Record<string, string> = {
  met: "bg-emerald-100 text-emerald-800",
  "not met": "bg-rose-100 text-rose-800",
  "not testable": "bg-amber-100 text-amber-800",
};

export function Status({ status }: { status: string }) {
  return (
    <span className={`rounded px-2 py-0.5 text-xs font-medium ${STATUS_STYLE[status] ?? "bg-slate-100 text-slate-700"}`}>
      {status}
    </span>
  );
}

export function Section({ title, id, children }: { title: string; id?: string; children: React.ReactNode }) {
  return (
    <section id={id} className="mt-8">
      <h2 className="mb-3 text-lg font-semibold tracking-tight">{title}</h2>
      {children}
    </section>
  );
}

export function PageTitle({ title, children }: { title: string; children?: React.ReactNode }) {
  return (
    <div>
      <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
      {children && <div className="mt-1 text-sm text-slate-600">{children}</div>}
    </div>
  );
}

export function Loading({ error }: { error: string | null }) {
  return error ? (
    <p className="text-rose-700">Could not load results: {error}</p>
  ) : (
    <p className="text-slate-500">Loading results…</p>
  );
}

export function RateText({ r, muted }: { r: Rate; muted?: boolean }) {
  return (
    <div className={muted ? "text-xs text-slate-400" : ""}>
      <span className={muted ? "" : "font-medium"}>{pct(r.rate)}</span> <span className="tabular-nums">({kn(r)})</span>
      {!muted && <div className="text-xs text-slate-500">{interval(r)}</div>}
    </div>
  );
}

export function Tile({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="mt-1 text-xl font-semibold tabular-nums">{value}</div>
      {sub && <div className="text-xs text-slate-500">{sub}</div>}
    </div>
  );
}

export const OUTCOMES: { key: Outcome; label: string; color: string; hex: string }[] = [
  { key: "correct", label: "Correct", color: "bg-emerald-500", hex: "#10b981" },
  { key: "missed", label: "Missed", color: "bg-slate-400", hex: "#94a3b8" },
  { key: "unsupported", label: "Unsupported", color: "bg-rose-500", hex: "#f43f5e" },
];

const OUTCOME_STYLE: Record<string, string> = {
  correct: "bg-emerald-100 text-emerald-800",
  missed: "bg-slate-200 text-slate-700",
  unsupported: "bg-rose-100 text-rose-800",
  pass: "bg-emerald-50 text-emerald-700",
  flag: "bg-amber-100 text-amber-800",
  block: "bg-rose-100 text-rose-800",
};

export function Chip({ value }: { value: string }) {
  return <span className={`rounded px-1.5 py-0.5 text-xs font-medium ${OUTCOME_STYLE[value] ?? "bg-slate-100"}`}>{value}</span>;
}

export function SeededTable({ s }: { s: Summary }) {
  const seeded = s.seeded_errors;
  const transforms = Object.keys(seeded.by_transform_quote_off).sort();
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="w-full min-w-[20rem] text-sm tabular-nums">
        <thead className="bg-slate-50 text-left text-xs text-slate-500">
          <tr>
            <th className="px-3 py-2 font-medium">Transform</th>
            <th className="px-3 py-2 font-medium">Detected, quote check off</th>
            <th className="px-3 py-2 font-medium">Detected, full</th>
          </tr>
        </thead>
        <tbody>
          {transforms.map((t) => (
            <tr key={t} className="border-t border-slate-100">
              <td className="px-3 py-2 font-mono">{t}</td>
              <td className="px-3 py-2">
                <RateText r={seeded.by_transform_quote_off[t]} />
              </td>
              <td className="px-3 py-2">
                <RateText r={seeded.by_transform_full[t]} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

const BAR_NAMES: Record<string, string> = {
  unsupported_claim_rate_falls: "Unsupported-claim rate falls, McNemar",
  abstain_rate_controls: "Control abstain rate",
  verifier_precision: "Verifier precision",
  test_set_fault_rate: "Test-set fault rate",
};
const OPS: Record<string, string> = { lt: "<", le: "≤", ge: "≥" };

/** A pass bar's title, with its threshold read from the summary key (e.g. `..._le_10pct_treatment`). */
export function barTitle(key: string): string {
  const m = key.match(/^(.*?)_(p_)?(lt|le|ge)_([\d.]+?)(pct)?(?:_([a-z]+))?$/);
  if (!m) return key;
  const [, name, p, op, value, isPct, scope] = m;
  return `${BAR_NAMES[name] ?? name} ${p ? "p " : ""}${OPS[op]} ${value}${isPct ? "%" : ""}${scope ? ` (${scope})` : ""}`;
}
