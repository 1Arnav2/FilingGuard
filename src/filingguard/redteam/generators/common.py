"""Shared pieces for the generators: context, located-fact options, period wording."""

import random
from collections.abc import Callable
from dataclasses import dataclass, field

from filingguard.redteam.corpus import Corpus, Metric
from filingguard.redteam.spec import ItemSpec, value_strings


@dataclass
class GenContext:
    corpus: Corpus
    rng: random.Random
    seed: int                                       # also seeds the restated pair selection
    used: set[tuple] = field(default_factory=set)   # (ticker, concept, period_end) already used
    stats: dict = field(default_factory=dict)       # per-generator counts, e.g. removals
    _facts: dict[str, list[tuple[Metric, dict]]] = field(default_factory=dict)

    def bump(self, key: str, n: int = 1) -> None:
        self.stats[key] = self.stats.get(key, 0) + n


def located_facts(ctx: GenContext, ticker: str, metrics: list[Metric] | None = None,
                  current_only: bool = False, include_used: bool = False) -> list[tuple[Metric, dict]]:
    """Every (metric, located fact) the latest 10-K shows on a line carrying the metric's label,
    excluding periods with a restated pair (their value differs between indexed filings) and,
    unless `include_used`, facts another item already uses."""
    corpus = ctx.corpus
    latest = corpus.latest(ticker)
    if ticker not in ctx._facts:
        restated = {(p["ticker"], p["concept"], p["period_end"]) for p in corpus.pairs}
        found = []
        for metric in corpus.metrics(ticker):
            for period_end in corpus.annual_values(ticker, metric, latest["accession"])["period_end"]:
                fact = corpus.fact(ticker, metric, latest["accession"], period_end)
                if fact and (ticker, fact["gold"]["concept"], period_end) not in restated:
                    found.append((metric, fact))
        ctx._facts[ticker] = found
    keys = {m.key for m in metrics} if metrics else None
    return [
        (m, f) for m, f in ctx._facts[ticker]
        if (keys is None or m.key in keys)
        and (not current_only or f["gold"]["period_end"] == latest["report_date"])
        and (include_used or (ticker, f["gold"]["concept"], f["gold"]["period_end"]) not in ctx.used)
    ]


def claim(ctx: GenContext, ticker: str, fact: dict) -> None:
    ctx.used.add((ticker, fact["gold"]["concept"], fact["gold"]["period_end"]))


def round_robin(ctx: GenContext, tickers: list[str], n: int,
                make: Callable[[str, int], ItemSpec | None]) -> list[ItemSpec]:
    """Cycle through companies in seeded order, asking `make(ticker, i)` for one spec each
    turn, until `n` specs exist or no company can supply another."""
    order = tickers[:]
    ctx.rng.shuffle(order)
    specs: list[ItemSpec] = []
    exhausted: set[str] = set()
    i = 0
    while len(specs) < n and len(exhausted) < len(order):
        for ticker in order:
            if len(specs) >= n:
                break
            if ticker in exhausted:
                continue
            spec = make(ticker, i)
            if spec is None:
                exhausted.add(ticker)
            else:
                specs.append(spec)
                i += 1
    return specs


# Every non-trap brief names the period the same way, with no dates, so wording alone does
# not tell controls from period-mismatch or unanswerable items (style check, D-028).
NO_DATES = "using the words 'fiscal {label}' and no dates or months"


def period_phrase(gold: dict, flow: bool) -> str:
    """'fiscal 2025' for a flow, 'the end of fiscal 2025' for a balance."""
    return f"fiscal {gold['fiscal_year']}" if flow else f"the end of fiscal {gold['fiscal_year']}"


def ask_value_brief(name: str, metric: Metric, gold: dict) -> str:
    when = ("for " if metric.flow else "as of ") + period_phrase(gold, metric.flow)
    return f"Ask for {name}'s {metric.label} {when}, {NO_DATES.format(label=gold['fiscal_year'])}."


def forbid_for(gold: dict) -> list[str]:
    return value_strings(gold["value"], gold["unit"])


def pick(ctx: GenContext, options: list) -> object | None:
    return ctx.rng.choice(options) if options else None


def cycle(values: tuple, i: int):
    return values[i % len(values)]

