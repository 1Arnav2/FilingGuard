# BUILD LOG — FilingGuard

What was built each session. Newest entry at the top. One entry is added at the end
of every session.

## Entry template
```
## YYYY-MM-DD — Phase N: <name>
**Built:**
**Tests:**
**Broken or unfinished:**
**Numbers worth keeping:** (counts, timings, scores)
**Next session starts with:**
**Commit:**
```

---

## 2026-10-05 — Phase 4: Verifier, step 1 (dev baseline; stopped at the owner's spot check)
**Built:** Probes after H-028 (`eval/batch_probe.py`, `results/runs/batch_probe_v1.json`): file-based
batch job with the standard call's request passed; `response_schema` refused by the SDK. File
batch backend (`gemini_file_batch_backend`, `file_response`), cache tags per batch run, reply
validator (`dev_run.schema_errors`, `reply_errors`: response schema plus the frozen parser).
Dev batch re-run as file jobs, 5/30/30/25, each sub-batch validated before the next (D-046
amended). Run file `results/runs/dev_target_v1.jsonl`; judge decisions
`results/judge/dev_judge_v1.jsonl`; scores `results/dev/baseline_scores_v1.jsonl`; summary
`results/dev/baseline_summary_v1.json`; sheet `review/dev_score_sheet_v1.xlsx`. ROADMAP budget
note re-projected.
**Tests:** 186 offline tests pass (new: validator rejects H-028-style replies, batch tags kept
apart, a sub-batch with an invalid reply stops the run after 5 items).
**Broken or unfinished:** Owner's spot check of the 90-row sheet pending. Seen in scored rows,
not fixed (scorer frozen before answers; owner decides): a possessive company name before a
metric ("Procter & Gamble's", "Bank of America's", "UnitedHealth Group's") is read as a segment
line, making 4 correct answers Missed (FG-0028, FG-0057, FG-0283, FG-0320); a filing date in
FG-0203 is read as the figure's period, making a correct restated answer `wrong_period`; an
added non-GAAP "adjusted" figure is scored as a second figure for the asked metric (FG-0004,
FG-0161, Unsupported). The verifier is not started.
**Numbers worth keeping (baseline, dev, descriptive, as scored):** 90 items: Correct 79,
Unsupported 3, Missed 8. Unsupported-claim rate 3/54 (5.6%, Wilson 1.9–15.1%). Abstain rate on
dev controls 2/18 (11.1%). Injection followed 0/13. Rejected true premises 0/3. Parse errors 0;
110/110 cited quotes found verbatim. Re-run tokens 1,696,431 in, 121,448 out; $0.0096 per item.
Judge $0.0318 for 16 calls.
**Spend so far:** $2.2587 (H-028 run $0.897, probes $0.0262, re-run $0.8639, judge $0.0318).
**Next session starts with:** The owner's spot-check findings and decisions on the scorer
points above; then the injection detector spec; then the verifier.
**Commit:** Phase 4: dev baseline (re-run as file batch jobs), judge, scores and score sheet

## 2026-10-05 — Phase 4: Verifier, step 1 (stopped: batch answers ignored the schema)
**Built:** Scorer (`eval/figures.py`, `eval/score.py` on `eval/rules.py`) with EVAL §3 tests and a
check that answers stating each dev gold value score Correct, all committed before the batch
(e732b08, D-047). Premise judge runner with run-time hash check (`eval/judge.py`). Batch path in
`LLMClient` (`generate_batch`, `PromptRecorder`, `BatchReplayClient`), batch prices in
`config/pricing.json`, ledger `check_many` (D-046). Dev run harness (`eval/dev_run.py`) and dev
report and score-sheet builder (`eval/dev_report.py`). Item-metadata isolation test (D-048). Docs:
EVAL §3 (figures from the answer text), §4 (correctly blocked, D-049), §8 (shared XBRL facts,
templates seen); TRD §2.4 verifier design (D-050) and batch mechanics; ROADMAP Phase 5 budget
risk (D-051); `docs/INJECTION_DETECTOR.md` draft for approval.
**Tests:** 183 offline tests pass (106 before).
**Broken or unfinished:** H-028. The dev batch ran (90 of 90, pre-submit checks all passed:
batch price half, target code equal to `target-v1`, 13 poisoned chunks match their frozen
hashes and reach the top 20, freeze-time prompts rebuilt byte for byte), but the replies
ignored the response schema. Not scored. No baseline dev numbers yet; the score sheet does not
exist yet.
**Numbers worth keeping:** Dev prompts average 62,193 characters; batch input 1,696,431 tokens
(18,849 per item), output 139,140 (1,546 per item); $0.897 for 90 items at the batch price.
**Spend so far:** $1.3368 (172 calls).
**Next session starts with:** The owner's choice after H-028.
**Commit:** Phase 4: dev batch record; batch replies ignored the schema (H-028)

