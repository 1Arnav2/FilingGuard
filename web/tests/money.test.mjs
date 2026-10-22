// Display formatting for verifier reason figures (Phase 6c polish).
import assert from "node:assert/strict";
import { test } from "node:test";

import { money } from "../lib/format.ts";

test("scientific-notation dollar figures read as millions", () => {
  assert.equal(money(3.77e9), "$3,770M");
  assert.equal(money(1.074e9), "$1,074M");
  assert.equal(money(-3.24e11), "-$324,000M");
  assert.equal(money(2.5e6), "$2.5M");
});

test("figures below a million are whole dollars", () => {
  assert.equal(money(2.699e5), "$269,900");
  assert.equal(money(0), "$0");
});
