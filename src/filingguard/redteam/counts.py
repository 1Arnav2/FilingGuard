"""Item counts per attack type (EVAL §2) and the D-021 rule for a short `restated` type."""

ATTACK_TYPES = (
    "control", "unanswerable", "unit_trap", "period_mismatch", "restated", "false_premise", "injection",
)
PLANNED = {
    "control": 60, "unanswerable": 40, "unit_trap": 40, "period_mismatch": 40,
    "restated": 40, "false_premise": 40, "injection": 40,
}
TOTAL = 300
CANDIDATES = 400  # phrased candidates across all types (D-025)


def allocate_counts(restated: int) -> dict[str, int]:
    """Final counts when `restated` has fewer than 40 items.

    The shortfall is spread evenly over the five types other than `control` and `restated`;
    any remainder goes to the earliest of them in table order. The total stays at 300.
    """
    if not 0 <= restated <= PLANNED["restated"]:
        raise ValueError(f"restated count {restated} outside 0..{PLANNED['restated']}")
    others = [t for t in ATTACK_TYPES if t not in ("control", "restated")]
    base, extra = divmod(PLANNED["restated"] - restated, len(others))
    counts = dict(PLANNED, restated=restated)
    for i, t in enumerate(others):
        counts[t] += base + (1 if i < extra else 0)
    assert sum(counts.values()) == TOTAL
    return counts


def candidate_counts(final: dict[str, int], total: int = CANDIDATES) -> dict[str, int]:
    """Candidates to phrase per type: `restated` uses every selected pair once; `control` gets
    a third more than its final count; the rest of `total` is split over the other types in
    proportion to their final counts (largest remainder)."""
    out = {"restated": final["restated"], "control": round(final["control"] * 4 / 3)}
    rest = [t for t in ATTACK_TYPES if t not in out]
    budget = total - sum(out.values())
    weight = sum(final[t] for t in rest)
    exact = {t: budget * final[t] / weight for t in rest}
    out.update({t: int(v) for t, v in exact.items()})
    for t in sorted(rest, key=lambda t: (-(exact[t] - int(exact[t])), ATTACK_TYPES.index(t)))[: total - sum(out.values())]:
        out[t] += 1
    return {t: out[t] for t in ATTACK_TYPES}
