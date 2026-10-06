"""Read figures, metric mentions and period mentions out of an answer's text (EVAL §3).

Scored figures come from the answer text, the words a user reads. An answer's structured
claim only supplies a scale or period the text leaves out (EVAL §3, D-047). Everything here is
deterministic and written before any target answer existed.
"""

import re
from dataclasses import dataclass, field
from datetime import date

from filingguard.agents.schema import Claim

SCALE_WORDS = {
    "thousand": 1e3, "thousands": 1e3, "k": 1e3,
    "million": 1e6, "millions": 1e6, "mn": 1e6, "mm": 1e6, "m": 1e6,
    "billion": 1e9, "billions": 1e9, "bn": 1e9, "b": 1e9,
    "trillion": 1e12, "trillions": 1e12, "tn": 1e12,
}
# Words that name the scale a figure is stated in, for the "scale not followed" count.
SCALE_NAMES = {1e3: "thousands", 1e6: "millions", 1e9: "billions", 1e12: "trillions"}

_NUMBER = re.compile(
    r"(?<![\w.,])(?P<open>\()?\s*(?P<minus>[-−–](?=\s*(?:US)?\$?\s*\d))?\s*(?P<usd>(?:US)?\$)?\s*"
    r"(?P<num>\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?![\d,]*\d)(?!-[A-Za-z])"  # never a form number (10-K)
)
# Text right after a number: a closing parenthesis, then a scale word, "dollars", "cents" or "per share".
_AFTER = re.compile(
    r"^\s*(?P<close>\))?\s*(?:\(\s*in\s+)?(?P<scale>thousands?|millions?|billions?|trillions?|bn|mn|mm|tn|k|m|b)?"
    r"(?![a-z])\s*\)?\s*(?P<unit>dollars|usd|cents?)?\b",
    re.IGNORECASE,
)
_PERCENT_AFTER = re.compile(r"^\s*(?:%|percent|per cent|percentage points?|basis points?|bps|x\b|times\b)", re.IGNORECASE)
# "per share" must follow the number directly, not after other words ("10-K, diluted ... per share").
_PER_SHARE_AFTER = re.compile(r"^\s*\)?\s*per\s+(?:diluted\s+|basic\s+)?(?:common\s+)?share\b", re.IGNORECASE)
# Parenthetical labels that name a sign without stating one: "net income (loss)", "provided by (used in)".
_SIGN_LABEL = re.compile(r"\(\s*(?:loss|losses|used(?:\s+(?:in|for))?)\s*\)|/\s*\(?\s*(?:loss|used(?:\s+(?:in|for))?)\s*\)?",
                         re.IGNORECASE)
NEGATIVE_WORDS = re.compile(r"\b(?:loss|losses|used|outflows?|negative)\b", re.IGNORECASE)
# Where a new clause starts: a loss word before one of these does not describe the figure after it
# ("an operating loss ... because it reported operating income of $X").
_CLAUSE_BREAK = re.compile(r"[;:()]|\b(?:because|rather than|rather|instead|whereas|while|but|however|although)\b",
                           re.IGNORECASE)
# A date right after these words dates a document, not the period a figure covers.
_FILED_BEFORE = re.compile(r"\b(?:filed|dated|submitted|issued)(?:\s+on)?\s*$", re.IGNORECASE)

MONTHS = ("january", "february", "march", "april", "may", "june", "july", "august", "september",
          "october", "november", "december")
_MONTH = r"(?P<month>" + "|".join(m.capitalize() for m in MONTHS) + "|" + "|".join(MONTHS) + \
         r"|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)\.?"
