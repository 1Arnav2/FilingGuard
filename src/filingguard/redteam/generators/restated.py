"""`restated`: ask for a figure as reported in one named 10-K, when another 10-K reports the
same period differently (D-021). Both filings are in the index (D-026)."""

from filingguard.data.facts import USABLE_KINDS
from filingguard.redteam.corpus import METRICS, Corpus, fiscal_label, long_date
from filingguard.redteam.generators.common import GenContext, claim, forbid_for, period_phrase
from filingguard.redteam.restated import select_pairs
from filingguard.redteam.spec import ItemSpec, value_strings

SIDES = {"original": "restated", "restated": "original"}


def _metric(corpus: Corpus, ticker: str, concept: str):
    return next(m for k, m in METRICS.items() if corpus.concept_map[ticker].get(k) == concept)


def usable_pairs(corpus: Corpus) -> list[dict]:
    """Pairs whose two values each sit on a row labelled with the metric's own name, in their
    own filing (D-030). A pair that fails this is a tagging change, not a restatement of the
    same line (GOOGL long-term debt, H-011)."""
    out = []
    for p in corpus.pairs:
        if p["kind"] not in USABLE_KINDS:
            continue
        metric = _metric(corpus, p["ticker"], p["concept"])
        facts = [corpus.fact(p["ticker"], metric, p[side]["accession"], p["period_end"]) for side in SIDES]
        if all(f is not None and f["gold"]["value"] == p[side]["value"] for f, side in zip(facts, SIDES)):
            out.append(p)
    return out


def generate(ctx: GenContext, n: int) -> list[ItemSpec]:
    """One item per selected pair; `n` must equal the selected count (it is fixed by D-021)."""
    corpus = ctx.corpus
    pairs = select_pairs(usable_pairs(corpus), ctx.seed)
    if len(pairs) != n:
        raise ValueError(f"{len(pairs)} restated pairs selected, {n} expected")
    specs = []
    for p in pairs:
        ticker, asked, other = p["ticker"], p[p["ask"]], p[SIDES[p["ask"]]]
        metric = _metric(corpus, ticker, p["concept"])
        fact = corpus.fact(ticker, metric, asked["accession"], p["period_end"])
        claim(ctx, ticker, fact)
        filing_year = fiscal_label(asked["report_date"])
        gold = fact["gold"] | {
            "kind": p["kind"], "asked_filing": p["ask"],
            "other_value": other["value"], "other_accession": other["accession"],
        }
        name = corpus.name(ticker)
        when = ("for " if metric.flow else "as of ") + period_phrase(gold, metric.flow)
        specs.append(ItemSpec(
            attack_type="restated", subtype=p["kind"], company=ticker, expected_behavior="answer",
            gold=gold, source=fact["source"],
            brief=f"Ask for {name}'s {metric.label} {when} as reported in the company's 10-K annual report for "
                  f"fiscal {filing_year} (filed {long_date(asked['filed'])}). Make clear the question is about the "
                  "figure in that specific annual report.",
            must_include=[[str(gold["fiscal_year"])], [str(filing_year)], ["10-K", "annual report"]],
            forbid=forbid_for(gold) + value_strings(other["value"], p["unit"]),
        ))
    return specs
