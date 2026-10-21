"use client";

import Link from "next/link";

import { StatusBadge } from "@/components/data/badges";
import { DataTable } from "@/components/data/DataTable";
import { Figure, Load, PageHeader, Panel, Section } from "@/components/data/layout";
import { OtherBasis, OutcomeBar, OutcomeCounts, OUTCOMES, sameCounts } from "@/components/data/outcomes";
import { LimitationText } from "@/components/site/LimitationText";
import { getSummary } from "@/lib/api";
import { bars, type Bar } from "@/lib/bars";
import { useBasis } from "@/lib/basis";
import {
  attackTypeDefinition,
  attackTypeName,
  basisName,
  conditionName,
  copy,
  fill,
  limitationGroups,
  outcomeName,
  statusName,
  transformDefinition,
  transformName,
} from "@/lib/content";
import { interval, kn, pct, points, seconds, usd } from "@/lib/format";
import type { Basis, Condition, ConditionSummary, Rate, Summary } from "@/lib/types";
import { useData } from "@/lib/useData";

const CONDITIONS: Condition[] = ["baseline", "treatment"];
const otherOf = (b: Basis): Basis => (b === "corrected" ? "as_scored" : "corrected");

interface BarValue {
  value: string;
  sub: string[];
  details: string[];
  status: string;
}

function barValue(s: Summary, key: string, basis: Basis): BarValue | null {
  const seeded = s.seeded_errors;
  const c = s.conditions[basis];
  const rateValue = (r: Rate & { status: string }, details: string[] = []): BarValue => ({
    value: pct(r.rate),
    sub: [kn(r), interval(r)].filter(Boolean),
    details,
    status: r.status,
  });
  switch (key) {
    case "unsupported_claim_rate_falls_p_lt_0.05": {
      const u = s.pass_bars[basis][key];
      return {
        value: `p = ${u.exact_two_sided_p}`,
        sub: [`Unsupported-claim rate ${pct(c.baseline.unsupported_claim_rate.rate)} → ${pct(c.treatment.unsupported_claim_rate.rate)}`],
        details: [
          `Unsupported without the verifier: ${u.baseline_unsupported}`,
          `Changed from unsupported to not: ${u.discordant_unsupported_to_not}; the other way: ${u.discordant_not_to_unsupported}`,
          `Best possible p if every one were blocked: ${u.best_possible_p_if_every_one_blocked}`,
        ],
        status: u.status,
      };
    }
    case "abstain_rate_controls_le_10pct_treatment": {
      const a = s.pass_bars[basis][key];
      return rateValue(a, [`${conditionName("baseline")}: ${pct(a.baseline.rate)} (${kn(a.baseline)})`]);
    }
    case "verifier_precision_ge_0.85": {
      const p = s.pass_bars[basis][key];
      return {
        value: pct(p.precision.rate),
        sub: [kn(p.precision), interval(p.precision)].filter(Boolean),
        details: [`Recall: ${kn(p.recall)} unsupported answers blocked`],
        status: p.status,
      };
    }
    case "test_set_fault_rate_le_5pct": {
      const f = s.pass_bars[basis][key];
      return rateValue(f, [f.source]);
    }
    case "seeded_macro":
      return basis === "corrected"
        ? {
            value: String(seeded.macro_detection_T1_T3_T4_T5_T6_quote_off),
            sub: ["Average over the planted error kinds below"],
            details: [],
            status: seeded.macro_status,
          }
        : null;
    case "false_blocks":
      return rateValue(seeded.false_block_rate[basis]);
  }
  return null;
}

function BarCard({ bar, s, basis }: { bar: Bar; s: Summary; basis: Basis }) {
  const mine = barValue(s, bar.key, basis) ?? barValue(s, bar.key, "corrected");
  const theirs = barValue(s, bar.key, otherOf(basis));
  if (!mine) return null;
  const differs = theirs !== null && (theirs.value !== mine.value || theirs.status !== mine.status);
  return (
    <Panel className="flex flex-col gap-4">
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-sm font-medium leading-snug">{bar.title}</h3>
        <StatusBadge status={mine.status} />
      </div>
      <div>
        <p className="text-3xl font-semibold tracking-tight tabular-nums">{mine.value}</p>
        {mine.sub.map((line) => (
          <p key={line} className="text-sm text-muted-foreground tabular-nums">
            {line}
          </p>
        ))}
        {differs && theirs && (
          <div className="mt-2">
            <OtherBasis basis={basis}>
              {theirs.value}, {statusName(theirs.status)}
            </OtherBasis>
          </div>
        )}
        {bar.key === "seeded_macro" && (
          <p className="mt-2 text-xs text-muted-foreground">Planted errors are not rescored, so this bar has one value.</p>
        )}
      </div>
      <p className="text-sm leading-relaxed">{bar.explain}</p>
      {mine.details.length > 0 && (
        <details className="group text-sm">
          <summary className="inline-flex min-h-11 cursor-pointer items-center font-medium sm:min-h-0">{copy.results.details}</summary>
          <ul className="mt-2 space-y-1 text-muted-foreground tabular-nums">
            {mine.details.map((d) => (
              <li key={d}>{d}</li>
            ))}
          </ul>
        </details>
      )}
    </Panel>
  );
}

