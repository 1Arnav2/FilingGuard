# Phase 5 plan: eval run on the test split

**Status:** Proposed 2026-10-06 after the verifier freeze (`verifier-v1`, D-060). **Approved by the
owner with changes on 2026-10-06 (D-062), before any test-split call.** The verifier was reopened and
re-frozen the same day for H-032 (D-061). The test batch is not submitted without the owner's
separate go-ahead.

## Fixed inputs
- Test set `testset-v1`: 210 test items, of which 42 are controls, 32 injection items and 39 premise
  items (55 premise items minus the 16 on dev).
- Target `target-v1`, verifier `verifier-v1` (prompt `verifier_v2`), judge `premise_judge_v1`, and
  the scorer at D-059. The frozen-file tests must pass before every step.
- Latency sample: the 30 test IDs in `data/testset/latency_sample_v1.json`, recorded at the freeze.

## Cost

Unit costs are from `results/spend/ledger.jsonl`:
- target via file batch: $0.0096 per dev item
- target via the standard API: $0.0179 per call (the probe)
- judge: $0.0020 per call
- verifier model call: $0.0039 on average over 16 calls

The verifier makes a model call on about 1.2% of runs on dev (6 of 486: 243 answers and copies, two modes).

| Part | Basis | Estimate |
|---|---|---|
| Test target, file batch | 210 × $0.0096, high end +20% | $2.02–$2.42 |
| Judge | 39 baseline premise answers; treatment answers are the same text, so they come from the cache; plus the premise items among the 30 latency answers | $0.08–$0.12 |
| Latency sample, target | 30 standard-API calls | $0.54–$0.65 |
| Verifier, test answers and test seeded set | about 210 natural + about 360 seeded copies, two modes, about 1,140 runs; 1–3% reach the model at $0.004–$0.008 | $0.05–$0.25 |
| Verifier on the 30 latency answers | rules first; 0–2 model calls | $0.00–$0.02 |
| Test seeded set, scoring, statistics | no model calls | $0 |
| **Phase 5 total** | | **$2.69–$3.46** |

**Projected final spend:** $2.321 so far + $2.69–$3.46 = **$5.01–$5.78**. This trips the $5 warning
and stays under the $7 hard cap with $1.22–$1.99 to spare. Phases 6 and 7 make no model calls.

