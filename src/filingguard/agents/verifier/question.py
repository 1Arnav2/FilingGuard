"""Rules that read what a question asks: metric, period, filing, named line, sign and premise."""

import re
from dataclasses import dataclass

from filingguard.agents.verifier.facts import FactStore
from filingguard.agents.verifier.lexicon import question_metric
from filingguard.figures import MONTHS, question_names_sign

_FY = re.compile(r"\b(?:fiscal(?:\s+year)?|FY)\s*'?((?:19|20)\d{2})\b", re.IGNORECASE)
_CAL = re.compile(r"\bcalendar(?:\s+year)?\s+((?:19|20)\d{2})\b", re.IGNORECASE)
_START = re.compile(r"\bbegan\s+in\s+(" + "|".join(MONTHS) + r")\s+((?:19|20)\d{2})\b", re.IGNORECASE)
_QUARTER = re.compile(r"\b(?:first|second|third|fourth|1st|2nd|3rd|4th)\s+(?:fiscal\s+)?quarter\b|\bQ[1-4]\b|"
                      r"\bthree months\b", re.IGNORECASE)
_FILING = re.compile(r"\b(?:fiscal\s+)?((?:19|20)\d{2})\s+(?:Form\s+)?10-K\b", re.IGNORECASE)
_FILED = re.compile(r"\bfiled\s+(?:on\s+)?(" + "|".join(MONTHS) + r")\s+(\d{1,2}),?\s+((?:19|20)\d{2})", re.IGNORECASE)
_YEAR = re.compile(r"(?<![\d$,.])((?:19|20)\d{2})(?![\d,])")
_UP = re.compile(r"\b(?:increase[ds]?|rose|rise|rising|grew|grow(?:th)?|higher|improve[ds]?|jump(?:ed)?|surge[ds]?)\b",
                 re.IGNORECASE)
_DOWN = re.compile(r"\b(?:decline[ds]?|decrease[ds]?|fell|fall(?:ing)?|drop(?:ped)?|lower|shr[ai]nk|reduc(?:ed|tion)|"
                   r"contract(?:ed|ion))\b", re.IGNORECASE)
_DOUBLE = re.compile(r"\b(more than\s+)?(doubled|tripled|quadrupled|halved)\b", re.IGNORECASE)
_PCT = re.compile(r"\bby\s+(?:more than|over|at least)\s+(\d+(?:\.\d+)?)\s*(?:%|percent)", re.IGNORECASE)
_PARENT = re.compile(r"\battributable to\b(?!\s+noncontrolling)", re.IGNORECASE)
_CONSOLIDATED = re.compile(r"\bconsolidated net (?:income|earnings)\b(?!\s+attributable)|\bincluding noncontrolling\b|"
                           r"\btotal equity\b", re.IGNORECASE)


@dataclass(frozen=True)
class Premise:
    years: tuple[int, int]
    direction: str | None   # "up" or "down"
    negative: bool          # the question says the metric was a loss in the later year
    factor: float | None    # claimed ratio later / earlier at least (doubled = 2.0) or at most (halved)
    at_least: bool


@dataclass(frozen=True)
class Ask:
    metric: str | None
    fy: int | None
    kind: str                # fiscal, calendar, start_month, quarter, none
    accession: str | None    # the 10-K the question names, if any
    line: str | None         # "parent" or "consolidated" if the question names that line
    sign_named: bool
    premise: Premise | None


def _driver_style(question: str) -> bool:
    return bool(re.search(r"\b(?:what|which)\b.*\b(?:drove|driv|factors?|caused?|led to|contribut|explain|reasons?)",
                          question, re.IGNORECASE))


def _premise(question: str, fy: int | None, metric: str | None) -> Premise | None:
    """A claimed change in a metric, read from the question. Facts decide whether it is true;
    wording alone never blocks anything."""
    if metric is None or not _driver_style(question):
        return None
    years = [int(y) for y in _YEAR.findall(question)]
    later = max(years) if years else fy
    if later is None:
        return None
    earlier = min(years) if len(set(years)) > 1 else later - 1
    sign_word = re.search(r"\b(?:net|operating)\s+loss\b|\bloss\s+(?:per share|from operations)\b", question, re.IGNORECASE)
    mult = _DOUBLE.search(question)
    pct = _PCT.search(question)
    factor, at_least = None, True
    if mult:
        factor = {"doubled": 2.0, "tripled": 3.0, "quadrupled": 4.0, "halved": 0.5}[mult.group(2).lower()]
        at_least = mult.group(2).lower() != "halved"
    elif pct:
        factor = 1 + float(pct.group(1)) / 100
    direction = "up" if _UP.search(question) else "down" if _DOWN.search(question) else None
    if not (direction or sign_word or factor):
        return None
    return Premise((earlier, later), direction, bool(sign_word), factor, at_least)


def read_question(question: str, ticker: str, store: FactStore) -> Ask:
    metric = question_metric(question)
    kind, fy = "none", None
    if m := _START.search(question):
        kind = "start_month"
        fy = store.fy_starting(ticker, int(m.group(2)), MONTHS.index(m.group(1).lower()) + 1)
    elif m := _CAL.search(question):
        kind, fy = "calendar", int(m.group(1))
    elif _QUARTER.search(question):
        kind = "quarter"
    fy_mentions = [int(y) for y in _FY.findall(question)]
    accession = None
    if m := _FILED.search(question):
        filed = f"{m.group(3)}-{MONTHS.index(m.group(1).lower()) + 1:02d}-{int(m.group(2)):02d}"
        accession = store.filing(ticker, filed=filed)
    elif m := _FILING.search(question):
        accession = store.filing(ticker, fy=int(m.group(1)))
    if kind == "none" and fy_mentions:
        kind = "fiscal"
        # "fiscal 2023 as reported in the fiscal 2025 10-K": the period is the year not naming the filing.
        filing_years = {int(y) for y in _FILING.findall(question)}
        period_years = [y for y in fy_mentions if y not in filing_years] or fy_mentions
        fy = min(period_years) if accession else period_years[0]
    if kind == "none" and (bare := _YEAR.findall(question)):
        kind, fy = "fiscal", int(bare[0])
    if kind == "quarter":
        fy = fy_mentions[0] if fy_mentions else None
    line = "parent" if _PARENT.search(question) else "consolidated" if _CONSOLIDATED.search(question) else None
    return Ask(metric, fy, kind, accession, line, question_names_sign(question), _premise(question, fy, metric))
