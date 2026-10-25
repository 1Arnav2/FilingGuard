# ROADMAP — FilingGuard

One phase per working session. Each phase ends with: tests pass, roadmap ticked,
`BUILD_LOG.md` and `DECISIONS_LOG.md` updated, commit made, and my approval to continue.

## Phase 0 — Setup (0.5 day)
- [x] Create repo and folder; copy docs into `docs/`
- [x] `pyproject.toml`, `.env.example`, pytest skeleton
- [x] `.gitignore` covers `.env`, `data/raw/`, caches; local tooling files go in
      `.git/info/exclude`
- [x] Confirm `git config user.name` and `user.email` are mine; install the `commit-msg`
      hook from `setup/`; make one test commit and check the message is clean
- [x] LLM client with disk cache
- **Done when:** `pytest` runs and a cached test call to Gemini returns.

## Phase 1 — Data (1 day)
- [x] EDGAR client (throttle, cache, User-Agent)
- [x] Resolve CIKs; download latest 10-K and company facts for 25 companies
- [x] Parse and chunk 10-Ks; build index
- [x] Normalise facts; build concept map; find restatement pairs
- [x] Fill in the corpus card in `CORPUS.md`
- [x] Added at phase start: retry with backoff in the LLM and EDGAR clients; fiscal
      year-end and revenue-mapping flags per company in the corpus card; gold isolation test
- **Done when:** corpus card is complete and a spot check of 10 facts matches the filings.

## Phase 2 — Target agent (1 to 2 days)
- [x] `TargetAgent` interface and `AgentAnswer` schema
- [x] 10-K RAG agent with citations, behind FastAPI
- [x] Smoke test on 10 hand-written questions (10/10 with citations)
- [x] Added: retrieval hit rate on smoke + two held-out sets; keyword search added (D-023)
- [x] Owner confirms model/quota (D-024) and retriever (D-023); finish smoke; freeze target
      (tag `target-v1`)
- [x] Added: spend tracker with $5 warning and $7 hard cap; pricing config (D-024)
- **Done when:** the agent answers the smoke set with citations and logs a trace.

## Phase 3 — Red-team and test set (2 days)
- [x] Download the third 10-K per company; find pairs; tag restatement / reclassification /
      stock split; apply D-021 caps; update EVAL §2 counts before generating anything
- [x] Red-team package in `src/filingguard/redteam/` (D-022)
- [x] One generator per attack type, built from gold facts
- [x] Generate 400 candidates; dedupe and filter to 300; top up a short attack type only
      after reporting the extra cost (D-025)
- [x] Assign frozen dev/test split
- [x] Hand-check 60 items; fix or drop faulty ones; record the fault rate (first: at least 7 of 60,
      halted; final: 0 of 60, `results/testset/fault_rate_v1.json`)
- [x] Freeze: split, latency sample, file hashes, frozen-file test; tag `testset-v1` (D-044)
- **Done when:** `data/testset/v1.jsonl` is frozen and tagged.

## Phase 4 — Verifier (1 to 2 days)
- [x] Step 1, dev baseline: scorer and §3 tests written before any answer (D-047); dev target
      batch, 90 items (D-046, re-run after H-028); premise judge on the 16 dev premise items;
      baseline dev report and the 90-row score sheet — all done 2026-10-05; owner spot-check of
      the sheet done 2026-10-19 (10 rows: the 4 abstentions and the 6 calendar-year rows, all
      scored correctly)
- [x] Owner approves `docs/INJECTION_DETECTOR.md` (D-052) and the seeded-error design (D-057)
- [x] Dev seeded-error set with sanity gate (`docs/SEEDED_ERRORS.md`): 151 kept, 3 dropped (H-030);
      v2 after the H-030 scorer fix: 153 kept, 1 dropped (D-059)
- [x] Claim extraction
- [x] Span, numeric, period, and injection checks with reason codes; premise check
- [x] Unit tests for every deterministic check (`tests/test_verifier.py`)
- [x] Tune on dev split only (rule changes in D-058); owner's review of the dev report done
      2026-10-06, fixes A and B and prompt `verifier_v2` (D-059); `results/verifier/dev_report.md`
- [x] Verifier frozen and tagged `verifier-v1` (D-060); reopened once for H-032 and re-frozen,
      tag moved (D-061); dev results logged
- [x] Facts check on dev filings, report only (D-061, EVAL §8)
- [x] Owner's 10 planted texts for the offline detector check (after the re-freeze, before the test
      batch; reported as is): 2 of 10 flagged, descriptive only (D-065), 2026-10-19
- **Done when:** verifier is frozen and tagged; dev results logged.

## Phase 5 — Eval run (1 day)
**Budget risk (D-051), to be decided by the owner before Phase 5.** Re-projected 2026-10-05 from
measured spend: $2.26 spent (H-028 cost $0.90 of it). Measured: $0.0096 per dev item through
file batch jobs; $0.002 per judge call. Still to come in Phase 4: verifier tuning about
$0.5–$1.5, robustness set about $0.13–$0.20 if approved. Phase 5: test batch about $2.0–$2.4,
latency sample about $0.6–$0.7, judge about $0.1, verifier on test $0.4–$1.3. Project end about
**$6.0–$8.5**: the $5 warning trips in Phase 4 or early Phase 5, and the high end passes the $7
cap. Options: one verifier model call per answer on test; test verifier calls through the Batch
API; skip the robustness set.
**Re-projected 2026-10-06** from measured unit costs, after the verifier freeze ($2.321 spent):
Phase 5 $2.69–$3.46, project end **$5.01–$5.78**, under the $7 cap (`docs/PHASE5_PLAN.md`).
- [x] Owner approves `docs/PHASE5_PLAN.md` (approved with changes 2026-10-06, D-062); test batch
      needs a separate go-ahead