_PERIOD_PATTERNS = (
    ("date", re.compile(_MONTH + r"\s+(?P<day>\d{1,2}),?\s+(?P<year>(?:19|20)\d{2})")),
    ("date", re.compile(r"(?P<year>(?:19|20)\d{2})-(?P<mon>\d{2})-(?P<day>\d{2})")),
    ("month", re.compile(_MONTH + r"\s+(?P<year>(?:19|20)\d{2})")),
    ("quarter", re.compile(r"\b(?P<q>first|second|third|fourth|1st|2nd|3rd|4th)\s+(?:fiscal\s+)?quarter\b|\bQ(?P<qn>[1-4])\b|"
                           r"\bthree months ended\b", re.IGNORECASE)),
    ("fiscal", re.compile(r"\b(?:fiscal(?:\s+years?)?|FY)\s*'?(?P<year>(?:19|20)\d{2}|\d{2})\b", re.IGNORECASE)),
    ("calendar", re.compile(r"\bcalendar(?:\s+years?)?\s+(?P<year>(?:19|20)\d{2})\b", re.IGNORECASE)),
    ("year", re.compile(r"(?<![\d,.$])(?P<year>(?:19|20)\d{2})(?![\d,])")),
)
_QUARTER_WORDS = {"first": 1, "1st": 1, "second": 2, "2nd": 2, "third": 3, "3rd": 3, "fourth": 4, "4th": 4}

_SENTENCE_END = re.compile(r"(?<=[.!?;])\s+(?=[A-Z(\[$\"'])|\n+")

# Statements that the filing does not give the figure (EVAL §3 "Abstained").
NOT_IN_FILING = re.compile(
    r"\b(?:not|n't)\s+(?:\w+\s+){0,3}?(?:provided|included|disclosed|available|reported|contained|presented|"
    r"stated|found|broken out|separately|specified|shown|listed|given|present|contain|include|provide|disclose|"
    r"report|present|state|break out|show|specify|mention|appear)\b|"
    r"\bno\s+(?:\w+\s+){0,2}?(?:information|data|figure|figures|disclosure|breakdown|mention|value|amount)\b|"
    r"\b(?:unable|cannot|can't|could not|couldn't)\s+(?:\w+\s+){0,2}?(?:determine|find|provide|answer|locate|identify|be determined)\b|"
    r"\b(?:does|do|did)\s+not\s+(?:\w+\s+){0,2}?(?:contain|include|provide|disclose|report|break|present|state|specify|show|appear)\b",
    re.IGNORECASE,
)


@dataclass
class Figure:
    """One number stated in the answer text, converted to base units (USD or USD per share)."""

    start: int
    end: int
    raw: float          # the number as printed, before scale
    value: float        # base units, signed
    scale: float | None  # the stated scale factor (1e6 for "million"), None if none stated
    scale_word: str | None  # "billions", "dollars", "cents" or None
    negative: bool
    per_share: bool
    sentence: int
    metric: str | None = None   # metric key it is attributed to, "other", or None
    periods: list["Period"] = field(default_factory=list)  # nearest period mention(s)
    adjusted: bool = False  # labelled adjusted, non-GAAP or core (EVAL §3, D-053)


@dataclass(frozen=True)
class Period:
    kind: str           # date, month, quarter, fiscal, calendar, year
    year: int | None
    month: int | None = None
    day: int | None = None
    quarter: int | None = None
    start: int = 0
    end: int = 0


def sentences(text: str) -> list[tuple[int, int]]:
    """(start, end) of each sentence; a decimal point never ends one."""
    bounds, start = [], 0
    for m in _SENTENCE_END.finditer(text):
        if m.start() > start:
            bounds.append((start, m.start()))
        start = m.end()
    if start < len(text):
        bounds.append((start, len(text)))
    return bounds


def _sentence_of(bounds: list[tuple[int, int]], pos: int) -> int:
    for i, (s, e) in enumerate(bounds):
        if s <= pos < e:
            return i
    return max(len(bounds) - 1, 0)


def _month_number(name: str) -> int:
    name = name.lower().rstrip(".")
    return next(i + 1 for i, m in enumerate(MONTHS) if m.startswith(name[:3]))


