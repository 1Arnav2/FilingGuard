"use client";

import { ArrowLeft, ArrowRight } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { OutcomeBadge, VerdictBadge } from "@/components/data/badges";
import { DataTable } from "@/components/data/DataTable";
import { ErrorState, LoadingState, Panel } from "@/components/data/layout";
import { OtherBasis } from "@/components/data/outcomes";
import { LAST_ITEMS_URL } from "@/components/pages/Items";
import { getItem } from "@/lib/api";
import { useBasis } from "@/lib/basis";
import {
  attackTypeName,
  conditionName,
  copy,
  expectedName,
  failureLabelName,
  goldFieldName,
  handcheckReasons,
  handcheckVerdict,
  outcomeName,
  reasonBasisName,
  reasonName,
  subtypeName,
  template,
  verdictName,
} from "@/lib/content";
import { evidenceText } from "@/lib/format";
import type { Basis, ItemDetail as Item, Reason } from "@/lib/types";
import { useData } from "@/lib/useData";

const T = copy.item;
const YEAR_FIELDS = new Set(["fiscal_year", "trap_fiscal_year", "calendar_year", "quarter"]);
const GOLD_EXTRAS = ["premise", "premise_true", "true_values", "true_change", "requested_scale", "value_in_requested_scale",
  "trap_fiscal_year", "trap_value", "other_value", "quarter", "calendar_year", "start_month", "canary", "payload_subtype"];

function lowerFirst(s: string): string {
  return s ? s[0].toLowerCase() + s.slice(1) : s;
}

function goldValue(key: string, v: unknown): string {
  if (typeof v === "boolean") return v ? "Yes" : "No";
  if (key === "true_change" && typeof v === "number") return `${v > 0 ? "+" : ""}${(v * 100).toFixed(1)}%`;
  if (YEAR_FIELDS.has(key)) return String(v);
  return evidenceText(v);
}

/** The "what happened" sentences, from fixed templates that hold no numbers. */
function whatHappened(item: Item, basis: Basis): string[] {
  const o = item.outcomes[basis];
  const v = item.verdict.full;
  const reason = v.reasons.find((r) => r.blocking) ?? v.reasons[0];
  const values = { reason: reason ? lowerFirst(reasonName(reason.code)) : "no reason recorded" };
  const templates = T.templates as Record<string, string>;
  const lines = [
    item.answer.parse_error ? templates.unparseable : template(templates[`${v.decision}_${o.baseline.outcome}`] ?? "", values),
  ];
  if (item.correction?.status === "corrected") {
    lines.push(template(templates.corrected, { as_scored: outcomeName(item.correction.as_scored[0] ?? "").toLowerCase() }));
  } else if (item.correction) {
    lines.push(templates.kept);
  }
  return lines.filter(Boolean);
}

function Step({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      {children}
    </div>
  );
}

function WhatHappened({ item, basis }: { item: Item; basis: Basis }) {
  const other: Basis = basis === "corrected" ? "as_scored" : "corrected";
  const mine = item.outcomes[basis];
  const theirs = item.outcomes[other];
  const differs = mine.baseline.outcome !== theirs.baseline.outcome || mine.treatment.outcome !== theirs.treatment.outcome;
  return (
    <section aria-labelledby="what-title" className="rounded-xl border bg-card p-5 sm:p-6">
      <h2 id="what-title" className="text-sm font-medium text-muted-foreground">
        {T.what_happened}
      </h2>
      <div className="mt-4 flex flex-wrap items-end gap-3 sm:gap-5">
        <Step label={conditionName("baseline")}>
          <OutcomeBadge outcome={mine.baseline.outcome} />
        </Step>
        <ArrowRight aria-hidden="true" className="mb-1 size-4 text-muted-foreground" />
        <Step label="Verifier">
          <VerdictBadge verdict={item.verdict.full.decision} />
        </Step>
        <ArrowRight aria-hidden="true" className="mb-1 size-4 text-muted-foreground" />
        <Step label={conditionName("treatment")}>
          <OutcomeBadge outcome={mine.treatment.outcome} />
        </Step>
      </div>
      {differs && (
        <div className="mt-3">
          <OtherBasis basis={basis}>
            {outcomeName(theirs.baseline.outcome)} {conditionName("baseline").toLowerCase()}, {outcomeName(theirs.treatment.outcome)}{" "}
            {conditionName("treatment").toLowerCase()}
          </OtherBasis>
        </div>
      )}
      <div className="mt-4 space-y-2 text-base leading-relaxed">
        {whatHappened(item, basis).map((line) => (
          <p key={line}>{line}</p>
        ))}
      </div>
      {mine.baseline.label && (
        <p className="mt-2 text-sm text-muted-foreground">
          Failure label {conditionName("baseline").toLowerCase()}: {failureLabelName(mine.baseline.label)}
        </p>
      )}
    </section>
  );
}

