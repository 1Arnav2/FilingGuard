// Typed client for the read-only results API. Always same-origin: the dev server forwards /api,
// and in production FastAPI serves both the API and this static export.

import type { ItemDetail, ItemFilters, ItemPage, Meta, Summary } from "./types";

async function get<T>(path: string): Promise<T> {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error(`${path}: HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

const once = new Map<string, Promise<unknown>>();

/** One request per page load for files that never change; a failed request can be retried. */
function cached<T>(path: string): Promise<T> {
  if (!once.has(path)) {
    once.set(path, get<T>(path).catch((e) => {
      once.delete(path);
      throw e;
    }));
  }
  return once.get(path) as Promise<T>;
}

export function getSummary(): Promise<Summary> {
  return cached<Summary>("/api/summary");
}

export function getMeta(): Promise<Meta> {
  return cached<Meta>("/api/meta");
}

export function itemsQuery(filters: ItemFilters | Record<string, string | number | undefined>): string {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "") query.set(key, String(value));
  }
  return query.size ? `?${query}` : "";
}

export function getItems(filters: ItemFilters | Record<string, string | number | undefined> = {}): Promise<ItemPage> {
  return get<ItemPage>(`/api/items${itemsQuery(filters)}`);
}

export function getItem(id: string): Promise<ItemDetail> {
  return get<ItemDetail>(`/api/items/${encodeURIComponent(id)}`);
}
