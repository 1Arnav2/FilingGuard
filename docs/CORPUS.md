# CORPUS — FilingGuard

**Status:** Draft v1 · **Last updated:** 2026-10-04

## 1. Sources
All data is public and free from SEC EDGAR. No API key. Every request must carry a
`User-Agent` header with a name and email, and stay well under 10 requests per second.

| Data | Endpoint |
|---|---|
| Ticker to CIK map | `https://www.sec.gov/files/company_tickers.json` |
| Filing list per company | `https://data.sec.gov/submissions/CIK{cik10}.json` |
| XBRL facts per company | `https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json` |
| Filing documents | `https://www.sec.gov/Archives/edgar/data/{cik}/{accession-no-dashes}/{primary_doc}` |

`cik10` is the CIK padded with leading zeros to 10 digits. CIKs are resolved from the ticker
map in Phase 1, not typed by hand.

## 2. Company list (25, proposed)
Chosen for sector spread and for a mix of fiscal year-ends, which the period-mismatch attack
needs. The notes below were written from memory; the confirmed fiscal year-ends from the
submissions data are in §7. Differences: JNJ (`0103`) and DIS (`1003`) use 52/53-week years,
and V (`0930`) is also non-calendar. Because "latest 10-K" depends on the fiscal year-end, the
corpus mixes FY2025 and FY2026 filings.

| Sector | Tickers | Note |
|---|---|---|
| Tech | AAPL, MSFT, NVDA, GOOGL, META, ORCL | AAPL, MSFT, NVDA, ORCL are non-calendar fiscal years |
| Retail and consumer | AMZN, WMT, COST, NKE, KO, PG | WMT, COST, NKE, PG are non-calendar |
| Healthcare | JNJ, PFE, UNH | |
| Energy and industrial | XOM, CVX, BA, CAT | |
| Media and auto | DIS, TSLA | DIS is non-calendar |
| Financials | JPM, GS, BAC, V | See section 5 |

## 3. Filings
- Latest 10-K per company (form type `10-K`, not `10-K/A`).
- For the restated-figure attack: the prior year's 10-K as well, for the subset of companies
  where a restatement is found (see section 4).

## 4. Facts
Pulled from company facts, `us-gaap` taxonomy. These normalised facts are public data that
any agent may look up; they become gold labels only when the red-team attaches one to a test
item (D-013). Starting concept list:

`Revenues` / `RevenueFromContractWithCustomerExcludingAssessedTax`, `NetIncomeLoss`,
`OperatingIncomeLoss`, `GrossProfit`, `Assets`, `Liabilities`, `StockholdersEquity`,
`CashAndCashEquivalentsAtCarryingValue`, `EarningsPerShareBasic`, `EarningsPerShareDiluted`,
`ResearchAndDevelopmentExpense`, `LongTermDebt`,
`NetCashProvidedByUsedInOperatingActivities`.

Companies tag revenue under different concepts. Map each company to the concept it actually
uses and record the mapping in `data/processed/concept_map.json`.

**Finding restatements:** in company facts, the same concept and period can appear in more
than one filing. Where the values differ between the original 10-K and a later one, that
period was restated or reclassified. Collect these pairs for the `restated` attack. If fewer
than 40 usable pairs exist, reduce that attack's count and log it.

## 5. Known data issues
- **Financials** (banks, brokers) often lack `GrossProfit` and tag revenue differently.
  Restrict their items to concepts they report, or drop to fewer financial companies.
- **Duplicate facts:** the same value appears in several filings. Deduplicate on
  `(concept, period_start, period_end, unit)` and keep the filing that matches the 10-K in
  the corpus.
- **Units:** XBRL values are in base units (USD, shares). Filing tables state "in millions"
  or "in thousands". The unit-trap attack depends on this gap.
- **Segment data** is not in company facts. Out of scope for v1.

## 6. Processing
1. Download and cache raw files to `data/raw/` (git-ignored).
2. Parse 10-K HTML to text, keep table text, label each part by Item (D-018).
3. Chunk (about 800 tokens, 100 overlap, measured as 3,200 and 400 characters, D-017) with
   metadata: company, accession, item, char offsets.
4. Embed and index (D-016).
5. Write normalised facts to `data/processed/facts.parquet`. The target and verifier may read
   this file. `data/gold/` holds only per-item gold labels, written by the red-team in
   Phase 3 and read only by `eval/` (D-013).

## 7. Corpus card
Generated from `data/processed/` by `filingguard.data.build_corpus.card_markdown()`.

| Field | Value |
|---|---|
| Companies | 25 |
| Filings | 26 (latest 10-K for each company, plus the prior 10-K for BAC, which has restatement pairs) |
| Chunks | 5,215 (jinaai/jina-embeddings-v2-small-en) |
| Facts | 16,411 rows from original 10-Ks, all years; 720 from the latest 10-Ks |
| Restatement pairs found | 12 (BAC); 2 rounding-only pairs excluded |
| Revenue not mapped | none (fallback concept used: GS) |
| Exclusions and why | none. CIK overrides: XOM → CIK 34088 (D-014) |
| Date pulled | 2026-10-04 |
| Spot check | 10/10 facts match the filing text for the right period (`data/processed/spot_check.json`) |

