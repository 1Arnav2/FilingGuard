# TRD — FilingGuard

**Status:** Draft v1 · **Last updated:** 2026-10-04

## 1. Architecture

```mermaid
flowchart LR
  subgraph Data
    E[SEC EDGAR 10-K text] --> C[Chunk + embed]
    X[XBRL company facts] --> G[Gold facts store]
  end
  G --> R[Red-team agent]
  E --> R
  R --> T[(Test set: ~300 items)]
  T --> H[Eval harness]
  H --> A[Target agent adapter]
  A --> A1[10-K RAG agent]
  A --> A2[FundClarity via MCP]
  A1 --> V[Verifier agent]
  A2 --> V
  C --> V
  X --> V
  V --> H
  G -.gold, eval only.-> H
  H --> S[(results/ SQLite + JSONL)]
  S --> API[FastAPI read-only results API]
  API --> D[React dashboard]
```

Two rules that the diagram encodes:
- The verifier reads filing text and XBRL facts, never the gold label for a test item.
- The harness is the only component that reads gold labels.

## 2. Components

### 2.1 Data layer (`src/data/`)
- `edgar_client.py`: throttled, cached client. Sends `User-Agent` from `.env`.
  - Ticker to CIK: `https://www.sec.gov/files/company_tickers.json`
  - Filing index: `https://data.sec.gov/submissions/CIK{cik10}.json`
  - Facts: `https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json`
  - Filing documents: `https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}`
- `parse_10k.py`: HTML to clean text, split by Item (1, 1A, 7, 7A, 8), keep tables as text.
- `facts.py`: normalise XBRL facts to rows of `(company, concept, period_start, period_end,
  fiscal_year, fiscal_period, unit, value, form, filed, accession)`.

### 2.2 Target agents (`src/agents/targets/`)
Common interface:

```python
class TargetAgent(Protocol):
    name: str
    def answer(self, question: str, company: str) -> AgentAnswer: ...

@dataclass
class AgentAnswer:
    text: str
    claims: list[Claim]        # value, unit, period, concept if stated
    citations: list[Citation]  # doc id + char span
    abstained: bool
    latency_s: float
    trace: dict
```

- `tenk_rag.py`: retrieve top-k chunks, generate with citations. No verifier inside it, so the
  baseline is honest.
- `fundclarity_mcp.py` (stretch): calls `ask_fund_question` on the existing MCP server.

### 2.3 Red-team agent (`src/agents/redteam/`)
Builds items from gold facts first, then asks the LLM only to phrase the question. This keeps
the gold answer independent of any model. One generator per attack type (see `EVAL.md`).

Item schema:

```json
{
  "id": "FG-0001", "company": "AAPL", "attack_type": "unit_trap",
  "question": "...", "expected_behavior": "answer|abstain",
  "gold": {"value": 0, "unit": "USD", "period_end": "YYYY-MM-DD", "concept": "..."},
  "source": {"accession": "...", "span": [0, 0]},
  "split": "dev|test", "human_checked": false
}
```

### 2.4 Verifier agent (`src/agents/verifier/`)
Pipeline, cheapest check first:
1. **Claim extraction:** pull each number, unit, period, and entity from the answer.
2. **Span check:** does the cited span exist and contain the claim?
3. **Numeric check:** match against XBRL facts with unit normalisation (thousands, millions,
   billions) and a relative tolerance set in config.
4. **Period check:** fiscal vs calendar year, and whether the value was later restated.
5. **Injection check:** flag answers that follow instructions found in retrieved text.
6. **Verdict:** `pass`, `block`, or `flag`, with a machine-readable reason code.

Steps 2 to 4 are deterministic. LLM calls are limited to steps 1 and 5.

### 2.5 Harness (`src/eval/`)
- `run.py`: for each item, call target, then verifier; store both.
- `score.py`: compare to gold; compute metrics and confidence intervals.
- `stats.py`: Wilson intervals, McNemar test, bootstrap by attack type.
- `taxonomy.py`: assign a failure label to each wrong answer.

### 2.6 Dashboard (`web/`)
Next.js (React, TypeScript), built as a static export and served by the same FastAPI service,
the pattern already used for FundClarity's new UI. Charts with Recharts.

Views:
- **Scorecard:** headline metrics with intervals, baseline vs verifier.
- **By attack type:** before/after bars for each of the seven item types.
- **Item explorer:** filter by attack type, verdict, and failure label; open any item to see
  question, answer, verdict, reason code, and the evidence span.
- **Method:** short plain-language summary linking to `EVAL.md`.

Read-only API (`src/api/`):
- `GET /api/summary` returns `results/summary.json`
- `GET /api/items?attack_type=&verdict=&label=` returns paged item results
- `GET /api/items/{id}` returns one item with trace and evidence

The dashboard reads committed results only. It makes no live LLM calls.

## 3. Stack
| Layer | Choice | Note |
|---|---|---|
| Language | Python 3.11 | |
| LLM | Gemini API | Exact model IDs pinned in `.env`; check current free-tier limits in Phase 2 |
| Embeddings + vector store | Local store (Chroma or FAISS) | Mirror FundClarity's choice unless there is a reason not to; log the decision |
| API | FastAPI | Target agent endpoint |
| Storage | SQLite + JSONL | |
| Dashboard | Next.js (React, TypeScript), Recharts, static export | Served by FastAPI; same pattern as FundClarity's new UI |
| Tests | pytest | Verifier steps 2 to 4 get unit tests |
| Deploy | Render free tier, Docker, one service | FastAPI serves the API and the static dashboard |

## 4. Repo layout
```
FilingGuard/
  README.md  .env.example  .gitignore  pyproject.toml  Dockerfile
  docs/      PRD.md TRD.md EVAL.md CORPUS.md ROADMAP.md BUILD_LOG.md DECISIONS_LOG.md
  src/
    data/    edgar_client.py parse_10k.py facts.py
    agents/  targets/ redteam/ verifier/
    eval/    run.py score.py stats.py taxonomy.py
    llm/     client.py cache.py
    api/     main.py routes.py
  web/       Next.js app (app/, components/, lib/)
  data/      raw/ (git-ignored)  processed/  gold/  testset/
  results/   runs/*.jsonl  summary.json
  tests/
```

## 5. Config (`.env`)
```
GEMINI_API_KEY=
TARGET_MODEL=
VERIFIER_MODEL=
SEC_USER_AGENT="Name email@example.com"
NUMERIC_REL_TOLERANCE=0.005
```

## 6. Non-functional
- **Reproducibility:** fixed seeds, pinned model IDs, cached calls, every run tagged with a
  git commit hash.
- **Cost:** zero. Free tiers only.
- **Runtime:** a full 300-item run should finish overnight on the free tier.

## 7. Known technical risks
- 10-K HTML is messy; tables may parse badly. Fallback: use XBRL facts for numbers and text
  only for citations.
- Financial companies use different XBRL concepts. See `CORPUS.md`.
- Free-tier quotas change. Keep the LLM client swappable.
