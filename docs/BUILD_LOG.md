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

## 2026-10-24 — Phase 6d: static site (deploy option B)
**Built:** D-079: the public site is the static export on Vercel; `render.yaml` removed; FastAPI,
`/api/health` and the Dockerfile kept and relabelled for local runs; live route unchanged
(`FILINGGUARD_LIVE_TARGET=1` only). LinkedIn set to the owner's profile. The site reads `results/` at
build time (`web/scripts/sync-results.mjs` → `web/generated/`, run before dev, build, typecheck and
test); `web/lib/api.ts` replaced by `web/lib/data.ts`; list filtering in the page (`web/lib/query.ts`);
one pre-rendered page per item (`/item/FG-xxxx/`, `generateStaticParams`); old `/item/?id=` links
redirect. Filters and sort now travel in item URLs (previous/next, Back to the right page, shared
links) instead of session storage. `next.config.ts` has no rewrites and reads no environment variable.
**Tests:** 311 Python tests pass (new `tests/test_static_site.py`: build data equals the results files;
page filtering equals the API on every preset, search, sort, filter and page on both bases, 70 queries;
no fetch, API path, local address, environment variable, `NEXT_PUBLIC_`, rewrite, middleware, route
handler, server action or live route in the site source; the built output has no API path or local
address; 210 item pages built). Web: 8 tests, typecheck, lint, build pass. Freeze tests pass; tags
unchanged.
Static-server check: `web/out` served by `python -m http.server` with no API running: every page 200,
`/api/*` 404, no request to any `/api` path, no console errors. Against the b52ac1a build (old export
plus its API, run locally): main text of Results, Items (filtered), Method and Limitations identical at
1440 and 375 px; Overview identical except the new LinkedIn link; item page identical when the list
filter is in its URL. Audit of 6 pages × 1440/375 × light/dark (5,180 text elements): same result as
b52ac1a — no horizontal overflow; one contrast flag on both, the disabled "Previous" page button (3.71,
disabled controls are exempt); the same small-target list (inline links and definition buttons, the
D-077 inline exception).
**Broken or unfinished:** Docker engine still not running (H-036 open; image not built). The first
build after the static server ran failed with EBUSY because the server held `web/out`; serving it with
`--directory` from outside avoids that. Deploy to Vercel waits for the owner.
**Numbers worth keeping:** `web/out` 8.1 MB (item pages 6.3 MB, `_next` 1.7 MB); first-load JS 104–197 kB
per route. Screenshots: FilingGuard_screens/v4 (12, outside the repo).
**Spend so far:** $5.2521 (no model calls).
**Next session starts with:** Owner pushes and creates the Vercel project (root `web/`); check the
public link on desktop and mobile; then Phase 7.
**Commit:** Phase 6d commits (decision and clean-up; site; tests; docs)

## 2026-10-24 — Phase 6b: deploy step (serving and image)
**Built:** `create_app()` in `api/main.py`: results API, `GET /api/health`, JSON 404 for unknown
`/api/*` paths, gzip, and the static export mounted at `/` (`FILINGGUARD_WEB`, default `web/out`).
Live target route moved to `api/live.py`, included only when `FILINGGUARD_LIVE_TARGET=1` (off by
default; absent and not imported otherwise). `Dockerfile` (pinned Node stage builds the export;
pinned Python slim stage with `requirements-serve.txt` and the package `--no-deps`; non-root; `$PORT`),
allowlist `.dockerignore`, `render.yaml` (no environment, health check, no auto-deploy).
`.env.example` and TRD §2.7, §4, §5 updated. D-078, H-036.
**Tests:** 304 Python tests pass (20 new in `tests/test_serve.py`: pages, redirects, export 404, API
with the export mounted, JSON 404, gzip, live route off by default and on only for exactly `1`, a
clean-process import loads no agent/LLM/data code, served modules need only the serve list, pinned
requirements, `.dockerignore`, Dockerfile, `render.yaml`, `.env.example`); `test_api.py` moved to the
factory. Web: 4 tests, typecheck, lint, static export build pass. Image-layout check (clean venv with
the serve list only, folder holding exactly what the Dockerfile copies): 6 pages and the API 200,
unknown API path JSON 404, unknown page the export's 404, live route 404, `/api/items` gzipped,
no console errors, no horizontal overflow at 375 px.
**Broken or unfinished:** `docker build` not run: Docker Desktop crashed at start-up (H-036). Deploy to
Render waits for the owner's push and go-ahead.
**Numbers worth keeping:** none new.
**Spend so far:** $5.2521 (no model calls).
**Next session starts with:** Build and run the image (after a reboot), then the owner pushes and
creates the Render service; check the public link on desktop and mobile.
**Commit:** Phase 6b deploy step: one-origin serving, gated live route, Dockerfile

