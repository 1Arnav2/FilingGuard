"""From phrased candidates to the draft test set: filter, select, split, latency sample,
review sample. Every step is deterministic given the seed; no model calls.

The draft is not frozen. Freezing happens after the owner's review is applied and the
scoring rules are approved (D-026, D-028).
"""

import random
import re
from collections import Counter, defaultdict
from collections.abc import Callable

from filingguard.redteam.counts import ATTACK_TYPES
from filingguard.redteam.spec import ItemSpec

DEV_SHARE = 0.3
DEV_TOTAL = 90
LATENCY_SAMPLE = 30
REVIEW_SAMPLE = 60
NEAR_DUPLICATE_JACCARD = 0.9
UNANSWERABLE_SUBTYPE_CAP = 0.5   # no subtype supplies more than half (D-028)


def largest_remainder(weights: dict[str, float], total: int) -> dict[str, int]:
    """Integer shares of `total` proportional to `weights`, ties broken by key order."""
    s = sum(weights.values())
    exact = {k: total * w / s for k, w in weights.items()}
    out = {k: int(v) for k, v in exact.items()}
    keys = list(weights)
    for k in sorted(keys, key=lambda k: (-(exact[k] - out[k]), keys.index(k)))[: total - sum(out.values())]:
        out[k] += 1
    return out


def _tokens(question: str) -> set[str]:
    return set(re.findall(r"[a-z0-9']+", question.lower()))


def near_duplicates(specs: list[ItemSpec], questions: dict[str, str]) -> set[str]:
    """Spec ids whose question is near-identical to an earlier one for the same company."""
    dropped, seen = set(), defaultdict(list)
    for s in specs:
        toks = _tokens(questions[s.spec_id])
        if any(len(toks & t) / len(toks | t) >= NEAR_DUPLICATE_JACCARD for t in seen[s.company]):
            dropped.add(s.spec_id)
        else:
            seen[s.company].append(toks)
    return dropped


def spread_by_company(specs: list[ItemSpec], rng: random.Random, company_order: list[str]) -> list[ItemSpec]:
    """Seeded order that takes one spec per company in turn, so a prefix spreads across companies.

    The company rotation itself is shuffled; a fixed rotation made every short prefix start
    with the same six tech companies (H-010).
    """
    by_company = defaultdict(list)
    shuffled = specs[:]
    rng.shuffle(shuffled)
    for s in shuffled:
        by_company[s.company].append(s)
    rotation = company_order[:]
    rng.shuffle(rotation)
    order = []
    while any(by_company.values()):
        for c in rotation:
            if by_company[c]:
                order.append(by_company[c].pop(0))
    return order


def select(specs: list[ItemSpec], counts: dict[str, int], rng: random.Random,
           company_order: list[str]) -> list[ItemSpec]:
    """Pick each type's final count, spread across companies.

    `unanswerable` keeps every `untagged_concept` item, then fills alternately from the other
    subtypes with no subtype above half of the type's count.
    """
    chosen = []
    for t in ATTACK_TYPES:
        pool = spread_by_company([s for s in specs if s.attack_type == t], rng, company_order)
        if t != "unanswerable":
            take = pool[: counts[t]]
        else:
            take = _select_unanswerable(pool, counts[t])
        if len(take) < counts[t]:
            raise RuntimeError(f"{t}: only {len(take)} of {counts[t]} after filtering")
        chosen += take
    return chosen


def _select_unanswerable(pool: list[ItemSpec], n: int) -> list[ItemSpec]:
    cap = int(n * UNANSWERABLE_SUBTYPE_CAP)
    take = [s for s in pool if s.subtype == "untagged_concept"][:cap]
    rest = {sub: [s for s in pool if s.subtype == sub] for sub in ("single_quarter", "old_period")}
    used = {sub: 0 for sub in rest}
    while len(take) < n and any(used[sub] < min(cap, len(rest[sub])) for sub in rest):
        for sub in rest:
            if len(take) < n and used[sub] < min(cap, len(rest[sub])):
                take.append(rest[sub][used[sub]])
                used[sub] += 1
    return take


