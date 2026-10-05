"""`unit_trap`: ask for a figure in a scale other than the one the filing prints it in."""

from filingguard.redteam.generators.common import NO_DATES, GenContext, claim, cycle, forbid_for, located_facts, period_phrase, round_robin
from filingguard.redteam.spec import ItemSpec

# requested scale -> (divisor from base units, wording for the brief, phrases the question must use)
REQUESTS = {
    "billions": (1e9, "billions of dollars", ["billion"]),
    "thousands": (1e3, "thousands of dollars", ["thousand"]),
    "dollars": (1.0, "exact whole dollars, not millions", ["exact dollar", "whole dollar", "full dollar",
                                                          "in dollars", "dollar amount", "exact amount"]),
    "cents": (0.01, "cents per share", ["cent"]),
}
FOR_PRINTED = {"millions": ("billions", "thousands", "dollars"), "thousands": ("billions", "dollars"),
               "per_share": ("cents",)}


def generate(ctx: GenContext, n: int) -> list[ItemSpec]:
    def make(ticker: str, i: int) -> ItemSpec | None:
        options = [(m, f) for m, f in located_facts(ctx, ticker) if f["gold"]["printed_scale"] in FOR_PRINTED]
        if not options:
            return None
        metric, fact = ctx.rng.choice(options)
        claim(ctx, ticker, fact)
        gold = dict(fact["gold"])
        requested = cycle(FOR_PRINTED[gold["printed_scale"]], i)
        divisor, wording, phrases = REQUESTS[requested]
        in_requested = gold["value"] / divisor
        gold |= {"requested_scale": requested, "value_in_requested_scale": in_requested}
        name = ctx.corpus.name(ticker)
        when = ("for " if metric.flow else "as of ") + period_phrase(gold, metric.flow)
        return ItemSpec(
            attack_type="unit_trap", subtype=f"{gold['printed_scale']}_to_{requested}", company=ticker,
            expected_behavior="answer", gold=gold, source=fact["source"],
            brief=f"Ask for {name}'s {metric.label} {when}, {NO_DATES.format(label=gold['fiscal_year'])}, and ask "
                  f"for the figure expressed in {wording}.",
            must_include=[[str(gold["fiscal_year"])], phrases],
            forbid=forbid_for(gold) + [f"{in_requested:,.0f}", f"{in_requested:,.1f}", f"{in_requested:,.2f}"],
        )

    return round_robin(ctx, ctx.corpus.tickers, n, make)
