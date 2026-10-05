"""Candidates v3: the committed v1 candidates revised under the rules adopted after the first
review, the v2 pre-screen and the pre-review checks (H-009 to H-024, D-030 to D-041), plus
replacements generated for what was removed.

Every v1 spec that still passes keeps its spec id, so its existing question is reused and
nothing is re-phrased that did not change. Deterministic given the v1 file and the seed.
"""

import random
from collections import Counter

from filingguard.redteam.corpus import METRICS, Corpus
from filingguard.redteam.generators import control, period_mismatch, restated, unanswerable, unit_trap
from filingguard.redteam.generators.common import GenContext
from filingguard.redteam.generators.unanswerable import absence_check, brief_and_phrases
from filingguard.redteam.injection import containing_chunk, insert_position
from filingguard.redteam.restated import select_pairs
from filingguard.redteam.spec import ItemSpec

START_MONTH_CANDIDATES = 30   # about half of 46 period items, plus room; 3 per non-calendar filer (D-034)
PERIOD_CANDIDATES = 54        # 46 period_mismatch items plus room for phrasing and review losses
SPARE = 2                     # each type must keep at least its final count plus this many candidates
SINGLE_QUARTER_CANDIDATES = 22   # 20 single-quarter items plus room (like-for-like replacement, D-041)
DRIVER_CANDIDATES = 13           # 10 true-premise driver controls plus room (D-041)


def _metric(corpus: Corpus, ticker: str, concept: str):
    return next(m for k, m in METRICS.items() if corpus.concept_map[ticker].get(k) == concept)


def _relocated(corpus: Corpus, spec: ItemSpec) -> dict | None:
    """The fact under the strict label rule (D-030), or None if it no longer qualifies."""
    g, src = spec.gold, spec.source
    fact = corpus.fact(spec.company, _metric(corpus, spec.company, g["concept"]), src["accession"], g["period_end"])
    if fact is None or fact["gold"]["value"] != g["value"]:
        return None
    return fact


def _prior_ok(corpus: Corpus, spec: ItemSpec) -> bool:
    """A false premise's prior-year value must also sit on a strictly labelled row."""
    metric = _metric(corpus, spec.company, spec.gold["concept"])
    accession = spec.source["accession"]
    prior_year = str(spec.gold["fiscal_year"] - 1)
    rows = corpus.annual_values(spec.company, metric, accession)
    for end in rows["period_end"]:
        fact = corpus.fact(spec.company, metric, accession, end)
        if fact and str(fact["gold"]["fiscal_year"]) == prior_year:
            return fact["gold"]["value"] == spec.gold["true_values"][prior_year]
    return False


def _rebuilt(spec: ItemSpec, **changes) -> ItemSpec:
    """A copy with `changes`, whose spec id is recomputed (it changes only if gold or brief do)."""
    fields = spec.to_dict() | changes | {"spec_id": ""}
    return ItemSpec(**fields)


def revise_one(corpus: Corpus, spec: ItemSpec) -> tuple[ItemSpec | None, str]:
    """The revised spec (or None) and the reason, for one v1 spec."""
    t, sub = spec.attack_type, spec.subtype
    if t == "restated":
        return None, "restated pairs reselected (D-030)"
    if t == "period_mismatch" and sub == "fiscal_label":
        return None, "fiscal_label subtype replaced by start_month (D-034)"
    if t == "unanswerable":
        metric = METRICS[next(k for k, m in METRICS.items() if m.label == spec.gold["metric"])]
        search = {"terms": spec.evidence["searched_terms"], "near": spec.evidence["required_nearby"]}
        evidence = absence_check(corpus, spec.company, sub, metric, spec.gold["fiscal_year"], search)
        if evidence is None:
            if sub == "untagged_concept":
                return None, "untagged concept can be computed from printed lines (D-032)"
            return None, "absence rule fails in another corpus filing (D-041)"
        evidence = {"filing": spec.evidence["filing"], **evidence}
        if sub == "single_quarter":
            brief, must = brief_and_phrases(corpus.name(spec.company), metric, sub, spec.gold["fiscal_year"],
                                            {"quarter": spec.gold["quarter"]})
            return _rebuilt(spec, brief=brief, must_include=must, evidence=evidence), "single-quarter brief reworded (D-033)"
        return _rebuilt(spec, evidence=evidence), "kept"
    fact = _relocated(corpus, spec)
    if fact is None:
        if (spec.company, spec.gold["concept"], spec.source["accession"], spec.gold["period_end"]) in corpus.same_label:
            return None, "a second figure is printed under the same row label (D-037)"
        return None, "value not on a row labelled with the metric's own name (D-030)"
    if t == "false_premise" and not _prior_ok(corpus, spec):
        return None, "prior-year value not on a strictly labelled row (D-030)"
    gold = spec.gold | {k: fact["gold"][k] for k in ("printed_scale", "printed_as", "metric")}
    if t == "unit_trap":
        requested = spec.gold["requested_scale"]
        if gold["printed_scale"] != spec.gold["printed_scale"]:
            return None, "printed scale changed on the strictly labelled row"
        metric = _metric(corpus, spec.company, spec.gold["concept"])
        rebuilt = unit_trap.build(spec.company, corpus.name(spec.company), metric, fact, requested)
        if rebuilt.spec_id == spec.spec_id:
            return rebuilt, "kept"
        return rebuilt, ("line named in the question (D-037)" if gold["metric"] != spec.gold["metric"]
                         else "dollars wording changed (D-033)")
    changes: dict = {"gold": gold, "source": fact["source"]}
    if t == "period_mismatch" and sub == "calendar_wording":
        metric = _metric(corpus, spec.company, spec.gold["concept"])
        trap = period_mismatch.calendar_trap(corpus, spec.company, metric, fact, spec.gold["calendar_year"])
        if trap is None or not period_mismatch.trap_far_enough(spec.gold["value"], trap["trap_value"]):
            return None, "trap value within 2% of gold or equal at 3 significant figures (D-041)"
        changes["evidence"] = trap
    if gold["metric"] != spec.gold["metric"]:
        old, new = f"'s {spec.gold['metric']}", f"'s {gold['metric']}"
        changes["brief"] = spec.brief.replace(old, new, 1)
        if "premise" in gold:
            gold["premise"] = gold["premise"].replace(old, new, 1)
    if t == "injection":
        chunk = containing_chunk(corpus.chunks, fact["source"]["accession"], fact["source"]["span"])
        if chunk is None:
            return None, "no single chunk holds the strictly labelled row"
        changes["injection"] = spec.injection | {"chunk_id": chunk["chunk_id"],
                                                 "insert_at": insert_position(chunk, fact["source"]["span"][1])}
    revised = _rebuilt(spec, **changes)
    if revised.spec_id == spec.spec_id:
        return revised, "kept"
    return revised, "line named in the question (D-037)" if "brief" in changes else "gold printed form changed"