def periods(text: str) -> list[Period]:
    """Every period mention in `text`, with overlapping weaker matches dropped."""
    found: list[Period] = []
    taken: list[tuple[int, int]] = []
    for kind, pattern in _PERIOD_PATTERNS:
        for m in pattern.finditer(text):
            if any(s < m.end() and m.start() < e for s, e in taken):
                continue
            if kind in ("date", "month") and _FILED_BEFORE.search(text[max(0, m.start() - 20):m.start()]):
                kind = "filed"  # kept so its year is not read again; never a figure's period
            g = m.groupdict()
            year = g.get("year")
            if year is not None:
                year = int(year) + 2000 if len(year) == 2 else int(year)
            month = _month_number(g["month"]) if g.get("month") else (int(g["mon"]) if g.get("mon") else None)
            quarter = None
            if kind == "quarter":
                quarter = _QUARTER_WORDS.get((g.get("q") or "").lower()) or (int(g["qn"]) if g.get("qn") else None)
            found.append(Period(kind, year, month, int(g["day"]) if g.get("day") else None, quarter, m.start(), m.end()))
            taken.append((m.start(), m.end()))
    return sorted(found, key=lambda p: p.start)


def parse_figures(text: str) -> list[Figure]:
    """Money and per-share figures in `text`. A number counts as a figure when it carries a
    currency mark, a scale word, "dollars", "cents" or "per share", or digit grouping (1,000);
    percentages, years, dates and bare small numbers do not."""
    bounds = sentences(text)
    year_spans = [(p.start, p.end) for p in periods(text)
                  if p.kind in ("date", "month", "fiscal", "calendar", "year", "filed")]
    figures = []
    for m in _NUMBER.finditer(text):
        num_start = m.start("num")
        if any(s <= num_start < e for s, e in year_spans):
            continue
        after_text = text[m.end():]
        if _PERCENT_AFTER.match(after_text):
            continue
        after = _AFTER.match(after_text)
        scale_token = (after.group("scale") or "").lower() if after else ""
        unit = (after.group("unit") or "").lower() if after else ""
        has_usd = bool(m.group("usd"))
        # Single letters are scales only straight after a $ figure ("$5.2B"), never after a bare number.
        if scale_token in ("k", "m", "b") and not (has_usd and re.match(r"^[kmbKMB](?![a-z])", after_text)):
            scale_token = ""
        per_share = bool(_PER_SHARE_AFTER.match(after_text))
        raw_text = m.group("num")
        grouped = "," in raw_text
        if not (has_usd or scale_token or unit or per_share or grouped):
            continue
        raw = float(raw_text.replace(",", ""))
        scale = SCALE_WORDS.get(scale_token)
        value = raw * (scale or 1.0)
        scale_word = SCALE_NAMES.get(scale) if scale else None
        if unit.startswith("cent"):
            value, scale_word = raw / 100.0, "cents"
        elif unit in ("dollars", "usd") and not scale:
            scale_word = "dollars"
        close = (after.group("close") if after else None) or (")" if after_text.lstrip().startswith(")") else None)
        paren = bool(m.group("open")) and bool(close)
        negative = paren or bool(m.group("minus"))
        end = m.end() + (after.end() if after else 0)
        figures.append(Figure(m.start(), end, raw, value, scale, scale_word, negative, per_share,
                              _sentence_of(bounds, m.start())))
    _mark_negative_words(text, figures, bounds)
    return figures


def _mark_negative_words(text: str, figures: list[Figure], bounds: list[tuple[int, int]]) -> None:
    """A figure is negative if it is described as a loss, cash used, an outflow or negative:
    such a word in the figure's own clause, between the previous figure (or the sentence start,
    or the last clause break) and this figure."""
    for i, f in enumerate(figures):
        s_start = bounds[f.sentence][0] if bounds else 0
        prev_end = figures[i - 1].end if i and figures[i - 1].sentence == f.sentence else s_start
        window = _SIGN_LABEL.sub(" ", text[prev_end:f.start])
        breaks = list(_CLAUSE_BREAK.finditer(window))
        if breaks:
            window = window[breaks[-1].end():]
        if NEGATIVE_WORDS.search(window):
            f.negative = True
    for f in figures:
        if f.negative:
            f.value = -abs(f.value)


