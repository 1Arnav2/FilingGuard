"""XBRL facts from the corpus 10-K filings only, looked up by company, metric and fiscal year."""

import json
from datetime import date
from functools import cached_property
from pathlib import Path

import pandas as pd

from filingguard.agents.verifier.lexicon import METRICS
from filingguard.data.filings import corpus_report_dates

PROCESSED = Path("data/processed")


def fiscal_label(period_end: str) -> int:
    """The fiscal year a period is called by: the year it ends in, except that a year ending in
    the first week of January belongs to the year before."""
    d = date.fromisoformat(period_end)
    return d.year - 1 if d.month == 1 and d.day <= 7 else d.year


class FactStore:
    def __init__(self, processed: Path = PROCESSED) -> None:
        self.processed = processed

    @cached_property
    def facts(self) -> pd.DataFrame:
        accessions = set(corpus_report_dates(self.processed / "filings.json"))
        f = pd.read_parquet(self.processed / "facts.parquet")
        f = f[f.accession.isin(accessions)].copy()
        f["fy"] = f.period_end.map(fiscal_label)
        return f

    @cached_property
    def filings(self) -> dict[str, list[dict]]:
        """Corpus filings per company: accession, report date, filed date, fiscal year."""
        out: dict[str, list[dict]] = {}
        dates = corpus_report_dates(self.processed / "filings.json")
        for company in json.loads((self.processed / "filings.json").read_text(encoding="utf-8")):
            for key in ("latest_10k", "prior_10k", "older_10k"):
                f = company.get(key)
                if f and f["accession"] in dates:
                    out.setdefault(company["ticker"], []).append(
                        {"accession": f["accession"], "report_date": f["report_date"], "filed": f["filed"],
                         "fy": fiscal_label(f["report_date"])})
        return out

    @cached_property
    def year_end_month(self) -> dict[str, int]:
        return {t: date.fromisoformat(fs[0]["report_date"]).month for t, fs in self.filings.items()}

    def rows(self, ticker: str, metric: str, concepts: tuple[str, ...] | None = None) -> pd.DataFrame:
        m = METRICS[metric]
        f = self.facts
        f = f[(f.ticker == ticker) & f.concept.isin(concepts or m.concepts)]
        return f[f.period_days.between(350, 380)] if m.flow else f[f.period_days.isna()]

    def values(self, ticker: str, metric: str, fy: int, accession: str | None = None,
               concepts: tuple[str, ...] | None = None) -> list[float]:
        """Distinct values reported for the fiscal year, from one filing if `accession` is given."""
        r = self.rows(ticker, metric, concepts)
        r = r[r.fy == fy]
        if accession:
            r = r[r.accession == accession]
        return sorted(set(r.value.tolist()))

    def other_years(self, ticker: str, metric: str, fy: int) -> dict[int, list[float]]:
        r = self.rows(ticker, metric)
        return {int(y): sorted(set(g.value.tolist())) for y, g in r[r.fy != fy].groupby("fy")}

    def other_filing_values(self, ticker: str, metric: str, fy: int, accession: str) -> list[float]:
        r = self.rows(ticker, metric)
        r = r[(r.fy == fy) & (r.accession != accession)]
        return sorted(set(r.value.tolist()))

    def fy_starting(self, ticker: str, year: int, month: int) -> int | None:
        """The fiscal year whose period starts in this month (from any annual flow fact)."""
        f = self.facts
        r = f[(f.ticker == ticker) & f.period_days.between(350, 380)]
        starts = {(date.fromisoformat(s), int(fy)) for s, fy in zip(r.period_start, r.fy)}
        exact = [fy for d, fy in starts if (d.year, d.month) == (year, month)]
        if exact:
            return exact[0]
        # A 52/53-week year can start in the last days of the month before.
        late = [fy for d, fy in starts if d.day >= 25 and (d.year + d.month // 12, d.month % 12 + 1) == (year, month)]
        return late[0] if late else None

    def filing(self, ticker: str, fy: int | None = None, filed: str | None = None) -> str | None:
        """The corpus 10-K for the fiscal year it reports, or the one filed on a date."""
        for f in self.filings.get(ticker, []):
            if (filed and f["filed"] == filed) or (fy is not None and not filed and f["fy"] == fy):
                return f["accession"]
        return None
