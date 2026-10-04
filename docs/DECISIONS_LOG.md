# DECISIONS LOG — FilingGuard

Every meaningful decision and every hurdle, with the reasoning. This is the record I use for
interviews, the README, and the NYU application. Newest at the bottom. IDs never change.

## Decision template
```
### D-0NN — <short title>
**Date:**
**Phase:**
**Context:** what forced a choice
**Options considered:**
**Decision:**
**Why:**
**Trade-off accepted:**
**Revisit if:**
```

## Hurdle template
```
### H-0NN — <short title>
**Date:**
**Phase:**
**What happened:**
**Impact:** time lost, scope changed, metric affected
**What I tried:**
**Resolution:**
**Lesson:**
**Linked decision:** D-0NN
```

---

## Decisions

### D-001 — Build FilingGuard as the flagship project
**Date:** 2026-10-04 · **Phase:** Planning
**Context:** Needed one project that fits the NYU "Agentic AI for Risk Management" team, has
public evidence of a real company problem, and is buildable solo in about 10 days.
**Options considered:** FilingGuard; AML alert triage; agent-supervision monitor; MCP
tool-poisoning tests; trace failure labelling; four others.
**Decision:** FilingGuard.
**Why:** Highest score across evidence, team fit, job fit, and outreach. It reuses my
verifier work and adds the multi-agent and adversarial layer.
**Trade-off accepted:** Cannot test a commercial agent, only a stand-in.
**Revisit if:** A vendor offers sandbox access.

### D-002 — New repo, not a fork of FundClarity
**Date:** 2026-10-04 · **Phase:** Planning
**Context:** FundClarity is live and has a different corpus (497K fund filings).
**Options considered:** Fork FundClarity; add a module inside it; new repo.
**Decision:** New repo. Reuse the pipeline pattern and verifier ideas, not the code base.
**Why:** Keeps the live app safe and makes FilingGuard a harness, not a chatbot.
**Trade-off accepted:** Some code is rewritten.
**Revisit if:** Shared code grows enough to justify a small common package.

### D-003 — Pluggable target agent
**Date:** 2026-10-04 · **Phase:** Planning
**Context:** The pitch is that a team can point the harness at their own agent.
**Options considered:** Hard-wire one agent; adapter interface.
**Decision:** `TargetAgent` adapter. Agent A is a 10-K RAG agent; FundClarity via MCP is a
stretch second target.
**Why:** Proves generality and reuses the existing MCP server.
**Trade-off accepted:** Slightly more design work in Phase 2.
**Revisit if:** The adapter slows the core build.

### D-004 — Gold answers come from XBRL, not from an LLM
**Date:** 2026-10-04 · **Phase:** Planning
**Context:** If a model writes both the questions and the answers, the test set inherits its
errors.
**Options considered:** LLM-generated question-answer pairs; XBRL facts as gold with LLM
phrasing only.
**Decision:** XBRL facts as gold.
**Why:** Independent ground truth, and deterministic scoring for numeric items.
**Trade-off accepted:** Limited to tagged concepts; no segment data.
**Revisit if:** A later version needs narrative questions.

### D-005 — Frozen dev/test split and pass bars set in advance
**Date:** 2026-10-04 · **Phase:** Planning
**Context:** Tuning a verifier on the same items it is scored on inflates results.
**Options considered:** Single set; 90 dev and 210 test.
**Decision:** 90/210, stratified, frozen by seed. Pass bars written in `EVAL.md` first.
**Why:** The result has to hold up to questions from a research team.
**Trade-off accepted:** Fewer items for the headline number, wider intervals per attack type.
**Revisit if:** The test set grows past 500.

### D-006 — Streamlit for the dashboard (superseded by D-007)
**Date:** 2026-10-04 · **Phase:** Planning
**Context:** Ten-day budget.
**Options considered:** React front end; Streamlit.
**Decision:** Streamlit for v1.
**Why:** One day of work instead of three. The result matters more than the UI here.
**Trade-off accepted:** Less polished look.
**Revisit if:** There is time after Phase 7.