function Field({ name, children }: { name: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-1 py-2 sm:grid-cols-[11rem_1fr] sm:gap-4">
      <dt className="text-sm text-muted-foreground">{name}</dt>
      <dd className="min-w-0 text-sm break-words">{children}</dd>
    </div>
  );
}

function Gold({ item }: { item: Item }) {
  const g = item.gold as Record<string, unknown>;
  const figure =
    g.value === null || g.value === undefined
      ? "Not in the filing"
      : `${String(g.printed_as ?? evidenceText(g.value))}${g.printed_scale ? ` (${String(g.printed_scale)})` : ""}`;
  return (
    <Panel>
      <h2 className="text-sm font-medium text-muted-foreground">{T.gold_title}</h2>
      <dl className="mt-3 divide-y">
        <Field name="Expected behaviour">{expectedName(item.gold.expected_behavior)}</Field>
        <Field name={goldFieldName("metric")}>{String(g.metric ?? "—")}</Field>
        <Field name="Figure">{figure}</Field>
        {g.fiscal_year !== undefined && g.fiscal_year !== null && <Field name={goldFieldName("fiscal_year")}>{String(g.fiscal_year)}</Field>}
        {typeof g.period_end === "string" && <Field name={goldFieldName("period_end")}>{g.period_end}</Field>}
        {GOLD_EXTRAS.filter((k) => g[k] !== undefined && g[k] !== null && g[k] !== "").map((k) => (
          <Field key={k} name={goldFieldName(k) ?? k}>
            {goldValue(k, g[k])}
          </Field>
        ))}
      </dl>
    </Panel>
  );
}

function Answer({ item }: { item: Item }) {
  const a = item.answer;
  return (
    <Panel>
      <h2 className="text-sm font-medium text-muted-foreground">{T.answer_title}</h2>
      {a.parse_error ? (
        <div className="mt-3 space-y-2 text-sm">
          <p className="font-medium">{T.unreadable_title}</p>
          <p className="text-muted-foreground">{T.unreadable_body}</p>
          <p className="text-muted-foreground tabular-nums">{a.unparseable_chars?.toLocaleString("en-US")} characters</p>
          <p className="font-mono text-xs break-words text-muted-foreground">{a.parse_error}</p>
        </div>
      ) : (
        <div className="mt-3 space-y-2">
          {a.abstained && <p className="text-sm font-medium text-muted-foreground">The agent declined to answer.</p>}
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{a.text}</p>
        </div>
      )}
    </Panel>
  );
}

function ReasonList({ reasons }: { reasons: Reason[] }) {
  if (!reasons.length) return <p className="text-sm text-muted-foreground">No reasons recorded: the verifier found nothing to object to.</p>;
  return (
    <ul className="space-y-3">
      {reasons.map((r, i) => (
        <li key={i} className="text-sm">
          <p>
            <span className="font-medium">{reasonName(r.code)}</span>{" "}
            <span className="text-muted-foreground">
              ({reasonBasisName(r.basis)}
              {r.blocking ? ", blocking" : ""})
            </span>
          </p>
          <p className="mt-0.5 font-mono text-xs break-words text-muted-foreground">{r.detail}</p>
        </li>
      ))}
    </ul>
  );
}

