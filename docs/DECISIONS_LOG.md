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