### D-007 — React dashboard instead of Streamlit
**Date:** 2026-10-04 · **Phase:** Planning
**Context:** D-006 chose Streamlit to save time. I would rather spend the time on a proper
front end.
**Options considered:** Streamlit; Next.js (React, TypeScript) static export served by FastAPI.
**Decision:** Next.js static export served by FastAPI, with Recharts.
**Why:** Matches the stack on my resume and the pattern already working in FundClarity, and
gives a demo that looks like a product.
**Trade-off accepted:** Phase 6 grows from 1 day to about 3. Total build is about 12 days.
**Revisit if:** The schedule slips past the NYU application date; then ship the scorecard
view first and the explorer after.

### D-008 — Clean git history with a single author
**Date:** 2026-10-04 · **Phase:** Planning
**Context:** The public repo should show one author and plain commit messages.
**Options considered:** Rely on habit; enforce with a hook, ignore rules, and a pre-push check.
**Decision:** Enforce: a local `commit-msg` hook strips trailer lines, local tooling config
files are excluded locally through `.git/info/exclude` (never pushed, so the public
`.gitignore` does not name them), and the log is checked before every push.
**Why:** A contributor entry is permanent once pushed unless history is rewritten.
**Trade-off accepted:** Local config files are not backed up by git; keep a copy elsewhere.
**Revisit if:** Never.

### D-009 — One installable package, `filingguard`
**Date:** 2026-10-04 · **Phase:** 0
**Context:** TRD §4 placed top-level packages `data`, `agents`, `eval`, `llm`, `api` directly
under `src/`. A package called `data` sits next to the repo's `data/` folder, and generic
top-level names can collide with installed libraries.
**Options considered:** Keep flat top-level packages; one package `src/filingguard/` with the
same subpackages.
**Decision:** `src/filingguard/{data,agents,eval,llm,api}`. TRD §4 updated.
**Why:** Unambiguous imports (`from filingguard.llm import ...`), no name clashes, standard
`src/` layout that installs with `pip install -e .`.
**Trade-off accepted:** One extra folder level in every path.
**Revisit if:** Never.

### D-010 — Reproducibility comes from committed run files, not the cache
**Date:** 2026-10-04 · **Phase:** 0
**Context:** The rule "re-runs cost zero API calls" relies on the disk cache, but `.cache/`
is git-ignored, so a fresh clone or the deployed dashboard would have to pay again.
**Options considered:** Commit the cache; archive the cache separately; keep the cache local
and commit raw responses per run.
**Decision:** Keep `.cache/` git-ignored. Every run writes the raw model response for each
item to `results/runs/*.jsonl`, which is committed. Scoring must re-run from those files with
zero API calls. Added to TRD §6.
**Why:** The run files are the evidence behind every published number, are small enough to
commit, and are readable by a reviewer. The cache is a build-time convenience.
**Trade-off accepted:** Re-running the target or verifier from a fresh clone costs API calls;
only re-scoring is free.
**Revisit if:** Someone needs to re-run generation bit-for-bit without API access.

### D-011 — `google-genai` SDK
**Date:** 2026-10-04 · **Phase:** 0
**Context:** TRD named Gemini but no SDK.
**Options considered:** `google-genai`; `google-generativeai`.
**Decision:** `google-genai` (2.28.0 at install).
**Why:** It is Google's current SDK; `google-generativeai` is deprecated.
**Trade-off accepted:** None material.
**Revisit if:** The LLM provider changes. The client takes a pluggable backend, so a swap
touches one function.

