"""Normalise XBRL company facts, map concepts per company, and find restated values.

Note: SEC's `fy` and `fp` describe the filing a value appeared in, not the period it covers
(Apple's FY2023 revenue appears with fy=2025 in the FY2025 10-K). They are stored as
`filing_fy` and `filing_fp` for that reason.
"""

from datetime import date

import pandas as pd

from filingguard.data.filings import Filing

REVENUE_PRIMARY = ["Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"]
REVENUE_FALLBACK = [
    "RevenuesNetOfInterestExpense",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
    "SalesRevenueNet",
]
# CORPUS.md §4, revenue handled separately through the candidate lists above.
OTHER_CONCEPTS = [
    "NetIncomeLoss",
    "OperatingIncomeLoss",
    "GrossProfit",
    "Assets",
    "Liabilities",
    "StockholdersEquity",
    "CashAndCashEquivalentsAtCarryingValue",
    "EarningsPerShareBasic",
    "EarningsPerShareDiluted",
    "ResearchAndDevelopmentExpense",
    "LongTermDebt",
    "NetCashProvidedByUsedInOperatingActivities",
]
ALL_CONCEPTS = REVENUE_PRIMARY + REVENUE_FALLBACK + OTHER_CONCEPTS

FULL_YEAR_DAYS = range(350, 381)  # covers 52/53-week fiscal years

COLUMNS = [
    "ticker", "cik", "concept", "unit", "period_start", "period_end", "period_days",
    "value", "filing_fy", "filing_fp", "form", "filed", "accession", "frame",
]


def _days(start: str | None, end: str) -> int | None:
    if not start:
        return None
    return (date.fromisoformat(end) - date.fromisoformat(start)).days


def normalise_company_facts(ticker: str, cik: int, companyfacts: dict) -> pd.DataFrame:
    """Return one row per reported value of the tracked concepts in original 10-K filings."""
    gaap = companyfacts["facts"].get("us-gaap", {})
    rows = []
    for concept in ALL_CONCEPTS:
        for unit, entries in gaap.get(concept, {}).get("units", {}).items():
            for e in entries:
                if e.get("form") != "10-K":
                    continue
                rows.append({
                    "ticker": ticker,
                    "cik": cik,
                    "concept": concept,
                    "unit": unit,
                    "period_start": e.get("start"),
                    "period_end": e["end"],
                    "period_days": _days(e.get("start"), e["end"]),
                    "value": float(e["val"]),
                    "filing_fy": e.get("fy"),
                    "filing_fp": e.get("fp"),
                    "form": e["form"],
                    "filed": e["filed"],
                    "accession": e["accn"],
                    "frame": e.get("frame"),
                })
    df = pd.DataFrame(rows, columns=COLUMNS)
    return df.drop_duplicates().reset_index(drop=True)


def is_annual(df: pd.DataFrame) -> pd.Series:
    """True for instant values and for durations of one fiscal year."""
    return df["period_start"].isna() | df["period_days"].isin(FULL_YEAR_DAYS)


def _has_latest_value(df: pd.DataFrame, concept: str, latest: Filing) -> bool:
    rows = df[
        (df["concept"] == concept)
        & (df["accession"] == latest.accession)
        & (df["period_end"] == latest.report_date)
        & is_annual(df)
    ]
    return not rows.empty


def map_concepts(df: pd.DataFrame, latest: Filing) -> dict:
    """Pick the concept each company uses for each metric in its latest 10-K.

    Revenue status is `primary` (a CORPUS §4 concept), `fallback` (an alternative revenue
    concept) or `unmapped`. Other metrics map to their concept, or None if not reported.
    """
    company = df[df["ticker"] == latest.ticker]
    revenue, status = None, "unmapped"
    for candidates, label in ((REVENUE_PRIMARY, "primary"), (REVENUE_FALLBACK, "fallback")):
        revenue = next((c for c in candidates if _has_latest_value(company, c, latest)), None)
        if revenue:
            status = label
            break
    others = {c: (c if _has_latest_value(company, c, latest) else None) for c in OTHER_CONCEPTS}
    return {"Revenue": revenue, "revenue_status": status, **others}


def _trailing_zeros(value: float) -> int:
    n = abs(int(round(value)))
    if n == 0 or n != abs(value):
        return 0
    zeros = 0
    while n % 10 == 0:
        n //= 10
        zeros += 1
    return zeros


def is_rounding(a: float, b: float, min_zeros: int = 5) -> bool:
    """True if one value is the other rounded to fewer digits (879,000,000 vs 900,000,000).

    Filers sometimes tag a prior-year comparative at the precision printed in the text
    ("$0.9 billion"). That is a precision change, not a restatement.
    """
    for rounded, precise in ((a, b), (b, a)):
        zeros = _trailing_zeros(rounded)
        if zeros >= min_zeros and _trailing_zeros(precise) < zeros and round(precise, -zeros) == rounded:
            return True
    return False


def find_restatements(df: pd.DataFrame, latest: Filing, prior: Filing, concept_map: dict) -> list[dict]:
    """Return annual values reported differently in the prior and latest 10-K.

    A pair means the same concept, unit and period carries one value in the prior 10-K and a
    different value in the latest 10-K. `kind` is `rounding` when one value is just the other
    at lower precision, otherwise `restated` (restated or reclassified).
    """
    concepts = [c for k, c in concept_map.items() if k != "revenue_status" and c]
    company = df[(df["ticker"] == latest.ticker) & df["concept"].isin(concepts) & is_annual(df)]
    key = ["concept", "unit", "period_start", "period_end"]
    old = company[company["accession"] == prior.accession][key + ["value"]].drop_duplicates()
    new = company[company["accession"] == latest.accession][key + ["value"]].drop_duplicates()
    # pandas matches missing period_start (instant values) to each other in a merge.
    merged = old.merge(new, on=key, suffixes=("_orig", "_new"))
    changed = merged[merged["value_orig"] != merged["value_new"]]
    pairs = []
    for r in changed.itertuples(index=False):
        pairs.append({
            "ticker": latest.ticker,
            "concept": r.concept,
            "unit": r.unit,
            "period_start": r.period_start,
            "period_end": r.period_end,
            "original": {"accession": prior.accession, "filed": prior.filed, "value": r.value_orig},
            "restated": {"accession": latest.accession, "filed": latest.filed, "value": r.value_new},
            "rel_change": (r.value_new - r.value_orig) / abs(r.value_orig) if r.value_orig else None,
            "kind": "rounding" if is_rounding(r.value_orig, r.value_new) else "restated",
        })
    return pairs
