# Verifier dev report

Dev split only, descriptive. Every number below is read from a file in `results/verifier/`,
`results/seeded/` or `results/dev/`. The test split was not touched.

**All dev numbers are in-sample.** The verifier's rules were tuned on these same dev answers and
seeded copies (D-058, D-059), so dev detection and false-block rates are optimistic. The test seeded
set and the natural test answers are the real measure.

## Versions

| | v1 (2026-10-05) | v2, frozen as `verifier-v1` (2026-10-06) |
|---|---|---|
| Prompt | `verifier_v1`, `78769c4f...` | `verifier_v2`, `b87fc579...` |
| Seeded set | `dev_seeded_v1.jsonl`: 151 kept | `dev_seeded_v2.jsonl`: 153 kept (T2 rebuilt after H-030) |
| Results | `dev_verifier_v1*`, `checks_v1.json` | `dev_verifier_v2*`, `checks_v2.json`, `dev_forced_model_restated_verifier_v2.json` |
| Review sheet | `review/verifier_dev_verifier_v1.xlsx` (owner's review) | `review/verifier_dev_verifier_v2.xlsx` |
| Freeze record | — | `freeze_v1.json`; decisions D-059, D-060 |

## Owner's review of the v1 block sheet (2026-10-06)

11 of the 151 quote-off rows were checked: 8 targeted and 3 sampled from T5. The notes are in
`review/verifier_dev_verifier_v1.xlsx`.

| Rows | Result |
|---|---|
| FG-0176 T1, T4, T6; T5 rows FG-0300, FG-0297, FG-0274 | 6 ok, no note |
| FG-0303 T3, T4, T6 | 3 ok with a note: the block is correct (net income figures do not match), but the `other_metric_mismatch` lines put R&D and gross profit figures in the wrong year and read acquisition costs as total R&D |
| FG-0203 T4, T6 | 2 wrong: the block is correct, but the model's evidence is the other filing's value ($59,553M); the asked filing reports $58,496M |

From this review, two fixes were made before the freeze (D-059):
- **A.** When the question names a filing, the model sees only that filing's excerpts and is told
  which filing it is. In v2, FG-0203 T4 and T6 cite $58,496M as the evidence.
- **B.** In FG-0303 the R&D figures now get the right years (2024: 17,232; 2025: 14,665). Acquired
  in-process R&D is no longer read as total R&D, and the gross-profit pair without its own year is
  no longer checked. The two R&D flags that remain come from the facts, not the period: JNJ's
  `ResearchAndDevelopmentExpense` fact is $1,841M for 2024, not total R&D.

## Results, v1 and v2

Seeded detection is seeded copies blocked over seeded copies kept. False blocks are blocks on the
86 untouched answers scored Correct at baseline.

| | v1 full | v1 quote off | v2 full | v2 quote off |
|---|---|---|---|---|
| Seeded detection, pooled | 151/151 | 151/151 | 152/153 | 152/153 |
| Macro over T1, T3–T6 | 1.0 | 1.0 | 1.0 | 1.0 |
| Macro, no model call | 0.9961 | 0.9843 | 0.9961 | 0.9843 |
| T2 (counts only) | not measured (H-030) | not measured | 1 of 2 | 1 of 2 |
| False blocks on Correct answers | 0/86 | 0/86 | 0/86 | 0/86 |
| Natural answers blocked / flagged | 0 / 1 (FG-0303) | 0 / 1 | 0 / 1 (FG-0303) | 0 / 1 |
| Control abstentions added | 0 | 0 | 0 | 0 |
| Model calls | 2 | 4 | 2 | 4 |

**Changes from v1 to v2.** No block or pass decision changed on any of the 151 v1 rows in either
mode. Reason details changed on FG-0176, FG-0203 (model evidence) and FG-0303 (the
other-metric lines went from 6 to 2). The two new T2 copies: FG-0203 is blocked (`stale_value`,
XBRL) and FG-0205 passes (H-032, below).

**Blocks by reason and basis, v2 quote off:** `numeric_mismatch` [xbrl] 177, `wrong_fiscal_year`
[xbrl] 16, `injection_followed` [detector] 13, `unsupported_figure` [model] 6, `stale_value` [xbrl]
1. These count reasons, so one blocked copy can carry more than one.

**Forced model path (A).** The model was sent every untouched dev `restated` answer, with the rules
skipped. FG-0209 is an abstention with no figure, so it got no call. Final run: 0 of 4 blocked. The
first v2 run blocked the correct FG-0205 answer because excerpts were cut at 1,500 characters and
the total-liabilities row sat at character 2,793 (H-031). Excerpts are now centred on the metric.

**Other checks (`checks_v2.json`).** Clean-corpus detector flags: 4 of 6,311 chunks (limit 6),
unchanged. Dev planted chunks: 13 of 13 flagged. Style swap: 0 of 16 verdicts changed.

**Spend.** Phase 4 verifier model spend is $0.0623 of the $0.60 cap: v1 $0.0252, the forced runs
$0.0157, v2 $0.0213.

## Known weaknesses

- **The style-swap check is weak.** 14 of the 16 premise answers carry the target's abstain flag,
  and the verifier skips figure checks on those (12 of 16 are abstentions under EVAL §3, where
  driver controls ignore the flag). So most pairs pass both ways for a reason other than the
  verifier ignoring question style.
- **Detection is in-sample.** The rules were tuned on these answers and copies (see the top note).
- **Small restatements pass (H-032).** BAC's restated values can differ by less than the verifier's
  0.5% tolerance, so T2 FG-0205 passes. 3 of 17 corpus restated pairs are that close.
- **Shared XBRL source and shared parser.** Blocks rest mostly on XBRL lookups of the same facts the
  gold values came from, and the scorer and the verifier share one number parser (EVAL §8).
