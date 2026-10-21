"use client";

import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { OUTCOMES, PageTitle, Section, SeededTable } from "@/components/ui";
import { BASIS_LABEL } from "@/lib/basis";
import { points } from "@/lib/format";
import type { Basis, Condition, Summary, TypeSummary } from "@/lib/types";

const CONDITIONS: { key: Condition; label: string; short: string }[] = [
  { key: "baseline", label: "Baseline", short: "B" },
  { key: "treatment", label: "With verifier", short: "V" },
];

function counts(t: TypeSummary): string {
  return OUTCOMES.map((o) => t.outcomes[o.key] ?? 0).join(" / ");
}

function Chart({ s, basis }: { s: Summary; basis: Basis }) {
  const types = Object.keys(s.conditions[basis].baseline.by_type);
  const data = types.flatMap((type) =>
    CONDITIONS.map((c) => {
      const t = s.conditions[basis][c.key].by_type[type];
      return { name: `${type} · ${c.short}`, ...Object.fromEntries(OUTCOMES.map((o) => [o.label, t.outcomes[o.key] ?? 0])) };
    }),
  );
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-2" style={{ height: data.length * 26 + 70 }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout="vertical" margin={{ left: 8, right: 16, top: 8, bottom: 8 }} barCategoryGap={3}>
          <CartesianGrid horizontal={false} stroke="#e2e8f0" />
          <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
          <YAxis type="category" dataKey="name" width={150} tick={{ fontSize: 11 }} interval={0} />
          <Tooltip />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          {OUTCOMES.map((o) => (
            <Bar key={o.key} dataKey={o.label} stackId="outcome" fill={o.hex} isAnimationActive={false} />
          ))}
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

function TypeTable({ s, basis }: { s: Summary; basis: Basis }) {
  const other: Basis = basis === "corrected" ? "as_scored" : "corrected";
  const types = Object.keys(s.conditions[basis].baseline.by_type);
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="w-full min-w-[40rem] text-sm tabular-nums">
        <thead className="bg-slate-50 text-left text-xs text-slate-500">
          <tr>
            <th className="px-3 py-2 font-medium">Attack type</th>
            <th className="px-3 py-2 font-medium">Items</th>
            {CONDITIONS.map((c) => (
              <th key={c.key} className="px-3 py-2 font-medium">
                {c.label}
                <div className="font-normal">correct / missed / unsupported</div>
              </th>
            ))}
            <th className="px-3 py-2 font-medium">
              Change in correct share, corrected
              <div className="font-normal">paired bootstrap 95% interval</div>
            </th>
          </tr>
        </thead>
        <tbody>
          {types.map((type) => {
            const boot = s.bootstrap_by_type_corrected[type]?.correct_share;
            return (
              <tr key={type} className="border-t border-slate-100 align-top">
                <td className="px-3 py-2 font-mono text-xs">{type}</td>
                <td className="px-3 py-2">{s.conditions[basis].baseline.by_type[type].n}</td>
                {CONDITIONS.map((c) => {
                  const mine = counts(s.conditions[basis][c.key].by_type[type]);
                  const theirs = counts(s.conditions[other][c.key].by_type[type]);
                  const labels = Object.entries(s.conditions[basis][c.key].by_type[type].labels);
                  return (
                    <td key={c.key} className="px-3 py-2">
                      <div className="font-medium">{mine}</div>
                      {labels.length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {labels.map(([label, k]) => (
                            <span key={label} className="text-xs text-rose-700">
                              {label} {k}
                            </span>
                          ))}
                        </div>
                      )}
                      {theirs !== mine && (
                        <div className="text-xs text-slate-400">
                          {BASIS_LABEL[other].toLowerCase()}: {theirs}
                        </div>
                      )}
                    </td>
                  );
                })}
                <td className="px-3 py-2">
                  {boot ? (
                    <>
                      {points(boot.change)}{" "}
                      <span className="text-xs text-slate-500">
                        ({points(boot.bootstrap95[0])} to {points(boot.bootstrap95[1])})
                      </span>
                    </>
                  ) : (
                    <span className="text-xs text-slate-500">counts only</span>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function AttackTypes({ summary: s, basis }: { summary: Summary; basis: Basis }) {
  return (
    <div>
      <PageTitle title="By attack type">
        Outcomes per attack type, baseline and with the verifier. Showing <strong>{BASIS_LABEL[basis].toLowerCase()}</strong>;
        the other basis is shown under a count wherever it differs. In the chart, B is baseline and V is with the verifier.
      </PageTitle>

      <Section title={`Outcomes, ${BASIS_LABEL[basis].toLowerCase()}`}>
        <Chart s={s} basis={basis} />
      </Section>

      <Section title="Counts on both bases">
        <TypeTable s={s} basis={basis} />
      </Section>

      <Section title="Seeded errors by transform">
        <p className="mb-3 text-sm text-slate-600">
          Planted errors copied into correct answers, one transform each; detection is a block by the frozen verifier.
        </p>
        <SeededTable s={s} />
      </Section>
    </div>
  );
}
