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
- Retriever choice is provisional pending the owner (D-023).
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