### D-012 — Pin `gemini-3.8-flash` for target and verifier
**Date:** 2026-10-04 · **Phase:** 0
**Context:** Phase 0 needs a pinned model ID for the cached test call. PRD §10 leaves model
choice open.
**Options considered:** Models the API key can use with `generateContent`, Flash tier:
`gemini-3.5-flash`, `gemini-3.6-flash`, `gemini-3.7-flash`, `gemini-3.8-flash` (all listed
as Stable on Google's models page); `gemini-3-flash-preview` (Preview);
`gemini-flash-latest` (moving alias); `gemini-2.5-flash` (access limited to past users).
**Decision:** `gemini-3.8-flash` for both `TARGET_MODEL` and `VERIFIER_MODEL`.
**Why:** Newest model in the Flash tier marked Stable. A fixed ID, not the `-latest` alias,
so results do not shift under us.
**Trade-off accepted:** Same model in both roles may share blind spots (EVAL §8). Free-tier
limits not checked yet.
**Revisit if:** Phase 2 finds free-tier limits too tight for an overnight 300-item run, or
the target and verifier should differ.

### D-013 — Facts in `data/processed/`, gold labels alone in `data/gold/`
**Date:** 2026-10-04 · **Phase:** 1
**Context:** CORPUS §6 wrote normalised XBRL facts to `data/gold/facts.parquet`, but the
verifier must check answers against XBRL facts, and nothing outside `eval/` may read
`data/gold/`.
**Options considered:** (1) facts in `data/processed/`, `data/gold/` holds only per-item
labels; (2) keep facts in `data/gold/` and exempt the verifier; (3) verifier fetches facts
from EDGAR itself.
**Decision:** Option 1, chosen by me. CORPUS §4 and §6, TRD §1 and §2.1 updated.
`tests/test_gold_isolation.py` fails if any module under `src/filingguard/agents/` imports
`filingguard.eval`, names a `gold` path segment, or reads an item's `"gold"` key.
**Why:** The verifier sees the same public facts any agent could look up, never the label
attached to a test item. The rule stays simple enough to enforce with a test.
**Trade-off accepted:** A gold label and a fact row can hold the same number. The separation
is about which item is being tested, not about hiding public data.
**Revisit if:** The red-team needs to live under `agents/` (see open question in BUILD_LOG).

### D-014 — CIK override for XOM
**Date:** 2026-10-04 · **Phase:** 1
**Context:** SEC's ticker map now resolves XOM to ExxonMobil Holdings Corp (CIK 2115436), a
successor issuer created on 2026-07-01 that has not filed a 10-K. See H-002.
**Options considered:** Override XOM to Exxon Mobil Corp (CIK 34088); replace XOM with
another energy company; run with 24 companies.
**Decision:** One documented override, `CIK_OVERRIDES = {"XOM": 34088}` in
`filings.py`. The pipeline now raises a clear error for any company with no 10-K.
**Why:** CIK 34088 filed the FY2025 10-K and holds all XBRL history. Keeps the CORPUS list
intact; the override is explicit and recorded in the corpus card.
**Trade-off accepted:** One CIK is set by hand, against CORPUS §1's "resolved, not typed".
**Revisit if:** The holding company files its first 10-K (expected early 2027).

### D-015 — Shared retry with exponential backoff
**Date:** 2026-10-04 · **Phase:** 1
**Context:** H-001 showed transient 503s; long runs will hit rate limits.
**Options considered:** Rely on the Gemini SDK's built-in retry; `tenacity`; a small shared
helper.
**Decision:** `filingguard/retry.py`: up to 6 attempts, full-jitter exponential backoff
(2 s base, 60 s cap). Retries HTTP 408, 429, 500, 502, 503, 504 and network errors; fails fast
on other 4xx. Used by the Gemini backend and the EDGAR client. Failed calls are never cached.
**Why:** One tested policy for both clients, no extra dependency, injectable sleep for tests.
**Trade-off accepted:** Stacks on top of the SDK's own short retry, so a hard outage takes a
few minutes to surface.
**Revisit if:** Phase 5 runs show long stalls; then add resume-from-checkpoint in the runner.

### D-016 — Local embeddings (jina-v2-small) and exact numpy search
**Date:** 2026-10-04 · **Phase:** 1
**Context:** TRD §3 suggested Chroma or FAISS and left the embedding model open. FundClarity's
choice could not be checked without reading its repo, which is consumed only through MCP.
**Options considered:** Gemini embeddings via API; local `bge-small-en-v1.5` (512-token limit);
local `jinaai/jina-embeddings-v2-small-en` (8,192 tokens, 512 dims); local
`snowflake-arctic-embed-m-long` (2,048 tokens, slower). Store: Chroma, FAISS, or numpy.
**Decision:** `jinaai/jina-embeddings-v2-small-en` through `fastembed` (ONNX, CPU), stored as
`embeddings.npy` + `chunks.jsonl` with exact cosine search. TRD §3 updated.
**Why:** No truncation of 800-token chunks; zero API quota spent on embeddings, so the Gemini
free tier is kept for the target and verifier; deterministic and free to rebuild. About
5,000 vectors do not need an approximate index.
**Trade-off accepted:** Smaller model than the best available; retrieval quality is unproven.
**Revisit if:** The Phase 2 smoke test shows retrieval misses; try arctic-embed-m-long first.

### D-017 — Chunk size in characters
**Date:** 2026-10-04 · **Phase:** 1
**Context:** CORPUS §6 asks for about 800 tokens with 100 overlap; the embedding model's
tokenizer is not the generation model's.
**Options considered:** Count tokens with the embedding tokenizer; count characters.
**Decision:** 3,200 characters with 400 overlap (about 4 characters per token), cut at line
breaks or spaces, every chunk carrying exact character offsets into the saved text.
**Why:** Simple, deterministic, model-independent, and offsets are what the span check needs.
**Trade-off accepted:** Token counts vary a little per chunk (tables tokenise denser).
**Revisit if:** Chunks overflow a model's context or retrieval suffers.

### D-018 — Index the whole 10-K, label chunks by Item
**Date:** 2026-10-04 · **Phase:** 1
**Context:** TRD §2.1 said split by Item 1, 1A, 7, 7A, 8. In practice several filers keep
financial statements or MD&A outside those headings. See H-003.
**Options considered:** Index only the five Items; add per-company layout rules; index the
whole document and label each chunk with its Item or `other`.
**Decision:** Whole document. Each chunk is labelled with the Item it falls in when that Item
is one of the five, otherwise `other`. Item detection keeps the longest section per Item and
ignores bare `Item N` running headers. TRD §2.1 updated.
**Why:** No company loses its financial statements; no per-company special cases.
**Trade-off accepted:** About 15% more chunks, and item labels are weak for six filers.
**Revisit if:** Retrieval is diluted by cover pages and exhibits lists.

### D-019 — Fact table fields and revenue fallbacks
**Date:** 2026-10-04 · **Phase:** 1
**Context:** SEC's `fy`/`fp` describe the filing, not the period (Apple's FY2023 revenue has
`fy=2025`). TRD named the columns `fiscal_year`, `fiscal_period`. Some companies tag revenue
with concepts outside CORPUS §4.
**Options considered:** Keep TRD names; rename; derive the period's fiscal year.
**Decision:** Columns `filing_fy`, `filing_fp`, plus `period_days` and `frame`. Keep every
original-10-K row for the tracked concepts (all years). Revenue is mapped from CORPUS §4
first, then `RevenuesNetOfInterestExpense`,
`RevenueFromContractWithCustomerIncludingAssessedTax`, `SalesRevenueNet`, and the status
(`primary`, `fallback`, `unmapped`) is recorded per company. TRD §2.1 updated.
**Why:** The renamed fields cannot be mistaken for the period's fiscal year, which the
period-mismatch attack depends on.
**Trade-off accepted:** Consumers must derive a period's fiscal year from `period_end` and the
company's fiscal year-end.
**Revisit if:** Phase 3 needs a period fiscal-year column; add it then.

