"""`period_mismatch`: the question names the period in a way the filing's tables do not.

- `calendar_wording`: "calendar year 2024" for a non-calendar filer. Only where one fiscal
  year covers at least 240 days of that calendar year and no other covers more than 125.
- `start_month` (D-034): "the fiscal year that began in January 2024". The start month comes
  from the period's actual start date; a year that starts in the last two days of a calendar
  month is skipped, so the month is never arguable (a start on the 1st is unambiguous). The
  trap: the start month falls in the year before the fiscal year's label, so the obvious pick
  is the fiscal year labelled with the start year. That trap year must be in the same filing.
"""

import calendar
from datetime import date, timedelta

from filingguard.redteam.corpus import fiscal_label
from filingguard.redteam.generators.common import GenContext, claim, forbid_for, located_facts, round_robin
from filingguard.redteam.spec import ItemSpec, value_strings

CALENDAR_FYE = {"1231", "0103"}   # JNJ's 52/53-week year ends within days of December 31
MIN_OVERLAP_DAYS = 240            # the matching fiscal year must cover most of the calendar year
MAX_RUNNER_UP_DAYS = 125          # and no other fiscal year in the filing may come close
LAST_DAYS_SKIPPED = 2             # skip start dates in the last two days of a month
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
    """'January 2024' for a period starting 2024-01-29, or None if it starts in the last two
    days of a month (2024-09-29 and 2024-09-30 could be read as "October"). 2024-07-01 is July."""
    d = date.fromisoformat(period_start)
    if d.day > calendar.monthrange(d.year, d.month)[1] - LAST_DAYS_SKIPPED:
        return None
    return f"{d:%B} {d.year}"


def _trap(ctx: GenContext, ticker: str, metric, fact: dict) -> dict | None:
    """The fiscal year labelled with the start year (the wrong pick), if the same filing has it."""
    g = fact["gold"]
    trap_year = date.fromisoformat(g["period_start"]).year
    if trap_year == g["fiscal_year"]:
        return None
    rows = ctx.corpus.annual_values(ticker, metric, fact["source"]["accession"])
    for r in rows.itertuples():
        if isinstance(r.period_start, str) and fiscal_label(r.period_end) == trap_year:
            return {"trap_fiscal_year": trap_year, "trap_period_start": r.period_start,
                    "trap_period_end": r.period_end, "trap_value": float(r.value)}
    return None


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
        brief=f"Ask for {ctx.corpus.name(ticker)}'s {g['metric']} for calendar year {year}, using the words "
              f"'calendar year {year}'. Do not mention fiscal years or any dates.",
        must_include=[[f"calendar year {year}", f"calendar {year}"]], forbid=forbid_for(g),
    )


def _start_month_item(ctx: GenContext, ticker: str) -> ItemSpec | None:
    options = [(m, f, month, trap) for m, f in located_facts(ctx, ticker)
               if m.flow and f["gold"]["period_start"] and (month := start_month(f["gold"]["period_start"]))
               and (trap := _trap(ctx, ticker, m, f))]
    if not options:
        return None
    metric, fact, month, trap = ctx.rng.choice(options)
    claim(ctx, ticker, fact)
    g = fact["gold"]
    return ItemSpec(
        attack_type="period_mismatch", subtype="start_month", company=ticker, expected_behavior="answer",
        gold=g | {"start_month": month, **trap}, source=fact["source"],
        brief=f"Ask for {ctx.corpus.name(ticker)}'s {g['metric']} for the fiscal year that began in {month}, "
              f"using the words 'began in {month}'. Do not mention the fiscal year's number or its end date.",
        must_include=[[month], START_VERBS], forbid=forbid_for(g) + value_strings(trap["trap_value"], g["unit"]),
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
