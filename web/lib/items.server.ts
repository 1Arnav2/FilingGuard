// Full item records, read at build time for the pre-rendered item pages only; never sent whole to
// the browser (each page gets its own item).

import { readFileSync } from "node:fs";
import { join } from "node:path";

import type { ItemDetail } from "./types";

let cache: ItemDetail[] | null = null;

export function allItems(): ItemDetail[] {
  cache ??= JSON.parse(readFileSync(join(process.cwd(), "generated", "items.json"), "utf-8")) as ItemDetail[];
  return cache;
}

export function itemById(id: string): ItemDetail | undefined {
  return allItems().find((item) => item.id === id);
}