function Verifier({ item }: { item: Item }) {
  const full = item.verdict.full;
  const off = item.verdict.quote_off;
  const differs = full.decision !== off.decision || full.reasons.map((r) => r.code).join() !== off.reasons.map((r) => r.code).join();
  return (
    <Panel>
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-sm font-medium text-muted-foreground">{T.verifier_title}</h2>
        <VerdictBadge verdict={full.decision} />
      </div>
      <div className="mt-3">
        <ReasonList reasons={full.reasons} />
      </div>
      {differs && (
        <div className="mt-4 border-t pt-4">
          <p className="text-sm text-muted-foreground">
            {T.quote_off_differs} {verdictName(off.decision)}
          </p>
          <div className="mt-2">
            <ReasonList reasons={off.reasons} />
          </div>
        </div>
      )}
    </Panel>
  );
}

function Correction({ item }: { item: Item }) {
  const c = item.correction;
  if (!c) return null;
  return (
    <Panel>
      <h2 className="text-sm font-medium text-muted-foreground">{T.correction_title}</h2>
      <dl className="mt-3 divide-y">
        <Field name="Status">{c.status === "corrected" ? "Corrected" : "Kept as scored"}</Field>
        <Field name="As scored">{c.as_scored.filter(Boolean).map((x) => (x === c.as_scored[0] ? outcomeName(x as string) : failureLabelName(x))).join(", ")}</Field>
        {c.corrected && <Field name="Corrected to">{outcomeName(c.corrected[0] ?? "")}</Field>}
        {c.pattern && <Field name="What the scorer misread">{c.pattern}</Field>}
        <Field name="Reason">{c.reason}</Field>
        {c.evidence && (
          <Field name="Evidence">
            <ul className="space-y-1">
              {Object.entries(c.evidence).map(([k, v]) => (
                <li key={k}>
                  <span className="text-muted-foreground">{k.replaceAll("_", " ")}:</span> {evidenceText(v)}
                </li>
              ))}
            </ul>
          </Field>
        )}
        {c.approval && <Field name="Approval">{c.approval}</Field>}
      </dl>
    </Panel>
  );
}

function HandCheck({ item }: { item: Item }) {
  const h = item.handcheck;
  if (!h) return null;
  return (
    <Panel>
      <h2 className="text-sm font-medium text-muted-foreground">{T.handcheck_title}</h2>
      <dl className="mt-3 divide-y">
        <Field name="Why it was checked">{handcheckReasons(h.why_listed)}</Field>
        <Field name="Owner's verdict">{handcheckVerdict(h.verdict)}</Field>
        {h.note && <Field name="Owner's note">{h.note}</Field>}
      </dl>
    </Panel>
  );
}

function Judge({ item }: { item: Item }) {
  const j = item.judge;
  if (!j) return null;
  const yn = (v: boolean | null) => (v === null ? "—" : v ? "Yes" : "No");
  return (
    <Panel>
      <h2 className="text-sm font-medium text-muted-foreground">{T.judge_title}</h2>
      <dl className="mt-3 divide-y">
        <Field name="Rejects the premise">{yn(j.rejects_premise)}</Field>
        <Field name="Confirms the change">{yn(j.confirms_change)}</Field>
        <Field name="Gives reasons">{yn(j.gives_reasons)}</Field>
        <Field name="Says no reasons given">{yn(j.says_no_reasons_given)}</Field>
        <Field name="Judge's reason">{j.reason ?? "—"}</Field>
      </dl>
      <p className="mt-3 text-xs text-muted-foreground">{T.judge_note}</p>
    </Panel>
  );
}

function Disclosure({ title, n, children }: { title: string; n: number; children: React.ReactNode }) {
  return (
    <details className="rounded-xl border">
      <summary className="flex min-h-11 cursor-pointer items-center px-5 py-3 text-sm font-medium">
        {title} <span className="ml-2 text-muted-foreground tabular-nums">({n})</span>
      </summary>
      <div className="border-t p-5">{children}</div>
    </details>
  );
}