### D-020 — What corpus output is committed
**Date:** 2026-10-04 · **Phase:** 1
**Context:** Reproducibility and repo size.
**Options considered:** Commit everything; commit nothing; commit small derived files only.
**Decision:** Commit `data/processed/{facts.parquet, concept_map.json, filings.json,
restatement_pairs.json, corpus_card.json, spot_check.json}`. Git-ignore `data/raw/`,
`data/processed/text/` and `data/processed/index/`; they rebuild from cached or public data
with `python -m filingguard.data.build_corpus`, with no API key.
**Why:** The committed files back every corpus-card number; the large files are
deterministic to rebuild.
**Trade-off accepted:** A fresh clone must re-download from SEC and re-embed (minutes).
**Revisit if:** Deploy needs the index (it should not; the dashboard reads results only).

### D-021 — Widen the restatement window; rules for the `restated` count
**Date:** 2026-10-04 · **Phase:** 2 (decided), applied at the start of Phase 3
**Context:** H-004: 12 usable pairs, all BAC, against 40 planned. A count over three 10-Ks
per company found up to 27 candidate pairs from BAC, NVDA, PFE and GOOGL.
**Options considered:** (A) keep 12 BAC items and move 28 elsewhere; (B) widen to three
10-Ks per company; (C) drop the attack type.
**Decision:** Option B, chosen by me, with these rules:
- Tag each pair `restatement`, `reclassification` or `stock_split`. Keep split adjustments
  only where the question can name the filing unambiguously; otherwise drop them.
