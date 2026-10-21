"use client";

import headline from "@/content/headline.json";
import { OUTCOMES, RateText, Section, SeededTable, Status, Tile, barTitle } from "@/components/ui";
import { BASIS_LABEL } from "@/lib/basis";
import { interval, kn, pct, seconds, usd } from "@/lib/format";
import type { Basis, Condition, ConditionSummary, PassBars, Rate, Summary } from "@/lib/types";

const BASES: Basis[] = ["corrected", "as_scored"];

interface Cell {
  value: string;
  detail: string[];
  status: string;
}

interface BarRow {
  key: string;
  title: string;
  cells: Record<Basis, Cell | null>;
}

function rateCell(r: Rate & { status: string }, extra: string[] = []): Cell {
  return { value: pct(r.rate), detail: [kn(r), interval(r), ...extra].filter(Boolean), status: r.status };
}

function barCell(s: Summary, basis: Basis, key: keyof PassBars): Cell {
  const bars = s.pass_bars[basis];
  const c = s.conditions[basis];
  switch (key) {
    case "unsupported_claim_rate_falls_p_lt_0.05": {
      const u = bars[key];
      return {
        value: `p = ${u.exact_two_sided_p}`,
        detail: [
          `rate ${pct(c.baseline.unsupported_claim_rate.rate)} → ${pct(c.treatment.unsupported_claim_rate.rate)}`,
          `baseline unsupported ${u.baseline_unsupported}; discordant ${u.discordant_unsupported_to_not} vs ${u.discordant_not_to_unsupported}`,
          `best possible p ${u.best_possible_p_if_every_one_blocked}`,
        ],
        status: u.status,
      };
    }
    case "abstain_rate_controls_le_10pct_treatment": {
      const a = bars[key];
      return rateCell(a, [`baseline ${pct(a.baseline.rate)} (${kn(a.baseline)})`]);
    }
    case "verifier_precision_ge_0.85": {
      const p = bars[key];
      return { value: pct(p.precision.rate), detail: [kn(p.precision), interval(p.precision), `recall ${kn(p.recall)}`], status: p.status };
    }
    case "test_set_fault_rate_le_5pct":
      return rateCell(bars[key], [bars[key].source]);
  }
}

function barRows(s: Summary): BarRow[] {
  const keys = Object.keys(s.pass_bars.corrected) as (keyof PassBars)[];
  const rows: BarRow[] = keys.map((key) => ({
    key,
    title: barTitle(key),
    cells: { corrected: barCell(s, "corrected", key), as_scored: barCell(s, "as_scored", key) },
  }));
  const seeded = s.seeded_errors;
  rows.push({
    key: "macro",
    title: `Seeded-error macro detection ≥ ${seeded.macro_threshold} (quote check off)`,
    cells: {
      corrected: { value: String(seeded.macro_detection_T1_T3_T4_T5_T6_quote_off), detail: ["T1, T3–T6"], status: seeded.macro_status },
      as_scored: null,
    },
  });
  rows.push({
    key: "false_blocks",
    title: `Verifier false blocks on correct answers ≤ ${seeded.false_block_rate.threshold}`,
    cells: {
      corrected: rateCell(seeded.false_block_rate.corrected),
      as_scored: rateCell(seeded.false_block_rate.as_scored),
    },
  });
  return rows;
}

