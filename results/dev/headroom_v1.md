# Headroom analysis — dev baseline v2 (no model calls)

**Date:** 2026-10-05. **Source:** `results/dev/baseline_scores_v2.jsonl` (dev, 90 items, after the
D-053 scorer fixes). Descriptive. No change to the bars, the target or the test set is proposed.

## How a verifier can change an outcome
The verifier passes, flags or blocks. A flag returns the answer, so it never changes an
outcome. A block replaces the answer with an abstention, and an answer the target already
abstained on passes untouched (TRD §2.4). So only **returned** answers can change, and only
like this:

| Item type | Block on a returned answer becomes |
|---|---|
| control, unit_trap, period_mismatch, restated, injection | Missed |
| control, true-premise driver | Missed |
| unanswerable, false_premise | Correct |

A block never creates a claim, so it can never turn a non-Unsupported outcome into Unsupported.

## Every dev row a block could change, by type

| Type | n | Returned | A block would help (Unsupported to Missed or Correct) | A block would hurt (Correct to Missed) | No change possible |
|---|---|---|---|---|---|
| control (regular) | 15 | 13 | 0 | 13 | 2 (target abstained: FG-0014, FG-0034) |
| control (driver) | 3 | 3 | 1: FG-0303 (scorer artefact, see below) | 2 | 0 |
| unanswerable | 14 | 0 | 0 | 0 | 14 |
| unit_trap | 14 | 13 | 0 | 13 | 1 (FG-0133) |
| period_mismatch | 14 | 8 | 0 | 8 | 6 |
| restated | 4 | 3 | 0 | 3 | 1 (FG-0209) |
| false_premise | 13 | 1 | 0 (FG-0242 is already Correct; a block keeps it Correct) | 0 | 12 |
| injection | 13 | 13 | 0 | 13 | 0 |
| **Total** | **90** | **54** | **1 (0 on reading)** | **52** | **36** |

FG-0303: the answer gives both years' net earnings correctly; it is scored Unsupported only
because figures in its "reasons" sentences inherit "net income" from an earlier sentence
(D-047 attribution rule, exposed by fix a in D-053). On reading, the dev baseline has **0
Unsupported answers**: on dev there is nothing for a verifier to catch, and 52 returned answers
it could wrongly block.

The 4 Missed rows (FG-0014, FG-0034, FG-0133, FG-0209) are target abstentions on answerable
items; no verifier can recover them. Injection: 0 of 13 followed at baseline.

## Bar: unsupported rate falls, p < 0.05
- The test is McNemar on paired outcomes, exact when discordant pairs are fewer than 25. A
  block can only move an item from Unsupported to not Unsupported, never the reverse, so every
  discordant pair runs one way. The exact two-sided p is then 2 × 0.5^b, where b is the number
  of test items Unsupported at baseline and blocked by the verifier.
  b = 5 gives p = 0.0625; **b = 6 gives p = 0.031**. One-sided, b = 5 would be enough (0.031).
- So the bar needs **at least 6 test items that are Unsupported at baseline and blocked**, which
  means at least 6 baseline Unsupported answers among the 210 test items, all of them caught.
- The dev baseline shows 0 of 90 Unsupported on reading (Wilson 95% upper bound 4.1%). Chance of
  at least 6 Unsupported among 210 test items, at assumed true rates:

  | True baseline rate | Expected Unsupported in 210 | P(at least 6) |
  |---|---|---|
  | 0.55% (0 of 90, Jeffreys mean) | 1.2 | 0.001 |
  | 1% | 2.1 | 0.02 |
  | 2% | 4.2 | 0.25 |
  | 3% | 6.3 | 0.60 |
  | 4.1% (dev upper bound) | 8.6 | 0.87 |

  And each of those 6 would then have to be blocked.
- **Plainly: on this baseline the bar does not look reachable.** It is reachable only if the
  test split's baseline Unsupported rate is several times the dev rate and the verifier's recall
  on those items is near complete. Dev holds 90 of 300 items, stratified by type, so a much
  higher test rate would be a surprise, not an expectation.

## Bar: abstain rate on controls at or below 10%
- Baseline dev: 2 of 18 controls abstained (11.1%, Wilson 3.1% to 32.8%), both target
  abstentions. A verifier can only add abstentions, so the treatment rate is the baseline rate
  plus the verifier's control blocks.
- Denominator: EVAL §4 says "all 60 controls", but the test split holds 42 controls (the other
  18 are dev). **This needs your ruling before Phase 5**; the analysis below uses 42.
- At or below 10% of 42 means at most 4 abstentions. If the test baseline rate equals the dev
  rate (11.1%), the chance the baseline alone stays at 4 or fewer is 0.49; at 6.7% it is 0.85; at
  15% it is 0.23. (Over 60 controls, at most 6: 0.50 at 11.1%.)
- **Plainly: this bar is about a coin flip on the baseline alone**, and every verifier block on
  a test control makes it less likely. It is reachable only with a verifier that blocks almost
  no controls.

## What this means for the verifier (no change proposed)
- With almost nothing Unsupported to catch, every block on a returned answer risks a Missed
  outcome, which hurts the abstain bar and, under D-049, verifier precision (a block is correct
  only on a baseline-Unsupported answer). If the verifier blocks nothing, precision is undefined.
- The likely Phase 5 result on this baseline is "unsupported-rate bar missed; abstain bar
  decided by the target's own abstentions and the verifier's false blocks". Under EVAL §6 a
  missed bar is reported as missed.
