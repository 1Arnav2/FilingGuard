"use client";

import Link from "next/link";

import { Chip, Section } from "@/components/ui";
import { BASIS_LABEL } from "@/lib/basis";
import { evidenceText } from "@/lib/format";
import type { Basis, Condition, ItemDetail as Item } from "@/lib/types";

const BASES: Basis[] = ["corrected", "as_scored"];
const CONDITIONS: { key: Condition; label: string }[] = [
  { key: "baseline", label: "Baseline" },
  { key: "treatment", label: "With verifier" },
];

function Box({ children, tone = "white" }: { children: React.ReactNode; tone?: "white" | "violet" | "sky" | "slate" }) {
  const style = {
    white: "border-slate-200 bg-white",
    violet: "border-violet-200 bg-violet-50",
    sky: "border-sky-200 bg-sky-50",
    slate: "border-slate-300 bg-slate-100",
  }[tone];
  return <div className={`rounded-lg border p-4 text-sm ${style}`}>{children}</div>;
}

function Field({ name, children }: { name: string; children: React.ReactNode }) {
  return (
    <div className="grid grid-cols-[9rem_1fr] gap-2 py-1">
      <div className="text-xs text-slate-500">{name}</div>
      <div className="break-words">{children}</div>
    </div>
  );
}

function yesNo(v: boolean | null): string {
  return v === null ? "—" : v ? "yes" : "no";
}

function Answer({ item }: { item: Item }) {
  const a = item.answer;
  if (a.parse_error) {
    return (
      <Box tone="slate">
        <p className="font-medium">Unparseable reply</p>
        <p className="mt-1 text-slate-700">
          The target&apos;s reply could not be parsed ({a.unparseable_chars?.toLocaleString("en-US")} characters). It is scored
          Missed and counted separately. The runaway text is not shown.
        </p>
        <p className="mt-1 font-mono text-xs text-slate-500">{a.parse_error}</p>
      </Box>
    );
  }
  return (
    <Box>
      {a.abstained && <p className="mb-2 text-xs font-medium text-slate-500">The target abstained.</p>}
      <p className="whitespace-pre-wrap">{a.text}</p>
      {a.citations.length > 0 && (
        <div className="mt-3 space-y-2">
          <div className="text-xs font-medium text-slate-500">Citations</div>
          {a.citations.map((c, n) => (
            <blockquote key={n} className="border-l-2 border-slate-300 pl-3 text-xs text-slate-700">
              <span className="whitespace-pre-wrap">{c.quote}</span>
              <div className="mt-0.5 font-mono text-slate-400">
                {c.chunk_id} · quote {c.quote_found ? "found in the passage" : "not found in the passage"}
              </div>
            </blockquote>
          ))}
        </div>
      )}
    </Box>
  );
}

