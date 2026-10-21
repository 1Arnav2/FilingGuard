"use client";

import { Load, PageHeader, Section } from "@/components/data/layout";
import { LimitationText } from "@/components/site/LimitationText";
import { getSummary } from "@/lib/api";
import { copy, limitationGroups } from "@/lib/content";
import type { Summary } from "@/lib/types";
import { useData } from "@/lib/useData";

function LimitationsBody({ s }: { s: Summary }) {
  return (
    <div>
      <PageHeader title={copy.limitations.title}>
        <p>{copy.limitations.intro}</p>
      </PageHeader>
      {limitationGroups.groups.map((g) => (
        <Section key={g.id} id={g.id} title={g.title}>
          <ol className="max-w-3xl space-y-4">
            {g.items.map((i) => (
              <li key={i} className="rounded-xl border p-5 text-base leading-relaxed">
                <LimitationText text={s.limitations[i]} />
              </li>
            ))}
          </ol>
        </Section>
      ))}
    </div>
  );
}

export default function Limitations() {
  const { data, error, retry } = useData(getSummary);
  return (
    <Load data={data} error={error} retry={retry}>
      {(s) => <LimitationsBody s={s} />}
    </Load>
  );
}
