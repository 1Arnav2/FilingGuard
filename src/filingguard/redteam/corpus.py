"""The red-team's view of the corpus: facts, filings, filing text, metric labels and lookups.

Everything here is deterministic. Gold values come from XBRL facts; the filing text is used
to find the span that shows each value and to prove that an unanswerable fact is absent.
"""

import json
import re
from dataclasses import dataclass
from datetime import date
from functools import cached_property
from pathlib import Path

import pandas as pd

from filingguard.data.facts import is_annual

PROCESSED = Path("data/processed")
EXCERPT_CHARS = 600


@dataclass(frozen=True)
class Metric:
    key: str             # key in concept_map.json
    label: str           # wording used in questions
    synonyms: tuple[str, ...]   # labels a filing may print; used to find spans and prove absence
    flow: bool           # True for a duration (income or cash flow), False for a balance


METRICS = {m.key: m for m in (
    Metric("Revenue", "total revenue", ("revenue", "revenues", "net sales", "total sales"), True),
    Metric("NetIncomeLoss", "net income",
           ("net income", "net earnings", "net loss", "net profit", "profit attributable"), True),
    Metric("OperatingIncomeLoss", "operating income",
           ("operating income", "income from operations", "operating profit", "operating loss",
            "operating earnings"), True),
    Metric("GrossProfit", "gross profit", ("gross profit", "gross margin"), True),
    Metric("Assets", "total assets", ("total assets",), False),
    Metric("Liabilities", "total liabilities", ("total liabilities",), False),
    Metric("StockholdersEquity", "total stockholders' equity",
           ("stockholders' equity", "shareholders' equity", "shareowners' equity", "total equity"), False),
    Metric("CashAndCashEquivalentsAtCarryingValue", "cash and cash equivalents",
           ("cash and cash equivalents", "cash and due from banks", "cash equivalents"), False),
    Metric("EarningsPerShareBasic", "basic earnings per share",
           ("earnings per share", "per share", "basic"), True),
    Metric("EarningsPerShareDiluted", "diluted earnings per share",
           ("earnings per share", "per share", "diluted"), True),
    Metric("ResearchAndDevelopmentExpense", "research and development expense",
           ("research and development", "research & development", "r&d", "product development",
            "technology and development", "research, development"), True),
    Metric("LongTermDebt", "long-term debt",
           ("long-term debt", "long term debt", "long-term borrowings", "senior notes", "notes payable"), False),
    Metric("NetCashProvidedByUsedInOperatingActivities", "net cash provided by operating activities",
           ("operating activities", "operating cash flow", "cash provided by operations"), True),
)}

# How each company is named in questions, and the names a question may use for it.
COMPANY_NAMES = {
    "AAPL": ("Apple",), "MSFT": ("Microsoft",), "NVDA": ("NVIDIA", "Nvidia"), "GOOGL": ("Alphabet", "Google"),
    "META": ("Meta",), "ORCL": ("Oracle",), "AMZN": ("Amazon",), "WMT": ("Walmart",), "COST": ("Costco",),
    "NKE": ("Nike",), "KO": ("Coca-Cola", "Coca Cola"), "PG": ("Procter & Gamble", "P&G", "Procter and Gamble"),
    "JNJ": ("Johnson & Johnson", "J&J", "Johnson and Johnson"), "PFE": ("Pfizer",), "UNH": ("UnitedHealth",),
    "XOM": ("ExxonMobil", "Exxon"), "CVX": ("Chevron",), "BA": ("Boeing",), "CAT": ("Caterpillar",),
    "DIS": ("Disney",), "TSLA": ("Tesla",), "JPM": ("JPMorgan", "JP Morgan"), "GS": ("Goldman Sachs", "Goldman"),
    "BAC": ("Bank of America",), "V": ("Visa",),
}

SCALES = (("millions", 1e6), ("thousands", 1e3), ("units", 1.0))


def fiscal_label(period_end: str) -> int:
    """The fiscal year a period is called by: the year it ends in, except that a 52/53-week
    year ending in the first week of January belongs to the year before (JNJ)."""
    d = date.fromisoformat(period_end)
    return d.year - 1 if d.month == 1 and d.day <= 7 else d.year


def long_date(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d:%B} {d.day}, {d.year}"


def normalise_text(text: str) -> str:
    """Straighten curly apostrophes so label searches match either form (same length)."""
    return text.replace("’", "'")


def renderings(value: float, unit: str) -> list[tuple[str, str]]:
    """(string, printed scale) pairs a 10-K might use for `value`, most likely first."""
    if unit == "USD/shares":
        return [(f"{abs(value):.2f}", "per_share")]
    out = []
    for scale, divisor in SCALES:
        scaled = value / divisor
        if abs(scaled - round(scaled)) < 1e-9 or scale == "millions":
            out.append((f"{abs(round(scaled)):,}", scale))
    return out


@dataclass(frozen=True)
class Located:
    start: int
    end: int
    rendering: str
    printed_scale: str
    on_label_line: bool


def _line_at(text: str, pos: int) -> str:
    lo = text.rfind("\n", 0, pos) + 1
    hi = text.find("\n", pos)
    return text[lo: hi if hi != -1 else len(text)]


def _number_at(text: str, start: int, end: int) -> bool:
    """True if [start, end) is a whole number, not part of a longer one (1,234 in 21,234.5)."""
    before = text[start - 1] if start > 0 else " "
    after = text[end] if end < len(text) else " "
    if before.isdigit() or before in ",." and start > 1 and text[start - 2].isdigit():
        return False
    return not (after.isdigit() or after in ",." and end + 1 < len(text) and text[end + 1].isdigit())