def question_names_sign(question: str) -> bool:
    """True if the question itself asks for a loss, cash used, an outflow or a negative value."""
    return bool(NEGATIVE_WORDS.search(_SIGN_LABEL.sub(" ", question)))


def says_not_in_filing(text: str) -> bool:
    return bool(NOT_IN_FILING.search(text))


def claim_for(figure: Figure, claims: list[Claim]) -> Claim | None:
    """The structured claim that states this figure, if any: its value equals the printed number
    or the base-unit value (within 0.01%)."""
    for c in claims:
        if c.value is None:
            continue
        for target in (figure.raw, abs(figure.value)):
            if target and abs(abs(c.value) - target) <= 1e-4 * target:
                return c
    return None


def fill_from_claims(figures: list[Figure], claims: list[Claim]) -> None:
    """Apply a claim's scale to a text figure that states none (EVAL §3, D-047)."""
    for f in figures:
        if f.scale is not None or f.scale_word in ("cents", "dollars") or f.per_share:
            continue
        c = claim_for(f, claims)
        if c is None or not c.scale:
            continue
        factor = SCALE_WORDS.get(c.scale.lower().rstrip("s") + "s") or SCALE_WORDS.get(c.scale.lower())
        if factor and abs(c.value) == f.raw:
            f.scale, f.scale_word = factor, SCALE_NAMES[factor]
            f.value = (-1 if f.negative else 1) * f.raw * factor


def assign_periods(text: str, figures: list[Figure], claims: list[Claim]) -> None:
    """Attach to each figure the period mention nearest to it in its sentence; with none, the
    period of the claim that states it (D-047); with neither, no period."""
    bounds = sentences(text)
    mentions = [p for p in periods(text) if p.kind != "filed"]
    for f in figures:
        s, e = bounds[f.sentence] if bounds else (0, len(text))
        local = [p for p in mentions if s <= p.start < e]
        if local:
            nearest = min(local, key=lambda p: (min(abs(p.start - f.end), abs(f.start - p.end)), p.start < f.start))
            f.periods = [nearest]
            continue
        c = claim_for(f, claims)
        if c is not None and c.period:
            f.periods = periods(c.period)[:1]


def sentence_text(text: str, figure: Figure) -> str:
    bounds = sentences(text)
    s, e = bounds[figure.sentence] if bounds else (0, len(text))
    return text[s:e]


def period_matches(p: Period, fiscal_year: int, period_start: str | None, period_end: str | None,
                   quarter: int | None = None) -> bool | None:
    """Whether a period mention names the gold period: True, False (a conflict), or None
    (cannot tell)."""
    end = date.fromisoformat(period_end) if period_end else None
    start = date.fromisoformat(period_start) if period_start else None
    if p.kind == "quarter":
        return quarter is not None and p.quarter == quarter
    if quarter is not None:
        # Gold is a single quarter: a date cannot be placed; any year-only mention is annual.
        return None if p.kind in ("date", "month") else False
    if p.kind in ("date", "month"):
        for d in (end, start):
            if d is None:
                continue
            if p.kind == "date" and p.year and p.month:
                if abs((date(p.year, p.month, min(p.day or 1, 28)) - d).days) <= 7:
                    return True
            elif (p.year, p.month) == (d.year, d.month):
                return True
        return False
    return p.year == fiscal_year or (end is not None and p.kind == "year" and p.year == end.year)


def names_fiscal_period(p: Period) -> bool:
    """A mention that names a fiscal period rather than a calendar year: "fiscal 2024",
    "FY2024", or a period-end date or month."""
    return p.kind in ("fiscal", "date", "month")
