"use client";

import { ArrowRight, Bot, CircleCheck, CircleX, MessageSquareText, ShieldCheck } from "lucide-react";
import Link from "next/link";
import { useRef } from "react";

import { StatusBadge } from "@/components/data/badges";
import { Load, Panel } from "@/components/data/layout";
import { OtherBasis } from "@/components/data/outcomes";
import { AuthorBlock } from "@/components/site/AuthorBlock";
import { ExplainerBody } from "@/components/site/Explainer";
import { AnimatedBeam } from "@/components/ui/animated-beam";
import { BentoGrid } from "@/components/ui/bento-grid";
import { BorderBeam } from "@/components/ui/border-beam";
import { NumberTicker } from "@/components/ui/number-ticker";
import { getMeta, getSummary } from "@/lib/data";
import { bars } from "@/lib/bars";
import { useBasis } from "@/lib/basis";
import { basisName, contactHref, copy, fill, headline, limitationGroups, media, resolvePath, statusName } from "@/lib/content";
import { count, share } from "@/lib/format";
import { presetHref } from "@/lib/links";
import type { Basis, Meta, Summary } from "@/lib/types";
import { useData } from "@/lib/useData";
import { cn } from "@/lib/utils";

type Stat = (typeof copy.overview.stats)[number] & { of?: string; from?: string; preset?: string; href?: string };

function StatCard({ stat, s, basis }: { stat: Stat; s: Summary; basis: Basis }) {
  const other: Basis = basis === "corrected" ? "as_scored" : "corrected";
  const value = resolvePath(s, stat.path, basis) as number;
  const otherValue = resolvePath(s, stat.path, other) as number;
  const format = stat.format === "percent" ? share : count;
  const of = stat.of ? (resolvePath(s, stat.of, basis) as number) : null;
  const from = stat.from ? (resolvePath(s, stat.from, basis) as number) : null;
  const href = stat.preset ? presetHref(stat.preset, basis) : (stat.href ?? "/results/");
  const otherText = `${format(otherValue)}${stat.of ? ` of ${count(resolvePath(s, stat.of, other) as number)}` : ""}`;
  return (
    <Panel className="flex flex-col gap-4">
      <div>
        <h2 className="text-sm font-medium text-muted-foreground">{stat.label}</h2>
        <p className="mt-3 text-5xl font-semibold tracking-tight">
          <NumberTicker value={value} format={format} />
        </p>
        <p className="mt-2 text-sm text-muted-foreground tabular-nums">
          {of !== null && <>of {count(of)} correct answers</>}
          {from !== null && <>from {share(from)} without the verifier</>}
        </p>
        {stat.path.includes("{basis}") && format(otherValue) !== format(value) && (
          <div className="mt-1">
            <OtherBasis basis={basis}>{otherText}</OtherBasis>
          </div>
        )}
      </div>
      <div className="mt-auto space-y-3">
        <p className="text-sm leading-relaxed">{stat.caption}</p>
        <Link href={href} className="inline-flex min-h-11 items-center gap-1 text-sm font-medium underline underline-offset-4 sm:min-h-0">
          {stat.preset ? "See these questions" : "See the results"}
          <ArrowRight aria-hidden="true" className="size-4" />
        </Link>
      </div>
    </Panel>
  );
}

function Node({ nodeRef, icon: Icon, label, tone = "default" }: {
  nodeRef: React.RefObject<HTMLDivElement | null>;
  icon: typeof Bot;
  label: string;
  tone?: "default" | "pass" | "block";
}) {
  return (
    <div className="z-10 flex flex-col items-center gap-2 text-center">
      <div
        ref={nodeRef}
        className={cn(
          "flex size-12 items-center justify-center rounded-full border bg-card shadow-sm sm:size-14",
          tone === "pass" && "text-success",
          tone === "block" && "text-danger",
        )}
      >
        <Icon aria-hidden="true" className="size-5 sm:size-6" />
      </div>
      <span className="max-w-24 text-xs leading-tight font-medium">{label}</span>
    </div>
  );
}