def assign_ids(items: list[ItemSpec], company_order: list[str]) -> dict[str, str]:
    """FG-0001.. in type order, then company order, then spec id."""
    ordered = sorted(items, key=lambda s: (ATTACK_TYPES.index(s.attack_type), company_order.index(s.company), s.spec_id))
    return {s.spec_id: f"FG-{i:04d}" for i, s in enumerate(ordered, start=1)}


def _systematic(n: int, k: int) -> set[int]:
    """k positions spread evenly over range(n)."""
    return {i for i in range(n) if (i + 1) * k // n > i * k // n}


def assign_split(items: list[ItemSpec], rng: random.Random, company_order: list[str],
                 dev_total: int = DEV_TOTAL) -> dict[str, str]:
    """Dev or test per spec id: 30% of each type to dev (exactly 90 overall), spread evenly
    across companies within the type."""
    counts = {t: sum(s.attack_type == t for s in items) for t in ATTACK_TYPES}
    dev = largest_remainder({t: c * DEV_SHARE for t, c in counts.items() if c}, dev_total)
    split = {}
    for t in ATTACK_TYPES:
        typed = [s for s in items if s.attack_type == t]
        keyed = {s.spec_id: rng.random() for s in sorted(typed, key=lambda s: s.spec_id)}
        typed.sort(key=lambda s: (company_order.index(s.company), keyed[s.spec_id]))
        dev_pos = _systematic(len(typed), dev.get(t, 0))
        split.update({s.spec_id: "dev" if i in dev_pos else "test" for i, s in enumerate(typed)})
    return split


MIN_REVIEW_COMPANIES = 20


def coverage_problems(sample: list[ItemSpec], sector_of: dict[str, str]) -> list[str]:
    """Ways a review sample fails the coverage rule: at least 20 companies, every sector, and
    every financial company (H-010)."""
    companies = {s.company for s in sample}
    problems = []
    if len(companies) < MIN_REVIEW_COMPANIES:
        problems.append(f"{len(companies)} companies, need {MIN_REVIEW_COMPANIES}")
    missing_sectors = set(sector_of.values()) - {sector_of[c] for c in companies}
    if missing_sectors:
        problems.append(f"missing sectors {sorted(missing_sectors)}")
    missing_fin = {t for t, sec in sector_of.items() if sec == "Financials"} - companies
    if missing_fin:
        problems.append(f"missing financials {sorted(missing_fin)}")
    return problems


def stratified_sample(items: list[ItemSpec], n: int, rng: random.Random, sector_of: dict[str, str],
                      strata: Callable[[ItemSpec], str]) -> list[ItemSpec]:
    """`n` items with each stratum's share proportional to its size, balanced across companies
    and sectors over the whole sample.

    Strata are filled smallest first (they have the fewest companies to choose from). Each pick
    takes the item whose company, then sector, is least used in the sample so far, with seeded
    tie-breaks (H-010).
    """
    groups = defaultdict(list)
    for s in items:
        groups[strata(s)].append(s)
    keys = sorted(groups, key=lambda k: (ATTACK_TYPES.index(k.split("|")[0]), k))
    quota = largest_remainder({k: len(groups[k]) for k in keys}, n)
    by_company: Counter = Counter()
    by_sector: Counter = Counter()
    out = []
    for k in sorted(keys, key=lambda k: (len({s.company for s in groups[k]}), keys.index(k))):
        pool = sorted(groups[k], key=lambda s: s.spec_id)
        rng.shuffle(pool)
        for _ in range(quota[k]):
            pick = min(pool, key=lambda s: (by_company[s.company], by_sector[sector_of[s.company]]))
            pool.remove(pick)
            by_company[pick.company] += 1
            by_sector[sector_of[pick.company]] += 1
            out.append(pick)
    return out