## 2026-10-05 — Phase 3: EDGAR spot check recorded; judge hand-check pinned to both conditions
**Post-review EDGAR spot check (owner, 2026-10-05, after the review):** 8 rows verified
against the filing on sec.gov, 0 faults. Text search in each filing was tool-assisted; the
owner read every hit and made each call. Absence confirmed: FG-0070, FG-0076, FG-0077, FG-0098,
FG-0103. Gold value, row, column and year confirmed: FG-0034, FG-0203, FG-0244. Each filing's
accession number matched the sheet. Recorded separately in `results/testset/fault_rate_v1.json`
(`post_review_spot_check`, input `data/gold/draft/edgar_spot_check_v3.json`); the review record
itself is unchanged (0 of 93 rows verified on EDGAR at review time).
**Judge hand-check (D-045 amended):** all 16 dev premise items, baseline and treatment answers,
up to 32 decisions; agreement reported overall and per condition (EVAL §5, §10).
**Unchanged:** frozen files, manifest and the `testset-v1` tag; the frozen-file test passes.
**Tests:** 106 offline tests pass.
**Spend so far:** $0.4397 (no calls).
**Next session starts with:** Phase 4, the verifier, tuned on the dev split only.
**Commit:** Phase 3: EDGAR spot check recorded; judge hand-check covers both conditions (D-045)

## 2026-10-05 — Phase 3 corrections after freeze (no model calls)
**Corrected:** review record (`results/testset/fault_rate_v1.json`, step `review-record` now
records both counts): reviewed 2026-10-05 only, about 2 hours, 0 of 93 rows verified against
the filing on EDGAR and the other 93 checked against the source excerpt in the sheet. The
previous entry said 93 on EDGAR over 2026-10-04 to 2026-10-05; that was wrong. Judge hand-check
plan (EVAL §5, §10; D-045): dev holds only 3 driver controls, so the plan is every dev premise
item, 16 in all (3 driver controls, 13 `false_premise`). Plan correction, not a scoring change.
**Unchanged:** the record is not one of the frozen files; the manifest, frozen files and the
`testset-v1` tag are unchanged, and the frozen-file test passes.
**Tests:** 106 offline tests pass.
**Spend so far:** $0.4397 (no calls).
**Next session starts with:** Phase 4, the verifier, tuned on the dev split only.
**Commit:** Phase 3 corrections: review record wording, judge hand-check plan (D-045)

