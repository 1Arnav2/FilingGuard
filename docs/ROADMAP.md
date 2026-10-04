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
- [ ] Smoke test on 10 hand-written questions (7/10 run; blocked by H-006)
- [x] Added: retrieval hit rate on smoke + two held-out sets; keyword search added (D-023)
- [ ] Owner confirms model/quota (H-006) and retriever (D-023); re-run smoke; freeze target
- **Done when:** the agent answers the smoke set with citations and logs a trace.

## Phase 3 — Red-team and test set (2 days)
- [ ] Download the third 10-K per company; find pairs; tag restatement / reclassification /
      stock split; apply D-021 caps; update EVAL §2 counts before generating anything
- [ ] Red-team package in `src/filingguard/redteam/` (D-022)
- [ ] One generator per attack type, built from gold facts
- [ ] Generate about 500 candidates; dedupe and filter to 300
- [ ] Assign frozen dev/test split
- [ ] Hand-check 60 items; fix or drop faulty ones; record the fault rate
- **Done when:** `data/testset/v1.jsonl` is frozen and tagged.

## Phase 4 — Verifier (1 to 2 days)
- [ ] Claim extraction
- [ ] Span, numeric, period, and injection checks with reason codes
- [ ] Unit tests for every deterministic check
- [ ] Tune on dev split only
- **Done when:** verifier is frozen and tagged; dev results logged.

## Phase 5 — Eval run (1 day)
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
- [ ] FundClarity as second target via MCP
- [ ] Second model comparison
- [ ] Timed user study

## Milestone for the NYU application
Phases 0 to 3 complete, plus dev-split results from Phase 4. Enough to show a working
project with an honest early number.