- No single company supplies more than half of the `restated` items.
- Use however many usable pairs result, up to 40. Spread the shortfall evenly across the
  other five attack types. Controls stay at 60; the total stays at 300.
- Update the counts table in EVAL §2 before any item is generated, and state there that the
  `restated` result is descriptive only because of the small count. This is the only EVAL.md
  change approved.
- The extra downloads happen at the start of Phase 3.
**Why:** More companies and pairs make the `restated` result less about one bank.
**Trade-off accepted:** The `restated` count will still be below 40 and its interval wide.
**Revisit if:** Never for this test set version.

### D-022 — Red-team lives outside `agents/`
**Date:** 2026-10-04 · **Phase:** 2
**Context:** TRD placed the red-team in `agents/redteam/`, but it must write gold labels, and
the gold isolation test forbids anything under `agents/` from touching `data/gold`.
**Options considered:** (A) move it to `src/filingguard/redteam/`; (B) exempt
`agents/redteam/` from the test; (C) red-team writes items without gold, `eval/` attaches it.
**Decision:** Option A, chosen by me. `agents/` holds only the target and verifier; the
isolation test stays strict. TRD §1, §2.3 and §4 updated.
**Why:** The red-team builds the test set; it is not an agent under test, so it belongs with
the data side, not with the agents that must never see gold.
**Trade-off accepted:** None material.
**Revisit if:** Never.

### D-023 — Target retrieval: interleaved keyword + dense, k = 20 (provisional)
**Date:** 2026-10-04 · **Phase:** 2
**Context:** Owner's rule: the target must be a fair baseline; report retrieval hit rate and
add keyword search if it is poor. Dense-only hit@8 on the smoke set was 80% (hit@3 50%).
**Options considered:** Dense; BM25; equal-weight reciprocal rank fusion (RRF); interleaved
union of BM25 and dense; each at k = 10 or 20. See H-007 for the order of events.
**Decision:** `InterleavedRetriever(BM25, dense)` with k = 20 (top 10 of each), BM25
k1 = 1.2, b = 0.75, no tuning. Provisional: the owner confirms before the target is frozen.
**Why:** Window size mattered far more than method; at k = 20 dense, RRF and interleaved are
within one question of each other on 30 questions. Interleaving keeps exact-figure matches
(keyword) and paraphrase matches (dense) both in the context.
**Trade-off accepted:** About 16k tokens of context per question. On the fresh held-out set
the committed design scored 7/10 while dense alone scored 10/10 (in hindsight).
**Revisit if:** The owner prefers dense-only or a larger k; any change gets a new held-out set.

