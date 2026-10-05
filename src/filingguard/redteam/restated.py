"""Select the restated pairs that become `restated` items (D-021)."""

import random
from collections import defaultdict

from filingguard.data.facts import USABLE_KINDS

MAX_ITEMS = 40


def capped_total(per_company: dict[str, int], max_items: int = MAX_ITEMS) -> int:
    """Largest item count N <= max_items in which no company supplies more than N // 2."""
    for n in range(min(max_items, sum(per_company.values())), 0, -1):
        if sum(min(c, n // 2) for c in per_company.values()) >= n:
            return n
    return 0


def _spread(pairs: list[dict], rng: random.Random) -> list[dict]:
    """Seeded order that cycles through concepts, so a trimmed company keeps variety."""
    shuffled = pairs[:]
    rng.shuffle(shuffled)
    by_concept: dict[str, list[dict]] = defaultdict(list)
    for p in shuffled:
        by_concept[p["concept"]].append(p)
    order = []
    while any(by_concept.values()):
        for concept in sorted(by_concept):
            if by_concept[concept]:
                order.append(by_concept[concept].pop(0))
    return order


def select_pairs(pairs: list[dict], seed: int) -> list[dict]:
    """Usable pairs kept as items, each with the filing the question asks about.

    Applies the half-per-company cap, trims over-cap companies across concepts, and picks by
    seed whether each item asks for the originally reported or the later value (`ask`).
    """
    rng = random.Random(seed)
    usable = [p for p in pairs if p["kind"] in USABLE_KINDS]
    by_company: dict[str, list[dict]] = defaultdict(list)
    for p in usable:
        by_company[p["ticker"]].append(p)
    n = capped_total({t: len(ps) for t, ps in by_company.items()})
    take = {t: min(len(ps), n // 2) for t, ps in by_company.items()}
    # Trim the largest takes first until the total is exactly n.
    while sum(take.values()) > n:
        largest = max(sorted(take), key=lambda t: take[t])
        take[largest] -= 1
    kept = []
    for ticker in sorted(by_company):
        for p in _spread(by_company[ticker], rng)[: take[ticker]]:
            kept.append(p | {"ask": rng.choice(["original", "restated"])})
    return kept