def revise(corpus: Corpus, v1: list[ItemSpec], seed: int, final: dict[str, int]) -> tuple[list[ItemSpec], dict]:
    """Candidates v3 and a record of what happened to every v1 spec."""
    ctx = GenContext(corpus, random.Random(f"{seed}-revise"), seed)
    kept, outcome = [], {}
    for spec in v1:
        revised, reason = revise_one(corpus, spec)
        outcome[spec.spec_id] = {"type": spec.attack_type, "subtype": spec.subtype, "reason": reason,
                                 "v3_spec_id": revised.spec_id if revised else None}
        if revised:
            kept.append(revised)
    key = lambda s: (s.company, s.gold["concept"], s.gold["period_end"])
    # Restated and start-month items are the scarcest, so they take facts first; any kept
    # candidate of another type that holds one of those facts is dropped as a duplicate, as
    # long as its type keeps its final count plus SPARE (checked below).
    added = restated.generate(ctx, len(select_pairs(restated.usable_pairs(corpus), seed)))
    # Start-month: redraw as before the trap rule, keep the draws that pass it, and replace the
    # rest with draws that must pass it (D-041), so passing items keep their phrased questions.
    starts = period_mismatch.generate_subtype(ctx, "start_month", START_MONTH_CANDIDATES, require_gap=False)
    passing = [s for s in starts if period_mismatch.trap_far_enough(s.gold["value"], s.gold["trap_value"])]
    trap_dropped = len(starts) - len(passing)
    added += passing + period_mismatch.generate_subtype(ctx, "start_month", trap_dropped)
    taken = {key(s) for s in added}
    by_new_id = {o["v3_spec_id"]: k for k, o in outcome.items() if o["v3_spec_id"]}
    for s in kept:
        if s.source and key(s) in taken:
            outcome[by_new_id[s.spec_id]] |= {"reason": "fact taken by a new restated or start-month item",
                                              "v3_spec_id": None}
    kept = [s for s in kept if not (s.source and key(s) in taken)]
    ctx.used |= {key(s) for s in kept if s.source}
    ctx.used |= {(s.company, s.subtype, next(k for k, m in METRICS.items() if m.label == s.gold["metric"]),
                  s.gold["fiscal_year"], tuple({"quarter": s.gold["quarter"]}.items()) if "quarter" in s.gold else ())
                 for s in kept if s.attack_type == "unanswerable"}
    period = sum(s.attack_type == "period_mismatch" for s in kept + added)
    added += period_mismatch.generate_subtype(ctx, "calendar_wording", max(0, PERIOD_CANDIDATES - period))
    quarters = sum(s.subtype == "single_quarter" for s in kept)
    added += unanswerable.generate(ctx, max(0, SINGLE_QUARTER_CANDIDATES - quarters), subtypes=("single_quarter",))
    added += control.generate_drivers(ctx, DRIVER_CANDIDATES)
    specs = kept + added
    # restated is fixed at its selected pair count, so it has no spares.
    short = {t: n for t, n in Counter(s.attack_type for s in specs).items()
             if n < final[t] + (0 if t == "restated" else SPARE)}
    if short or set(final) - {s.attack_type for s in specs}:
        raise RuntimeError(f"too few candidates after revision: {short}")
    random.Random(f"{seed}-v3-order").shuffle(specs)
    stats = {
        "seed": seed, "v1": len(v1), "v1_kept": len(kept), "added": len(added), "v3": len(specs),
        "v1_outcomes": dict(Counter((o["type"], o["reason"]) for o in outcome.values()).most_common()),
        "v3_by_type": dict(Counter(s.attack_type for s in specs)),
        "v3_by_subtype": dict(Counter(f"{s.attack_type}/{s.subtype}" for s in specs)),
        "start_month_by_company": dict(Counter(s.company for s in specs if s.subtype == "start_month")),
        "start_month_draws_failing_trap_rule": trap_dropped,
        "driver_companies": sorted(s.company for s in specs if s.subtype == "true_premise_driver"),
    }
    stats["v1_outcomes"] = [{"type": k[0], "reason": k[1], "count": v} for k, v in stats["v1_outcomes"].items()]
    return specs, {"stats": stats, "per_spec": outcome}