---

---

## Hurdles

### H-001 — 503 "high demand" from Gemini on a test call
**Date:** 2026-10-04
**Phase:** 0
**What happened:** A live call to `gemini-3.8-flash` returned `503 UNAVAILABLE: This model
is currently experiencing high demand`, after the SDK's own internal retries.
**Impact:** A few minutes. No scope change. Failed calls are never written to the cache, so
nothing bad was stored.
**What I tried:** Re-ran the same call once; it succeeded.
**Resolution:** Transient. No code change in Phase 0.
**Lesson:** A long overnight run will hit this. The Phase 5 runner needs retry with backoff
and must resume from completed items rather than restart.
**Linked decision:** D-012

### H-002 — XOM ticker resolves to a company with no 10-K
**Date:** 2026-10-04
**Phase:** 1
**What happened:** The first full pull crashed at XOM. SEC's ticker map points XOM to
ExxonMobil Holdings Corp (CIK 2115436), which became the listed entity on 2026-07-01
(8-K12B) and has filed only S-8 POS, 8-K and similar forms.
**Impact:** About 15 minutes. No scope change.
**What I tried:** Listed every form type for CIK 2115436 (no 10-K on any page); checked the
predecessor Exxon Mobil Corp, CIK 34088, which filed the FY2025 10-K on 2026-02-18 and has
full company facts.
**Resolution:** CIK override for XOM, and a clear error for any company without a 10-K.
**Lesson:** Ticker maps follow the listed entity, not the filer of record. Corporate
reorganisations will break "ticker → latest 10-K" for other companies over time.
**Linked decision:** D-014

### H-003 — 10-K Item structure is not reliable across filers
**Date:** 2026-10-04
**Phase:** 1
**What happened:** First parse of all 25 latest 10-Ks: 16 companies had 80–96% of text inside
Items 1, 1A, 7, 7A, 8. MSFT had 7%: it prints a bare "Item 7" running header on every page,
and each one cut the section. NVDA, ORCL and DIS put financial statements after Item 15
(Item 8 says "see page F-1"). XOM, CVX and JPM keep MD&A and statements in a separate
financial section after Item 16, or use a cross-reference index.
**Impact:** About an hour. Item labels for six filers are weak; no text is lost.
**What I tried:** Longest-section-per-Item to skip the table of contents; a 150-character
heading length limit to skip prose such as "see Item 7"; requiring punctuation after the Item
number, which fixed MSFT (7% → 86%); inspected XOM's heading lines and found the
"FINANCIAL SECTION" outside the Item structure.
**Resolution:** Index the whole document and label chunks by Item or `other`.
**Lesson:** Item labels are useful metadata but not a safe filter. The target agent should
search the whole filing.
**Linked decision:** D-018

### H-004 — Too few restatement pairs for the `restated` attack
**Date:** 2026-10-04
**Phase:** 1
**What happened:** Comparing the prior and latest 10-K for every mapped concept found 14 pairs
from 2 companies (BAC 12, XOM 2), against the 40 items EVAL §2 plans for `restated`. Reading
them showed the 2 XOM pairs are not restatements: R&D was tagged 879m and 987m originally and
900m and 1,000m ("$0.9 billion", "$1.0 billion") as comparatives in the next 10-K. Only the
12 BAC pairs are real restatements (revenue, net income, EPS, equity, assets, liabilities move
together, consistent with a retrospective accounting change).
**Impact:** The `restated` attack cannot reach 40 items from this corpus. Changing the counts
alters the test set's composition, so it is the owner's decision (pending).
**What I tried:** Checked every mapped concept for every company, instant and full-year
periods; confirmed most companies simply did not restate between the two filings. Added a
rounding rule (`is_rounding` in `facts.py`, tested) that tags precision-only changes as
`rounding`; they stay in `restatement_pairs.json` with that tag but are not counted.
**Resolution:** Pending: 12 usable pairs, from one company. Options listed in the Phase 1
summary. CORPUS §4 already says to reduce the count and log it if fewer than 40 pairs exist.
**Lesson:** Restatements are rare in a one-year window for large caps; this attack needs a
wider window or a broader definition to reach 40.
**Linked decision:** none yet

