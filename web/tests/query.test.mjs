// Item list filtering in the page (Phase 6d); tests/test_static_site.py checks it against the API.
import assert from "node:assert/strict";
import { test } from "node:test";

import { queryItems } from "../lib/query.ts";

const score = (outcome, label = null) => ({ outcome, label, notes: [], abstained: false, scale_not_followed: false,
  unparseable: false, injection: null, answer_followed: null });
const item = (id, company, base, treat, verdict, flags = {}) => ({
  id, company, attack_type: "control", subtype: "x", question: "?", verdict, reason_codes: [],
  corrected: false, unparseable: false, handchecked: false, ...flags,
  outcomes: { corrected: { baseline: score(base), treatment: score(treat) }, as_scored: { baseline: score("missed"), treatment: score(treat) } },
});
const ITEMS = [item("FG-0002", "AAPL", "correct", "missed", "block"), item("FG-0001", "MSFT", "correct", "correct", "pass"),
  item("FG-0003", "AAPL", "missed", "missed", "flag", { corrected: true })];

test("default is all items by ID, on the corrected basis", () => {
  const page = queryItems(ITEMS);
  assert.deepEqual(page.items.map((r) => r.id), ["FG-0001", "FG-0002", "FG-0003"]);
  assert.equal(page.basis, "corrected");
  assert.equal(page.items[0].baseline.outcome, "correct");
});

test("search, flags and outcome on a condition and basis", () => {
  assert.equal(queryItems(ITEMS, { q: "aap" }).total, 2);
  assert.equal(queryItems(ITEMS, { corrected: "true" }).items[0].id, "FG-0003");
  assert.equal(queryItems(ITEMS, { outcome: "missed", condition: "baseline" }).total, 1);
  assert.equal(queryItems(ITEMS, { outcome: "missed", condition: "baseline", basis: "as_scored" }).total, 3);
});

test("descending sort reverses ties on the ID too, as the API does", () => {
  const page = queryItems(ITEMS, { sort: "company", order: "desc" });
  assert.deepEqual(page.items.map((r) => r.id), ["FG-0001", "FG-0003", "FG-0002"]);
  assert.deepEqual(queryItems(ITEMS, { sort: "verdict" }).items.map((r) => r.id), ["FG-0001", "FG-0003", "FG-0002"]);
});

test("paging", () => {
  const page = queryItems(ITEMS, { page: 2, page_size: 2 });
  assert.equal(page.total, 3);
  assert.deepEqual(page.items.map((r) => r.id), ["FG-0003"]);
});
