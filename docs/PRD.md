# PRD — FilingGuard

**Owner:** Arnav Ambre · **Status:** Draft v1 · **Last updated:** 2026-10-04

## 1. Problem
Finance research agents answer questions about company filings, but they sometimes return
wrong numbers or unsupported claims with full confidence. Users then re-check every answer
against the source, which removes most of the time saved. Regulators (FINRA's 2026 oversight
report, SEC FY2026 exam priorities) now expect firms to supervise AI agents and to be able to
show how accurate they are.

Teams shipping these agents lack a cheap, repeatable way to answer two questions:
1. Where exactly does our agent fail?
2. How much does a verification gate help, and what does it cost in coverage?

## 2. Users
| User | Need |
|---|---|
| **PM on an agent team** (primary) | A number to set a launch bar on, and a failure breakdown to prioritise fixes |
| **Agent engineer** | A regression suite to run before each release |
| **Compliance reviewer** | Evidence that unsupported answers are blocked and logged |

## 3. Goals
- G1. Generate a labelled adversarial test set from real 10-K filings, with gold answers that
  come from XBRL facts and not from an LLM.
- G2. Measure a target agent's unsupported-claim rate, by attack type.
- G3. Show how much a hard-gated verifier reduces that rate, and what it costs in coverage
  and latency.
- G4. Work on more than one agent through a simple adapter.

## 4. Non-goals (v1)
- Testing Rogo's, Hebbia's, or any vendor's actual product.
- Earnings-call audio, slide or model generation, fine-tuning.
- A leaderboard across many models (max two).
- Real-time or streaming use. Multi-user accounts.
- Any claim about investment advice.

## 5. Metrics
| Type | Metric | Definition |
|---|---|---|
| **North Star** | Verified-answer rate | Share of all questions where the system returned an answer and it was correct |
| Primary | Unsupported-claim rate | Share of returned answers that are wrong or unsupported |
| Guardrail | Abstain rate on control items | Share of clean, answerable questions the verifier wrongly blocked |
| Guardrail | Latency | Median and p95 seconds per question, with and without the verifier |
| Verifier quality | Precision and recall | On the task "should this answer be blocked?" |
| User value | Verification time | Minutes to check an answer with vs without FilingGuard (small timed study) |

Targets are set in `EVAL.md` before any test-split run.

## 6. Scope of v1
**In**
- 25 companies, latest 10-K each, plus XBRL company facts.
- Target agent A: a new 10-K RAG agent behind a FastAPI endpoint.
- Target agent B (stretch): FundClarity via its existing MCP server.
- Red-team generator: six attack types plus clean control items, about 300 items.
- Verifier: span check, numeric check against XBRL, unit and period normalisation, abstain path.
- Eval runner, results store, dashboard with drill-down by attack type.
- README with method, limits, and reproducible numbers. Three-minute demo video.

**Out**
- Everything listed in Non-goals.

## 7. User stories
- As a PM, I upload nothing and run one command, and I get a scorecard by attack type.
- As an engineer, I point the harness at my agent's endpoint by writing one adapter class.
- As a reviewer, I open any blocked answer and see the claim, the evidence searched, and the
  reason it was blocked.

## 8. Go-to-market framing
Position as a **pre-deployment agent audit**: a scorecard a team attaches to its supervisory
procedures. Open source, so the outreach ask is feedback on the failure categories, not a sale.

## 9. Risks
| Risk | Mitigation |
|---|---|
| Red-team items are themselves wrong | Gold answers come from XBRL; 60 items hand-checked; error rate of the test set is reported |
| Verifier is tuned to the test | Frozen dev/test split |
| Free-tier rate limits slow the build | Cache all calls; batch runs overnight |
| Stand-in agent is weaker than commercial agents | State this plainly; pitch the harness, not the findings |
| Bank and insurer XBRL differs from industrial companies | Handle in corpus selection; log exclusions |

## 10. Open questions
- Which Gemini model for target vs verifier, given current free-tier limits?
- Is the timed user study feasible in the schedule, or does it move to v1.1?
