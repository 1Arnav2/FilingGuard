# FilingGuard

A stress-test harness and hard-gated verifier for LLM finance research agents, built on SEC
10-K filings and XBRL facts.

> Status: in development. Results below are placeholders until the Phase 5 run.

## What it does
1. A **red-team agent** writes adversarial questions from real filings.
2. A **target agent** answers them.
3. A **verifier agent** checks every claim against the filing and blocks what it cannot support.
4. The **harness** scores both conditions and reports where the agent fails.

## Results
_To be filled from `results/summary.json`._

## Method
See `docs/EVAL.md`.

## Limits
See `docs/EVAL.md`, section 8.

## Reproduce
_To be written in Phase 7._