**Budget (owner's decision, D-062):** option 1. The verifier runs on the standard API, with one
model call per answer at most. The $5 warning is expected to trip; the run continues past it and
stops only at a spend gate or the $7 cap. (Options 2, file batch for the verifier, and 3, skipping
extras, were not chosen.)

**Spend gates in code (approved as written):**
- Test batch: a limit of $2.60, checked before each sub-batch, as on dev.
- Verifier: a Phase 5 cap of $0.40, counted from Phase 5's start.
- Project: the $7 hard cap.

**Measured projection for the test batch (step 2, 2026-10-06):** $2.02 at dev's mean output per
item; $2.60 if every item produced dev's 90th-percentile output. Before each sub-batch the code
projects the remainder at no less than $0.013 per item. So if real costs run near the 90th
percentile, the gate stops before the last sub-batch. That stop would be reported, not overridden:
the unsubmitted items are reported as not run, and resubmitting them needs the owner's approval
(D-063, 2026-10-06, before any test-split call).

## Order of steps
1. **Judge hand-check on dev (owner, EVAL §5).** A sheet of the 16 dev premise items with the judge's
   decisions, baseline and treatment (32 decisions; on dev the treatment answers equal baseline, as
   none was blocked). Cohen's kappa is reported overall and per condition. No cost. *Sheet built
   2026-10-06: `review/judge_handcheck_dev_v1.xlsx`.*
2. **Test run harness.** *Built and checks run 2026-10-06, nothing submitted (D-062).* `dev_run` is generalised to take the split, and the test split is refused
   without an explicit `--owner-approved-test` flag. Pre-submit checks, where any failure stops:
   - batch price is half of standard
   - target code equals `target-v1`, and the verifier freeze test passes
   - each of the 32 test injection items' planted chunk matches its frozen hash
   - the cached freeze-time prompts rebuild byte for byte
   - 210 test items, 0 dev

   Report the checks and wait for the go-ahead.
2a. **Offline detector check (owner, D-057).** The owner's 10 planted texts go through the frozen
   detector after the re-freeze and before the test batch. No model calls. The result is reported as
   is, and the detector is not changed afterwards.
3. **Test target batch (after the go-ahead).** File-based jobs only, the same request path as
   the dev re-run (H-028).
   - Sub-batches of 1, 30, 30, 50, 50 and 49 items in ID order. The first is a one-item probe.
   - Every reply is checked against the response schema and the frozen parser before the next
     sub-batch, stopping on the first invalid reply.
   - Missing items are re-submitted alone, and that is logged.
4. **Baseline scoring.** The scorer runs on all 210, with judge calls on the 39 premise answers.
   This writes `results/test/baseline_scores_v1.jsonl`.
5. **Test seeded set.** Copies of baseline answers scored Correct with a figure, made with the same
   six transforms and gate. It is frozen with its hash before the verifier sees any of it. No calls.
6. **Verifier run.** The frozen verifier runs once on the 210 natural answers and the seeded set,
   in both modes (full; quote rule off for the seeded headline). Natural answers use the full mode
   for treatment.
7. **Treatment scoring.** Blocked answers are abstentions (EVAL §3, D-059), and `answer_followed`
   is kept for every injection item.
8. **Latency sample.** The 30 items run on the standard API. The target is timed, and so is the
   verifier on those answers. The consistency check reports how many of the 30 reach the same scored
   outcome as their batch answer.
9. **Owner's hand-check (EVAL §10 4a, D-062).** The sheet holds:
   - 30 scored test rows drawn by seed `20261006-handcheck`, stratified by type, each in both
     conditions (60 decisions)
   - every baseline row not scored Correct
   - every natural answer the verifier blocked or flagged
   - every missed seeded error

   Each row shows the answer text, the gold value and the scorer's outcome. Agreement on the random
   30 is reported separately from the other rows.
9a. **Scorer faults found on test (D-062).** Results are reported twice: as scored by the frozen
   scorer, and after corrections. A correction is allowed only for a parsing fault (a figure, sign,
   scale, period or label misread), never for a rule in EVAL §3. Every corrected row is listed with
   before, after and the reason, and the owner approves each one. The verifier is never changed.
10. **Statistics and summary.** Wilson intervals, McNemar's exact test, bootstrap by type, the
    failure taxonomy and `results/summary.json`. Every bar is marked met, not met or not testable
    (D-056), with the seeded-error thresholds alongside. The bars are evaluated on the corrected
    scores, with the as-scored result shown beside each.

## What I report
- After step 2: the pre-submit checks, and the test batch's projected cost against its limit.
- After step 3: valid replies out of 210, missing items, and the cost.
- After steps 4–7, in one report:
  - baseline and treatment outcomes by type
  - Unsupported count at baseline and whether McNemar's test can reach p < 0.05
  - verifier precision and recall (D-049)
  - blocks by reason and by basis (XBRL lookup vs text alone)
  - false-block rate
  - seeded detection by transform (macro over T1, T3–T6, quote rule off), with T2 as counts
  - control abstain rate, and control abstentions added
  - `injection_followed` and `answer_followed` counts
  - model calls and spend
- After steps 8–10: latency (median and p95 per condition, "measured on a 30-item sample"), the
  consistency check, the hand-check agreement (the random 30 separately), the judge kappa, every
  proposed scorer correction for approval, and each bar's status on corrected and as-scored
  results.

Nothing is tuned on test. A fault found on test is reported as found, not fixed.
