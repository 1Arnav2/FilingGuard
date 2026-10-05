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
    subtypes with no subtype above half of the type's count. `period_mismatch` takes every
    `start_month` item up to half the type, then fills with `calendar_wording` (D-034).
    """
    chosen = []
    for t in ATTACK_TYPES:
        pool = spread_by_company([s for s in specs if s.attack_type == t], rng, company_order)
        if t == "unanswerable":
            take = _select_unanswerable(pool, counts[t])
        elif t == "period_mismatch":
            starts = [s for s in pool if s.subtype == "start_month"][: counts[t] // 2]
            take = _alternate(pool, counts[t], ("calendar_wording",), counts[t], starts)
        else:
            take = pool[: counts[t]]
        if len(take) < counts[t]:
            raise RuntimeError(f"{t}: only {len(take)} of {counts[t]} after filtering")
        chosen += take
    return chosen


def _select_unanswerable(pool: list[ItemSpec], n: int) -> list[ItemSpec]:
    cap = int(n * UNANSWERABLE_SUBTYPE_CAP)
    first = [s for s in pool if s.subtype == "untagged_concept"][:cap]
    return _alternate(pool, n, ("single_quarter", "old_period"), cap, first)


def _alternate(pool: list[ItemSpec], n: int, subtypes: tuple[str, ...], cap: int, take: list[ItemSpec]) -> list[ItemSpec]:
    """Append items from `subtypes` in turn to `take` until it holds `n`, at most `cap` each."""
    take = list(take)
    rest = {sub: [s for s in pool if s.subtype == sub] for sub in subtypes}
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


DRIVERS_IN_CONTROLS = 10   # true-premise driver controls among the 60 (D-041)


def _sector_balanced(pool: list[ItemSpec], n: int, sector_of: dict[str, str]) -> list[ItemSpec]:
    """`n` items from `pool` (in its order), at most one per company, cycling through sectors."""
    by_sector: dict[str, list[ItemSpec]] = defaultdict(list)
    for s in pool:
        by_sector[sector_of[s.company]].append(s)
    take, companies = [], set()
    while len(take) < n and any(by_sector.values()):
        for sector in sorted(by_sector):
            while by_sector[sector] and by_sector[sector][0].company in companies:
                by_sector[sector].pop(0)
            if by_sector[sector] and len(take) < n:
                s = by_sector[sector].pop(0)
                take.append(s)
                companies.add(s.company)
    return take



def sticky_select(specs: list[ItemSpec], counts: dict[str, int], rng: random.Random, company_order: list[str],
                  previous: dict[str, tuple[str, str]], sector_of: dict[str, str]) -> tuple[list[ItemSpec], dict]:
    """Like `select`, but keeps every previously selected item (`previous`: spec id -> (type,
    subtype)) that is still available, and fills each freed slot from the same type and, where
    the pool allows, the same subtype (D-041). Controls take 10 true-premise drivers, one per
    company across sectors; the regular controls they displace are dropped from the driver
    companies first. Returns the items and a per-type record."""
    chosen, record = [], {}
    for t in ATTACK_TYPES:
        pool = spread_by_company([s for s in specs if s.attack_type == t], rng, company_order)
        n, take = counts[t], []
        if t == "control":
            take = _sector_balanced([s for s in pool if s.subtype == "true_premise_driver"], DRIVERS_IN_CONTROLS, sector_of)
            driver_companies = {s.company for s in take}
            pool = [s for s in pool if s.subtype != "true_premise_driver"]
            kept = sorted((s for s in pool if s.spec_id in previous), key=lambda s: s.company in driver_companies)
        else:
            kept = [s for s in pool if s.spec_id in previous]
        kept = kept[: n - len(take)]
        take += kept
        taken = {s.spec_id for s in take}
        left = Counter(sub for sid, (typ, sub) in previous.items() if typ == t and sid not in taken)
        free = [s for s in pool if s.spec_id not in taken]
        for s in free:   # like for like: the subtypes of the items that left
            if len(take) < n and left[s.subtype] > 0:
                take.append(s)
                taken.add(s.spec_id)
                left[s.subtype] -= 1
        for s in free:   # then any subtype, if the pool for a subtype ran out
            if len(take) < n and s.spec_id not in taken:
                take.append(s)
                taken.add(s.spec_id)
        if len(take) < n:
            raise RuntimeError(f"{t}: only {len(take)} of {n} after filtering")
        chosen += take
        record[t] = {"kept_from_previous": len(kept), "by_subtype": dict(Counter(s.subtype for s in take))}
    return chosen, record


def sticky_ids(items: list[ItemSpec], previous_ids: dict[str, str], company_order: list[str]) -> dict[str, str]:
    """Surviving items keep their ID; new items get the next free numbers, in type then company order."""
    ids = {s.spec_id: previous_ids[s.spec_id] for s in items if s.spec_id in previous_ids}
    next_n = 1 + max((int(i.split("-")[1]) for i in previous_ids.values()), default=0)
    new = sorted((s for s in items if s.spec_id not in ids),
                 key=lambda s: (ATTACK_TYPES.index(s.attack_type), company_order.index(s.company), s.spec_id))
    for k, s in enumerate(new):
        ids[s.spec_id] = f"FG-{next_n + k:04d}"
    return ids


def revise_sample(previous: list[str], items: list[ItemSpec], split: dict[str, str], rng: random.Random,
                  sector_of: dict[str, str], previous_types: dict[str, tuple[str, str]]) -> tuple[list[ItemSpec], list[dict]]:
    """The previous review sample with only its departed rows swapped, each for an item of the
    same type, least-used company and then sector first."""
    by_id = {s.spec_id: s for s in items}
    sample = [by_id[sid] for sid in previous if sid in by_id]
    by_company = Counter(s.company for s in sample)
    by_sector = Counter(sector_of[s.company] for s in sample)
    in_sample = {s.spec_id for s in sample}
    swaps = []
    for sid in previous:
        if sid in by_id:
            continue
        typ, _ = previous_types[sid]
        pool = [s for s in items if s.attack_type == typ and s.spec_id not in in_sample]
        rng.shuffle(pool)
        pick = min(pool, key=lambda s: (by_company[s.company], by_sector[sector_of[s.company]]))
        sample.append(pick)
        in_sample.add(pick.spec_id)
        by_company[pick.company] += 1
        by_sector[sector_of[pick.company]] += 1
        swaps.append({"old_spec_id": sid, "new_spec_id": pick.spec_id, "type": typ})
    return sample, swaps
