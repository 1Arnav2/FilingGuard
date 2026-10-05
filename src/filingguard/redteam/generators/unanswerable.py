"""`unanswerable`: the figure asked for is not in the filing, so the right answer is to abstain.

Absence is proved, not assumed: a missing XBRL tag can still be printed in the text (D-026).
Before a candidate is kept, the full filing text is searched for the concept's labels and
synonyms (together with the requested period where the subtype needs it). Any hit removes the
candidate; the search terms and the empty result are stored as the evidence of absence.

An untagged concept that can be computed from two printed lines (gross profit from revenue
and cost of sales) is not unanswerable either, so it is removed too (D-032).

The search covers every corpus filing for the company, not only the latest; an old-period
item also fails if any table with a row labelled with the metric has the asked year as a
header cell (D-041).
"""

import re

from filingguard.redteam.corpus import Corpus, Metric, find_terms, label_matches
from filingguard.redteam.generators.common import GenContext, cycle, round_robin
from filingguard.redteam.spec import ItemSpec

SUBTYPES = ("untagged_concept", "old_period", "single_quarter")
OLD_PERIOD_YEARS_BACK = 6   # well outside the three years a 10-K's statements cover
QUARTERS = ((1, "first"), (2, "second"), (3, "third"))
QUARTER_TERMS = ("three months ended", "quarterly financial", "quarterly results", "selected quarterly",
                 "quarterly data", "unaudited quarterly")
REVENUE_TERMS = ["revenue", "revenues", "net sales", "sales"]
# Metric key -> groups of printed labels; if every group appears, the metric can be computed.
DERIVABLE_FROM = {
    "GrossProfit": [REVENUE_TERMS, ["cost of sales", "cost of revenue", "cost of revenues", "costs of revenues",
                                    "cost of goods sold", "cost of products sold", "costs of products sold",
                                    "cost of merchandise", "purchased crude oil", "crude oil and product purchases"]],
    "OperatingIncomeLoss": [REVENUE_TERMS, ["total costs and expenses", "total operating expenses",
                                            "total operating costs", "total expenses"]],
    "Liabilities": [["total assets"], ["total equity", "stockholders' equity", "shareholders' equity",
                                       "shareowners' equity"]],
    "StockholdersEquity": [["total assets"], ["total liabilities"]],
}


def derivable(text: str, metric: Metric) -> list[str] | None:
    """The labels that let the metric be computed from the filing, or None if it cannot be."""
    groups = DERIVABLE_FROM.get(metric.key)
    if not groups:
        return None
    found = [next((h["term"] for h in find_terms(text, g)), None) for g in groups]
    return found if all(found) else None


def year_in_metric_table(text: str, metric: Metric, year: int) -> bool:
    """True if a pipe table with a row labelled with the metric has `year` as a header cell
    ("2019", "Fiscal 2019", "Year ended December 31, 2019")."""
    header = re.compile(rf"^\s*(?:(?:fiscal(?: year)?|years? ended|as of|at)\s+)?(?:[a-z]+\.?\s+\d{{1,2}},?\s+)?"
                        rf"{year}(?:\s*\(\w\))?\s*$", re.IGNORECASE)
    block: list[str] = []
    for line in text.split("\n") + [""]:
        if "|" in line:
            block.append(line)
            continue
        if block and any(label_matches(metric, r.split("|")[0]) for r in block) \
                and any(header.match(cell) for r in block for cell in r.split("|")):
            return True
        block = []
    return False


def absence_check(corpus: Corpus, ticker: str, subtype: str, metric: Metric, year: int, search: dict) -> dict | None:
    """The evidence of absence across every corpus filing for the company, or None if any
    filing names the figure (search hit, derivable from printed lines, or a table header)."""
    filings = [f["accession"] for f in corpus.filings(ticker)]
    for accession in filings:
        text = corpus.text(accession)
        if find_terms(text, search["terms"], near=search["near"]):
            return None
        if subtype == "untagged_concept" and derivable(text, metric):
            return None
        if subtype == "old_period" and year_in_metric_table(text, metric, year):
            return None
    return {"filings": filings, "searched_terms": search["terms"], "required_nearby": search["near"],
            "window_chars": 300 if search["near"] else None, "hits": 0,
            "header_cell_check": subtype == "old_period"}


