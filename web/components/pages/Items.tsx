"use client";

import { X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect } from "react";

import { FlagBadge, OutcomeBadge, VerdictBadge } from "@/components/data/badges";
import { DataTable } from "@/components/data/DataTable";
import { ErrorState, LoadingState, PageHeader } from "@/components/data/layout";
import { getItems, getMeta } from "@/lib/api";
import { useBasis } from "@/lib/basis";
import {
  attackTypeName,
  basisName,
  conditionName,
  copy,
  failureLabelName,
  labels,
  outcomeName,
  verdictName,
} from "@/lib/content";
import { itemHref } from "@/lib/links";
import type { Basis, ItemRow } from "@/lib/types";
import { useData } from "@/lib/useData";
import { cn } from "@/lib/utils";

const PAGE_SIZE = 25;
const FILTER_KEYS = ["attack_type", "verdict", "outcome", "label", "condition", "corrected", "unparseable", "handchecked"] as const;
type FilterKey = (typeof FILTER_KEYS)[number];
type Filters = Partial<Record<FilterKey, string>>;
const PRESETS = copy.items.presets as { id: string; name: string; filters: Filters }[];
export const LAST_ITEMS_URL = "filingguard:last-items-url";

function readFilters(params: URLSearchParams): Filters {
  const out: Filters = {};
  for (const k of FILTER_KEYS) {
    const v = params.get(k);
    if (v) out[k] = v;
  }
  if (out.condition === "treatment") delete out.condition;
  return out;
}

function same(a: Filters, b: Filters): boolean {
  const norm = (f: Filters) => JSON.stringify(Object.entries(f).filter(([k, v]) => v && !(k === "condition" && v === "treatment")).sort());
  return norm(a) === norm(b);
}

function filterLabel(key: FilterKey, value: string): string {
  switch (key) {
    case "attack_type":
      return attackTypeName(value);
    case "verdict":
      return verdictName(value);
    case "outcome":
      return outcomeName(value);
    case "label":
      return failureLabelName(value);
    case "condition":
      return conditionName(value);
    default:
      return (copy.items.flags as Record<string, string>)[key] ?? key;
  }
}

function Select({ label, value, options, onChange }: {
  label: string;
  value: string;
  options: [string, string][];
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex flex-col gap-1 text-xs font-medium text-muted-foreground">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="min-h-11 rounded-lg border bg-background px-2 text-sm text-foreground sm:min-h-9"
      >
        {options.map(([v, name]) => (
          <option key={v} value={v}>
            {name}
          </option>
        ))}
      </select>
    </label>
  );
}

