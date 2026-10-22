// Content files and plain-name lookups. Numbers in copy are {summary:path} / {meta:path} placeholders,
// filled here from the API responses; tests/test_web_content.py keeps every one bound to results/.

import author from "@/content/author.json";
import copy from "@/content/copy.json";
import headline from "@/content/headline.json";
import labels from "@/content/labels.json";
import limitationGroups from "@/content/limitations.json";
import media from "@/content/media.json";
import method from "@/content/method.json";

import { money } from "./format";
import type { Basis, Meta, Summary } from "./types";

export { author, copy, headline, labels, limitationGroups, media, method };

export interface Sources {
  summary?: Summary | null;
  meta?: Meta | null;
}

const PLACEHOLDER = /\{(summary|meta):([A-Za-z0-9_.]+)(?:\|(usd0|usd2|pct0|pct1))?\}/g;

/** Display formats a placeholder may name after a bar: money, or a share as a percentage. */
const FORMATS: Record<string, (v: number) => string> = {
  usd0: (v) => `$${v.toLocaleString("en-US", { maximumFractionDigits: 0 })}`,
  usd2: (v) => `$${v.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
  pct0: (v) => `${(v * 100).toFixed(0)}%`,
  pct1: (v) => `${(v * 100).toFixed(1)}%`,
};

/** The value at a dotted path, with `{basis}` replaced by the chosen basis. A key that itself contains a
 * dot (such as `unsupported_claim_rate_falls_p_lt_0.05`) is matched by joining segments. */
export function resolvePath(root: unknown, path: string, basis: Basis = "corrected"): unknown {
  const parts = path.replace("{basis}", basis).split(".");
  let node: unknown = root;
  let key = "";
  for (const part of parts) {
    if (node === null || typeof node !== "object") return undefined;
    key = key ? `${key}.${part}` : part;
    if (key in (node as Record<string, unknown>)) {
      node = (node as Record<string, unknown>)[key];
      key = "";
    }
  }
  return key ? undefined : node;
}

/** Fill `{summary:path}` and `{meta:path}` placeholders, with an optional `|format`; an unresolved one
 * stays visible as "—". */
export function fill(text: string, sources: Sources): string {
  return text.replace(PLACEHOLDER, (_, source: "summary" | "meta", path: string, format?: string) => {
    const value = resolvePath(sources[source], path);
    if (value === undefined || value === null) return "—";
    return format && typeof value === "number" ? FORMATS[format](value) : String(value);
  });
}

type Named = Record<string, { name: string; definition: string }>;

function lookup(map: Record<string, string>, code: string | null | undefined): string {
  if (!code) return "—";
  return map[code] ?? code.replaceAll("_", " ");
}

export const attackTypeName = (code: string) => (labels.attack_types as Named)[code]?.name ?? lookup({}, code);
export const attackTypeDefinition = (code: string) => (labels.attack_types as Named)[code]?.definition ?? "";
export const subtypeName = (code: string) => lookup(labels.subtypes, code);
export const outcomeName = (code: string) => (labels.outcomes as Named)[code]?.name ?? lookup({}, code);
export const verdictName = (code: string) => (labels.verdicts as Named)[code]?.name ?? lookup({}, code);
export const conditionName = (code: string) => lookup(labels.conditions, code);
export const basisName = (code: string) => lookup(labels.bases, code);
export const statusName = (code: string) => lookup(labels.statuses, code);
export const reasonName = (code: string) => lookup(labels.reason_codes, code);
export const reasonBasisName = (code: string) => lookup(labels.reason_bases, code);
export const failureLabelName = (code: string | null) => lookup(labels.failure_labels, code);
export const expectedName = (code: string) => lookup(labels.expected_behaviors, code);
export const transformName = (code: string) => (labels.transforms as Named)[code]?.name ?? code;
export const transformDefinition = (code: string) => (labels.transforms as Named)[code]?.definition ?? "";
export const goldFieldName = (key: string) => (labels.gold_fields as Record<string, string>)[key];

/** The owner's hand-check reasons ("random 30; verifier block") in plain words. */
export function handcheckReasons(why: string): string {
  return why
    .split(";")
    .map((part) => lookup(labels.handcheck_reasons, part.trim()))
    .join(" · ");
}

/** The owner's verdict; an empty one is a row decided earlier under D-071. */
export function handcheckVerdict(verdict: string | null): string {
  return (labels.handcheck_verdicts as Record<string, string>)[verdict ?? ""] ?? verdict ?? "—";
}

/** Insert `{name}` values into a template that holds no numbers of its own. */
export function template(text: string, values: Record<string, string>): string {
  return text.replace(/\{([a-z_]+)\}/g, (_, key: string) => values[key] ?? "");
}

/** A verifier reason detail as recorded, made readable: the metric in plain words and each figure in
 * scientific notation shown as money ("operating income $3,770M does not match the fact for 2025").
 * Every figure the verifier writes this way is a dollar amount from the filing's XBRL data. */
export function reasonDetail(detail: string): string {
  return detail
    .replace(/^([a-z_]+)(?= )/, (m) => (labels.metric_names as Record<string, string>)[m] ?? m.replaceAll("_", " "))
    .replace(/-?\d+(?:\.\d+)?e[+-]\d+/gi, (m) => money(Number(m)));
}

/** The LinkedIn URL, or "" while author.json still holds the placeholder text. */
export function linkedinUrl(): string {
  return author.linkedin.startsWith("https://") ? author.linkedin : "";
}

/** "Get in touch": LinkedIn if set, else email, else the author block on the page. */
export function contactHref(): string {
  if (linkedinUrl()) return linkedinUrl();
  if (author.email) return `mailto:${author.email}`;
  return "#author";
}

export type GlossarySource =
  | "outcomes" | "verdicts" | "conditions" | "bases" | "attack_types" | "transforms" | "metrics" | "reason_codes";

/** Every glossary entry of one kind: [code, name, definition]. */
export function glossaryEntries(source: GlossarySource): [string, string, string][] {
  const named = (m: Named) => Object.entries(m).map(([k, v]): [string, string, string] => [k, v.name, v.definition]);
  const paired = (names: Record<string, string>, defs: Record<string, string>) =>
    Object.keys(names).map((k): [string, string, string] => [k, names[k], defs[k] ?? ""]);
  switch (source) {
    case "outcomes":
      return named(labels.outcomes as Named);
    case "verdicts":
      return named(labels.verdicts as Named);
    case "attack_types":
      return named(labels.attack_types as Named);
    case "transforms":
      return named(labels.transforms as Named).map(([k, n, d]) => [k, `${n} (${k})`, d]);
    case "metrics":
      return named(copy.results.metrics as Named);
    case "conditions":
      return paired(labels.conditions, labels.condition_definitions);
    case "bases":
      return paired(labels.bases, labels.basis_definitions);
    case "reason_codes":
      return paired(labels.reason_codes, labels.reason_definitions);
  }
}

/** The definition of one term, for tooltips. */
export function definition(source: GlossarySource, code: string): string {
  return glossaryEntries(source).find(([k]) => k === code)?.[2] ?? "";
}
