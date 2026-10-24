// The committed results, built into the site (D-079). `scripts/sync-results.mjs` copies them from
// results/ into generated/ before every build; nothing is fetched at run time.

import meta from "@/generated/meta.json";
import rows from "@/generated/rows.json";
import summary from "@/generated/summary.json";

import { type ItemQuery, queryItems } from "./query";
import type { ItemPage, ItemSource, Meta, Summary } from "./types";

export const ITEMS = rows as unknown as ItemSource[];

export function getSummary(): Promise<Summary> {
  return Promise.resolve(summary as unknown as Summary);
}

export function getMeta(): Promise<Meta> {
  return Promise.resolve(meta as unknown as Meta);
}

export function getItems(query: ItemQuery = {}): Promise<ItemPage> {
  return Promise.resolve(queryItems(ITEMS, query));
}