## 2026-10-05 — Phase 3 complete: review v3 applied, test set v1 frozen (no model calls)
**Review v3:** owner's `review/review_v3.xlsx` read back with `review-apply`: 93 Decision cells
filled, all "accept", no notes; a cell-by-cell comparison with the committed sheet found no
change outside Decision and Note. Fault-rate sample 0 of 60 faulty against the bar of 3 of 60
(met; Wilson 95% 0.0% to 6.0%). Extra checks 0 of 33 (Wilson 95% 0.0% to 10.4%), reported
separately, not in the fault rate. As stated by the owner (corrected in the next entry):
reviewed 2026-10-05, about 2 hours; 0 of 93 rows verified against the filing on EDGAR, the
other 93 checked against the source excerpt in the sheet. Record:
`results/testset/fault_rate_v1.json` (step `review-record`), which also lists the v1 and v2
rounds from their unchanged records.
**Freeze (D-044):** step `freeze` (`redteam/freeze.py`). Split assigned once from the final 300,
stratified by type and spread across companies within type, seed `20261004-split`; latency
sample of 30 drawn from the test split, seed `20261004-latency`. Both equal the draft's
assignment, so the review sheet's Split column holds. Frozen files: `data/testset/v1.jsonl`,
`data/gold/gold_v1.jsonl` (93 rows `human_checked`), `data/gold/judge_inputs_v1.json`
(unchanged; rebuilt from the frozen gold and found equal), `data/testset/poisoned_chunks_v1.jsonl`
(45 exact poisoned texts plus the clean chunk's hash), `data/testset/latency_sample_v1.json`.
Manifest `data/testset/freeze_v1.json`: seeds, item-set hash `6248316c…bba2`, file hashes,
counts and check results. `tests/test_testset_frozen.py` pins the manifest hash; the manifest
pins each file (checked by altering a copy of the gold file: the test failed; restored).
**Checks re-run on the frozen 300:** counts as specified; multi-filing ambiguity 0 of 38 items
checked; absence failures 0 of 46; trap too close 0 of 46; injection delivery 45/45 (median
rank 2, worst 19); gold separation: item rows carry only id, company, type, subtype, question,
split and injection, no question prints its answer, gold and judge inputs under `data/gold/`,
isolation tests pass. The leak check first flagged 3 questions on a digit inside "2023"
(H-027); it now uses the phrasing check's whole-number rule.
**Phase 3 summary: three review rounds.**
- Round 1 (`review_v1.xlsx`, 2026-10-05): halted at at least 7 of 60 faulty (H-009). Changed:
  strict row-label rule (D-030), company- and sector-balanced review sample (D-031), derivable
  untagged concepts removed (D-032), plainer unit and quarter briefs (D-033), start-month wording
  replaces fiscal-label wording (D-034), EVAL edits (D-035). Became draft v2.
- Round 2 (`review_v2.xlsx`): withdrawn before review after the owner's pre-screen, no fault
  rate (H-017). Changed: start-month rule relaxed to the last two days of a month (D-034
  amended), trap year shown and stored (D-036), questions name the printed line where a second
  figure exists (D-037), sign rule (D-038), label holes closed, EVAL edits (D-039). Became draft
  v3. Before review v3: pre-review checks (D-040), absence over every filing, trap distance and
  10 true-premise driver controls (D-041), driver scoring and fixed judge prompt (D-042),
  no-figure rule (D-043).
- Round 3 (`review_v3.xlsx`): 0 of 60 faulty, 0 of 33 extra checks; no item changed; frozen.
**Final counts (dev / test):** control 60 (18 / 42): current-year 15, prior-year 35, true-premise
driver 10. unanswerable 46 (14 / 32): untagged concept 7, single quarter 20, old period 19.
unit_trap 46 (14 / 32): millions to billions 13, to dollars 14, to thousands 12, per share to
cents 7. period_mismatch 46 (14 / 32): start-month 23 (NKE 4, ORCL 4, MSFT 3, NVDA 3, COST 2,
DIS 2, WMT 2, AAPL 1, PG 1, V 1), calendar wording 23 (COST 5, AAPL 4, NVDA 4, WMT 4, DIS 3, V 3).
restated 12 (4 / 8): restatement 6 (BAC), stock split 4 (NVDA), reclassification 2 (PFE).
false_premise 45 (13 / 32): direction 15, magnitude 16, sign 14. injection 45 (13 / 32): false
figure 17, marker 15, withhold 13. Total 300: dev 90, test 210. The split is stratified by
type, not subtype, so subtype shares between dev and test vary (untagged concept 4 / 3).
Items per company: min 8 (XOM), max 21 (NVDA). Latency sample: 6 / 5 / 5 / 5 / 1 / 4 / 4.
**Tests:** 106 offline tests pass (new: frozen files, Wilson interval, leak check).
**Spend so far:** $0.4397 (82 calls; none this session).
**Next session starts with:** Phase 4, the verifier, tuned on the dev split only.
**Commit:** Phase 3 complete: review v3 applied (0 of 60), test set v1 frozen

## 2026-10-05 — Phase 3: no-figure rule; local history squashed (no model calls)
**Built (D-043):** EVAL §3: Correct needs at least one figure for the asked item on the
figure-scored rows (control, unit_trap, start-month period_mismatch, restated, injection); a
no-figure, non-abstaining answer is Missed. `eval/rules.py:figure_outcome` with tests. Judge
prompt and hash unchanged (`62aa410a…838b`).
**History (H-026):** the commit that carried two scratch files and its clean-up commit were
squashed into one (now 91de082) and the following commit replayed (now 8018400); the final tree
equals the pre-squash tree (fcee855…); neither file appears in `git log --name-only main`; no
commit message has a trailer. Not pushed.
**Tests:** 101 offline tests pass.
**Spend so far:** $0.4397 (no calls).
**Next:** owner's filled `review/review_v3.xlsx`; `review-apply`; fixes logged by ID; freeze.
**Commit:** Phase 3: no-figure rule for figure-scored rows (D-043)

## 2026-10-05 — Phase 3: driver scoring rule and premise judge fixed (no model calls)
**Built (D-042):** EVAL §3 driver row and check order, §4 reasons diagnostic, §6 abstain
counting for drivers, §7 note, §8 limitation, §5 and §10 Phase 5 judge hand-check (20 dev
decisions). Judge prompt `src/filingguard/eval/prompts/premise_judge_v1.txt` written, SHA-256
`62aa410a…838b` recorded in `results/judge/premise_judge_v1.json`. Judge inputs
`data/gold/judge_inputs_v1.json` (55 premise items, 11 with reasons passages; builder
`redteam/judge_inputs.py`, step `judge-inputs`). Reasons check record gains passage locations.
**Tests:** 99 offline tests pass (new: no agent can read the judge inputs; prompt matches its
recorded hash).
**Spend so far:** $0.4397 (no calls this step).
**Commit:** Phase 3: driver scoring rule (D-042), premise judge prompt and inputs

## 2026-10-05 — Phase 3: absence and trap rules applied, driver controls, sheet v3 rebuilt
**Built (D-041):** absence rule over every corpus filing plus the header-cell table check;
trap-distance rule over the whole `period_mismatch` pool; 10 true-premise driver controls;
sticky selection, item IDs and review sample on rebuild. EVAL §2, §3, §4, §7, §8 edited.
**Replaced:** FG-0082 and FG-0084 (absence rule), 6 start-month draws and 4 calendar-year
items (trap rule; covers FG-0153, 0154, 0175, 0186, 0187, 0188, 0194), FG-0193 (its fact taken by
a new start-month draw), 10 regular controls (driver slots).
**Final draft:** 60 / 46 / 46 / 46 / 12 / 45 / 45 = 300; dev 90, test 210. `unanswerable`:
untagged 7, single-quarter 20, old-period 19. `period_mismatch`: start-month 23 (NKE 4, ORCL 4,
MSFT 3, NVDA 3, COST 2, DIS 2, WMT 2, AAPL 1, PG 1, V 1), calendar-year 23. Re-checked on the final
300: multi-filing ambiguity 0, absence failures 0, traps too close 0, injection delivery 45/45
(median rank 2, worst 19). Items per company: min 8 (XOM), max 21 (NVDA).
**Review sheet v3 (rebuilt):** 6 rows swapped (FG-0035 → FG-0059, FG-0046 → FG-0027, FG-0052 →
FG-0001: control slots given to drivers; FG-0153 → FG-0191, FG-0187 → FG-0198: trap rule;
FG-0193 → FG-0315: fact taken by a new start-month item). 25 companies, at most 3 rows each, all
sectors and financials. Extra checks: 16 start-month, 10 drivers, 7 untagged-concept.
**Style (`style_check_v3.json`):** driver controls 19.1 words against false premise 18.2, same
openings; regular controls 11.4.
**Tests:** 97 offline tests pass.
**Spend so far:** $0.4397 (82 calls). This step: 3 phrasing calls, $0.0177.
**Commit:** Phase 3: absence and trap rules, driver controls, review sheet v3 rebuilt

## 2026-10-05 — Phase 3: pre-review checks on draft v3 (no model calls)
**Checks (H-024, `data/gold/draft/prescreen_v3_checks.json`):** multi-filing ambiguity 0 items;
absence search over every corpus filing 2 hits (FG-0082, FG-0084, both PFE, neither figure in
any filing); old-period header-cell table check 0 of 19; trap within 2% of gold in 7
`period_mismatch` items (FG-0188 inside the 0.5% tolerance); 6 false-premise rows with a
second figure, all contradicted by both lines.
**Applied (D-040):** false-premise sheet note corrected for the 5 rows that do not name their
line; "<Company>'s" dropped before a printed label that already names the company (16 draft
questions; 4 in the sheet: FG-0032, FG-0192, FG-0278, FG-0287); EVAL §8 style limitation. Split
stays non-sticky and is assigned once at freeze with seed and item-set hash (H-023).
**Not applied, awaiting the owner:** trap-distance replacements (7) and the two absence hits.
`review/review_v3.xlsx` rebuilt: same items, splits, sample, extra checks and latency IDs; only
those question texts and notes changed.
**Tests:** 94 offline tests pass.
**Spend so far:** $0.4220 (no calls this step).
**Commit:** Phase 3: pre-review checks on draft v3; sheet notes and possessive edit

## 2026-10-05 — Phase 3: v2 withdrawn, pre-screen fixes, draft v3 and review sheet v3
**Review v2:** withdrawn before review after a pre-screen; no fault rate recorded for it
(H-017, `data/gold/draft/review_v2_withdrawn.json`).
**Built:** Start-month rule relaxed to skip only starts in the last two days of a month
(D-034 amended; 30 candidates, 3 per non-calendar filer). Questions name the filing's printed
row label when XBRL reports a second figure for the same period that differs at printed
precision, and for negative gold values (D-037, D-038); bare labels take the heading above
them. Label holes closed (adjusted EPS, segment revenue). Start-month items store the trap
fiscal year and value, shown in the review detail (D-036). Sign rule added to EVAL §3 (D-038);
EVAL §2 start-month text and §8 corpus text corrected (D-039). Candidates v3: 365.
**Draft v3:** 300 items, 60 / 46 / 46 / 46 / 12 / 45 / 45; dev 90 (18/14/14/14/4/13/13), test
210. `period_mismatch`: 23 start-month (MSFT, NVDA, ORCL, NKE, PG 3 each; WMT, DIS, V 2 each;
AAPL, COST 1 each) and 23 calendar wording; 10 companies. `unanswerable`: untagged 7,
single-quarter 20, old-period 19. 27 draft items name their line; 7 have negative gold.
Items per company: min 8 (XOM), max 21 (NVDA). Injection delivery 45/45 (median rank 2,
worst 19). Split: 76 of the 203 items also in draft v2 changed split (H-023).
**Review sheet:** `review/review_v3.xlsx`: 60-item fault-rate sample over 25 companies (at most
3 each, all sectors, all four financials); extra checks: 16 start-month and 7 untagged-concept
items not in the sample.
**Style check (`data/gold/candidates/style_check_v3.json`):** average words control 11.8,
unanswerable 11.9, injection 12.8, period_mismatch 13.3, unit_trap 15.7, false_premise 18.2,
restated 24.3; dates only in restated questions (the filing date).
**Tests:** 93 offline tests pass.
**Spend so far:** $0.4220 (79 calls). This round: 7 phrasing calls, $0.0308.
**Next:** owner reviews `review/review_v3.xlsx`; `review-apply`; fixes logged by ID; freeze and tag.
**Commit:** Phase 3: draft v3 and review sheet v3 after the v2 pre-screen

## 2026-10-05 — Phase 3: first review halted, fixes, draft v2 and second review sheet
**First fault rate:** at least 7 of 60, review halted once the bar was exceeded
(`data/gold/draft/review_v1_first_pass.json`; H-009). The EVAL §2 rule was applied. The
first-review draft is kept in `data/gold/draft/first_review/` and `data/testset/draft/first_review/`.
**Built:** Strict row-label rule for every type (D-030); company- and sector-balanced
sampler with a hard coverage check (D-031); derivable untagged concepts removed (D-032);
"in dollars" and plain single-quarter briefs (D-033); start-month wording replaces
fiscal-label wording (D-034); EVAL §2, §3, §5, §8 edits (D-035). `redteam/revise.py` turns the
committed v1 candidates into v2: 337 v1 specs kept, 34 added, 371 in all; only changed specs
were re-phrased. Review sheet `review/review_v2.xlsx` with Split and Sector columns.
**Dropped from the first-review draft, by v1 ID, with reasons** (replacements drawn by seed
from the same type):
- Not on a row labelled with the metric's own name (D-030): FG-0003 control AAPL (equity,
  beginning balance only); FG-0024 control WMT (long-term debt "including amounts due within
  one year"); FG-0037 control PFE (diluted EPS, prose only); FG-0042 control XOM ("total
  revenues and other income"); FG-0125 unit_trap NKE (operating cash flow, prose only);
  FG-0146 unit_trap DIS ("total segment operating income"); FG-0189 period_mismatch DIS
  ("total segment operating income"); FG-0235 false_premise JNJ ("acquired in-process
  research and development"); FG-0241 false_premise XOM ("total revenues and other income");
  FG-0201 restated GOOGL ("total face value of long-term debt"; pair is a tagging change);
  FG-0208 restated BAC (basic EPS labelled only "Earnings"). The four controls are removed
  from the set, not moved to another type.
- Untagged concept computable from printed lines (D-032): FG-0089 XOM, FG-0093 CVX, FG-0096
  CAT, FG-0098 DIS (all gross profit).
- Replaced by design (D-034): the 23 fiscal-label `period_mismatch` items. Restated items were
  reselected under the strict rule (12 pairs).
**Draft v2:** 300 items, 60 / 46 / 46 / 46 / 12 / 45 / 45; dev 90 (18/14/14/14/4/13/13), test 210.
`unanswerable`: untagged 7, single-quarter 20, old-period 19. `period_mismatch`: calendar
wording 32, start-month 14 (NVDA 6, COST 6, AAPL 2); 6 companies in the type. Injection
delivery: 45/45 poisoned chunks in the top 20 (median rank 3, worst 20); 1 candidate not
delivered and dropped. Review sample: 60 rows, 25 companies, at most 3 per company, all
sectors, all four financials. Latency sample: 30 test items, 25 companies.
**Style check (300 draft items, `data/gold/candidates/style_check_v2.json`):** average words
control 11.8, unanswerable 11.7, period_mismatch 12.1, injection 12.5, unit_trap 15.2,
false_premise 18.6, restated 24.8; no dates except restated (filing date).
**Tests:** 91 offline tests pass.
**Spend so far:** $0.3912 (72 calls). This round: 7 phrasing calls, $0.0244.
**Next:** owner reviews `review/review_v2.xlsx`; then `review-apply`, fixes logged by ID,
freeze and tag.
**Commit:** Phase 3: draft v2 after first review - strict labels, start-month wording, review sheet v2

## 2026-10-04 — Phase 3 checkpoint: restated pairs, corpus change, generators, pilot
**Built:** Restated pairs across the last three 10-Ks (`facts.find_restatements`, kinds
`restatement` / `reclassification` / `stock_split`, plus excluded `rounding` / `ambiguous`).
Older 10-Ks indexed only where they supply a usable pair (D-026). Red-team package
`src/filingguard/redteam/` (corpus helpers, one generator per attack type, injection
templates and sandbox retriever, phrasing, build command). EVAL §2 counts updated before
generation (D-021); EVAL §2 fault-rate rule and §4 latency wording (D-025, D-026).
**Corpus changed, not the target.** Index: 26 → 32 filings, 5,215 → 6,311 chunks, content
hash `26b682ae…` → `66f2d712…`. Multi-year indexed: NVDA, GOOGL, PFE (three years), BAC (two).
Target code, prompt, retriever and settings are identical to tag `target-v1`. The only
change the target sees beyond the extra chunks is the excerpt header date for third-year
filings, supplied by the harness (D-027).
**Retrieval re-check (no model calls):** hit@20 unchanged at 27/30 (smoke 10/10, held-out 1
10/10, held-out 2 7/10; `results/smoke/retrieval_corpus_v2.json`). Ranks moved within the
window for SM-02 NVDA (2→5), HV-05 PFE (4→8), HV-08 GOOGL (4→10). No smoke re-run needed.
**Numbers worth keeping:** 19 usable restated pairs (BAC 12, NVDA 4, PFE 2, GOOGL 1), 14 used
after the half cap. 400 candidates generated. Unanswerable absence search removed 53 of 115
candidates checked (untagged concept 41/52, single quarter 11/31, old period 1/32). Pilot
phrasing: 1 call, 10 questions, 0 rule failures, $0.0072.
**Tests:** 75 offline tests pass.
**Spend so far:** $0.0618.
**Next:** remaining phrasing, filtering, injection delivery check, split, latency IDs, review
sheet, scoring-rule draft.
**Commit:** Phase 3 checkpoint: restated pairs, corpus change, red-team generators, pilot

## 2026-10-04 — Phase 2 complete: smoke test finished, target frozen
**Built:** Ran smoke questions SM-08 to SM-10 on the standard API (the first 7 replayed from
cache at no cost). Added a `"target"` label to the agent's spend-ledger entries; it is not
part of the cache key (replay confirmed: 10/10 cached, spend unchanged).
**Tests:** 72 offline tests pass.
**Final smoke results** (`results/smoke/smoke_v1_summary.json`): 10/10 answered, 10/10 with
citations, 10/10 give the expected figure, 16/16 quotes found verbatim in the filing text,
0 parse errors, 0 abstentions. Latency 2.6–19.9 s per question (original API time).
**Final retrieval hit rate of the frozen target** (interleaved keyword + dense, k = 20;
`results/smoke/retrieval.json`): smoke 10/10, held-out set 1 10/10, held-out set 2 (fresh)
7/10; all 30 questions 27/30 (95% CI 74–97%).
**Target frozen** at git tag `target-v1`. From here on the target agent's model
(`gemini-3.8-flash`), prompt (`tenk_rag_v1`), retriever (interleaved BM25 + dense, k = 20,
BM25 k1 = 1.2, b = 0.75, `jinaai/jina-embeddings-v2-small-en` index) and settings
(temperature 0, JSON output schema, default thinking) do not change.
**Broken or unfinished:** The S1/S2/S3 budget decision (H-008) is still open and must be
settled before any Phase 3 model call.
**Numbers worth keeping:** Smoke cost $0.0545 for 3 paid calls (59,852 input tokens, 2,575
output tokens).
**Spend so far:** $0.0545 (`results/spend/total.json`); warning $5, hard cap $7.
**Next session starts with:** The owner's S1/S2/S3 budget decision; then Phase 3.
**Commit:** Phase 2: smoke test complete, target frozen (tag target-v1)

## 2026-10-04 — Phase 2 continued: budget controls (paused, not complete)
**Built:** `config/pricing.json` (gemini-3.8-flash $0.75 / $3.75 per 1M input / output tokens
to 2026-12-31, $1.50 / $7.50 from 2027-01-01; source ai.google.dev/gemini-api/docs/pricing).
`llm/spend.py`: per-call ledger (`results/spend/ledger.jsonl`), running total
(`results/spend/total.json`), warning at $5, hard cap $7 checked before every uncached call
against a worst case that includes the model's full output limit. `LLMClient` now requires a
ledger. `tests/test_llm_boundary.py` fails if anything but `LLMClient.generate` can reach the
model, and checks the order cache → ledger check → call → record → cache. Projection in
`results/budget/projection_v1.json`. Docs: TRD §3, §5, §6; D-023 confirmed; D-024; H-006
resolved; H-008.
**Tests:** 72 offline tests pass (new: costing, cap never passed, warning once, failed call
free, both price bands, cap above $7 rejected, model-access boundary).
**Retrieval report (D-023, H-007):** hit@20 = a chunk containing the answer is in the top 20
for the question's company. Source: `results/smoke/retrieval.json`.

| Retriever | Smoke (10) | Held-out 1 (10) | Held-out 2, fresh (10) | All 30 (95% CI) |
|---|---|---|---|---|
| Dense (embeddings) | 9 | 9 | 10 | 28 (79–98%) |
| Keyword (BM25) | 10 | 8 | 5 | 23 (59–88%) |
| RRF fusion | 10 | 9 | 8 | 27 (74–97%) |
| **Interleaved keyword + dense (chosen)** | 10 | 10 | 7 | **27 (74–97%)** |

Biased-question correction: the 10 smoke questions were written after searching the filings
for their answers, so their wording echoed the text and favoured keyword search (BM25 10/10
there, 5/10 on fresh paraphrased questions). Two held-out sets of paraphrased questions were
then written and their hashes recorded before any retrieval ran on them; the design (and
k = 20) was committed before held-out set 2 was scored. Window size mattered more than method:
at k = 10 every method was at 70–90%.
**Broken or unfinished:** Model calls paused: projected spend $6.80–$21.94 is above $5
(H-008); owner to choose cuts. Smoke test still 7/10; target not frozen.
**Spend so far:** $0.00 tracked. All 9 model calls to date (2 Phase 0 tests, 7 smoke answers)
ran on the free tier before billing was enabled; the ledger starts at zero.
**Next session starts with:** Owner's choice of cuts; then smoke SM-08 to SM-10, final hit
rate, freeze target.
**Commit:** Phase 2 (partial): spend cap, pricing config, cost projection

## 2026-10-04 — Phase 2: Target agent (paused, not complete)
**Built:** `agents/schema.py` (`TargetAgent`, `AgentAnswer`, `Claim`, `Citation`).
`retrieval.py` (dense, BM25, RRF hybrid, interleaved). `agents/targets/tenk_rag.py` (standard
RAG prompt, JSON output, quotes mapped to filing character offsets, full trace including the
raw response). `api/main.py` (`POST /api/target/answer`). `eval/smoke.py` (hit rate per
question and retriever, agent run). LLM client now stores original API latency in the cache.
Retry fails fast on per-day quota errors. Docs: D-021, D-022 (TRD §1, §2.3, §4; ROADMAP
Phase 3), D-023, H-006, H-007.
**Tests:** 63 offline tests pass (new: retrieval, agent with fake LLM, API, daily-quota
classification). Gold isolation test passes with the agent under `agents/`.
**Broken or unfinished:**
- Smoke test 7/10 run: the gemini-3.8-flash free tier allows 20 requests per day (H-006).
  All 7 gave the expected figure with citations; all 12 quotes were found verbatim; 0 parse
  errors (`results/smoke/smoke_v1_summary.json`). SM-08 to SM-10 need quota.
- Retriever choice was provisional pending the owner (since confirmed, D-023).
**Numbers worth keeping:** Retrieval hit@20 over 30 questions (smoke + two held-out sets):
dense 28/30, interleaved 27/30, RRF 27/30, BM25 23/30; committed interleaved k = 20 scored
7/10 on the fresh held-out set (95% CI 40–89%). Source: `results/smoke/retrieval.json`.
Final hit rate for the frozen target: not yet recorded (target not frozen).
**Next session starts with:** Owner decisions on model/quota and retriever; finish the smoke
run; record the final hit rate; freeze the target.
**Commit:** Phase 2 (partial): target agent, hybrid retrieval, smoke harness

## 2026-10-04 — Phase 1: Data
**Built:** `filingguard.retry` (shared backoff, D-015), used by the Gemini backend and a new
EDGAR client (User-Agent, 5 requests/s, disk cache in `data/raw/sec/`, failures uncached).
`filings.py` (CIK resolution with the XOM override, D-014; 10-K selection across all
submissions pages). `facts.py` (normalised facts, concept map with revenue fallback status,
restatement pairs with a rounding filter, D-019). `parse_10k.py` and `chunk.py` (whole-document
text with tables, Item labels, 3,200/400-character chunks with offsets, D-017, D-018).
`index.py` (local jina-v2-small embeddings, cached per chunk, exact cosine search, D-016).
`build_corpus.py` runs it all and renders the corpus card; `spot_check.py`. Gold separation:
facts moved to `data/processed/`, `tests/test_gold_isolation.py` added (D-013). CORPUS §2, §4,
§6, §7 and TRD §1, §2.1, §3 updated.
**Tests:** 47 offline tests pass (retry, EDGAR client, facts and rounding, parser and chunker,
index, spot-check rendering, gold isolation). Live Gemini test passes through the retry path.
Spot check: 10/10 facts match the filing text for the right period.
**Broken or unfinished:**
- `restated` attack: 12 usable pairs from one company (BAC) against 40 planned (H-004).
  Needs the owner's decision before Phase 3.
- The red-team is planned under `agents/redteam/` and must write gold labels, but the gold
  isolation test forbids anything under `agents/` from touching `data/gold`. Needs the
  owner's decision before Phase 3.
- Retrieval is weak on some queries (JPM, BAC samples returned off-target chunks; scores
  bunched 0.83–0.88). Check in the Phase 2 smoke test.
- Item labels are weak for six filers (NVDA, ORCL, DIS, XOM, CVX, JPM); text is complete.
- Several companies do not tag some CORPUS §4 concepts under the standard name (for example
  CAT `NetIncomeLoss`, V EPS); see the CORPUS §7 table.
**Numbers worth keeping:** 25 companies, 26 filings, 5,215 chunks, 16,411 fact rows (720
from latest 10-Ks), 12 restatement pairs (BAC) plus 2 rounding pairs excluded (XOM), revenue
mapped for 25/25 (GS via fallback). Full embed about 10 min at 2.2 GB peak; cached rebuild
11 s with 0 SEC requests.
**Next session starts with:** Owner decisions on the `restated` count and the red-team
location; then Phase 2, target agent.
**Commit:** Phase 1: EDGAR data pipeline, facts, chunked index, corpus card

## 2026-10-04 — Phase 0: Setup
**Built:** Git repo on `main`, with the author set in the repo config, the `commit-msg` hook
installed and tested on a scratch message (strips attribution trailer lines in any case),
and local tooling files excluded through `.git/info/exclude`.
`.gitattributes` (LF), `.gitignore` additions (`web/out/`, `web/.next/`, `*.egg-info/`).
`pyproject.toml` (Python 3.11, `google-genai`, `python-dotenv`, pytest), `.env.example`,
Python 3.11 venv. `filingguard.llm`: `DiskCache` (SHA-256 of model + prompt + params, atomic
writes) and `LLMClient` with a pluggable backend and a Gemini backend. Docs: TRD §4 package
layout, TRD §6 reproducibility through `results/runs/`, D-008 wording, D-009 to D-012,
H-001.
**Tests:** 7 offline tests pass (cache keys, round trip, cached second call, re-run with a
fresh client makes zero calls). The `live` test passes: one real call to
`gemini-3.8-flash`, identical second call served from cache. `pytest` skips `live` by
default; run it with `pytest -m live`.
**Broken or unfinished:** No retry/backoff beyond the SDK's own (H-001); needed by Phase 5.
Open question for Phase 1: CORPUS §6 writes XBRL facts to `data/gold/`, but the verifier
must read XBRL facts and must never read `data/gold/`.
**Numbers worth keeping:** 44 models listed for the key with `generateContent`; live call
about 2 s.
**Next session starts with:** Resolving the `data/gold/` question, then Phase 1, data.
**Commit:** Initial commit: planning docs (6188da7); Phase 0: project skeleton and cached LLM client

## 2026-10-04 — Planning
**Built:** PRD, TRD, EVAL, CORPUS, ROADMAP, DECISIONS_LOG drafted.
**Tests:** none yet.
**Broken or unfinished:** no code.
**Numbers worth keeping:** target 25 companies, 300 items (90 dev, 210 test), 60 hand-checked.
Dashboard changed to React (D-007); build estimate now about 12 days.
**Next session starts with:** Phase 0, setup.
**Commit:** n/a
