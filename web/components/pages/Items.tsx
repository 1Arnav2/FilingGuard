"use client";

import { X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";

import { FlagBadge, OutcomeBadge, VerdictBadge } from "@/components/data/badges";
import { DataTable } from "@/components/data/DataTable";
import { ErrorState, LoadingState, PageHeader } from "@/components/data/layout";
import { getItems, getMeta } from "@/lib/data";
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

export const PAGE_SIZE = 25;
const FILTER_KEYS = ["q", "attack_type", "verdict", "outcome", "label", "condition", "corrected", "unparseable", "handchecked"] as const;
const SORT_KEYS = Object.keys(copy.items.sort);
type FilterKey = (typeof FILTER_KEYS)[number];
type Filters = Partial<Record<FilterKey, string>>;
const PRESETS = copy.items.presets as { id: string; name: string; filters: Filters }[];

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
    case "q":
      return `“${value}”`;
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

/** Search by ID or company; the URL updates a moment after typing stops. */
function Search({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [text, setText] = useState(value);
  const input = useRef<HTMLInputElement>(null);
  // Follow the URL (Clear all, a preset) only when the box is not being typed in.
  useEffect(() => {
    if (document.activeElement !== input.current) setText(value);
  }, [value]);
  useEffect(() => {
    if (text === value) return;
    const t = setTimeout(() => onChange(text.trim()), 300);
    return () => clearTimeout(t);
  }, [text, value, onChange]);
  return (
    <label className="flex flex-col gap-1 text-xs font-medium text-muted-foreground">
      {copy.items.search_label}
      <input
        ref={input}
        type="search"
        value={text}
        maxLength={40}
        placeholder={copy.items.search_placeholder}
        onChange={(e) => setText(e.target.value)}
        className="min-h-11 rounded-lg border bg-background px-3 text-sm text-foreground placeholder:text-muted-foreground sm:min-h-9"
      />
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
  const sortKey = SORT_KEYS.includes(params.get("sort") ?? "") ? (params.get("sort") as string) : "id";
  const order: "asc" | "desc" = params.get("order") === "desc" ? "desc" : "asc";
  const key = params.toString();

  // A shared link with ?preset=... opens that view with its filters spelled out in the URL.
  useEffect(() => {
    const preset = PRESETS.find((p) => p.id === params.get("preset"));
    if (!preset) return;
    const next = new URLSearchParams(preset.filters as Record<string, string>);
    if (basis === "as_scored") next.set("basis", basis);
    router.replace(`${pathname}${next.size ? `?${next}` : ""}`, { scroll: false });
  }, [params, basis, pathname, router]);

  const items = useData(() => getItems({ ...filters, basis, sort: sortKey, order, page, page_size: PAGE_SIZE }), [key, basis]);

  const set = (name: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(name, value);
    else next.delete(name);
    next.delete("preset");
    if (name !== "page") next.delete("page");
    router.replace(`${pathname}${next.size ? `?${next}` : ""}`, { scroll: false });
  };
  const setSort = (k: string, o: "asc" | "desc") => {
    const next = new URLSearchParams(params);
    if (k === "id" && o === "asc") {
      next.delete("sort");
      next.delete("order");
    } else {
      next.set("sort", k);
      next.set("order", o);
    }
    next.delete("page");
    router.replace(`${pathname}${next.size ? `?${next}` : ""}`, { scroll: false });
  };
  const onSort = (k: string) => setSort(k, k === sortKey && order === "asc" ? "desc" : "asc");
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
          <div className="mb-3 grid grid-cols-1 gap-3 md:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
            <Search value={filters.q ?? ""} onChange={(v) => set("q", v)} />
            <div className="grid grid-cols-2 gap-3 md:hidden">
              <Select
                label={copy.items.sort_label}
                value={sortKey}
                options={Object.entries(copy.items.sort)}
                onChange={(v) => setSort(v, order)}
              />
              <Select
                label="Order"
                value={order}
                options={Object.entries(copy.items.sort_order)}
                onChange={(v) => setSort(sortKey, v as "asc" | "desc")}
              />
            </div>
          </div>
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
            sort={{ key: sortKey, order, onSort }}
            columns={[
              {
                key: "id",
                header: "Question",
                primary: true,
                sortKey: "id",
                className: "w-[38%]",
                cell: (r) => (
                  <div className="space-y-1">
                    <Link
                      href={itemHref(r.id, basis, Object.fromEntries(params))}
                      aria-label={`${r.id}: ${r.question}`}
                      className="font-mono text-sm font-medium underline underline-offset-4"
                    >
                      {r.id}
                    </Link>
                    <p className="text-sm font-normal">{r.question}</p>
                  </div>
                ),
              },
              { key: "company", header: "Company", sortKey: "company", cell: (r) => r.company },
              { key: "type", header: "Attack type", sortKey: "attack_type", cell: (r) => attackTypeName(r.attack_type) },
              { key: "baseline", header: conditionName("baseline"), sortKey: "baseline", cell: (r) => <OutcomeBadge outcome={r.baseline.outcome} /> },
              { key: "verdict", header: "Verifier", sortKey: "verdict", cell: (r) => <VerdictBadge verdict={r.verdict} /> },
              { key: "treatment", header: conditionName("treatment"), sortKey: "treatment", cell: (r) => <OutcomeBadge outcome={r.treatment.outcome} /> },
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