function countsText(counts: ConditionSummary["outcomes"]): string {
  return OUTCOMES.map((o) => `${counts[o.key] ?? 0} ${outcomeName(o.key).toLowerCase()}`).join(" · ");
}

function Outcomes({ s, basis }: { s: Summary; basis: Basis }) {
  return (
    <Panel className="space-y-6">
      {CONDITIONS.map((c) => {
        const mine = s.conditions[basis][c].outcomes;
        const theirs = s.conditions[otherOf(basis)][c].outcomes;
        return (
          <div key={c} className="space-y-2">
            <h3 className="text-sm font-medium">{conditionName(c)}</h3>
            <OutcomeBar label={conditionName(c)} counts={mine} n={s.n_items} />
            <OutcomeCounts counts={mine} basis={basis} condition={c} />
            {!sameCounts(mine, theirs) && <OtherBasis basis={basis}>{countsText(theirs)}</OtherBasis>}
          </div>
        );
      })}
    </Panel>
  );
}

const METRIC_KEYS = Object.keys(copy.results.metrics) as (keyof typeof copy.results.metrics)[];

function Metrics({ s, basis }: { s: Summary; basis: Basis }) {
  const cell = (key: (typeof METRIC_KEYS)[number], c: Condition) => {
    const mine = s.conditions[basis][c][key];
    const theirs = s.conditions[otherOf(basis)][c][key];
    return (
      <div className="space-y-0.5">
        <div>
          <span className="font-medium">{pct(mine.rate)}</span> <span className="text-muted-foreground">({kn(mine)})</span>
        </div>
        <div className="text-xs text-muted-foreground">{interval(mine)}</div>
        {(mine.k !== theirs.k || mine.n !== theirs.n) && (
          <OtherBasis basis={basis}>
            {pct(theirs.rate)} ({kn(theirs)})
          </OtherBasis>
        )}
      </div>
    );
  };
  return (
    <DataTable
      caption={`Metrics on the ${basisName(basis)} basis`}
      rowKey={(k) => k}
      rows={METRIC_KEYS}
      columns={[
        {
          key: "metric",
          header: "Metric",
          primary: true,
          cell: (k) => (
            <div>
              <div className="font-medium">{copy.results.metrics[k].name}</div>
              <div className="text-xs text-muted-foreground">{copy.results.metrics[k].definition}</div>
            </div>
          ),
        },
        { key: "baseline", header: conditionName("baseline"), cell: (k) => cell(k, "baseline") },
        { key: "treatment", header: conditionName("treatment"), cell: (k) => cell(k, "treatment") },
      ]}
    />
  );
}

