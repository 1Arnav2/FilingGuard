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
- [ ] Step 1, dev baseline: scorer and §3 tests written before any answer (D-047); dev target
      batch, 90 items (D-046, re-run after H-028); premise judge on the 16 dev premise items;
      baseline dev report and the 90-row score sheet — all done 2026-10-05; **owner spot-check
      of the sheet pending** (ticked after it)
- [x] Owner approves `docs/INJECTION_DETECTOR.md` (D-052) and the seeded-error design (D-057)
- [x] Dev seeded-error set with sanity gate (`docs/SEEDED_ERRORS.md`): 151 kept, 3 dropped (H-030)
- [x] Claim extraction
- [x] Span, numeric, period, and injection checks with reason codes; premise check
- [x] Unit tests for every deterministic check (`tests/test_verifier.py`)
- [x] Tune on dev split only (prompt v1 only; rule changes in D-058); **owner review of the dev
      report pending; verifier not frozen or tagged**
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
- [ ] Baseline and treatment on test split, once
- [ ] Metrics, intervals, McNemar, bootstrap by type
- [ ] Failure taxonomy labels
- [ ] `results/summary.json`
- **Done when:** every pass bar in `EVAL.md` is marked met or missed.

## Phase 6 — Dashboard (3 days, two sessions)
**6a. API and scaffold**
- [ ] Read-only FastAPI routes: summary, items list, item detail
- [ ] Next.js app scaffold, typed API client, layout
- [ ] Scorecard view

**6b. Views and deploy**
- [ ] Before/after by attack type (Recharts)
- [ ] Item explorer with filters and evidence drill-down
- [ ] Method page
- [ ] Static export served by FastAPI; Dockerfile; deploy to Render
- **Done when:** the public link loads from committed results on desktop and mobile.

## Phase 7 — Ship (1 day)
- [ ] README: problem, method, results, limits, how to reproduce
- [ ] Author check on full git history before making the repo public
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