def locate(text: str, value: float, unit: str, metric: Metric) -> Located | None:
    """Where the filing prints `value`, preferring a line that also carries the metric's label.

    Returns the first whole-number match on a labelled line; failing that, the first
    whole-number match anywhere (flagged `on_label_line=False` for the reviewer).
    """
    lowered = normalise_text(text).lower()
    fallback = None
    for rendering, scale in renderings(value, unit):
        for m in re.finditer(re.escape(rendering), text):
            if not _number_at(text, m.start(), m.end()):
                continue
            line = _line_at(lowered, m.start())
            hit = Located(m.start(), m.end(), rendering, scale, any(s in line for s in metric.synonyms))
            if hit.on_label_line:
                return hit
            fallback = fallback or hit
    return fallback


def excerpt(text: str, start: int, end: int, width: int = EXCERPT_CHARS) -> dict:
    """About `width` characters around [start, end), with the match's position inside it."""
    lo = max(0, start - width // 2)
    hi = min(len(text), end + width // 2)
    return {"text": text[lo:hi], "match": [start - lo, end - lo]}


def find_terms(text: str, terms: list[str], near: list[str] | None = None, window: int = 300) -> list[dict]:
    """Case-insensitive whole-word hits of `terms`; with `near`, only hits that have one of
    `near` within `window` characters. Used as the evidence-of-absence search."""
    lowered = normalise_text(text).lower()
    near_pattern = re.compile("|".join(rf"\b{re.escape(n.lower())}\b" for n in near)) if near else None
    hits = []
    for term in terms:
        for m in re.finditer(rf"(?<![a-z0-9]){re.escape(term.lower())}(?![a-z0-9])", lowered):
            if near_pattern and not near_pattern.search(lowered, max(0, m.start() - window), m.end() + window):
                continue
            hits.append({"term": term, "offset": m.start(), "context": text[max(0, m.start() - 80): m.end() + 80]})
            break
    return hits


class Corpus:
    """Lazy access to the committed corpus files and the parsed filing text."""

    def __init__(self, processed: Path = PROCESSED) -> None:
        self.processed = Path(processed)
        self.facts = pd.read_parquet(self.processed / "facts.parquet")
        self.concept_map = json.loads((self.processed / "concept_map.json").read_text(encoding="utf-8"))
        self.companies = {c["ticker"]: c for c in json.loads((self.processed / "filings.json").read_text(encoding="utf-8"))}
        self.pairs = json.loads((self.processed / "restatement_pairs.json").read_text(encoding="utf-8"))
        self._text: dict[str, str] = {}

    @cached_property
    def chunks(self) -> list[dict]:
        """Chunk metadata and text from the committed index (no embeddings)."""
        with (self.processed / "index" / "chunks.jsonl").open(encoding="utf-8") as f:
            return [json.loads(line) for line in f]

    @cached_property
    def tickers(self) -> list[str]:
        return list(self.companies)

    def name(self, ticker: str) -> str:
        return COMPANY_NAMES[ticker][0]

    def latest(self, ticker: str) -> dict:
        return self.companies[ticker]["latest_10k"]

    def text(self, accession: str) -> str:
        if accession not in self._text:
            self._text[accession] = (self.processed / "text" / f"{accession}.txt").read_text(encoding="utf-8")
        return self._text[accession]

    def metrics(self, ticker: str) -> list[Metric]:
        """Metrics the company tags in its latest 10-K."""
        return [m for k, m in METRICS.items() if self.concept_map[ticker].get(k)]

    def untagged(self, ticker: str) -> list[Metric]:
        return [m for k, m in METRICS.items() if not self.concept_map[ticker].get(k)]

    def annual_values(self, ticker: str, metric: Metric, accession: str) -> pd.DataFrame:
        """Annual values of a metric reported in one filing, one row per period, USD only.

        Periods reported with more than one value in the filing are dropped as ambiguous.
        """
        concept = self.concept_map[ticker][metric.key]
        f = self.facts
        rows = f[(f["ticker"] == ticker) & (f["concept"] == concept) & (f["accession"] == accession)
                 & is_annual(f) & f["unit"].isin(["USD", "USD/shares"])]
        rows = rows.drop_duplicates(["period_start", "period_end", "value"])
        counts = rows.groupby("period_end")["value"].transform("nunique")
        return rows[counts == 1].sort_values("period_end", ascending=False).reset_index(drop=True)

    def fact(self, ticker: str, metric: Metric, accession: str, period_end: str) -> dict | None:
        """One located fact: value, unit, period, and the span that shows it in the filing."""
        rows = self.annual_values(ticker, metric, accession)
        rows = rows[rows["period_end"] == period_end]
        if rows.empty:
            return None
        r = rows.iloc[0]
        text = self.text(accession)
        loc = locate(text, float(r["value"]), r["unit"], metric)
        if loc is None:
            return None
        filing = next(f for f in self.filings(ticker) if f["accession"] == accession)
        return {
            "gold": {
                "value": float(r["value"]), "unit": r["unit"], "concept": r["concept"], "metric": metric.label,
                "period_start": r["period_start"] if isinstance(r["period_start"], str) else None,
                "period_end": r["period_end"], "fiscal_year": fiscal_label(r["period_end"]),
                "printed_scale": loc.printed_scale, "printed_as": loc.rendering,
            },
            "source": {
                "accession": accession, "filed": filing["filed"], "report_date": filing["report_date"],
                "span": [loc.start, loc.end], "on_label_line": loc.on_label_line,
            },
        }

    def filings(self, ticker: str) -> list[dict]:
        """Indexed filings for a company, newest first."""
        c = self.companies[ticker]
        out = [c["latest_10k"]]
        for key in ("prior_10k", "older_10k"):
            if c.get(key) and c[key]["in_corpus"]:
                out.append(c[key])
        return out