function Figures({ item }: { item: Item }) {
  if (!item.figures.length) return <Box>The scorer read no figures in this answer.</Box>;
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="w-full min-w-[36rem] text-xs tabular-nums">
        <thead className="bg-slate-50 text-left text-slate-500">
          <tr>
            {["Value", "Scale", "Metric", "Asked", "Period", "Period ok", "Adjusted"].map((h) => (
              <th key={h} className="px-3 py-2 font-medium">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {item.figures.map((f, n) => (
            <tr key={n} className="border-t border-slate-100">
              <td className="px-3 py-2">{f.value.toLocaleString("en-US")}{f.negative ? " (negative)" : ""}</td>
              <td className="px-3 py-2">{f.scale ?? "—"}</td>
              <td className="px-3 py-2 font-mono">{f.metric ?? "—"}</td>
              <td className="px-3 py-2">{yesNo(f.asked)}</td>
              <td className="px-3 py-2">{f.period ?? "—"}</td>
              <td className="px-3 py-2">{yesNo(f.period_ok)}</td>
              <td className="px-3 py-2">{yesNo(f.adjusted)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Outcomes({ item, basis }: { item: Item; basis: Basis }) {
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {BASES.map((b) => (
        <div key={b} className={`rounded-lg border bg-white p-4 text-sm ${b === basis ? "border-slate-400" : "border-slate-200 opacity-70"}`}>
          <div className="text-xs font-medium text-slate-500">{BASIS_LABEL[b]}</div>
          {CONDITIONS.map((c) => {
            const o = item.outcomes[b][c.key];
            return (
              <div key={c.key} className="mt-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="w-24 text-xs text-slate-500">{c.label}</span>
                  <Chip value={o.outcome} />
                  {o.label && <span className="font-mono text-xs text-rose-700">{o.label}</span>}
                </div>
                {o.notes.length > 0 && <div className="mt-0.5 text-xs text-slate-500">{o.notes.join("; ")}</div>}
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}

function Verdicts({ item }: { item: Item }) {
  const modes: { key: "full" | "quote_off"; label: string }[] = [
    { key: "full", label: "Full (the verdict the treatment used)" },
    { key: "quote_off", label: "Quote check off" },
  ];
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {modes.map((m) => {
        const v = item.verdict[m.key];
        return (
          <Box key={m.key}>
            <div className="flex items-center gap-2">
              <span className="text-xs text-slate-500">{m.label}</span>
              <Chip value={v.decision} />
            </div>
            {v.reasons.length === 0 ? (
              <p className="mt-2 text-xs text-slate-500">No reasons recorded.</p>
            ) : (
              <ul className="mt-2 space-y-1 text-xs">
                {v.reasons.map((r, n) => (
                  <li key={n}>
                    <span className="font-mono">{r.code}</span> <span className="text-slate-500">[{r.basis}]</span>
                    {r.blocking && <span className="text-rose-700"> blocking</span>}: {r.detail}
                  </li>
                ))}
              </ul>
            )}
          </Box>
        );
      })}
    </div>
  );
}

export default function ItemDetail({ item, basis }: { item: Item; basis: Basis }) {
  const back = `/items/${basis === "as_scored" ? "?basis=as_scored" : ""}`;
  return (
    <div>
      <Link href={back} className="text-sm text-slate-500 hover:text-slate-900">
        ← All items
      </Link>
      <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
        <h1 className="font-mono text-2xl font-semibold">{item.id}</h1>
        <span className="text-slate-500">{item.company}</span>
        <span className="font-mono text-slate-500">
          {item.attack_type} / {item.subtype}
        </span>
      </div>
      <p className="mt-3 text-lg text-slate-900">{item.question}</p>

      <Section title="Gold label">
        <Box>
          <Field name="Expected behaviour">
            <span className="font-mono">{item.gold.expected_behavior}</span>
          </Field>
          <Field name="Gold">
            <span className="whitespace-pre-wrap">{item.gold.text}</span>
          </Field>
        </Box>
      </Section>

      <Section title="Answer">
        <Answer item={item} />
      </Section>

      <Section title="Figures the scorer read">
        <Figures item={item} />
      </Section>

      <Section title="Judge decision">
        {item.judge ? (
          <Box>
            <Field name="Rejects premise">{yesNo(item.judge.rejects_premise)}</Field>
            <Field name="Confirms change">{yesNo(item.judge.confirms_change)}</Field>
            <Field name="Gives reasons">{yesNo(item.judge.gives_reasons)}</Field>
            <Field name="Says no reasons given">{yesNo(item.judge.says_no_reasons_given)}</Field>
            <Field name="Judge's reason">{item.judge.reason ?? "—"}</Field>
            <p className="mt-2 text-xs text-slate-500">
              The judge read this answer once; a passed answer keeps the decision with the verifier.
            </p>
          </Box>
        ) : (
          <Box>No judge call: the judge reads only answers to premise questions.</Box>
        )}
      </Section>

      <Section title="Outcomes">
        <Outcomes item={item} basis={basis} />
      </Section>

      <Section title="Verifier verdict">
        <Verdicts item={item} />
      </Section>

      <Section title="D-071 correction">
        {item.correction ? (
          <Box tone="violet">
            <Field name="Status">{item.correction.status}</Field>
            <Field name="As scored">{item.correction.as_scored.filter(Boolean).join(" ")}</Field>
            {item.correction.corrected && <Field name="Corrected to">{item.correction.corrected.filter(Boolean).join(" ")}</Field>}
            {item.correction.pattern && <Field name="Pattern">{item.correction.pattern}</Field>}
            <Field name="Reason">{item.correction.reason}</Field>
            {item.correction.evidence && (
              <Field name="Evidence">
                <ul className="space-y-0.5">
                  {Object.entries(item.correction.evidence).map(([k, v]) => (
                    <li key={k}>
                      <span className="font-mono text-xs text-slate-500">{k}</span>: {evidenceText(v)}
                    </li>
                  ))}
                </ul>
              </Field>
            )}
            {item.correction.approval && <Field name="Approval">{item.correction.approval}</Field>}
          </Box>
        ) : (
          <Box>No D-071 correction or review record for this item.</Box>
        )}
      </Section>

      <Section title="Owner's hand-check">
        {item.handcheck ? (
          <Box tone="sky">
            <Field name="Why listed">{item.handcheck.why_listed}</Field>
            <Field name="Verdict">{item.handcheck.verdict ?? "pre-filled, not re-marked"}</Field>
            {item.handcheck.note && <Field name="Note">{item.handcheck.note}</Field>}
            {item.handcheck.pre_filled && <Field name="Already decided">{item.handcheck.pre_filled}</Field>}
          </Box>
        ) : (
          <Box>Not in the owner&apos;s hand-check sheet.</Box>
        )}
      </Section>

      <Section title="Passages retrieved">
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="w-full min-w-[28rem] text-xs tabular-nums">
            <thead className="bg-slate-50 text-left text-slate-500">
              <tr>
                {["Rank", "Chunk", "10-K item", "Search", "Score"].map((h) => (
                  <th key={h} className="px-3 py-2 font-medium">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {item.retrieved.map((r) => (
                <tr key={r.rank} className="border-t border-slate-100">
                  <td className="px-3 py-2">{r.rank}</td>
                  <td className="px-3 py-2 font-mono">{r.chunk_id}</td>
                  <td className="px-3 py-2">{r.item ?? "—"}</td>
                  <td className="px-3 py-2">{r.source}</td>
                  <td className="px-3 py-2">{r.score}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Section>
    </div>
  );
}
