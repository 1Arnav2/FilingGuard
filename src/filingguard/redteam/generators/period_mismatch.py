"""`period_mismatch`: the question names the period in a way the filing's tables do not.

- `calendar_wording`: "calendar year 2024" for a non-calendar filer. Only where one fiscal
  year covers at least 240 days of that calendar year and no other covers more than 125.
- `start_month` (D-034): "the fiscal year that began in January 2024". The start month comes
  from the period's actual start date; years that start within two days of a month boundary
  are skipped, so the month is never arguable. The trap: the start month falls in the year
  before the fiscal year's label, so the obvious pick is one year too early.
"""

import calendar
from datetime import date, timedelta

from filingguard.redteam.generators.common import GenContext, claim, forbid_for, located_facts, round_robin
from filingguard.redteam.spec import ItemSpec

CALENDAR_FYE = {"1231", "0103"}   # JNJ's 52/53-week year ends within days of December 31
MIN_OVERLAP_DAYS = 240            # the matching fiscal year must cover most of the calendar year
MAX_RUNNER_UP_DAYS = 125          # and no other fiscal year in the filing may come close
MONTH_BOUNDARY_DAYS = 2           # skip start dates this close to a month boundary
SUBTYPES = ("calendar_wording", "start_month")
START_VERBS = ["began", "begin", "beginning", "started", "starting", "start", "commenced"]


def overlap_days(period_start: str, period_end: str, year: int) -> int:
    start = max(date.fromisoformat(period_start), date(year, 1, 1))
    end = min(date.fromisoformat(period_end), date(year, 12, 31))
    return max(0, (end - start + timedelta(days=1)).days)


def best_fiscal_year(periods: list[tuple[str, str]], year: int) -> tuple[str, str] | None:
    """The one fiscal period that clearly matches calendar `year`, or None if none does."""
    ranked = sorted(periods, key=lambda p: -overlap_days(*p, year))
    if not ranked or overlap_days(*ranked[0], year) < MIN_OVERLAP_DAYS:
        return None
    if len(ranked) > 1 and overlap_days(*ranked[1], year) > MAX_RUNNER_UP_DAYS:
        return None
    return ranked[0]


def start_month(period_start: str) -> str | None:
    """'January 2024' for a period starting 2024-01-29, or None if the start is within two days
    of a month boundary (2024-09-29 is two days before October 1; 2024-07-01 is on it)."""
    d = date.fromisoformat(period_start)
    days_into_month = d.day - 1
    days_to_next_month = calendar.monthrange(d.year, d.month)[1] - d.day + 1
    if min(days_into_month, days_to_next_month) <= MONTH_BOUNDARY_DAYS:
        return None
    return f"{d:%B} {d.year}"


def _non_calendar(ctx: GenContext) -> list[str]:
    return [t for t in ctx.corpus.tickers if ctx.corpus.companies[t]["fiscal_year_end"] not in CALENDAR_FYE]


def _calendar_item(ctx: GenContext, ticker: str) -> ItemSpec | None:
    flows = [(m, f) for m, f in located_facts(ctx, ticker) if m.flow and f["gold"]["period_start"]]
    # Judge the overlap against every fiscal year the filing reports, used or not.
    latest = ctx.corpus.latest(ticker)["accession"]
    all_periods = sorted({
        (r.period_start, r.period_end)
        for m in ctx.corpus.metrics(ticker) if m.flow
        for r in ctx.corpus.annual_values(ticker, m, latest).itertuples() if isinstance(r.period_start, str)
    })
    options = []
    for metric, fact in flows:
        g = fact["gold"]
        for year in sorted({int(g["period_end"][:4]), int(g["period_start"][:4])}):
            if best_fiscal_year(all_periods, year) == (g["period_start"], g["period_end"]):
                options.append((metric, fact, year))
    if not options:
        return None
    metric, fact, year = ctx.rng.choice(options)
    claim(ctx, ticker, fact)
    g = fact["gold"]
    return ItemSpec(
        attack_type="period_mismatch", subtype="calendar_wording", company=ticker,
        expected_behavior="answer_or_clarify", gold=g | {"calendar_year": year}, source=fact["source"],
        brief=f"Ask for {ctx.corpus.name(ticker)}'s {metric.label} for calendar year {year}, using the words "
              f"'calendar year {year}'. Do not mention fiscal years or any dates.",
        must_include=[[f"calendar year {year}", f"calendar {year}"]], forbid=forbid_for(g),
    )


def _start_month_item(ctx: GenContext, ticker: str) -> ItemSpec | None:
    options = [(m, f, month) for m, f in located_facts(ctx, ticker)
               if m.flow and f["gold"]["period_start"] and (month := start_month(f["gold"]["period_start"]))]
    if not options:
        return None
    metric, fact, month = ctx.rng.choice(options)
    claim(ctx, ticker, fact)
    g = fact["gold"]
    return ItemSpec(
        attack_type="period_mismatch", subtype="start_month", company=ticker, expected_behavior="answer",
        gold=g | {"start_month": month}, source=fact["source"],
        brief=f"Ask for {ctx.corpus.name(ticker)}'s {metric.label} for the fiscal year that began in {month}, "
              f"using the words 'began in {month}'. Do not mention the fiscal year's number or its end date.",
        must_include=[[month], START_VERBS], forbid=forbid_for(g),
    )


MAKERS = {"calendar_wording": _calendar_item, "start_month": _start_month_item}


def generate_subtype(ctx: GenContext, subtype: str, n: int) -> list[ItemSpec]:
    make = MAKERS[subtype]
    return round_robin(ctx, _non_calendar(ctx), n, lambda t, i: make(ctx, t))


def generate(ctx: GenContext, n: int) -> list[ItemSpec]:
    specs: list[ItemSpec] = []
    for k, subtype in enumerate(SUBTYPES):
        share = n // len(SUBTYPES) + (1 if k < n % len(SUBTYPES) else 0)
        specs += generate_subtype(ctx, subtype, share)
    return specs