function ByAttackType({ s, basis }: { s: Summary; basis: Basis }) {
  const types = Object.keys(s.conditions[basis].baseline.by_type);
  return (
    <ul className="divide-y rounded-xl border">
      {types.map((t) => {
        const boot = s.bootstrap_by_type_corrected[t]?.correct_share;
        return (
          <li key={t} className="grid gap-4 p-5 lg:grid-cols-[14rem_1fr_14rem]">
            <div>
              <h3 className="font-medium">{attackTypeName(t)}</h3>
              <p className="text-sm text-muted-foreground">{attackTypeDefinition(t)}</p>
              <p className="mt-1 text-xs text-muted-foreground tabular-nums">{s.conditions[basis].baseline.by_type[t].n} questions</p>
            </div>
            <div className="space-y-4">
              {CONDITIONS.map((c) => {
                const mine = s.conditions[basis][c].by_type[t];
                const theirs = s.conditions[otherOf(basis)][c].by_type[t];
                return (
                  <div key={c} className="space-y-1.5">
                    <div className="text-xs font-medium text-muted-foreground">{conditionName(c)}</div>
                    <OutcomeBar label={`${attackTypeName(t)}, ${conditionName(c)}`} counts={mine.outcomes} n={mine.n} />
                    <OutcomeCounts counts={mine.outcomes} basis={basis} condition={c} filters={{ attack_type: t }} />
                    {!sameCounts(mine.outcomes, theirs.outcomes) && <OtherBasis basis={basis}>{countsText(theirs.outcomes)}</OtherBasis>}
                  </div>
                );
              })}
            </div>
            <div className="text-sm">
              <div className="text-xs font-medium text-muted-foreground">Change in share correct ({basisName("corrected")})</div>
              {boot ? (
                <p className="mt-1 tabular-nums">
                  <span className="font-medium">{points(boot.change)}</span>
                  <span className="block text-xs text-muted-foreground">
                    95% interval {points(boot.bootstrap95[0])} to {points(boot.bootstrap95[1])}
                  </span>
                </p>
              ) : (
                <p className="mt-1 text-muted-foreground">Counts only: too few questions for an interval.</p>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}

function Seeded({ s }: { s: Summary }) {
  const seeded = s.seeded_errors;
  const kinds = Object.keys(seeded.by_transform_quote_off).sort();
  const rate = (r: Rate) => (
    <span>
      <span className="font-medium">{pct(r.rate)}</span> <span className="text-muted-foreground">({kn(r)})</span>
      <span className="block text-xs text-muted-foreground">{interval(r)}</span>
    </span>
  );
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3 text-sm">
        <span>
          Average detection <span className="font-semibold tabular-nums">{seeded.macro_detection_T1_T3_T4_T5_T6_quote_off}</span>, bar{" "}
          <span className="tabular-nums">{seeded.macro_threshold}</span>
        </span>
        <StatusBadge status={seeded.macro_status} />
      </div>
      <DataTable
        caption="Planted errors detected, by kind"
        rowKey={(k) => k}
        rows={kinds}
        columns={[
          {
            key: "kind",
            header: "Kind of planted error",
            primary: true,
            cell: (k) => (
              <div>
                <div className="font-medium">
                  {transformName(k)} <span className="font-mono text-xs text-muted-foreground">{k}</span>
                </div>
                <div className="text-xs text-muted-foreground">{transformDefinition(k)}</div>
              </div>
            ),
          },
          { key: "off", header: "Detected, quote check off", cell: (k) => rate(seeded.by_transform_quote_off[k]) },
          { key: "full", header: "Detected, all checks", cell: (k) => rate(seeded.by_transform_full[k]) },
        ]}
      />
    </div>
  );
}

function Latency({ s }: { s: Summary }) {
  const l = s.latency;
  const t = copy.results.latency;
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <Panel><Figure label={t.p50} value={seconds(l.end_to_end_s.p50)} sub={fill(t.sample, { summary: s })} /></Panel>
      <Panel><Figure label={t.p95} value={seconds(l.end_to_end_s.p95)} /></Panel>
      <Panel><Figure label={t.rules} value={seconds(l.verifier_rule_s.p50)} /></Panel>
      <Panel><Figure label={t.spend} value={usd(s.spend.total_usd)} sub={fill(t.cap, { summary: s })} /></Panel>
    </div>
  );
}

function ResultsBody({ s }: { s: Summary }) {
  const basis = useBasis();
  const group = limitationGroups.groups.find((g) => g.id === "headline");
  const r = copy.results;
  return (
    <div>
      <PageHeader title={r.title}>
        <p>
          {r.intro} Showing <strong className="font-medium text-foreground">{basisName(basis)}</strong>; the other basis appears
          only where it differs.{" "}
          <Link href="/method/#scoring" className="underline underline-offset-4">
            {copy.explainer.title}
          </Link>
        </p>
      </PageHeader>
      <Section id="bars" title={r.bars_title}>
        <div className="grid gap-4 md:grid-cols-2">
          {bars(s).map((b) => (
            <BarCard key={b.key} bar={b} s={s} basis={basis} />
          ))}
        </div>
      </Section>
      <Section id="outcomes" title={r.outcomes_title}>
        <Outcomes s={s} basis={basis} />
      </Section>
      <Section id="metrics" title={r.metrics_title}>
        <Metrics s={s} basis={basis} />
      </Section>
      <Section id="by-attack-type" title={r.types_title} intro={r.types_intro}>
        <ByAttackType s={s} basis={basis} />
      </Section>
      <Section id="seeded" title={r.seeded_title} intro={r.seeded_intro}>
        <Seeded s={s} />
      </Section>
      <Section id="latency" title={r.latency_title}>
        <Latency s={s} />
      </Section>
      <Section id="limits" title={r.limits_title}>
        <ul className="space-y-3">
          {group?.items.map((i) => (
            <li key={i} className="text-sm leading-relaxed">
              <LimitationText text={s.limitations[i]} />
            </li>
          ))}
        </ul>
        <Link href="/limitations/" className="mt-4 inline-flex min-h-11 items-center text-sm font-medium underline underline-offset-4 sm:min-h-0">
          All limitations
        </Link>
      </Section>
    </div>
  );
}

export default function Results() {
  const { data, error, retry } = useData(getSummary);
  return (
    <Load data={data} error={error} retry={retry}>
      {(s) => <ResultsBody s={s} />}
    </Load>
  );
}