Per company. Fiscal year-end is `MMDD` from SEC submissions data. Labelled share is the
share of text inside Items 1, 1A, 7, 7A, 8 (the rest is indexed as `other`, D-018). The
last column lists CORPUS §4 concepts with no annual value under that exact tag in the
latest 10-K; the company may report the figure under another tag.

| Ticker | Fiscal year-end | Latest 10-K period | Filed | Revenue concept | Labelled share | Standard concepts not tagged |
|---|---|---|---|---|---|---|
| AAPL | 0926 | 2025-09-27 | 2025-10-31 | RevenueFromContractWithCustomerExcludingAssessedTax | 80% | — |
| MSFT | 0630 | 2026-06-30 | 2026-07-29 | RevenueFromContractWithCustomerExcludingAssessedTax | 86% | — |
| NVDA | 0131 | 2026-01-25 | 2026-02-25 | Revenues | 59% | — |
| GOOGL | 1231 | 2025-12-31 | 2026-02-05 | Revenues | 87% | GrossProfit |
| META | 1231 | 2025-12-31 | 2026-01-29 | RevenueFromContractWithCustomerExcludingAssessedTax | 83% | GrossProfit |
| ORCL | 0531 | 2026-05-31 | 2026-06-22 | Revenues | 54% | GrossProfit, Liabilities, LongTermDebt |
| AMZN | 1231 | 2025-12-31 | 2026-02-06 | RevenueFromContractWithCustomerExcludingAssessedTax | 88% | GrossProfit, Liabilities, ResearchAndDevelopmentExpense |
| WMT | 0131 | 2026-01-31 | 2026-03-13 | Revenues | 84% | GrossProfit, Liabilities, ResearchAndDevelopmentExpense |
| COST | 0830 | 2025-08-31 | 2025-10-08 | Revenues | 73% | GrossProfit, LongTermDebt, ResearchAndDevelopmentExpense |
| NKE | 0531 | 2026-05-31 | 2026-07-15 | RevenueFromContractWithCustomerExcludingAssessedTax | 90% | Liabilities, OperatingIncomeLoss, ResearchAndDevelopmentExpense |
| KO | 1231 | 2025-12-31 | 2026-02-20 | Revenues | 83% | Liabilities, LongTermDebt, ResearchAndDevelopmentExpense |
| PG | 0630 | 2026-06-30 | 2026-08-04 | Revenues | 86% | CashAndCashEquivalentsAtCarryingValue, GrossProfit, LongTermDebt, StockholdersEquity |
| JNJ | 0103 | 2025-12-28 | 2026-02-11 | RevenueFromContractWithCustomerExcludingAssessedTax | 87% | OperatingIncomeLoss, StockholdersEquity |
| PFE | 1231 | 2025-12-31 | 2026-02-26 | Revenues | 86% | GrossProfit, LongTermDebt, OperatingIncomeLoss, ResearchAndDevelopmentExpense |
| UNH | 1231 | 2025-12-31 | 2026-03-02 | Revenues | 84% | GrossProfit, LongTermDebt, ResearchAndDevelopmentExpense, StockholdersEquity |
| XOM | 1231 | 2025-12-31 | 2026-02-18 | Revenues | 10% | GrossProfit, LongTermDebt, OperatingIncomeLoss |
| CVX | 1231 | 2025-12-31 | 2026-02-24 | Revenues | 23% | CashAndCashEquivalentsAtCarryingValue, GrossProfit, LongTermDebt, OperatingIncomeLoss |
| BA | 1231 | 2025-12-31 | 2026-01-30 | Revenues | 88% | — |
| CAT | 1231 | 2025-12-31 | 2026-02-13 | Revenues | 87% | GrossProfit, LongTermDebt, NetIncomeLoss, StockholdersEquity |
| DIS | 1003 | 2025-09-27 | 2025-11-13 | Revenues | 48% | GrossProfit, Liabilities, ResearchAndDevelopmentExpense |
| TSLA | 1231 | 2025-12-31 | 2026-01-29 | Revenues | 90% | — |
| JPM | 1231 | 2025-12-31 | 2026-02-13 | Revenues | 13% | CashAndCashEquivalentsAtCarryingValue, GrossProfit, LongTermDebt, OperatingIncomeLoss, ResearchAndDevelopmentExpense |
| GS | 1231 | 2025-12-31 | 2026-02-25 | RevenuesNetOfInterestExpense **(fallback)** | 96% | GrossProfit, LongTermDebt, OperatingIncomeLoss, ResearchAndDevelopmentExpense |
| BAC | 1231 | 2025-12-31 | 2026-02-25 | Revenues | 95% | CashAndCashEquivalentsAtCarryingValue, GrossProfit, OperatingIncomeLoss, ResearchAndDevelopmentExpense |
| V | 0930 | 2025-09-30 | 2025-11-06 | RevenueFromContractWithCustomerExcludingAssessedTax | 90% | EarningsPerShareBasic, EarningsPerShareDiluted, GrossProfit, LongTermDebt, ResearchAndDevelopmentExpense, StockholdersEquity |
