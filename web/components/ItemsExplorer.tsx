"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

import { Chip, Loading, PageTitle } from "@/components/ui";
import { getItems, getMeta } from "@/lib/api";
import { BASIS_LABEL, useBasis } from "@/lib/basis";
import type { Condition, Decision, ItemFilters, Outcome } from "@/lib/types";
import { useData } from "@/lib/useData";

const PAGE_SIZE = 25;
const OUTCOMES: Outcome[] = ["correct", "missed", "unsupported"];
const VERDICTS: Decision[] = ["pass", "flag", "block"];
const LABELS = ["wrong_number", "wrong_unit", "wrong_period", "stale_restated", "fabricated_fact", "accepted_false_premise",
  "rejected_true_premise", "injection_followed", "bad_citation", "retrieval_miss", "other"]; // EVAL §7

function Select({ label, value, options, onChange }: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  return (
    <label className="flex flex-col text-xs text-slate-500">
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 rounded border border-slate-300 bg-white px-2 py-1 text-sm text-slate-900"
      >
        <option value="">any</option>
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
    </label>
  );
}

export default function ItemsExplorer() {
  const basis = useBasis();
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const meta = useData(getMeta);

  const filters: ItemFilters = {
    attack_type: params.get("attack_type") ?? undefined,
    verdict: (params.get("verdict") as Decision) ?? undefined,
    outcome: (params.get("outcome") as Outcome) ?? undefined,
    label: params.get("label") ?? undefined,
    condition: (params.get("condition") as Condition) ?? "treatment",
    page: Number(params.get("page") ?? "1"),
    page_size: PAGE_SIZE,
    basis,
  };
  const key = params.toString();
  const { data, error } = useData(() => getItems(filters), [key, basis]);

  const set = (name: string, value: string) => {
    const next = new URLSearchParams(params);
    if (value) next.set(name, value);
    else next.delete(name);
    if (name !== "page") next.delete("page");
    router.replace(`${pathname}?${next}`);
  };
  const detailHref = (id: string) => `/item/?id=${id}${basis === "as_scored" ? "&basis=as_scored" : ""}`;
  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <div>
      <PageTitle title="Items">
        Every test item with its outcomes on the <strong>{BASIS_LABEL[basis].toLowerCase()}</strong> basis. Outcome and label
        filters apply to the condition you choose. Open an item for its gold label, answer, verdict and evidence.
      </PageTitle>

      <div className="mt-4 grid grid-cols-2 gap-3 rounded-lg border border-slate-200 bg-white p-3 sm:grid-cols-3 lg:grid-cols-5">
        <Select label="Attack type" value={filters.attack_type ?? ""} options={Object.keys(meta.data?.attack_types_test ?? {})}
          onChange={(v) => set("attack_type", v)} />
        <Select label="Verdict" value={filters.verdict ?? ""} options={VERDICTS} onChange={(v) => set("verdict", v)} />
        <Select label="Outcome" value={filters.outcome ?? ""} options={OUTCOMES} onChange={(v) => set("outcome", v)} />
        <Select label="Failure label" value={filters.label ?? ""} options={LABELS} onChange={(v) => set("label", v)} />
        <label className="flex flex-col text-xs text-slate-500">
          Outcome and label of
          <select
            value={filters.condition}
            onChange={(e) => set("condition", e.target.value === "treatment" ? "" : e.target.value)}
            className="mt-1 rounded border border-slate-300 bg-white px-2 py-1 text-sm text-slate-900"
          >
            <option value="treatment">with verifier</option>
            <option value="baseline">baseline</option>
          </select>
        </label>
      </div>

      {!data ? (
        <div className="mt-4">
          <Loading error={error} />
        </div>
      ) : (
        <>
          <p className="mt-4 text-sm text-slate-600">
            {data.total} matching {data.total === 1 ? "item" : "items"}
            {data.total > 0 && `, page ${data.page} of ${pages}`}
          </p>
          <ul className="mt-2 divide-y divide-slate-100 rounded-lg border border-slate-200 bg-white">
            {data.items.map((i) => (
              <li key={i.id}>
                <Link href={detailHref(i.id)} className="block px-3 py-3 hover:bg-slate-50">
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="font-mono font-medium text-slate-900">{i.id}</span>
                    <span className="text-slate-500">{i.company}</span>
                    <span className="font-mono text-slate-500">{i.attack_type}</span>
                    {i.corrected && <span className="rounded bg-violet-100 px-1.5 text-violet-800">D-071 corrected</span>}
                    {i.unparseable && <span className="rounded bg-slate-200 px-1.5 text-slate-700">unparseable</span>}
                    {i.handchecked && <span className="rounded bg-sky-100 px-1.5 text-sky-800">hand-checked</span>}
                  </div>
                  <div className="mt-1 text-sm text-slate-800">{i.question}</div>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-slate-500">
                    baseline <Chip value={i.baseline.outcome} />
                    with verifier <Chip value={i.treatment.outcome} />
                    verdict <Chip value={i.verdict} />
                    {i.reason_codes.length > 0 && <span className="font-mono">{[...new Set(i.reason_codes)].join(", ")}</span>}
                  </div>
                </Link>
              </li>
            ))}
          </ul>
          {pages > 1 && (
            <div className="mt-3 flex items-center gap-2 text-sm">
              <button type="button" disabled={data.page <= 1} onClick={() => set("page", String(data.page - 1))}
                className="rounded border border-slate-300 bg-white px-3 py-1 disabled:opacity-40">
                Previous
              </button>
              <button type="button" disabled={data.page >= pages} onClick={() => set("page", String(data.page + 1))}
                className="rounded border border-slate-300 bg-white px-3 py-1 disabled:opacity-40">
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
