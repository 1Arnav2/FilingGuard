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
