import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";

import { cn } from "@/lib/utils";

export interface Column<T> {
  key: string;
  header: React.ReactNode;
  cell: (row: T) => React.ReactNode;
  /** Shown as the card title on narrow screens instead of as a labelled field. */
  primary?: boolean;
  className?: string;
  /** The API sort key, when the column can be sorted. */
  sortKey?: string;
}

export interface TableSort {
  key: string;
  order: "asc" | "desc";
  onSort: (key: string) => void;
}

/** A table on wide screens and one card per row on narrow screens, so no column is ever hidden. */
export function DataTable<T>({ caption, columns, rows, rowKey, sort }: {
  caption: string;
  columns: Column<T>[];
  rows: T[];
  rowKey: (row: T) => string;
  sort?: TableSort;
}) {
  const primary = columns.find((c) => c.primary);
  const rest = columns.filter((c) => c !== primary);
  return (
    <>
      <div className="hidden overflow-hidden rounded-xl border md:block">
        <table className="w-full text-sm tabular-nums">
          <caption className="sr-only">{caption}</caption>
          <thead className="bg-muted/50 text-left text-xs text-muted-foreground">
            <tr>
              {columns.map((c) => {
                const active = sort && c.sortKey && sort.key === c.sortKey;
                const Icon = active ? (sort.order === "asc" ? ArrowUp : ArrowDown) : ArrowUpDown;
                return (
                  <th
                    key={c.key}
                    scope="col"
                    aria-sort={sort && c.sortKey ? (active ? (sort.order === "asc" ? "ascending" : "descending") : "none") : undefined}
                    className={cn("px-4 py-3 align-bottom font-medium", c.className)}
                  >
                    {sort && c.sortKey ? (
                      <button
                        type="button"
                        onClick={() => sort.onSort(c.sortKey as string)}
                        className={cn("-mx-1.5 inline-flex items-center gap-1 rounded-md px-1.5 py-1 text-left hover:bg-muted hover:text-foreground", active && "text-foreground")}
                      >
                        {c.header}
                        <Icon aria-hidden="true" className="size-3.5 shrink-0" />
                      </button>
                    ) : (
                      c.header
                    )}
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={rowKey(row)} className="border-t align-top">
                {columns.map((c, i) =>
                  i === 0 ? (
                    <th key={c.key} scope="row" className={cn("px-4 py-3 text-left font-normal", c.className)}>
                      {c.cell(row)}
                    </th>
                  ) : (
                    <td key={c.key} className={cn("px-4 py-3", c.className)}>
                      {c.cell(row)}
                    </td>
                  ),
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ul aria-label={caption} className="space-y-3 md:hidden">
        {rows.map((row) => (
          <li key={rowKey(row)} className="rounded-xl border bg-card p-4 text-sm tabular-nums">
            {primary && <div className="mb-2 font-medium">{primary.cell(row)}</div>}
            <dl className="space-y-2">
              {rest.map((c) => (
                <div key={c.key} className="grid grid-cols-[minmax(0,2fr)_minmax(0,3fr)] gap-3">
                  <dt className="text-xs text-muted-foreground">{c.header}</dt>
                  <dd className="min-w-0 break-words">{c.cell(row)}</dd>
                </div>
              ))}
            </dl>
          </li>
        ))}
      </ul>
    </>
  );
}
