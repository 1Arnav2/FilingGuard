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
is git-ignored, and the log is checked before every push.
**Why:** A contributor entry is permanent once pushed unless history is rewritten.
**Trade-off accepted:** Local config files are not backed up by git; keep a copy elsewhere.
**Revisit if:** Never.

---

## Hurdles

_None yet._