function PresetCounts({ basis, active }: { basis: Basis; active: string | null }) {
  const counts = useData(
    () => Promise.all(PRESETS.map((p) => getItems({ ...p.filters, basis, page_size: 1 }).then((r) => r.total))),
    [basis],
  );
  return (
    <nav aria-label={copy.items.presets_label}>
      <ul className="flex flex-wrap gap-2">
        {PRESETS.map((p, i) => {
          const query = new URLSearchParams(p.filters as Record<string, string>);
          if (basis === "as_scored") query.set("basis", basis);
          return (
            <li key={p.id}>
              <Link
                href={`/items/${query.size ? `?${query}` : ""}`}
                aria-current={active === p.id ? "true" : undefined}
                className={cn(
                  "inline-flex min-h-11 items-center gap-2 rounded-full border px-3 text-sm sm:min-h-8",
                  active === p.id ? "border-foreground bg-foreground text-background" : "hover:bg-muted",
                )}
              >
                {p.name}
                {counts.data && <span className="tabular-nums opacity-80">{counts.data[i]}</span>}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

export default function Items() {
  const basis = useBasis();
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const meta = useData(getMeta);
  const filters = readFilters(params);
  const page = Math.max(1, Number(params.get("page") ?? "1"));
  const key = params.toString();

  // A shared link with ?preset=... opens that view with its filters spelled out in the URL.
  useEffect(() => {
    const preset = PRESETS.find((p) => p.id === params.get("preset"));
    if (!preset) return;
    const next = new URLSearchParams(preset.filters as Record<string, string>);
    if (basis === "as_scored") next.set("basis", basis);
    router.replace(`${pathname}${next.size ? `?${next}` : ""}`, { scroll: false });
  }, [params, basis, pathname, router]);

  useEffect(() => {
    try {
      sessionStorage.setItem(LAST_ITEMS_URL, `/items/${key ? `?${key}` : ""}`);
    } catch {
      // storage can be unavailable; the back link then goes to the plain list
    }
  }, [key]);

  const items = useData(() => getItems({ ...filters, basis, page, page_size: PAGE_SIZE }), [key, basis]);

  const set = (name: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(name, value);
    else next.delete(name);
    next.delete("preset");
    if (name !== "page") next.delete("page");
    router.replace(`${pathname}${next.size ? `?${next}` : ""}`, { scroll: false });
  };
  const clearAll = () => router.replace(`${pathname}${basis === "as_scored" ? "?basis=as_scored" : ""}`, { scroll: false });

  const active = PRESETS.find((p) => same(p.filters, filters))?.id ?? null;
  const chips = (Object.entries(filters) as [FilterKey, string][]).filter(([k]) => k !== "condition");
  const condition = filters.condition ?? "treatment";
  const total = items.data?.total ?? 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const first = total ? (page - 1) * PAGE_SIZE + 1 : 0;
  const last = Math.min(page * PAGE_SIZE, total);
  const any: [string, string] = ["", "Any"];

  return (
    <div>
      <PageHeader title={copy.items.title}>
        <p>
          {copy.items.intro} Outcomes on the <strong className="font-medium text-foreground">{basisName(basis)}</strong> basis.
        </p>
      </PageHeader>

      <div className="mt-8 space-y-4">
        <h2 className="sr-only">{copy.items.presets_label}</h2>
        <PresetCounts basis={basis} active={active} />

        <section aria-labelledby="filters-title" className="rounded-xl border p-4">
          <h2 id="filters-title" className="sr-only">
            {copy.items.filters_label}
          </h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <Select
              label="Attack type"
              value={filters.attack_type ?? ""}
              options={[any, ...Object.keys(meta.data?.attack_types_test ?? {}).map((t): [string, string] => [t, attackTypeName(t)])]}
              onChange={(v) => set("attack_type", v)}
            />
            <Select
              label="Verifier"
              value={filters.verdict ?? ""}
              options={[any, ...Object.keys(labels.verdicts).map((v): [string, string] => [v, verdictName(v)])]}
              onChange={(v) => set("verdict", v)}
            />
            <Select
              label={copy.items.condition_label}
              value={condition}
              options={[["baseline", conditionName("baseline")], ["treatment", conditionName("treatment")]]}
              onChange={(v) => set("condition", v === "treatment" ? "" : v)}
            />
            <Select
              label="Outcome"
              value={filters.outcome ?? ""}
              options={[any, ...Object.keys(labels.outcomes).map((o): [string, string] => [o, outcomeName(o)])]}
              onChange={(v) => set("outcome", v)}
            />
            <Select
              label="Failure label"
              value={filters.label ?? ""}
              options={[any, ...Object.keys(labels.failure_labels).map((l): [string, string] => [l, failureLabelName(l)])]}
              onChange={(v) => set("label", v)}
            />
          </div>
          {chips.length > 0 && (
            <div className="mt-4 flex flex-wrap items-center gap-2">
              {chips.map(([k, v]) => (
                <button
                  key={k}
                  type="button"
                  onClick={() => set(k, "")}
                  className="inline-flex min-h-11 items-center gap-1 rounded-full bg-muted px-3 text-sm sm:min-h-8"
                  aria-label={`Remove filter: ${filterLabel(k, v)}`}
                >
                  {filterLabel(k, v)}
                  <X aria-hidden="true" className="size-3.5" />
                </button>
              ))}
              <button type="button" onClick={clearAll} className="min-h-11 px-2 text-sm font-medium underline underline-offset-4 sm:min-h-8">
                {copy.items.clear}
              </button>
            </div>
          )}
        </section>

        <p aria-live="polite" className="text-sm text-muted-foreground tabular-nums">
          {items.data
            ? total
              ? `Showing ${first}–${last} of ${total} questions; outcome and failure label are for ${conditionName(condition).toLowerCase()}.`
              : copy.items.empty
            : ""}
        </p>

        {items.error ? (
          <ErrorState error={items.error} onRetry={items.retry} />
        ) : !items.data ? (
          <LoadingState />
        ) : total === 0 ? (
          <div className="rounded-xl border p-6 text-sm">
            <p>{copy.items.empty}</p>
            <button type="button" onClick={clearAll} className="mt-2 min-h-11 font-medium underline underline-offset-4 sm:min-h-0">
              {copy.items.clear}
            </button>
          </div>
        ) : (
          <DataTable<ItemRow>
            caption={`Test questions, ${basisName(basis)} basis`}
            rowKey={(r) => r.id}
            rows={items.data.items}
            columns={[
              {
                key: "id",
                header: "Question",
                primary: true,
                className: "w-[45%]",
                cell: (r) => (
                  <div className="space-y-1">
                    <Link
                      href={itemHref(r.id, basis)}
                      aria-label={`${r.id}: ${r.question}`}
                      className="font-mono text-sm font-medium underline underline-offset-4"
                    >
                      {r.id}
                    </Link>
                    <p className="text-sm font-normal">{r.question}</p>
                  </div>
                ),
              },
              {
                key: "type",
                header: "Company and type",
                cell: (r) => (
                  <span>
                    {r.company}
                    <span className="block text-xs text-muted-foreground">{attackTypeName(r.attack_type)}</span>
                  </span>
                ),
              },
              { key: "baseline", header: conditionName("baseline"), cell: (r) => <OutcomeBadge outcome={r.baseline.outcome} /> },
              { key: "verdict", header: "Verifier", cell: (r) => <VerdictBadge verdict={r.verdict} /> },
              { key: "treatment", header: conditionName("treatment"), cell: (r) => <OutcomeBadge outcome={r.treatment.outcome} /> },
              {
                key: "flags",
                header: "Notes",
                cell: (r) => (
                  <span className="flex flex-wrap gap-1">
                    {r.corrected && <FlagBadge>{copy.items.flags.corrected}</FlagBadge>}
                    {r.unparseable && <FlagBadge>{copy.items.flags.unparseable}</FlagBadge>}
                    {r.handchecked && <FlagBadge>{copy.items.flags.handchecked}</FlagBadge>}
                    {!r.corrected && !r.unparseable && !r.handchecked && <span className="text-muted-foreground">—</span>}
                  </span>
                ),
              },
            ]}
          />
        )}

        {items.data && pages > 1 && (
          <nav aria-label="Pages" className="flex items-center gap-2 text-sm">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => set("page", String(page - 1))}
              className="min-h-11 rounded-lg border px-4 disabled:opacity-50 sm:min-h-9"
            >
              Previous
            </button>
            <span className="text-muted-foreground tabular-nums">
              Page {page} of {pages}
            </span>
            <button
              type="button"
              disabled={page >= pages}
              onClick={() => set("page", String(page + 1))}
              className="min-h-11 rounded-lg border px-4 disabled:opacity-50 sm:min-h-9"
            >
              Next
            </button>
          </nav>
        )}
      </div>
    </div>
  );
}
