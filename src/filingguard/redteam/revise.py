"""Candidates v2: the committed v1 candidates revised under the rules adopted after the first
review (H-009 to H-016, D-030 to D-034), plus replacements generated for what was removed.

Every v1 spec that still passes keeps its spec id, so its existing question is reused and
nothing is re-phrased that did not change. Deterministic given the v1 file and the seed.
"""

import random
from collections import Counter

from filingguard.redteam.corpus import METRICS, Corpus
from filingguard.redteam.generators import period_mismatch, restated, unit_trap
from filingguard.redteam.generators.common import GenContext
from filingguard.redteam.generators.unanswerable import brief_and_phrases, derivable
from filingguard.redteam.injection import containing_chunk, insert_position
from filingguard.redteam.restated import select_pairs
from filingguard.redteam.spec import ItemSpec

START_MONTH_CANDIDATES = 36   # every start-month option the boundary rule leaves (D-034)
PERIOD_CANDIDATES = 52        # 46 period_mismatch items plus room for phrasing and review losses


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
        if sub == "untagged_concept":
            metric = METRICS[next(k for k, m in METRICS.items() if m.label == spec.gold["metric"])]
            if derivable(corpus.text(spec.evidence["filing"]), metric):
                return None, "untagged concept can be computed from printed lines (D-032)"
            return spec, "kept"
        if sub == "single_quarter":
            metric = METRICS[next(k for k, m in METRICS.items() if m.label == spec.gold["metric"])]
            brief, must = brief_and_phrases(corpus.name(spec.company), metric, sub, spec.gold["fiscal_year"],
                                            {"quarter": spec.gold["quarter"]})
            return _rebuilt(spec, brief=brief, must_include=must), "single-quarter brief reworded (D-033)"
        return spec, "kept"
    fact = _relocated(corpus, spec)
    if fact is None:
        return None, "value not on a row labelled with the metric's own name (D-030)"
    if t == "false_premise" and not _prior_ok(corpus, spec):
        return None, "prior-year value not on a strictly labelled row (D-030)"
    gold = spec.gold | {k: fact["gold"][k] for k in ("printed_scale", "printed_as")}
    if t == "unit_trap":
        requested = spec.gold["requested_scale"]
        if gold["printed_scale"] != spec.gold["printed_scale"]:
            return None, "printed scale changed on the strictly labelled row"
        metric = _metric(corpus, spec.company, spec.gold["concept"])
        rebuilt = unit_trap.build(spec.company, corpus.name(spec.company), metric, fact, requested)
        return rebuilt, "kept" if rebuilt.spec_id == spec.spec_id else "dollars wording changed (D-033)"
    changes: dict = {"gold": gold, "source": fact["source"]}
    if t == "injection":
        chunk = containing_chunk(corpus.chunks, fact["source"]["accession"], fact["source"]["span"])
        if chunk is None:
            return None, "no single chunk holds the strictly labelled row"
        changes["injection"] = spec.injection | {"chunk_id": chunk["chunk_id"],
                                                 "insert_at": insert_position(chunk, fact["source"]["span"][1])}
    revised = _rebuilt(spec, **changes)
    return revised, "kept" if revised.spec_id == spec.spec_id else "gold printed form changed"


def revise(corpus: Corpus, v1: list[ItemSpec], seed: int) -> tuple[list[ItemSpec], dict]:
    """Candidates v2 and a record of what happened to every v1 spec."""
    ctx = GenContext(corpus, random.Random(f"{seed}-revise"), seed)
    kept, outcome = [], {}
    for spec in v1:
        revised, reason = revise_one(corpus, spec)
        outcome[spec.spec_id] = {"type": spec.attack_type, "subtype": spec.subtype, "reason": reason,
                                 "v2_spec_id": revised.spec_id if revised else None}
        if revised:
            kept.append(revised)
    key = lambda s: (s.company, s.gold["concept"], s.gold["period_end"])
    # Controls have spare candidates (76 for 60), so new items may take a fact a control
    # candidate holds; that control candidate is then dropped as a duplicate.
    ctx.used |= {key(s) for s in kept if s.source and s.attack_type != "control"}
    added = restated.generate(ctx, len(select_pairs(restated.usable_pairs(corpus), seed)))
    added += period_mismatch.generate_subtype(ctx, "start_month", START_MONTH_CANDIDATES)
    period = sum(s.attack_type == "period_mismatch" for s in kept + added)
    added += period_mismatch.generate_subtype(ctx, "calendar_wording", max(0, PERIOD_CANDIDATES - period))
    taken = {key(s) for s in added}
    for s in kept:
        if s.attack_type == "control" and key(s) in taken:
            outcome[next(k for k, o in outcome.items() if o["v2_spec_id"] == s.spec_id)] |= {
                "reason": "fact taken by a new restated or start-month item", "v2_spec_id": None}
    kept = [s for s in kept if not (s.attack_type == "control" and key(s) in taken)]
    specs = kept + added
    random.Random(f"{seed}-v2-order").shuffle(specs)
    stats = {
        "seed": seed, "v1": len(v1), "v1_kept": len(kept), "added": len(added), "v2": len(specs),
        "v1_outcomes": dict(Counter((o["type"], o["reason"]) for o in outcome.values()).most_common()),
        "v2_by_type": dict(Counter(s.attack_type for s in specs)),
        "v2_by_subtype": dict(Counter(f"{s.attack_type}/{s.subtype}" for s in specs)),
    }
    stats["v1_outcomes"] = [{"type": k[0], "reason": k[1], "count": v} for k, v in stats["v1_outcomes"].items()]
    return specs, {"stats": stats, "per_spec": outcome}
