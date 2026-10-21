// Run with `npm test` (Node's built-in test runner; Node strips the types from format.ts).
import assert from "node:assert/strict";
import { test } from "node:test";

import { evidenceText } from "../lib/format.ts";

test("nested gold evidence is shown as year: value pairs, never [object Object]", () => {
  const text = evidenceText({ 2024: 9992000000.0, 2025: 13762000000.0 });
  assert.equal(text, "2024: 9,992,000,000; 2025: 13,762,000,000");
  assert.ok(!text.includes("[object"));
});

test("scalars, lists and missing values", () => {
  assert.equal(evidenceText(29943000000.0), "29,943,000,000");
  assert.equal(evidenceText(0.0056), "0.0056");
  assert.equal(evidenceText("$29,943M"), "$29,943M");
  assert.equal(evidenceText([1, "a", { b: 2 }]), "1, a, b: 2");
  assert.equal(evidenceText(null), "—");
});