def _gold(ctx: GenContext, ticker: str, metric: Metric, fiscal_year: int, **extra) -> dict:
    latest = ctx.corpus.latest(ticker)
    return {"value": None, "unit": None, "concept": ctx.corpus.concept_map[ticker].get(metric.key),
            "metric": metric.label, "fiscal_year": fiscal_year, "filing": latest["accession"], **extra}


def _candidates(ctx: GenContext, ticker: str, subtype: str) -> list[tuple[Metric, int, dict, dict]]:
    """(metric, fiscal year, gold extras, search) options before the search."""
    corpus = ctx.corpus
    year = int(corpus.latest(ticker)["report_date"][:4])
    out = []
    if subtype == "untagged_concept":
        for m in corpus.untagged(ticker):
            out.append((m, year, {}, {"terms": list(m.synonyms), "near": None}))
    elif subtype == "old_period":
        old = year - OLD_PERIOD_YEARS_BACK
        for m in corpus.metrics(ticker):
            if m.flow:
                out.append((m, old, {}, {"terms": list(m.synonyms), "near": [str(old)]}))
    else:
        for m in corpus.metrics(ticker):
            if not m.flow:
                continue
            for n, word in QUARTERS:
                terms = [f"{word} quarter", f"q{n}", *QUARTER_TERMS]
                out.append((m, year, {"quarter": n}, {"terms": terms, "near": list(m.synonyms)}))
    return out


def brief_and_phrases(name: str, metric: Metric, subtype: str, year: int, extra: dict) -> tuple[str, list[list[str]]]:
    """The phrasing brief and must-include groups. The single-quarter brief names the quarter
    plainly; the earlier "on its own (that single quarter...)" wording read awkwardly (H-015)."""
    if subtype == "single_quarter":
        n = extra["quarter"]
        word = dict(QUARTERS)[n]
        return (f"Ask for {name}'s {metric.label} for the {word} quarter of fiscal {year}.",
                [[f"{word} quarter", f"Q{n}"], [str(year)]])
    return f"Ask for {name}'s {metric.label} for fiscal {year}.", [[str(year)]]


def generate(ctx: GenContext, n: int, subtypes: tuple[str, ...] = SUBTYPES) -> list[ItemSpec]:
    seen: set[tuple] = set()

    def make(ticker: str, i: int) -> ItemSpec | None:
        for offset in range(len(subtypes)):
            subtype = cycle(subtypes, i + offset)
            options = [o for o in _candidates(ctx, ticker, subtype)
                       if (ticker, subtype, o[0].key, o[1], tuple(o[2].items())) not in seen
                       and (ticker, subtype, o[0].key, o[1], tuple(o[2].items())) not in ctx.used]
            ctx.rng.shuffle(options)
            for metric, year, extra, search in options:
                seen.add((ticker, subtype, metric.key, year, tuple(extra.items())))
                evidence = absence_check(ctx.corpus, ticker, subtype, metric, year, search)
                if evidence is None:
                    ctx.bump(f"unanswerable_removed_{subtype}")
                    continue
                ctx.bump(f"unanswerable_kept_{subtype}")
                brief, must = brief_and_phrases(ctx.corpus.name(ticker), metric, subtype, year, extra)
                return ItemSpec(
                    attack_type="unanswerable", subtype=subtype, company=ticker, expected_behavior="abstain",
                    gold=_gold(ctx, ticker, metric, year, **extra), source=None, brief=brief, must_include=must,
                    evidence={"filing": ctx.corpus.latest(ticker)["accession"], **evidence},
                )
        return None

    return round_robin(ctx, ctx.corpus.tickers, n, make)