function HowItWorks() {
  const container = useRef<HTMLDivElement>(null);
  const question = useRef<HTMLDivElement>(null);
  const agent = useRef<HTMLDivElement>(null);
  const verifier = useRef<HTMLDivElement>(null);
  const passed = useRef<HTMLDivElement>(null);
  const blocked = useRef<HTMLDivElement>(null);
  const n = copy.overview.how_nodes;
  return (
    <Panel className="md:col-span-2">
      <h2 className="text-sm font-medium text-muted-foreground">{copy.overview.how_title}</h2>
      <figure className="mt-4">
        <div ref={container} className="relative grid grid-cols-4 items-center gap-2 py-4">
          <Node nodeRef={question} icon={MessageSquareText} label={n.question} />
          <Node nodeRef={agent} icon={Bot} label={n.agent} />
          <Node nodeRef={verifier} icon={ShieldCheck} label={n.verifier} />
          <div className="flex flex-col gap-6">
            <Node nodeRef={passed} icon={CircleCheck} label={n.passed} tone="pass" />
            <Node nodeRef={blocked} icon={CircleX} label={n.blocked} tone="block" />
          </div>
          <AnimatedBeam containerRef={container} fromRef={question} toRef={agent} pathColor="var(--muted-foreground)" gradientStartColor="var(--foreground)" gradientStopColor="var(--muted-foreground)" />
          <AnimatedBeam containerRef={container} fromRef={agent} toRef={verifier} delay={0.4} pathColor="var(--muted-foreground)" gradientStartColor="var(--foreground)" gradientStopColor="var(--muted-foreground)" />
          <AnimatedBeam containerRef={container} fromRef={verifier} toRef={passed} delay={0.8} curvature={20} pathColor="var(--muted-foreground)" gradientStartColor="var(--bar-correct)" gradientStopColor="var(--bar-correct)" />
          <AnimatedBeam containerRef={container} fromRef={verifier} toRef={blocked} delay={0.8} curvature={-20} pathColor="var(--muted-foreground)" gradientStartColor="var(--bar-unsupported)" gradientStopColor="var(--bar-unsupported)" />
        </div>
        <figcaption className="mt-2 text-sm leading-relaxed text-muted-foreground">{copy.overview.how_caption}</figcaption>
      </figure>
      <Link href="/method/" className="mt-3 inline-flex min-h-11 items-center gap-1 text-sm font-medium underline underline-offset-4 sm:min-h-0">
        {copy.overview.how_link}
        <ArrowRight aria-hidden="true" className="size-4" />
      </Link>
    </Panel>
  );
}

function BarsGlance({ s, basis }: { s: Summary; basis: Basis }) {
  return (
    <Panel>
      <h2 className="text-sm font-medium text-muted-foreground">{copy.overview.bars_title}</h2>
      <p className="mt-1 text-xs text-muted-foreground">{copy.overview.bars_intro}</p>
      <ul className="mt-4 divide-y">
        {bars(s).map((b) => (
          <li key={b.key} className="flex items-start justify-between gap-3 py-2.5">
            <span className="text-sm leading-snug">{b.title}</span>
            <span className="flex shrink-0 flex-col items-end gap-1">
              <StatusBadge status={b.status.corrected ?? ""} />
              {b.status.as_scored && b.status.as_scored !== b.status.corrected && (
                <span className="text-xs text-muted-foreground">
                  {basisName("as_scored")}: {statusName(b.status.as_scored)}
                </span>
              )}
            </span>
          </li>
        ))}
      </ul>
      <Link href={basis === "as_scored" ? "/results/?basis=as_scored#bars" : "/results/#bars"} className="mt-2 inline-flex min-h-11 items-center gap-1 text-sm font-medium underline underline-offset-4 sm:min-h-0">
        {copy.overview.bars_link}
        <ArrowRight aria-hidden="true" className="size-4" />
      </Link>
    </Panel>
  );
}

function Honest({ s, m }: { s: Summary; m: Meta }) {
  return (
    <Panel className="md:col-span-2">
      <h2 className="text-sm font-medium text-muted-foreground">{copy.overview.honest_title}</h2>
      <ul className="mt-4 grid gap-4 sm:grid-cols-2">
        {copy.overview.honest.map((h) => (
          <li key={h.href} className="flex gap-3">
            <CircleCheck aria-hidden="true" className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
            <Link href={h.href} className="text-sm leading-relaxed underline decoration-border underline-offset-4 hover:decoration-foreground">
              {fill(h.text, { summary: s, meta: m })}
            </Link>
          </li>
        ))}
      </ul>
    </Panel>
  );
}

