"use client";

import { ArrowRight } from "lucide-react";
import Link from "next/link";

import { Load, PageHeader, Section } from "@/components/data/layout";
import { LimitationText } from "@/components/site/LimitationText";
import { getSummary } from "@/lib/data";
import { copy, limitationGroups } from "@/lib/content";
import { presetHref } from "@/lib/links";
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
            {g.items.map((i) => {
              const link = (limitationGroups.links as Record<string, { label: string; preset: string }>)[String(i)];
              return (
                <li key={i} id={`limitation-${i}`} className="scroll-mt-24 rounded-xl border p-5 text-base leading-relaxed target:border-foreground">
                  <LimitationText text={s.limitations[i]} />
                  {link && (
                    <Link
                      href={presetHref(link.preset, "corrected")}
                      className="mt-3 flex min-h-11 w-fit items-center gap-1 text-sm font-medium underline underline-offset-4 sm:min-h-0"
                    >
                      {link.label}
                      <ArrowRight aria-hidden="true" className="size-4" />
                    </Link>
                  )}
                </li>
              );
            })}
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