function BarCard({ row, basis }: { row: BarRow; basis: Basis }) {
  const statuses = BASES.map((b) => row.cells[b]?.status).filter(Boolean);
  const differ = statuses.length === 2 && statuses[0] !== statuses[1];
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-medium">{row.title}</h3>
        {differ && (
          <a href="#bases" className="shrink-0 rounded bg-violet-100 px-2 py-0.5 text-xs font-medium text-violet-800">
            bases differ
          </a>
        )}
      </div>
      <div className="mt-3 grid grid-cols-2 gap-3">
        {BASES.map((b) => {
          const cell = row.cells[b];
          return (
            <div key={b} className={`rounded p-2 ${b === basis ? "bg-slate-100 ring-1 ring-slate-300" : "opacity-70"}`}>
              <div className="text-xs text-slate-500">{BASIS_LABEL[b]}</div>
              {cell ? (
                <>
                  <div className="mt-1 flex flex-wrap items-center gap-2">
                    <span className="text-lg font-semibold tabular-nums">{cell.value}</span>
                    <Status status={cell.status} />
                  </div>
                  {cell.detail.map((d) => (
                    <div key={d} className="text-xs text-slate-600 tabular-nums">
                      {d}
                    </div>
                  ))}
                </>
              ) : (
                <div className="mt-1 text-sm text-slate-400">— (one basis only)</div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function OutcomeBar({ label, c, n }: { label: string; c: ConditionSummary; n: number }) {
  return (
    <div>
      <div className="mb-1 flex justify-between text-xs text-slate-600">
        <span>{label}</span>
        <span className="tabular-nums">
          {OUTCOMES.map((o) => `${c.outcomes[o.key] ?? 0} ${o.label.toLowerCase()}`).join(" · ")}
        </span>
      </div>
      <div className="flex h-5 overflow-hidden rounded bg-slate-100" role="img" aria-label={`${label} outcomes`}>
        {OUTCOMES.map((o) => {
          const count = c.outcomes[o.key] ?? 0;
          return count ? <div key={o.key} className={o.color} style={{ width: `${(count / n) * 100}%` }} title={`${o.label}: ${count}`} /> : null;
        })}
      </div>
    </div>
  );
}

const METRICS: { key: keyof Omit<ConditionSummary, "outcomes" | "by_type">; label: string }[] = [
  { key: "unsupported_claim_rate", label: "Unsupported-claim rate" },
  { key: "correct_handling", label: "Correct handling" },
  { key: "answer_coverage", label: "Answer coverage" },
  { key: "abstain_rate_controls", label: "Control abstain rate" },
  { key: "injection_followed", label: "Injections followed" },
];

function MetricsTable({ s, basis }: { s: Summary; basis: Basis }) {
  const other: Basis = basis === "corrected" ? "as_scored" : "corrected";
  const conditions: Condition[] = ["baseline", "treatment"];
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="w-full min-w-[28rem] text-sm tabular-nums">
        <thead className="bg-slate-50 text-left text-xs text-slate-500">
          <tr>
            <th className="px-3 py-2 font-medium">Metric ({BASIS_LABEL[basis].toLowerCase()})</th>
            <th className="px-3 py-2 font-medium">Baseline</th>
            <th className="px-3 py-2 font-medium">With verifier</th>
          </tr>
        </thead>
        <tbody>
          {METRICS.map((m) => (
            <tr key={m.key} className="border-t border-slate-100 align-top">
              <td className="px-3 py-2">{m.label}</td>
              {conditions.map((c) => {
                const mine = s.conditions[basis][c][m.key];
                const theirs = s.conditions[other][c][m.key];
                const same = mine.k === theirs.k && mine.n === theirs.n;
                return (
                  <td key={c} className="px-3 py-2">
                    <RateText r={mine} />
                    {!same && (
                      <div className="text-xs text-slate-400">
                        {BASIS_LABEL[other].toLowerCase()}: {pct(theirs.rate)} ({kn(theirs)})
                      </div>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function Scorecard({ summary: s, basis }: { summary: Summary; basis: Basis }) {
  const lat = s.latency;
  return (
    <div>
      <p className="mb-6 border-l-4 border-slate-900 pl-4 text-lg leading-relaxed text-slate-800">{headline.text}</p>
      <h1 className="text-2xl font-semibold tracking-tight">Scorecard</h1>
      <p className="mt-1 text-sm text-slate-600">
        Baseline target alone vs the same answers through the frozen verifier, on the {s.split} split ({s.n_items} items).
        Showing <strong>{BASIS_LABEL[basis].toLowerCase()}</strong>; the other basis is shown beside it.
      </p>
      <p id="bases" className="mt-2 rounded border border-violet-200 bg-violet-50 p-3 text-sm text-violet-900">
        {s.bases}
      </p>

      <Section title="Pass bars">
        <div className="grid gap-4 md:grid-cols-2">
          {barRows(s).map((row) => (
            <BarCard key={row.key} row={row} basis={basis} />
          ))}
        </div>
      </Section>

      <Section title="Baseline → with verifier">
        <div className="grid gap-4 md:grid-cols-2">
          {BASES.map((b) => (
            <div key={b} className={`space-y-3 rounded-lg border bg-white p-4 ${b === basis ? "border-slate-400" : "border-slate-200 opacity-70"}`}>
              <div className="text-xs font-medium text-slate-500">{BASIS_LABEL[b]}</div>
              <OutcomeBar label="Baseline" c={s.conditions[b].baseline} n={s.n_items} />
              <OutcomeBar label="With verifier" c={s.conditions[b].treatment} n={s.n_items} />
            </div>
          ))}
        </div>
        <div className="mt-4">
          <MetricsTable s={s} basis={basis} />
        </div>
      </Section>

      <Section title="Seeded errors">
        <p className="mb-3 text-sm text-slate-600">
          Macro detection {s.seeded_errors.macro_detection_T1_T3_T4_T5_T6_quote_off} against a bar of{" "}
          {s.seeded_errors.macro_threshold} <Status status={s.seeded_errors.macro_status} />
        </p>
        <SeededTable s={s} />
      </Section>

      <Section title="Latency and cost">
        <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
          <Tile label="End to end, p50" value={seconds(lat.end_to_end_s.p50)} sub={`${lat.run} of ${lat.sample} sampled items`} />
          <Tile label="End to end, p95" value={seconds(lat.end_to_end_s.p95)} />
          <Tile label="Verifier rules, p50" value={seconds(lat.verifier_rule_s.p50)} sub={`p95 ${seconds(lat.verifier_rule_s.p95)}`} />
          <Tile label="Model spend" value={usd(s.spend.total_usd)} sub={`cap ${usd(s.spend.cap_usd, 2)}`} />
        </div>
      </Section>

      <Section title="Known limitations">
        <ul className="space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
          {s.limitations.map((l) => (
            <li key={l} className="list-inside list-disc">
              {l}
            </li>
          ))}
        </ul>
      </Section>
    </div>
  );
}
