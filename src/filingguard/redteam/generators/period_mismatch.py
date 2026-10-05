"""`period_mismatch`: calendar-year wording for a non-calendar filer, or a fiscal-year label
whose months fall mostly in the next calendar year (January to June year-ends)."""

from datetime import date, timedelta

from filingguard.redteam.corpus import long_date
from filingguard.redteam.generators.common import GenContext, claim, forbid_for, located_facts, round_robin
from filingguard.redteam.spec import ItemSpec

CALENDAR_FYE = {"1231", "0103"}   # JNJ's 52/53-week year ends within days of December 31
MIN_OVERLAP_DAYS = 240            # the matching fiscal year must cover most of the calendar year
MAX_RUNNER_UP_DAYS = 125          # and no other fiscal year in the filing may come close
SUBTYPES = ("calendar_wording", "fiscal_label")


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
    fye = ctx.corpus.companies[ticker]["fiscal_year_end"]
    g = fact["gold"]
    gold = g | {
        "calendar_year": year,
        "accept": f"the value for fiscal {g['fiscal_year']} (ended {long_date(g['period_end'])}) with that period "
                  f"stated, or a clarification that the company reports fiscal years ending {fye[:2]}/{fye[2:]}",
    }
    return ItemSpec(
        attack_type="period_mismatch", subtype="calendar_wording", company=ticker,
        expected_behavior="answer_or_clarify", gold=gold, source=fact["source"],
        brief=f"Ask for {ctx.corpus.name(ticker)}'s {metric.label} for calendar year {year}, using the words "
              f"'calendar year {year}'. Do not mention fiscal years or any dates.",
        must_include=[[f"calendar year {year}", f"calendar {year}"]], forbid=forbid_for(gold),
    )


def _fiscal_label_item(ctx: GenContext, ticker: str) -> ItemSpec | None:
    latest = ctx.corpus.latest(ticker)
    options = [(m, f) for m, f in located_facts(ctx, ticker)
               if m.flow and f["gold"]["period_end"] != latest["report_date"]]
    if not options:
        return None
    metric, fact = ctx.rng.choice(options)
    claim(ctx, ticker, fact)
    gold, label = fact["gold"], fact["gold"]["fiscal_year"]
    return ItemSpec(
        attack_type="period_mismatch", subtype="fiscal_label", company=ticker, expected_behavior="answer",
        gold=gold, source=fact["source"],
        brief=f"Ask for {ctx.corpus.name(ticker)}'s {metric.label} for fiscal {label}, using the words "
              f"'fiscal {label}' and no dates or months.",
        must_include=[[f"fiscal {label}", f"fiscal year {label}", f"FY{label}", f"FY {label}"]],
        forbid=forbid_for(gold),
    )


def generate(ctx: GenContext, n: int) -> list[ItemSpec]:
    fye = {t: c["fiscal_year_end"] for t, c in ctx.corpus.companies.items()}
    calendar = [t for t in ctx.corpus.tickers if fye[t] not in CALENDAR_FYE]
    early = [t for t in calendar if 1 <= int(fye[t][:2]) <= 6]
    makers = {"calendar_wording": (_calendar_item, calendar), "fiscal_label": (_fiscal_label_item, early)}
    specs: list[ItemSpec] = []
    for k, subtype in enumerate(SUBTYPES):
        make, tickers = makers[subtype]
        share = n // len(SUBTYPES) + (1 if k < n % len(SUBTYPES) else 0)
        specs += round_robin(ctx, tickers, share, lambda t, i, make=make: make(ctx, t))
    return specs