function Limits({ s }: { s: Summary }) {
  const group = limitationGroups.groups.find((g) => g.id === "headline");
  return (
    <Panel className="md:col-span-2">
      <h2 className="text-sm font-medium text-muted-foreground">{copy.overview.limits_title}</h2>
      <ul className="mt-4 space-y-3">
        {group?.items.map((i) => (
          <li key={i} className="text-sm leading-relaxed">
            {fill(limitationGroups.summaries[i], { summary: s })}{" "}
            <Link href={`/limitations/#limitation-${i}`} className="inline-flex min-h-11 items-center font-medium whitespace-nowrap underline underline-offset-4 sm:min-h-0">
              {copy.overview.limits_more}
            </Link>
          </li>
        ))}
      </ul>
      <Link href="/limitations/" className="mt-3 inline-flex min-h-11 items-center gap-1 text-sm font-medium underline underline-offset-4 sm:min-h-0">
        {copy.overview.limits_link}
        <ArrowRight aria-hidden="true" className="size-4" />
      </Link>
    </Panel>
  );
}

function DemoVideo() {
  const url = media.demo_video_url;
  if (!url) return null;
  const file = /\.(mp4|webm)(\?|$)/i.test(url);
  return (
    <Panel className="md:col-span-3">
      <h2 className="text-sm font-medium text-muted-foreground">{copy.overview.video_title}</h2>
      <div className="mt-4 aspect-video overflow-hidden rounded-lg border">
        {file ? (
          <video src={url} controls preload="metadata" className="size-full" aria-label={media.demo_video_title} />
        ) : (
          <iframe src={url} title={media.demo_video_title} className="size-full" allow="encrypted-media; picture-in-picture" allowFullScreen />
        )}
      </div>
    </Panel>
  );
}

function OverviewBody({ s, m }: { s: Summary; m: Meta }) {
  const basis = useBasis();
  return (
    <div>
      <section className="relative -mx-4 -mt-8 px-4 pt-12 pb-10 sm:-mx-6 sm:-mt-12 sm:px-6 sm:pt-20">
        <div aria-hidden="true" className="hero-grid pointer-events-none absolute inset-0" />
        <div className="relative max-w-3xl space-y-4">
          <p className="text-sm font-medium text-muted-foreground">{copy.overview.eyebrow}</p>
          <h1 className="text-4xl font-semibold tracking-tight sm:text-5xl">{copy.site.name}</h1>
          <p className="text-lg leading-relaxed text-muted-foreground">{fill(copy.overview.intro, { summary: s, meta: m })}</p>
        </div>
      </section>

      <div className="relative overflow-hidden rounded-xl border bg-card p-6 sm:p-8">
        <p className="text-xl leading-relaxed font-medium tracking-tight sm:text-2xl">{headline.text}</p>
        <BorderBeam size={120} duration={10} colorFrom="var(--foreground)" colorTo="var(--muted-foreground)" />
      </div>

      <BentoGrid className="mt-4">
        {(copy.overview.stats as Stat[]).map((stat) => (
          <StatCard key={stat.id} stat={stat} s={s} basis={basis} />
        ))}
        <HowItWorks />
        <BarsGlance s={s} basis={basis} />
        <Panel>
          <ExplainerBody headingLevel={2} />
        </Panel>
        <Honest s={s} m={m} />
        <Limits s={s} />
        <div className="flex flex-col gap-4">
          <Panel>
            <a href={contactHref()} className="text-base leading-relaxed font-medium underline underline-offset-4">
              {copy.overview.outreach}
            </a>
          </Panel>
          <Panel className="flex-1">
            <AuthorBlock id="author" />
          </Panel>
        </div>
        <DemoVideo />
      </BentoGrid>
    </div>
  );
}

export default function Overview() {
  const summary = useData(getSummary);
  const meta = useData(getMeta);
  return (
    <Load
      data={summary.data && meta.data ? { s: summary.data, m: meta.data } : null}
      error={summary.error ?? meta.error}
      retry={() => {
        summary.retry();
        meta.retry();
      }}
    >
      {({ s, m }) => <OverviewBody s={s} m={m} />}
    </Load>
  );
}
