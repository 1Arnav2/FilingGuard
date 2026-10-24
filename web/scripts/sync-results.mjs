// Copies the committed results the site shows into web/generated/ before every build (D-079).
// Reads only results/summary.json and the dashboard export; nothing is computed except the item rows'
// list fields, which are the export's own values. Usage: node scripts/sync-results.mjs [out-dir]

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const RESULTS = resolve(dirname(fileURLToPath(import.meta.url)), "..", "..", "results");
const SUMMARY = "summary.json";
const META = "dashboard/meta_v1.json";
const ITEMS = "dashboard/items_v1.jsonl";

function read(path) {
  return readFileSync(join(RESULTS, path), "utf-8");
}

/** The fields the Items list filters, sorts and shows, for both bases. */
function listRow(item) {
  return {
    id: item.id,
    company: item.company,
    attack_type: item.attack_type,
    subtype: item.subtype,
    question: item.question,
    outcomes: item.outcomes,
    verdict: item.verdict.full.decision,
    reason_codes: item.verdict.full.reasons.map((r) => r.code),
    corrected: item.correction?.status === "corrected",
    unparseable: item.answer.parse_error !== null,
    handchecked: item.handcheck !== null,
  };
}

const out = resolve(process.argv[2] ?? join(dirname(fileURLToPath(import.meta.url)), "..", "generated"));
const items = read(ITEMS).split("\n").filter((line) => line.trim()).map((line) => JSON.parse(line));
const files = {
  "summary.json": { ...JSON.parse(read(SUMMARY)), generated_from: `results/${SUMMARY}` },
  "meta.json": { ...JSON.parse(read(META)), generated_from: `results/${META}` },
  "items.json": items,
  "rows.json": items.map(listRow),
};
mkdirSync(out, { recursive: true });
for (const [name, data] of Object.entries(files)) {
  writeFileSync(join(out, name), JSON.stringify(data), "utf-8");
}
console.log(`results synced: ${items.length} items -> ${out}`);