### H-005 — Embedding run used 8.5 GB of RAM
**Date:** 2026-10-04
**Phase:** 1
**What happened:** The first index build embedded in batches of 32. The process grew to
8.5 GB and left 0.8 GB free on a 15.3 GB machine.
**Impact:** About 20 minutes and one discarded run. No data lost (SEC downloads were cached).
**What I tried:** Stopped the process; timed batch size 4 on the 64 most number-dense chunks
(13.8 s); added a background guard that kills the build above 6 GB.
**Resolution:** Batch size 4, and a per-chunk embedding cache in `.cache/embeddings/` written
every 64 chunks so an interrupted build resumes. Peak memory over the full run fell to
2.2 GB; the run took about 10 minutes for 5,397 chunks. A cached rebuild takes 11 seconds.
**Lesson:** Attention memory scales with batch size times sequence length squared, and
financial tables tokenise densely. Measure on the worst chunks before a full run.
**Linked decision:** D-016

### H-006 — Free tier allows 20 requests per day for gemini-3.8-flash
**Date:** 2026-10-04
**Phase:** 2
**What happened:** The smoke run stopped at question 6 of 10 with `429 RESOURCE_EXHAUSTED`,
quota `GenerateRequestsPerDayPerProjectPerModel-FreeTier`, limit 20. Google's rate-limit page
does not publish free-tier numbers; they show only in AI Studio.
**Impact:** The smoke test is incomplete (7/10 run and cached). The full project needs
roughly 1,500 LLM calls (red-team phrasing, dev tuning, test run, judge), which is about 75
days at 20 per day. Blocks Phase 2 completion and every later phase until resolved.
**What I tried:** Read the error's quota details; checked the rate-limits docs page (limits
not listed). The retry layer was retrying this 429 with backoff, which cannot help a daily
quota; it now fails fast on per-day quota errors (tested) and still retries per-minute ones.
**Resolution:** Pending owner decision on model or billing (options in the Phase 2 summary).
**Lesson:** Check quotas, not just model names, before pinning a model. D-012 picked the
newest stable Flash without knowing its daily limit.
**Linked decision:** D-012

### H-007 — Retrieval choice nearly overfit to my own smoke questions
**Date:** 2026-10-04
**Phase:** 2
**What happened:** Dense-only retrieval was weak on the smoke set (hit@5 60%). BM25 scored
100% at k = 5, but I had written the smoke questions after grepping the filings for their
answers, so their wording echoed the text and favoured keyword search.
**Impact:** About two hours. Two extra held-out sets written.
**What I tried:** (1) Committed to interleaved k = 10 before testing it on held-out set 1
(10 paraphrased questions, hash recorded before any retrieval ran): 7/10 at k = 10; every
method's misses sat just outside the window. (2) Committed to interleaved k = 20, wrote
held-out set 2 (hash `b5502f78…`) before running it: 7/10. Across all 30 questions at k = 20:
dense 28/30 (95% CI 79–98%), interleaved 27/30 (74–97%), RRF 27/30, BM25 23/30.
**Resolution:** Stopped iterating; the choice goes to the owner (D-023). All results are in
`results/smoke/retrieval.json`.
**Lesson:** Questions for a retrieval check must be written without looking at the target
text, and a design must be fixed before its held-out set is scored.
**Linked decision:** D-023
