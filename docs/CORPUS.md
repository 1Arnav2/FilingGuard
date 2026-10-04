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
needs. Fiscal year-ends below are from memory and must be confirmed from the submissions
data in Phase 1.

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

## 4. Gold facts
Pulled from company facts, `us-gaap` taxonomy. Starting concept list:

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
2. Parse 10-K HTML to text, split by Item, keep table text.
3. Chunk (target about 800 tokens, 100 overlap) with metadata: company, accession, item,
   char offsets.
4. Embed and index.
5. Write normalised facts to `data/gold/facts.parquet`.

## 7. Corpus card (fill in during Phase 1)
| Field | Value |
|---|---|
| Companies | |
| Filings | |
| Chunks | |
| Gold facts | |
| Restatement pairs found | |
| Exclusions and why | |
| Date pulled | |
