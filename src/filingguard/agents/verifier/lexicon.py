"""The verifier's own metric vocabulary, built from the XBRL concepts in `facts.parquet` and their
standard labels (D-050). It never reads the red-team's wording."""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class VMetric:
    key: str
    concepts: tuple[str, ...]   # XBRL concepts that report this metric, parent line first
    phrases: tuple[str, ...]    # how filings and answers name it
    flow: bool                  # a duration (income, cash flow) rather than a balance
    can_be_negative: bool


METRICS = {m.key: m for m in (
    VMetric("revenue", ("Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax", "SalesRevenueNet",
                        "RevenuesNetOfInterestExpense", "RevenueFromContractWithCustomerIncludingAssessedTax"),
            ("total net revenues", "total revenues", "total revenue", "net revenues", "net revenue", "total net sales",
             "net sales", "revenues", "revenue", "sales to customers", "total sales"), True, False),
    VMetric("net_income", ("NetIncomeLoss",),
            ("net income attributable to", "net earnings attributable to", "net income", "net earnings", "net loss",
             "profit attributable"), True, True),
    VMetric("operating_income", ("OperatingIncomeLoss",),
            ("operating income", "income from operations", "operating profit", "operating loss", "loss from operations",
             "operating earnings"), True, True),
    VMetric("gross_profit", ("GrossProfit",), ("gross profit", "gross margin"), True, True),
    VMetric("assets", ("Assets",), ("total assets",), False, False),
    VMetric("liabilities", ("Liabilities",), ("total liabilities",), False, False),
    VMetric("equity", ("StockholdersEquity",),
            ("stockholders' equity", "shareholders' equity", "shareowners' equity", "stockholders equity",
             "shareholders equity", "total equity"), False, True),
    VMetric("cash", ("CashAndCashEquivalentsAtCarryingValue",), ("cash and cash equivalents", "cash and due from banks"),
            False, False),
    VMetric("eps_basic", ("EarningsPerShareBasic",), ("basic earnings per share", "basic net income per share",
                                                     "basic eps", "per basic share", "basic"), True, True),
    VMetric("eps_diluted", ("EarningsPerShareDiluted",), ("diluted earnings per share", "diluted net income per share",
                                                         "diluted eps", "per diluted share", "diluted"), True, True),
    VMetric("rnd", ("ResearchAndDevelopmentExpense",), ("research and development", "research & development", "r&d"),
            True, False),
    VMetric("long_term_debt", ("LongTermDebt",), ("long-term debt", "long term debt"), False, False),
    VMetric("operating_cash_flow", ("NetCashProvidedByUsedInOperatingActivities",),
            ("net cash provided by operating activities", "cash provided by operating activities", "operating activities",
             "operating cash flow", "cash from operations", "cash provided by operations"), True, True),
)}

# Lines that are not any metric above; named first so they are never read as one.
OTHER_PHRASES = (
    "cost of revenue", "cost of revenues", "cost of sales", "cost of goods sold", "liabilities and stockholders' equity",
    "liabilities and shareholders' equity", "liabilities and equity", "total current assets", "total current liabilities",
    "comprehensive income", "noncontrolling interest", "non-controlling interest", "before income taxes",
    "before taxes", "operating expenses", "total expenses", "investing activities", "financing activities",
    "free cash flow", "capital expenditures", "dividends", "repurchase", "interest expense", "income taxes",
    "income tax", "net interest income", "noninterest income", "current portion of long-term debt", "short-term debt",
    "total debt", "segment", "other income", "other (income)", "in-process research and development",
    "in-process r&d", "ipr&d", "acquired in-process",
)
GENERIC_EPS = ("earnings per share", "net income per share", "per share", "eps")
_SEGMENT_QUALIFIERS = {"segment", "product", "products", "service", "services", "subscription", "advertising",
                       "automotive", "cloud", "hardware", "software", "licensing", "international", "domestic"}


def _pattern(phrase: str) -> str:
    return r"\b" + re.escape(phrase).replace(r"\ ", r"\s+").replace("'", "['’]?") + r"\b"


def _ordered() -> list[tuple[str, re.Pattern]]:
    out = [("other", re.compile(_pattern(p), re.IGNORECASE)) for p in OTHER_PHRASES]
    for key in ("eps_diluted", "eps_basic"):
        out += [(key, re.compile(_pattern(p), re.IGNORECASE)) for p in METRICS[key].phrases]
    out += [("eps", re.compile(_pattern(p), re.IGNORECASE)) for p in GENERIC_EPS]
    for key, m in METRICS.items():
        if not key.startswith("eps"):
            out += [(key, re.compile(_pattern(p), re.IGNORECASE)) for p in sorted(m.phrases, key=len, reverse=True)]
    return out


PATTERNS = _ordered()


def mentions(text: str) -> list[tuple[int, int, str]]:
    """(start, end, metric key) for each metric named in `text`; earlier patterns win overlaps.
    A metric word right after a segment or product qualifier ("services revenue") is "other"."""
    found: list[tuple[int, int, str]] = []
    for key, pattern in PATTERNS:
        for m in pattern.finditer(text):
            if any(s < m.end() and m.start() < e for s, e, _ in found):
                continue
            before = re.findall(r"[\w’'&.-]+", text[max(0, m.start() - 25):m.start()])
            qualifier = before[-1].lower() if before else ""
            found.append((m.start(), m.end(), "other" if qualifier in _SEGMENT_QUALIFIERS else key))
    return sorted(found)


def question_metric(question: str) -> str | None:
    """The metric a question asks about: the first metric it names (generic EPS wording alone
    resolves to diluted only if the question says diluted, else basic)."""
    for _, _, key in mentions(question):
        if key == "eps":
            return "eps_diluted" if re.search(r"\bdiluted\b", question, re.IGNORECASE) else "eps_basic"
        if key != "other":
            return key
    return None
