// Typed client for the read-only results API. Always same-origin: the dev server forwards /api.

import type { ItemDetail, ItemFilters, ItemPage, Summary } from "./types";

async function get<T>(path: string): Promise<T> {
  const response = await fetch(path, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error(`${path}: HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}

export function getSummary(): Promise<Summary> {
  return get<Summary>("/api/summary");
}

export function getItems(filters: ItemFilters = {}): Promise<ItemPage> {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "") query.set(key, String(value));
  }
  const suffix = query.size ? `?${query}` : "";
  return get<ItemPage>(`/api/items${suffix}`);
}

export function getItem(id: string): Promise<ItemDetail> {
  return get<ItemDetail>(`/api/items/${encodeURIComponent(id)}`);
}