- [x] Test harness generalised; pre-submit checks run on test, nothing submitted (D-062)
- [x] Owner's judge hand-check on the 16 dev premise items (EVAL §5), 2026-10-19: scoring fields
      32/32 (kappa 1.0); reasons_in_filing rated on 4 rows, disagree on all 4 (judge had no
      passages), 28 not rated by either (`results/judge/handcheck_dev_v1.json`)
- [x] Baseline and treatment on test split, once (D-067–D-069; 2026-10-19)
- [x] Owner hand-checks 30 scored test rows chosen by seed, both conditions, plus every non-Correct
      baseline row, every blocked or flagged answer and every missed seeded error; agreement on the
      random 30 reported separately (EVAL §10 4a): random 30 29/30, others 38/48
- [x] Results reported as scored and after owner-approved parsing corrections (EVAL §10 4b, D-071)
- [x] Metrics, intervals, McNemar, bootstrap by type
- [x] Failure taxonomy labels (per type in `results/summary.json`)
- [x] `results/summary.json` — Phase 5 done 2026-10-19; every bar marked met, not met or not
      testable
- **Done when:** every pass bar in `EVAL.md` is marked met or missed.

## Phase 6 — Dashboard (3 days, two sessions)
**6a. API and scaffold**
- [x] Read-only FastAPI routes: summary, items list, item detail (D-074)
- [x] Next.js app scaffold, typed API client, layout
- [x] Scorecard view: both bases, pass bars, limitations (2026-10-21)

**6b. Views and deploy**
- [x] Fixes to 6a: per-item data from a results export, overlay not re-stated in the API (D-075);
      headline as a content file, checked against summary.json
- [x] Before/after by attack type (Recharts in 6b; plain HTML bars since 6c)
- [x] Item explorer with filters and evidence drill-down (gold, figures read, judge, both bases,
      verdict, D-071 correction, owner's hand-check)
- [x] Method page (2026-10-21)
- [x] Static export served by FastAPI; Dockerfile; live target route behind `FILINGGUARD_LIVE_TARGET`,
      off by default (D-078, 2026-10-24)
- [ ] ~~Deploy to Render~~ superseded by 6d: static site on Vercel (D-079)

**6d. Static deploy (D-079)**
- [x] Render path dropped (`render.yaml` removed); FastAPI and Docker kept for local runs
- [x] LinkedIn link set in `web/content/author.json`
- [x] Site reads `results/` at build time; filters, search, sort, presets and navigation in the page;
      one static page per item; no runtime API (2026-10-24)
- [x] Safety tests on the source and the built output; page filtering checked equal to the API
- [ ] Deploy to Vercel (owner: push, then create the project with `web/` as the root)

**6c. Redesign (owner's DESIGN_SPEC.md, Must tier; D-076)**
- [x] Overview page with stat cards, how-it-works diagram, author block, outreach line, video slot
- [x] "Why two numbers?" explainer; corrected primary, as scored only where it differs
- [x] Numbers link to pre-filtered Items views; Items presets (API flag filters)
- [x] Mobile: tables become cards, nothing hidden; 44 px tap targets
- [x] Accessibility (spec 4.8): contrast measured in light and dark, focus ring, titles, skip link,
      labelled landmarks, live regions, text alternatives, reduced motion
- [x] Item detail in decision-first order with the "what happened" sentence
- [x] Plain names instead of codes (spec 4.7 copy); light and dark mode with a toggle (2026-10-21)
- [x] Polish after review: plain limitation summaries on Overview, every rate as a percentage, money
      in verifier reasons, footer spend, Details chevron, new hero eyebrow (D-077)
- [x] Should tier: search by ID or company, sortable columns, previous/next within the current list,
      Jump to on Results, Method and item detail, glossary and definition tooltips, H-034 linked to the
      False blocks view (2026-10-22)
- [ ] Could tier: later
- **Done when:** the public link loads from committed results on desktop and mobile.

## Phase 7 — Ship (1 day)
- [x] README: problem, method, results, limits, how to reproduce; numbers checked against
      `results/` by `tests/test_readme.py` (2026-10-24)
- [x] Author check on full git history before making the repo public (7a audit, 2026-10-24)
- [ ] Repo topics (GitHub CLI not installed in 7a; owner to add)
- [x] Brand: logo in the header, favicon, touch icon, link-preview image, README lockup (7b, D-083)
- [ ] Three-minute demo video
- [ ] Resume bullet with real numbers
- [ ] Outreach messages sent
- **Done when:** repo is public and the first five messages are out.

## Stretch
- [ ] Weaker-target side experiment (one setting changed, e.g. top-5 retrieval; labelled side run,
      never a headline): an option after Phase 5 only if budget remains (D-057); about $1.7–$2.7
- [ ] FundClarity as second target via MCP
- [ ] Second model comparison
- [ ] Timed user study

## Milestone for the NYU application
Phases 0 to 3 complete, plus dev-split results from Phase 4. Enough to show a working
project with an honest early number.
