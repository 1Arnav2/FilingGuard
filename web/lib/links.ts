// Links into the Items view. Every count that links somewhere uses these, so a number always
// opens the questions it counts.

import { copy } from "./content";
import type { Basis } from "./types";

export function itemsHref(filters: Record<string, string>, basis: Basis): string {
  const query = new URLSearchParams(filters);
  if (basis === "as_scored") query.set("basis", basis);
  return `/items/${query.size ? `?${query}` : ""}`;
}

export function presetHref(id: string, basis: Basis): string {
  const preset = copy.items.presets.find((p) => p.id === id);
  return itemsHref(preset ? (preset.filters as Record<string, string>) : {}, basis);
}

/** An item's own page; `view` carries the list's filters and sort, so previous/next and Back keep them. */
export function itemHref(id: string, basis: Basis, view: Record<string, string> = {}): string {
  const query = new URLSearchParams(view);
  query.delete("page");
  query.delete("preset");
  query.delete("basis");
  if (basis === "as_scored") query.set("basis", basis);
  return `/item/${encodeURIComponent(id)}/${query.size ? `?${query}` : ""}`;
}
