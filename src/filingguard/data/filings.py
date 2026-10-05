"""Company list, CIK resolution, and 10-K selection from EDGAR submissions data."""

import json
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from pathlib import Path

from filingguard.data.edgar_client import TICKERS_URL, EdgarClient, submissions_url

# CORPUS.md §2. Order is the order used everywhere downstream.
COMPANIES: dict[str, str] = {
    "AAPL": "Tech", "MSFT": "Tech", "NVDA": "Tech", "GOOGL": "Tech", "META": "Tech", "ORCL": "Tech",
    "AMZN": "Retail and consumer", "WMT": "Retail and consumer", "COST": "Retail and consumer",
    "NKE": "Retail and consumer", "KO": "Retail and consumer", "PG": "Retail and consumer",
    "JNJ": "Healthcare", "PFE": "Healthcare", "UNH": "Healthcare",
    "XOM": "Energy and industrial", "CVX": "Energy and industrial", "BA": "Energy and industrial",
    "CAT": "Energy and industrial",
    "DIS": "Media and auto", "TSLA": "Media and auto",
    "JPM": "Financials", "GS": "Financials", "BAC": "Financials", "V": "Financials",
}


# Tickers whose SEC ticker-map CIK has not filed the 10-K we need (D-014).
# XOM: on 2026-07-01 the ticker moved to ExxonMobil Holdings Corp (CIK 2115436, 8-K12B
# successor issuer), which has no 10-K yet. The FY2025 10-K was filed by Exxon Mobil Corp.
CIK_OVERRIDES: dict[str, int] = {"XOM": 34088}


@dataclass(frozen=True)
class Filing:
    ticker: str
    cik: int
    accession: str
    form: str
    filed: str
    report_date: str
    primary_document: str

    def to_dict(self) -> dict:
        return asdict(self)


def resolve_ciks(client: EdgarClient, tickers: list[str]) -> dict[str, int]:
    """Map each ticker to its CIK using SEC's ticker file, then `CIK_OVERRIDES`.

    Raises if any ticker is missing from the map.
    """
    rows = client.get_json(TICKERS_URL).values()
    by_ticker = {row["ticker"].upper(): int(row["cik_str"]) for row in rows}
    missing = [t for t in tickers if t not in by_ticker]
    if missing:
        raise KeyError(f"tickers not in SEC map: {missing}")
    return {t: CIK_OVERRIDES.get(t, by_ticker[t]) for t in tickers}


def _rows(block: dict) -> Iterator[dict]:
    keys = ("accessionNumber", "form", "filingDate", "reportDate", "primaryDocument")
    for values in zip(*(block[k] for k in keys)):
        yield dict(zip(keys, values))


def iter_filings(client: EdgarClient, submissions: dict) -> Iterator[dict]:
    """Yield every filing for a company, newest first: the `recent` block, then older pages."""
    yield from _rows(submissions["filings"]["recent"])
    for page in submissions["filings"].get("files", []):
        yield from _rows(client.get_json(f"https://data.sec.gov/submissions/{page['name']}"))


def _to_filing(ticker: str, cik: int, row: dict) -> Filing:
    return Filing(
        ticker=ticker,
        cik=cik,
        accession=row["accessionNumber"],
        form=row["form"],
        filed=row["filingDate"],
        report_date=row["reportDate"],
        primary_document=row["primaryDocument"],
    )


CORPUS_FILING_KEYS = ("latest_10k", "prior_10k", "older_10k")


def corpus_report_dates(filings_path: Path = Path("data/processed/filings.json")) -> dict[str, str]:
    """Map every indexed accession, including older 10-Ks, to its fiscal period end.

    The frozen target's own loader reads only the latest and prior 10-K; the harness passes
    this map to the agent's `report_dates` argument so excerpts from a third filing are dated.
    """
    dates = {}
    for company in json.loads(filings_path.read_text(encoding="utf-8")):
        for key in CORPUS_FILING_KEYS:
            filing = company.get(key)
            if filing and (key == "latest_10k" or filing["in_corpus"]):
                dates[filing["accession"]] = filing["report_date"]
    return dates


def ten_k_filings(client: EdgarClient, ticker: str, cik: int, submissions: dict, limit: int = 2) -> list[Filing]:
    """Return up to `limit` original 10-K filings (not 10-K/A), newest first.

    Raises if the company has no 10-K at all, which usually means the CIK is wrong.
    """
    found = []
    for row in iter_filings(client, submissions):
        if row["form"] == "10-K":
            found.append(_to_filing(ticker, cik, row))
            if len(found) == limit:
                break
    if not found:
        raise LookupError(f"{ticker} (CIK {cik}) has no 10-K; check CIK_OVERRIDES")
    return found
