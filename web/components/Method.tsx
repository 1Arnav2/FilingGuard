"use client";

import method from "@/content/method.json";
import { PageTitle, Section, Status, barTitle } from "@/components/ui";
import { usd } from "@/lib/format";
import type { Meta, PassBars, Summary } from "@/lib/types";

const PLACEHOLDER = /\{(summary|meta):([A-Za-z0-9_.]+)\}/g;

/** Fill `{summary:path}` and `{meta:path}` placeholders from the API responses. */
function fill(text: string, sources: { summary: Summary; meta: Meta }): string {
  return text.replace(PLACEHOLDER, (_, source: "summary" | "meta", path: string) => {
    let node: unknown = sources[source];
    for (const key of path.split(".")) node = (node as Record<string, unknown>)[key];
    return String(node);
  });
}

function Prose({ id, sources }: { id: string; sources: { summary: Summary; meta: Meta } }) {
  const section = method.sections.find((s) => s.id === id);
  if (!section) return null;
  return (
    <Section title={section.title} id={id}>
      <div className="space-y-3 text-sm leading-relaxed text-slate-700">
        {section.paragraphs.map((p, n) => (
          <p key={n}>{fill(p, sources)}</p>
        ))}
      </div>
    </Section>
  );
}

function Tags({ meta }: { meta: Meta }) {
  return (
    <Section title="Frozen versions" id="tags">
      <p className="mb-3 text-sm text-slate-700">
        Each component was frozen with a git tag before the test run. Freeze tests in the repository fail if a frozen file changes.
      </p>
      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="w-full min-w-[24rem] text-sm">
          <thead className="bg-slate-50 text-left text-xs text-slate-500">
            <tr>
              <th className="px-3 py-2 font-medium">Tag</th>
              <th className="px-3 py-2 font-medium">Commit</th>
            </tr>
          </thead>
          <tbody>
            {Object.entries(meta.freeze_tags).map(([tag, t]) => (
              <tr key={tag} className="border-t border-slate-100">
                <td className="px-3 py-2 font-mono">{tag}</td>
                <td className="px-3 py-2">
                  <a href={t.url} className="font-mono text-sky-700 underline" target="_blank" rel="noreferrer">
                    {t.commit.slice(0, 7)}
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  );
}

function Bars({ s }: { s: Summary }) {
  const keys = Object.keys(s.pass_bars.corrected) as (keyof PassBars)[];
  const seeded = s.seeded_errors;
  const rows: { title: string; corrected: string; as_scored: string | null }[] = [
    ...keys.map((k) => ({ title: barTitle(k), corrected: s.pass_bars.corrected[k].status, as_scored: s.pass_bars.as_scored[k].status })),
    { title: `Seeded-error macro detection ≥ ${seeded.macro_threshold} (quote check off)`, corrected: seeded.macro_status, as_scored: null },
    {
      title: `Verifier false blocks on correct answers ≤ ${seeded.false_block_rate.threshold}`,
      corrected: seeded.false_block_rate.corrected.status,
      as_scored: seeded.false_block_rate.as_scored.status,
    },
  ];
  return (
    <div className="mt-3 overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="w-full min-w-[28rem] text-sm">
        <thead className="bg-slate-50 text-left text-xs text-slate-500">
          <tr>
            <th className="px-3 py-2 font-medium">Bar</th>
            <th className="px-3 py-2 font-medium">Corrected</th>
            <th className="px-3 py-2 font-medium">As scored</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.title} className="border-t border-slate-100">
              <td className="px-3 py-2">{r.title}</td>
              <td className="px-3 py-2">
                <Status status={r.corrected} />
              </td>
              <td className="px-3 py-2">{r.as_scored ? <Status status={r.as_scored} /> : <span className="text-slate-400">—</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Spend({ s }: { s: Summary }) {
  return (
    <div className="mt-3 overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="w-full min-w-[20rem] text-sm tabular-nums">
        <thead className="bg-slate-50 text-left text-xs text-slate-500">
          <tr>
            <th className="px-3 py-2 font-medium">Purpose (spend ledger)</th>
            <th className="px-3 py-2 font-medium">USD</th>
          </tr>
        </thead>
        <tbody>
          {Object.entries(s.spend.by_purpose_usd).map(([purpose, cost]) => (
            <tr key={purpose} className="border-t border-slate-100">
              <td className="px-3 py-2 font-mono text-xs">{purpose}</td>
              <td className="px-3 py-2">{usd(cost)}</td>
            </tr>
          ))}
          <tr className="border-t border-slate-300 font-medium">
            <td className="px-3 py-2">Total</td>
            <td className="px-3 py-2">{usd(s.spend.total_usd)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );
}

export default function Method({ summary, meta }: { summary: Summary; meta: Meta }) {
  const sources = { summary, meta };
  return (
    <div>
      <PageTitle title="Method">How the result on the other pages was produced, in plain terms.</PageTitle>
      <Prose id="question" sources={sources} />
      <Prose id="agents" sources={sources} />
      <Prose id="testset" sources={sources} />
      <Tags meta={meta} />
      <Prose id="scoring" sources={sources} />
      <Prose id="bars" sources={sources} />
      <Bars s={summary} />
      <Prose id="spend" sources={sources} />
      <Spend s={summary} />
      <Section title="Known limitations" id="limitations">
        <ul className="space-y-2 rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-950">
          {summary.limitations.map((l) => (
            <li key={l} className="list-inside list-disc">
              {l}
            </li>
          ))}
        </ul>
      </Section>
      <p className="mt-8 text-xs text-slate-500">
        Per-item data: <code className="font-mono">{meta.generated_from.replace("meta_v1.json", "items_v1.jsonl")}</code>, written by{" "}
        <code className="font-mono">{meta.generated_by}</code> from the frozen run files; their SHA-256 hashes are recorded in{" "}
        <code className="font-mono">{meta.generated_from}</code>.
      </p>
    </div>
  );
}
