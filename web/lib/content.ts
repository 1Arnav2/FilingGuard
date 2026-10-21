// Content files and plain-name lookups. Numbers in copy are {summary:path} / {meta:path} placeholders,
// filled here from the API responses; tests/test_web_content.py keeps every one bound to results/.

import author from "@/content/author.json";
import copy from "@/content/copy.json";
import headline from "@/content/headline.json";
import labels from "@/content/labels.json";
import limitationGroups from "@/content/limitations.json";
import media from "@/content/media.json";
import method from "@/content/method.json";

import type { Basis, Meta, Summary } from "./types";

export { author, copy, headline, labels, limitationGroups, media, method };

export interface Sources {
  summary?: Summary | null;
  meta?: Meta | null;
}

const PLACEHOLDER = /\{(summary|meta):([A-Za-z0-9_.]+)\}/g;

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

/** Fill `{summary:path}` and `{meta:path}` placeholders; an unresolved one stays visible as "—". */
export function fill(text: string, sources: Sources): string {
  return text.replace(PLACEHOLDER, (_, source: "summary" | "meta", path: string) => {
    const value = resolvePath(sources[source], path);
    return value === undefined || value === null ? "—" : String(value);
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
