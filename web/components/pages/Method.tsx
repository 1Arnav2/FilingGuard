"use client";

import Link from "next/link";

import { StatusBadge } from "@/components/data/badges";
import { DataTable } from "@/components/data/DataTable";
import { Load, PageHeader, Section } from "@/components/data/layout";
import { JumpTo } from "@/components/site/JumpTo";
import { getMeta, getSummary } from "@/lib/data";
import { bars } from "@/lib/bars";
import { copy, fill, glossaryEntries, method, type GlossarySource } from "@/lib/content";
import { usd } from "@/lib/format";
import type { Meta, Summary } from "@/lib/types";
import { useData } from "@/lib/useData";

function Prose({ id, s, m, children }: { id: string; s: Summary; m: Meta; children?: React.ReactNode }) {
  const section = method.sections.find((x) => x.id === id);
  if (!section) return null;
  return (
    <Section id={id} title={section.title}>
      <div className="max-w-3xl space-y-4 text-base leading-relaxed text-muted-foreground">
        {section.paragraphs.map((p) => (
          <p key={p}>{fill(p, { summary: s, meta: m })}</p>
        ))}
      </div>
      {children && <div className="mt-6">{children}</div>}
    </Section>
  );
}

function Glossary() {
  const g = copy.glossary;
  return (
    <Section id="glossary" title={g.title} intro={g.intro}>
      <div className="grid gap-8 lg:grid-cols-2">
        {g.sections.map((section) => (
          <div key={section.id} id={`glossary-${section.source}`} className="scroll-mt-24">
            <h3 className="font-medium">{section.title}</h3>
            <dl className="mt-3 divide-y rounded-xl border">
              {glossaryEntries(section.source as GlossarySource).map(([code, name, def]) => (
                <div key={code} className="grid gap-1 px-4 py-3 text-sm">
                  <dt className="font-medium">{name}</dt>
                  <dd className="leading-relaxed text-muted-foreground">{def}</dd>
                </div>
              ))}
            </dl>
          </div>
        ))}
      </div>
    </Section>
  );
}

function MethodBody({ s, m }: { s: Summary; m: Meta }) {
  const tags = Object.entries(m.freeze_tags);
  const spend = Object.entries(s.spend.by_purpose_usd);
  return (
    <div>
      <PageHeader title={copy.method.title}>
        <p>{copy.method.intro}</p>
      </PageHeader>
      <JumpTo
        sections={[
          ...method.sections.slice(0, 3).map((x) => ({ id: x.id, label: x.title })),
          { id: "tags", label: "Frozen versions" },
          ...method.sections.slice(3).map((x) => ({ id: x.id, label: x.title })),
          { id: "glossary", label: copy.glossary.title },
          { id: "sources", label: "Data sources" },
        ]}
      />
      <Prose id="question" s={s} m={m} />
      <Prose id="agents" s={s} m={m} />
      <Prose id="testset" s={s} m={m} />
      <Section id="tags" title="Frozen versions" intro="Each part was frozen with a git tag before the test run. Freeze tests in the repository fail if a frozen file changes.">
        <DataTable
          caption="Freeze tags and their commits"
          rowKey={([t]) => t}
          rows={tags}
          columns={[
            { key: "tag", header: "Tag", primary: true, cell: ([t]) => <span className="font-mono">{t}</span> },
            {
              key: "commit",
              header: "Commit",
              cell: ([t, c]) => (
                <a href={c.url} className="font-mono underline underline-offset-4">
                  {c.commit.slice(0, 7)}
                  <span className="sr-only"> (commit for {t} on GitHub)</span>
                </a>
              ),
            },
          ]}
        />
      </Section>
      <Prose id="scoring" s={s} m={m} />
      <Prose id="bars" s={s} m={m}>
        <DataTable
          caption="Pass bars on both bases"
          rowKey={(b) => b.key}
          rows={bars(s)}
          columns={[
            { key: "bar", header: "Bar", primary: true, cell: (b) => b.title },
            { key: "corrected", header: "Corrected", cell: (b) => (b.status.corrected ? <StatusBadge status={b.status.corrected} /> : "—") },
            {
              key: "as_scored",
              header: "As scored",
              cell: (b) => (b.status.as_scored ? <StatusBadge status={b.status.as_scored} /> : <span className="text-muted-foreground">One value only</span>),
            },
          ]}
        />
      </Prose>
      <Prose id="spend" s={s} m={m}>
        <DataTable
          caption="Model spend by purpose"
          rowKey={([p]) => p}
          rows={[...spend, ["Total", s.spend.total_usd] as [string, number]]}
          columns={[
            { key: "purpose", header: "Purpose (spend ledger)", primary: true, cell: ([p]) => <span className={p === "Total" ? "font-medium" : "font-mono text-xs"}>{p}</span> },
            { key: "usd", header: "USD", cell: ([p, v]) => <span className={p === "Total" ? "font-medium tabular-nums" : "tabular-nums"}>{usd(v)}</span> },
          ]}
        />
      </Prose>
      <Glossary />
      <Section id="sources" title="Data sources">
        <p className="max-w-3xl text-sm leading-relaxed text-muted-foreground">
          Summary numbers come from <code className="font-mono break-all">results/summary.json</code>. Per-question data comes from{" "}
          <code className="font-mono break-all">{m.generated_from.replace("meta_v1.json", "items_v1.jsonl")}</code>, written by{" "}
          <code className="font-mono break-all">{m.generated_by}</code> from the frozen run files; their SHA-256 hashes are in{" "}
          <code className="font-mono break-all">{m.generated_from}</code>. What these results do not show is listed under{" "}
          <Link href="/limitations/" className="underline underline-offset-4">
            Limitations
          </Link>
          .
        </p>
      </Section>
    </div>
  );
}

export default function Method() {
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
      {({ s, m }) => <MethodBody s={s} m={m} />}
    </Load>
  );
}