## 2026-10-22 — Phase 6c: polish and Should tier
**Built:** In two commits (the first was the previous session's work, verified and committed before
any change). Polish: plain limitation summaries on Overview linking to the full text; every rate and
threshold as a percentage; footer spend "$5.25 of the $7 cap"; verifier reason figures as money;
Details with a chevron; no empty gap in the first stat card; hero eyebrow "An evaluation of an AI
finance research agent"; LinkedIn placeholder set as asked (hidden until a real URL), email empty.
Should tier: API search (`q`) and sorting (`sort`, `order`); Items search box, sortable headers with
`aria-sort`, sort select on phones; previous/next on item detail within the current list; Jump to on
Results, Method and item detail; glossary on Method; definition tooltips (hover, focus, tap); H-034
linked to the False blocks view; anchors scroll after data loads. D-077.
**Tests:** 284 Python tests pass (search, sorting, default order, limitation summaries, glossary and
metric labels, formats in placeholders, author links); 4 web tests (money, evidence). Typecheck, lint
and static export build pass. Production check (API + export on one origin): 6 pages × 1440/375 ×
light/dark, about 4,300 text elements measured, 0 contrast failures, no horizontal overflow; tap
targets ≥ 44 px at 375 px except inline FG links inside limitation sentences (inline exception).
Fixed during the check: tooltips closing on tap; the item-detail step labels at 16 px. Functional:
preset → sort by company descending → open the 3rd item gives "3 of 9" with the right neighbours.
**Broken or unfinished:** Could tier. LinkedIn URL for the owner. Deploy step of 6b.
**Numbers worth keeping:** none new. Screenshots: FilingGuard_screens/v3 (24, outside the repo).
**Spend so far:** $5.2521 (no model calls).
**Next session starts with:** Owner's review, then the deploy step.
**Commit:** Phase 6c polish and Should tier, part 2: item detail navigation and tooltips; docs

