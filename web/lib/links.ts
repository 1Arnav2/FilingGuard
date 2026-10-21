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

export function itemHref(id: string, basis: Basis): string {
  return `/item/?id=${encodeURIComponent(id)}${basis === "as_scored" ? "&basis=as_scored" : ""}`;
}