function Evidence({ item }: { item: Item }) {
  const yn = (v: boolean | null) => (v === null ? "—" : v ? "Yes" : "No");
  return (
    <section aria-labelledby="evidence-title" className="space-y-3">
      <h2 id="evidence-title" className="text-sm font-medium text-muted-foreground">
        {T.evidence_title}
      </h2>
      <Disclosure title={T.citations} n={item.answer.citations.length}>
        <ul className="space-y-3">
          {item.answer.citations.map((c, i) => (
            <li key={i} className="border-l-2 pl-3 text-sm">
              <p className="whitespace-pre-wrap">{c.quote}</p>
              <p className="mt-1 font-mono text-xs text-muted-foreground">
                {c.chunk_id} · {c.quote_found ? "quote found in the passage" : "quote not found in the passage"}
              </p>
            </li>
          ))}
        </ul>
      </Disclosure>
      <Disclosure title={T.figures} n={item.figures.length}>
        <DataTable
          caption={T.figures}
          rowKey={(f) => `${f.value}-${f.period}-${f.metric}`}
          rows={item.figures}
          columns={[
            { key: "value", header: "Value", primary: true, cell: (f) => `${f.value.toLocaleString("en-US")}${f.negative ? " (negative)" : ""}` },
            { key: "scale", header: "Scale", cell: (f) => f.scale ?? "—" },
            { key: "metric", header: "Metric", cell: (f) => <span className="font-mono text-xs break-all">{f.metric ?? "—"}</span> },
            { key: "asked", header: "Asked for", cell: (f) => yn(f.asked) },
            { key: "period", header: "Period", cell: (f) => f.period ?? "—" },
            { key: "period_ok", header: "Period right", cell: (f) => yn(f.period_ok) },
          ]}
        />
      </Disclosure>
      <Disclosure title={T.passages} n={item.retrieved.length}>
        <DataTable
          caption={T.passages}
          rowKey={(r) => String(r.rank)}
          rows={item.retrieved}
          columns={[
            { key: "rank", header: "Rank", primary: true, cell: (r) => `Rank ${r.rank}` },
            { key: "chunk", header: "Passage", cell: (r) => <span className="font-mono text-xs break-all">{r.chunk_id}</span> },
            { key: "item", header: "10-K item", cell: (r) => r.item ?? "—" },
            { key: "source", header: "Search", cell: (r) => (r.source === "bm25" ? "Keyword" : r.source === "dense" ? "Semantic" : r.source) },
            { key: "score", header: "Score", cell: (r) => r.score },
          ]}
        />
      </Disclosure>
    </section>
  );
}

function ItemBody({ item, basis }: { item: Item; basis: Basis }) {
  const [back, setBack] = useState("/items/");
  useEffect(() => {
    document.title = `${item.id} · Items · FilingGuard`;
    try {
      setBack(sessionStorage.getItem(LAST_ITEMS_URL) ?? "/items/");
    } catch {
      // storage can be unavailable; keep the plain list
    }
  }, [item.id]);
  return (
    <div className="space-y-6">
      <Link href={back} className="inline-flex min-h-11 items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft aria-hidden="true" className="size-4" />
        {T.back}
      </Link>
      <header className="space-y-3">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-sm text-muted-foreground">
          <span>{item.company}</span>
          <span aria-hidden="true">·</span>
          <span>{attackTypeName(item.attack_type)}</span>
          <span aria-hidden="true">·</span>
          <span>{subtypeName(item.subtype)}</span>
        </div>
        <h1 className="font-mono text-2xl font-semibold tracking-tight">{item.id}</h1>
        <p className="max-w-3xl text-xl leading-relaxed">{item.question}</p>
      </header>
      <WhatHappened item={item} basis={basis} />
      <div className="grid gap-6 md:grid-cols-2">
        <Gold item={item} />
        <Answer item={item} />
      </div>
      <Verifier item={item} />
      <Correction item={item} />
      <HandCheck item={item} />
      <Judge item={item} />
      <Evidence item={item} />
    </div>
  );
}

export default function ItemDetail() {
  const basis = useBasis();
  const id = useSearchParams().get("id") ?? "";
  const { data, error, retry } = useData(() => (id ? getItem(id) : Promise.reject(new Error("no id"))), [id]);
  if (!id) return <p role="alert">{T.no_id} <Link href="/items/" className="underline">{T.back}</Link></p>;
  if (error?.includes("HTTP 404")) {
    return (
      <div role="alert" className="space-y-2">
        <h1 className="text-2xl font-semibold">{id}</h1>
        <p>{T.not_found}</p>
        <Link href="/items/" className="underline underline-offset-4">
          {T.back}
        </Link>
      </div>
    );
  }
  if (error) return <ErrorState error={error} onRetry={retry} />;
  if (!data) return <LoadingState />;
  return <ItemBody item={data} basis={basis} />;
}