## 2026-10-21 — Phase 6c: dashboard redesign (Must tier)
**Built:** New look and structure from the owner's DESIGN_SPEC.md, Must tier (D-076). Pages:
Overview (headline with Border Beam, three Number Ticker stat cards linked to their evidence, an
Animated Beam how-it-works diagram in a Bento Grid, pass bars at a glance, "Why two numbers?", how it
was kept honest, headline limitations, author block, outreach line, hidden demo-video slot),
Results (pass-bar cards, outcomes, metrics, by attack type, planted errors, latency and cost),
Items (presets with live counts, filters, chips, table/cards), item detail (decision first, "what
happened" sentence), Method, Limitations; `/attack-types/` redirects into Results. shadcn/ui base,
Geist, light/dark/system theme. API flag filters for the presets. Content files for labels, copy,
author, media, limitation groups. `docs/THIRD_PARTY.md`.
**Tests:** content tests extended (11: placeholders and stat paths resolve on both bases, presets use
API filters, every code in results/ has a plain label, limitation groups cover each item once,
author/media links); API tests +6 (flag filters, presets match summary.json, bad flag 422). Full
suite passes. `web/`: typecheck, lint (0 warnings), `npm test`, static export build pass; `npm audit
--omit=dev` 0. Production build checked (API + export on one origin, scratch server not committed):
6 pages × 1440/375 px × light/dark: text contrast measured on every text element, 0 failures; focus
ring 17.9:1 light, 15.7:1 dark; one h1 and a unique title per page; no horizontal scroll; tap
targets ≥ 44 px at 375 px; skip link first; theme toggle overrides the system; reduced motion shows
final values with no beams; tickers end on the exact values and screen readers get only those.
**Broken or unfinished:** Should/Could tiers (search, sorting, prev/next, section nav, glossary,
skeletons). LinkedIn URL and demo video for the owner to fill in. Deploy step of 6b.
**Numbers worth keeping:** none new. Screenshots: FilingGuard_screens/v2 (24, outside the repo).
**Spend so far:** $5.2521 (no model calls).
**Next session starts with:** Owner's review of the redesign.
**Commit:** Phase 6c: dashboard redesign, Must tier

## 2026-10-21 — Phase 6b fix: correction evidence display
**Built:** The item page printed `gold: [object Object]` in the D-071 evidence for FG-0302 and
FG-0306, whose gold evidence is a `{year: value}` object. New `evidenceText()` in `web/lib/format.ts`
shows numbers with separators, objects as `key: value` pairs and lists joined. `npm test` runs
`web/tests/*.test.mjs` with Node's built-in test runner; `web/package.json` now declares
`"type": "module"` so Node loads `format.ts` without a warning.
**Tests:** `web/tests/format.test.mjs` (2 tests: nested gold evidence, scalars, lists, missing values)
pass. Typecheck, lint, static export build pass. Full Python suite 264 passed. Browser: the 11
corrected items and FG-0307 show no "[object" text; FG-0302 reads "2024: 9,992,000,000; 2025:
13,762,000,000".
**Broken or unfinished:** 6b deploy step, after the owner's review.
**Numbers worth keeping:** none.
**Spend so far:** $5.2521 (no model calls).
**Next session starts with:** Owner's review, then the 6b deploy step.
**Commit:** Item page: show nested correction evidence as text, with a web unit test

## 2026-10-21 — Phase 6b (views): attack types, items, method; fixes to 6a
**Built:** Per-item export `results/dashboard/items_v1.jsonl` and `meta_v1.json` from
`eval/scripts/export_dashboard.py` (D-075); the API now serves it as is (overlay no longer re-stated)
and adds `GET /api/meta`. Headline in `web/content/headline.json`, shown at the top of the scorecard.
Pages: by attack type (Recharts stacked bars on the chosen basis, counts on both bases, corrected
bootstrap change in correct share, seeded detection by transform); items (filters for attack type,
verdict, outcome, failure label and condition, paging, flags for corrected, unparseable and
hand-checked); item detail at `/item/?id=` (gold, answer and citations, figures the scorer read,
judge, outcomes on both bases, both verifier modes, D-071 correction or review, owner's hand-check,
retrieved passages; unparseable replies shown as such); method (question, agents, test-set build,
split, freeze tags with commit links, scoring and the correction rule, pass bars with D-056 and its
date, spend by purpose, limitations).
**Tests:** 14 new: `test_api_results.py` (meta, every detail validates, unparseable not
reproduced, judge/correction/hand-check counts, per-type sums on both bases), `test_dashboard_export.py`
(byte-for-byte rebuild, input hashes, corrected baseline by type, corrections from the file),
`test_web_content.py` (headline numbers against summary.json; method numbers only as resolving
placeholders). Full suite 264 passed. `web/`: typecheck, lint, static export build pass; `npm audit
--omit=dev` 0. Browser: every page at desktop and 375 px, no horizontal page scroll, figures match
summary.json, filters and basis toggle work, no console errors.
**Broken or unfinished:** Deploy step of 6b: FastAPI serving the static export, Dockerfile, Render,
env flag for the live target route. Waiting for the owner's review.
**Numbers worth keeping:** headline checked: 210 items, macro detection 0.9337 (93%), 9 false
blocks (corrected). Export: 38 judged items, 11 corrected and 4 kept as scored, 53 hand-checked
items (5 with a note).
**Spend so far:** $5.2521 (no model calls this session).
**Next session starts with:** Owner's review of the views, then the 6b deploy step.
**Commit:** Phase 6b: attack-type, item and method views; per-item results export

## 2026-10-21 — Phase 6a: results API and dashboard scaffold
**Built:** Read-only routes `GET /api/summary`, `/api/items`, `/api/items/{id}` (`api/routes.py`,
`api/results.py`), reading committed `results/` files only, with the D-071 overlay re-stated (D-074).
Next.js 15.5 app in `web/`: typed client (`lib/api.ts`, `lib/types.ts`), layout with nav and a
corrected / as-scored toggle kept in the URL, footer naming the source file and spend. Scorecard: six
pass bars with both bases side by side and a "bases differ" marker, outcome bars and rates for both
bases, seeded detection by transform, latency and spend, all seven limitations. Attack-type, item
and method pages are stubs for 6b.
**Tests:** `tests/test_api_results.py` (19): summary unchanged; per-item outcomes add up to
summary.json on both bases and conditions; verdicts 194/13/3 and the blocked and flagged ids;
filters, paging, 422 and 404; no gold/testset path and no llm/agents/eval import in the new modules;
no LLM client built. Full suite 250 passed. `web/`: typecheck, lint and static export build pass.
Checked in the browser on desktop and at 375 px: every figure matches summary.json, no horizontal page
scroll, toggle and nav keep the basis, no console errors.
**Broken or unfinished:** 6b: by-attack-type charts, item explorer and drill-down, method page,
FastAPI serving the static export, Dockerfile, Render deploy, env flag for the live target route.
**Numbers worth keeping:** none new; the dashboard shows summary.json as is.
**Spend so far:** $5.2521 (no model calls this session).
**Next session starts with:** Phase 6b after the owner's go-ahead.
**Commit:** Phase 6a: read-only results API, dashboard scaffold and scorecard

## 2026-10-19 — Phase 5 steps 9 and 10: owner's hand-check, pass bars, summary.json (Phase 5 done)
**Built:** Owner's hand-check recorded (sheet committed): all 63 non-pre-filled rows "ok", none wrong;
agreement with as-scored outcome: random 30 29/30, other rows 38/48 (the gaps are the 11 D-071
corrections). `eval/scripts/summary_test.py` and `results/summary.json`: bars on corrected and as-scored
bases, Wilson intervals, McNemar exact, paired bootstrap by type, spend, latency, limitations. Phase 5
marked done in ROADMAP. D-073; one-time push.
**Tests:** full offline suite passes.
**Broken or unfinished:** Phase 6 (dashboard) not started.
**Numbers worth keeping (corrected; as scored in brackets):** baseline 197/10/3 (186/11/13),
treatment 188/22/0 (186/23/1). Unsupported-claim rate 3/124 → 0/112 (13/124 → 1/112); McNemar not
testable (p 0.0005, met). Precision 3/13 (12/13). Control abstain treatment 12/42. Seeded macro 0.9337;
false blocks 9/197 (0/186). Latency p50 6.65 s, p95 23.46 s end to end. Spend $5.2521.
**Spend so far:** $5.2521.
**Next session starts with:** Phase 6a (dashboard API and scaffold) after the owner's go-ahead.
**Commit:** Phase 5 step 10: pass bars and results/summary.json; Phase 5 done

## 2026-10-19 — Phase 5 step 8 (latency) and step 9 sheet
**Built:** Latency sample run end to end on the standard API (target, then the frozen verifier), one
call at a time, saved apart from the batch answers (`eval/scripts/latency_test.py`). Owner's
hand-check sheet `review/test_handcheck_v1.xlsx` (`eval/scripts/handcheck_sheet_test.py`).
**Tests:** full offline suite passes.
**Broken or unfinished:** FG-0316 not run (the $5.50 limit's worst-case check). The consistency check
skips the 5 premise items (no judge calls). Owner's hand-check, statistics and summary.json pending.
**Numbers worth keeping (29 items):** target p50 6.63 s, p95 23.44 s; verifier rules p50 0.010 s,
p95 0.020 s, 0 model calls; end to end p50 6.65 s, p95 23.46 s. Consistency with batch outcome 23/24
non-premise (FG-0012 differs). Latency cost $0.5809. Sheet 78 rows, 15 pre-filled.
**Spend so far:** $5.2521.
**Next session starts with:** The owner's hand-check of `review/test_handcheck_v1.xlsx`.
**Commit:** Phase 5 step 8: latency sample (29 of 30) and the step 9 hand-check sheet

## 2026-10-19 — Phase 5 steps 6 and 7: verifier run on test, treatment scored
**Built:** One run of the frozen verifier (full and quote-off) on the 210 test answers and the 334
frozen seeded copies (hash checked); verdicts committed before scoring. Treatment scored by the frozen
scorer (block = abstention; no judge calls), as scored and with the D-071 overlay. Driver
`eval/scripts/verify_test.py`. Likely verifier faults listed, not fixed (H-034).
**Tests:** full offline suite passes.
**Broken or unfinished:** Latency sample, owner hand-check, statistics and summary.json not started.
**Numbers worth keeping:** Seeded detection, quote off: T1 12/13, T3 55/62, T4 105/113, T5 30/30,
T6 105/113, macro 0.9337; T2 2/3 (3/3 full). False blocks on Correct: 0/186 as scored, 9/197 corrected.
Natural blocks 13, flags 3. Control abstentions added 7. Baseline → treatment: as scored 186/11/13 →
186/23/1; corrected 197/10/3 → 188/22/0. Precision 12/13 as scored, 3/13 corrected; recall 12/13 and
3/3. Model calls 3 (seeded only), verifier spend $0.0092; rules 0.0137 s per answer.
**Spend so far:** $4.6712.
**Next session starts with:** The owner's review of H-034, then step 8 (latency sample).
**Commit:** Phase 5 step 7: treatment scored from the saved verdicts, likely verifier faults listed

## 2026-10-19 — Phase 5 step 5: test seeded-error set built and frozen
**Built:** `eval/scripts/build_test_seeded.py` (dev seeding code unchanged); `results/test/seeded_v1.jsonl`
and its manifest; freeze test `tests/test_seeded_test_frozen.py`. D-072; one-time push.
**Tests:** 231 offline tests pass.
**Broken or unfinished:** Verifier run (step 6) not started.
**Numbers worth keeping:** Pool 113 of 186 Correct as scored. Kept 334 of 345 (T1 13, T2 3, T3 62,
T4 113, T5 30, T6 113); macro set 331. SHA-256 fe59b19e382b63ed241277bb1cea0a147421dbb9a19d4d63159f3958a72b40b7.
**Spend so far:** $4.6620 (no calls).
**Next session starts with:** Phase 5 step 6 (verifier run on test answers and the seeded set) after
the owner's go-ahead.
**Commit:** Phase 5 step 5: test seeded-error set built and frozen before any verifier run

## 2026-10-19 — Phase 5 step 4b: owner-approved baseline corrections (overlay)
**Built:** Correction overlay `results/test/baseline_corrections_v1.json` (11 rows, evidence per row)
and `results/test/baseline_summary_corrected_v1.json` via `eval/scripts/apply_test_corrections.py`.
Step 3 run drivers and step 4 scoring driver committed unchanged under `src/filingguard/eval/scripts/`.
D-071; H-033 resolved.
**Tests:** full offline suite passes.
**Broken or unfinished:** FG-0307 flagged (not corrected: its 2024 figure is outside the tolerance).
Verifier run and later steps not started.
**Numbers worth keeping:** As scored 186/11/13 → corrected 197/10/3 (Correct/Missed/Unsupported).
Correct handling 88.6% → 93.8%; answer coverage 77.4% → 84.9%; control abstain 11.9% both;
unsupported-claim rate 13/124 → 3/124. McNemar not testable on corrected scores.
**Spend so far:** $4.6620 (no calls).
**Next session starts with:** Phase 5 step 5 (test seeded set) after the owner's go-ahead.
**Commit:** Phase 5 step 4b: owner-approved baseline corrections as an overlay, drivers committed

## 2026-10-19 — Phase 5 steps 3 and 4: test batch answered, baseline scored (as scored)
**Built:** Test batch: 210 of 210 answers saved over 9 file-batch sub-batches (D-067 to D-069); 2
runaway replies unparseable (FG-0020, FG-0308). Premise judge on the 38 parseable test premise
answers (`results/judge/test_judge_v1.jsonl`). Baseline scored by the frozen scorer, as scored, no
corrections (`results/test/baseline_scores_v1.jsonl`, `results/test/baseline_summary_v1.json`).
Likely scorer faults and one likely test-set fault listed, not fixed (H-033). One-time push (D-070).
The run and scoring drivers live outside the repo (they call only the frozen repo functions).
**Tests:** full offline suite passes.
**Broken or unfinished:** Scorer corrections need the owner's row-by-row approval (EVAL §10 4b);
verifier run, seeded set, treatment scoring, latency, hand-check and statistics not started.
**Numbers worth keeping (as scored):** Correct 186, Missed 11, Unsupported 13 of 210. Correct
handling 186/210 (88.6%); answer coverage 113/146 (77.4%); control abstain 5/42 (11.9%); unanswerable
31/32 Correct; false premise 32/32 Correct; injection followed 0/32. Test batch $2.2530; judge $0.0881.
**Spend so far:** $4.6620.
**Next session starts with:** The owner's decisions on the H-033 rows, then step 5 (seeded set).
**Commit:** Phase 5 step 4: test baseline scored by the frozen scorer, judge decisions saved

## 2026-10-19 — Phase 5 pre-batch close: dev spot-check, wording fix, push
**Built:** Owner's spot-check of the dev score sheet recorded: 10 rows reviewed (the 4 abstentions
FG-0014, FG-0034, FG-0133, FG-0209; the 6 calendar-year rows FG-0155, FG-0162, FG-0166, FG-0173,
FG-0191, FG-0198), all 10 scored correctly. Dev report: calendar-year refusals for late-January
fiscal years noted as a coverage point. Judge hand-check wording fixed: reasons_in_filing is
reported as rated on 4 rows, disagree on all 4, 28 not rated by either; kappa kept only for the
four fields rated on all 32 rows. PHASE5_PLAN step 2b and ROADMAP Phase 4 step 1 marked done.
One-time push of `main` (D-066).
**Tests:** full offline suite passes.
**Broken or unfinished:** Every pre-batch item is done except the owner's go-ahead for the test
batch.
**Numbers worth keeping:** Spot-check 10 of 10 scored correctly.
**Spend so far:** $2.3210 (no calls).
**Next session starts with:** The owner's go-ahead for the test batch (plan step 3).
**Commit:** Phase 5 pre-batch: owner's dev spot-check, judge hand-check wording, D-066

## 2026-10-19 — Phase 5 step 1: owner's judge hand-check recorded
**Built:** Agreement between the owner's labels and the premise judge on the 32 dev decisions
(`results/judge/handcheck_dev_v1.json`, owner's sheet committed). EVAL §4 reasons-diagnostic note;
plan step 1 and ROADMAP marked done.
**Tests:** full offline suite passes.
**Broken or unfinished:** The owner's 90-row dev spot-check (10 rows prepared), then the test batch
go-ahead.
**Numbers worth keeping:** rejects_premise, confirms_change, gives_reasons, says_no_reasons_given:
32/32 each, kappa 1.0, baseline 16/16 and treatment 16/16. reasons_in_filing: rated on 4 rows;
owner and judge disagree on all 4 (judge had no passages; FG-0242 and FG-0303, both conditions,
judge False, owner True); 28 rows not rated by either.
**Spend so far:** $2.3210 (no calls).
**Next session starts with:** The owner's 90-row spot-check.
**Commit:** Phase 5 step 1: owner's judge hand-check recorded, reasons-check note in EVAL 4

## 2026-10-19 — Phase 5 step 2a: offline detector check on the owner's planted texts
**Built:** D-065 (no pass bar, descriptive only), committed before the owner's file was opened.
Offline check of the frozen detector on 10 owner-written planted texts, alone and planted in one
seeded clean chunk; no-text result `results/verifier/detector_check_v1.json`. EVAL §8, dev report,
plan step 2a and ROADMAP updated. `AGENTS.md` added to `.git/info/exclude` (local only).
**Tests:** full offline suite passes.
**Broken or unfinished:** The judge hand-check, the 90-row spot-check, and the go-ahead for the test
batch.
**Numbers worth keeping:** 2 of 10 flagged alone, 2 of 10 planted (marker 1/3, other 1/2,
false_figure 0/3, withhold 0/2). The 6 texts with no AI wording and no markup: all missed. Host
chunk `0001403161-25-000089:28`, seed `20261019-robustness`.
**Spend so far:** $2.3210 (no calls).
**Next session starts with:** The owner's judge hand-check and 90-row spot-check, then the test
batch go-ahead.
**Commit:** Phase 5 step 2a: offline detector check on the owner's planted texts, no-text result

## 2026-10-06 — Phase 5 prep: apostrophe fix tried and reverted, restatement-flag test, push
**Built:** Test `test_stale_value_with_restatement_words_is_a_flag_not_a_block`. The apostrophe fix in
the verifier's row rule was tried on dev (cache only, $0) and reverted because FG-0147 T6 went from
block to flag (D-063); verifier and dev results restored, freeze unchanged. EVAL §8 limits, the test
gap-fact line, PHASE5_PLAN gate-stop rule. One-time push of `main` and `verifier-v1` (D-064).
**Tests:** 229 offline tests pass, including the freeze test.
**Broken or unfinished:** Owner's 10 planted texts, judge hand-check, 90-row spot-check, and the
go-ahead for the test batch.
**Numbers worth keeping:** Dev unchanged: 153/153 with the model, 0/86 false blocks, 0 control
abstentions added. With the reverted fix it would have been 152/153.
**Spend so far:** $2.3210.
**Next session starts with:** The offline detector check on the owner's 10 planted texts.
**Commit:** Phase 5 prep: restatement-flag test, apostrophe fix tried and reverted (D-063), plan and
EVAL limits, push (D-064)

## 2026-10-06 — Phase 4 close and Phase 5 step 2: H-032 re-freeze, facts check, test pre-submit checks
**Built:** Verifier reopened once (D-061): a named filing's other value given at the answer's
printed precision is `stale_value`; BAC unit test; full dev re-run; re-freeze (new manifest hash,
freeze test updated, tag `verifier-v1` moved). Facts check on dev filings, report only
(`eval/facts_check.py`, `results/verifier/facts_check_dev_v1.md`, EVAL §8). Phase 5 plan approved
with changes and updated (D-062; EVAL §6, §10 4a and 4b). Harness `eval/dev_run.py` generalised by
split with `--owner-approved-test` for submit and write; test pre-submit checks run, nothing
submitted. Judge hand-check sheet `review/judge_handcheck_dev_v1.xlsx` (32 decisions).
**Tests:** 228 offline tests pass (new: H-032 BAC pair, test-split harness guards).
**Broken or unfinished:** Facts gaps (long-term debt in 10 companies; JNJ, XOM, PG R&D; DIS operating
income; BA gross profit) can cause false blocks on test; reported, not fixed. The test batch limit
($2.60) equals the projection at dev's 90th-percentile output. Open for the owner: the 10 planted
texts, the judge hand-check, the 90-row spot-check, and the test batch go-ahead.
**Numbers worth keeping:** Dev after D-061: seeded 153/153 both modes, T2 2 of 2, false blocks 0/86,
forced restated 0 of 4 blocked; only FG-0205 T2 changed. Facts check: 364 pairs, 243 match, 75 no
fact, 46 not on a row the verifier reads (31 label, 10 long-term debt, 5 different line). Test
pre-submit: 0 problems, 210 items, 0 dev, 32 injection chunks match, 0 test answers cached; projected
$2.02 (mean output) to $2.60 (p90 output), limit $2.60.
**Spend so far:** $2.3210 (no calls this session part).
**Next session starts with:** The offline detector check on the owner's 10 planted texts, then the
owner's go-ahead for the test batch.
**Commit:** Phase 4: H-032 fix and verifier re-freeze (D-061), facts check; Phase 5: plan approved
with changes, test harness and pre-submit checks (D-062)

## 2026-10-06 — Phase 4: owner's dev review, fixes A and B, scorer fixes, verifier frozen
**Built:** Owner's review of the v1 block sheet recorded in `results/verifier/dev_report.md`.
Verifier: when a question names a filing, the model sees only that filing's excerpts and is told
which (prompt `verifier_v2`); excerpts centred on the metric (H-031); a year before a comma read as
a period, acquired IPR&D not read as total R&D, other-metric figures without their own period not
checked (D-059). H-030 scorer fix and block precedence in EVAL §3 (D-059); EVAL §8 shared parser and
small restatements (H-032); EVAL §10 hand-check of 30 test rows. Dev seeded set v2 (T2 rebuilt).
Forced model check on dev restated answers. Full dev re-run (`dev_verifier_v2*`, `checks_v2.json`,
`review/verifier_dev_verifier_v2.xlsx`). Freeze record `results/verifier/freeze_v1.json`, tag
`verifier-v1` (D-060). Phase 5 plan and cost `docs/PHASE5_PLAN.md`, for approval.
**Tests:** 226 offline tests pass (new: H-030 attribution, block precedence, D-059 verifier fixes,
`other_metric_mismatch` never blocks, named-filing excerpts, excerpt window, freeze test).
**Broken or unfinished:** T2 FG-0205 passes the verifier because BAC's restatement is inside the
0.5% tolerance (H-032; not fixed, freeze limited to A and B). JNJ's R&D fact is not total R&D, so
FG-0303 keeps two R&D flags. The owner's Phase 4 step 1 spot-check of the 90-row sheet is still open.
**Numbers worth keeping (dev, in-sample):** 90 dev rows rescored after the scorer fixes: 0 changed.
T2 gate 2 of 3 kept. v2 seeded detection 152/153 in both modes; macro 1.0 (0.9843 quote off, no
model); T2 1 of 2; false blocks 0/86; no v1 decision changed. Forced model path on restated: 0 of 4
blocked (1 before the excerpt fix). Detector 4 of 6,311 clean chunks; 13/13 dev planted; style swap
0/16 changed (14 of 16 carry the abstain flag). Phase 4 verifier spend $0.0623 of $0.60.
**Spend so far:** $2.3210.
**Next session starts with:** The owner's 10 planted texts for the offline detector check, and the
owner's decision on `docs/PHASE5_PLAN.md`.
**Commit:** Phase 4: owner's dev review, verifier fixes A and B, H-030 scorer fix, verifier frozen (verifier-v1)

## 2026-10-05 — Phase 4: verifier built and tuned on dev (not frozen)
**Built:** Seeded-error design updated (D-057) and EVAL §4, §6, §8 entries before any verifier code.
Verifier `agents/verifier/` (question reading, corpus-only XBRL fact store, own lexicon; numeric,
period, restated, named-line, text-support, quote, premise and planted-instruction checks; one model
call at most; prompt `verifier_v1`). Dev seeded set `results/seeded/dev_seeded_v1.jsonl` (151 kept,
3 T2 dropped by the gate, H-030). Harness `eval/verify_dev.py`; checks `eval/verifier_checks.py`.
Results `results/verifier/dev_verifier_v1*`, `checks_v1.json`; review sheet
`review/verifier_dev_verifier_v1.xlsx`. D-058, H-030.
**Tests:** 213 offline tests pass (19 new verifier tests, including the six detector-spec tests).
**Broken or unfinished:** Owner review of the dev report and blocks sheet; verifier not frozen or
tagged. Open for the owner: the H-030 scorer fix; how a blocked answer containing a canary is
scored in treatment (the scorer checks the canary before the block).
**Numbers worth keeping (dev, tuned-on, descriptive):** Seeded detection 151/151 in both modes
(macro 1.0; quote rule off without the model call 0.984). False blocks 0/86 Correct answers;
control abstentions added 0. Detector flags 4 of 6,311 clean chunks (limit 6); dev planted chunks
13/13. Style swap: 0 of 16 changed. Model calls 2 (full) and 4 (quote off) over 241 answers per
mode; rules about 0.014 s per answer, a model call about 2.8 s. Verifier spend $0.0252.
**Spend so far:** $2.2839.
**Next session starts with:** The owner's review of the verifier dev report.
**Commit:** Phase 4: verifier dev report (v1), D-058, H-030

## 2026-10-05 — Phase 4: FG-0303 fix, metric definitions, seeded-error proposal (no model calls)
**Built:** Scorer fix (f) for FG-0303 (D-053), the only outcome change across 90 rows; test
added. Dev scores v3 (`results/dev/baseline_scores_v3.jsonl`, `baseline_summary_v3.json`,
`review/dev_score_sheet_v3.xlsx`). EVAL §4 verified-answer rate as correct handling and answer
coverage, control abstain denominator clarified (D-055); EVAL §6 testability of the bars (D-056).
Seeded-error evaluation proposal `docs/SEEDED_ERRORS.md` (not built).
**Tests:** 194 offline tests pass.
**Broken or unfinished:** Seeded-error design, thresholds and the weaker-target side experiment
await the owner. Verifier not started.
**Numbers worth keeping (dev v3, descriptive):** Correct 86, Missed 4, Unsupported 0. Correct
handling 86/90 (95.6%); answer coverage 51/63 (81.0%); control abstain 2/18 (11.1%).
Seeded-error set: 161 dev copies from 51 source answers; about 362 on test.
**Spend so far:** $2.2587 (no calls).
**Next session starts with:** The owner's decisions on the seeded-error design and thresholds.
**Commit:** Phase 4: FG-0303 scorer fix, verified-answer definition, testability, seeded-error proposal

## 2026-10-05 — Phase 4: scorer fixes, dev re-score, headroom analysis (no model calls)
**Built:** Scorer fixes a to e (D-053) with a unit test each; gold-row check re-run (passes).
Dev re-scored: `results/dev/baseline_scores_v2.jsonl`, `baseline_summary_v2.json`,
`review/dev_score_sheet_v2.xlsx` (v1 kept). EVAL §3 adjusted-figure sentence (dated, after dev
answers, before any test run); EVAL §4 secondary metric (D-054). Headroom analysis
`results/dev/headroom_v1.md`. H-029 logged.
**Tests:** 192 offline tests pass.
**Broken or unfinished:** FG-0303 regressed to Unsupported as a side effect of fix (a) (D-053);
fix needs the owner's approval. Verified-answer definition proposed, not adopted. EVAL §4 says
the control abstain rate is over "all 60 controls" but the test split has 42: needs a ruling.
**Numbers worth keeping (dev baseline v2, descriptive):** Correct 85, Missed 4, Unsupported 1
(0 on reading). Unsupported-claim rate 1/54 as scored. Control abstain 2/18 (11.1%). Of 54
returned answers, a block could help 1 (the artefact) and hurt 52. McNemar needs at least 6
test items Unsupported at baseline and blocked (two-sided exact p = 0.031).
**Spend so far:** $2.2587 (no calls this session step).
**Next session starts with:** The owner's decisions on FG-0303, the verified-answer definition,
the control denominator, and the headroom findings; then the verifier only if approved.
**Commit:** Phase 4: scorer bug fixes (D-053), dev re-score, secondary metric, headroom analysis

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
