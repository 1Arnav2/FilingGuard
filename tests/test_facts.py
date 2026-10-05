from filingguard.data.facts import (
    find_restatements,
    is_rounding,
    is_split_adjustment,
    map_concepts,
    normalise_company_facts,
)
from filingguard.data.filings import Filing

LATEST = Filing("ACME", 1, "A-26", "10-K", "2026-02-01", "2025-12-31", "acme.htm")
PRIOR = Filing("ACME", 1, "A-25", "10-K", "2025-02-01", "2024-12-31", "acme24.htm")
OLDER = Filing("ACME", 1, "A-24", "10-K", "2024-02-01", "2023-12-31", "acme23.htm")


def entry(val, end, accn, start=None, form="10-K", fy=2025):
    e = {"end": end, "val": val, "accn": accn, "fy": fy, "fp": "FY", "form": form, "filed": "2026-02-01"}
    if start:
        e["start"] = start
    return e


def facts(gaap):
    return {"facts": {"us-gaap": {c: {"units": {"USD": rows}} for c, rows in gaap.items()}}}


def test_keeps_only_original_10k_and_names_filing_fields():
    df = normalise_company_facts("ACME", 1, facts({
        "Assets": [entry(10, "2025-12-31", "A-26"), entry(11, "2025-12-31", "Q", form="10-Q")],
    }))
    assert len(df) == 1
    assert {"filing_fy", "filing_fp"} <= set(df.columns)
    assert df["period_start"].isna().all()


def test_revenue_prefers_primary_then_fallback_then_unmapped():
    annual = dict(start="2025-01-01", end="2025-12-31", accn="A-26")
    primary = normalise_company_facts("ACME", 1, facts({
        "Revenues": [entry(5, **annual)],
        "RevenuesNetOfInterestExpense": [entry(4, **annual)],
    }))
    assert map_concepts(primary, LATEST)["Revenue"] == "Revenues"
    assert map_concepts(primary, LATEST)["revenue_status"] == "primary"

    fallback = normalise_company_facts("ACME", 1, facts({"RevenuesNetOfInterestExpense": [entry(4, **annual)]}))
    assert map_concepts(fallback, LATEST)["revenue_status"] == "fallback"

    quarterly_only = normalise_company_facts("ACME", 1, facts({
        "Revenues": [entry(1, start="2025-10-01", end="2025-12-31", accn="A-26")],
    }))
    mapped = map_concepts(quarterly_only, LATEST)
    assert mapped["Revenue"] is None and mapped["revenue_status"] == "unmapped"


def test_finds_changed_values_between_prior_and_latest():
    df = normalise_company_facts("ACME", 1, facts({
        "Revenues": [
            entry(100, "2024-12-31", "A-25", start="2024-01-01"),
            entry(103, "2024-12-31", "A-26", start="2024-01-01"),
            entry(120, "2025-12-31", "A-26", start="2025-01-01"),
        ],
        "Assets": [entry(50, "2024-12-31", "A-25"), entry(50, "2024-12-31", "A-26"), entry(60, "2025-12-31", "A-26")],
    }))
    pairs = find_restatements(df, [LATEST, PRIOR], map_concepts(df, LATEST))
    assert len(pairs) == 1
    pair = pairs[0]
    assert pair["concept"] == "Revenues"
    assert (pair["original"]["value"], pair["restated"]["value"]) == (100, 103)
    assert abs(pair["rel_change"] - 0.03) < 1e-12
    assert pair["kind"] == "reclassification"  # net income and equity unchanged


def test_rounding_is_not_a_restatement():
    # XOM R&D: 879m in the original 10-K, tagged as $0.9bn in the next one.
    assert is_rounding(879_000_000, 900_000_000)
    assert is_rounding(987_000_000, 1_000_000_000)
    assert is_rounding(1_000_000_000, 987_000_000)
    # BAC revenue: a real change, both precise to the million.
    assert not is_rounding(98_581_000_000, 102_769_000_000)
    # Same trailing zeros on both sides: not a precision change.
    assert not is_rounding(26_515_000_000, 26_305_000_000)
    # Rounds to a different value: a real change.
    assert not is_rounding(879_000_000, 800_000_000)
    # Per-share values never count as rounding.
    assert not is_rounding(3.10, 3.07)


def test_instant_values_are_compared_too():
    df = normalise_company_facts("ACME", 1, facts({
        "Revenues": [entry(1, "2025-12-31", "A-26", start="2025-01-01")],
        "Assets": [entry(50, "2024-12-31", "A-25"), entry(55, "2024-12-31", "A-26"), entry(60, "2025-12-31", "A-26")],
    }))
    pairs = find_restatements(df, [LATEST, PRIOR], map_concepts(df, LATEST))
    assert [(p["concept"], p["original"]["value"], p["restated"]["value"]) for p in pairs] == [("Assets", 50, 55)]


def test_consecutive_filings_across_three_10ks_and_kinds():
    year = dict(start="2023-01-01")
    df = normalise_company_facts("ACME", 1, facts({
        # Changed between the oldest and the middle filing, with net income: a restatement.
        "Revenues": [entry(100, "2023-12-31", "A-24", **year), entry(104, "2023-12-31", "A-25", **year),
                     entry(104, "2023-12-31", "A-26", **year), entry(130, "2025-12-31", "A-26", start="2025-01-01")],
        "NetIncomeLoss": [entry(10, "2023-12-31", "A-24", **year), entry(11, "2023-12-31", "A-25", **year),
                          entry(13, "2025-12-31", "A-26", start="2025-01-01")],
        # A 10-for-1 split between the middle and the latest filing.
        "EarningsPerShareBasic": [entry(12.05, "2024-12-31", "A-25", start="2024-01-01"),
                                  entry(1.21, "2024-12-31", "A-26", start="2024-01-01"),
                                  entry(1.5, "2025-12-31", "A-26", start="2025-01-01")],
    }))
    pairs = find_restatements(df, [LATEST, PRIOR, OLDER], map_concepts(df, LATEST))
    got = sorted((p["concept"], p["original"]["accession"], p["restated"]["accession"], p["kind"]) for p in pairs)
    assert got == [
        ("EarningsPerShareBasic", "A-25", "A-26", "stock_split"),
        ("NetIncomeLoss", "A-24", "A-25", "restatement"),
        ("Revenues", "A-24", "A-25", "restatement"),
    ]


def test_two_values_in_one_filing_make_a_pair_ambiguous():
    df = normalise_company_facts("ACME", 1, facts({
        "Revenues": [entry(1, "2025-12-31", "A-26", start="2025-01-01")],
        "Assets": [entry(50, "2024-12-31", "A-25"), entry(55, "2024-12-31", "A-26"), entry(56, "2024-12-31", "A-26"),
                   entry(60, "2025-12-31", "A-26")],
    }))
    pairs = find_restatements(df, [LATEST, PRIOR], map_concepts(df, LATEST))
    assert {p["kind"] for p in pairs} == {"ambiguous"}


def test_split_adjustment_needs_a_whole_ratio_on_a_per_share_concept():
    assert is_split_adjustment("EarningsPerShareBasic", 1.76, 0.18)  # NVDA, rounded to the cent
    assert is_split_adjustment("EarningsPerShareDiluted", 11.93, 1.19)
    assert not is_split_adjustment("EarningsPerShareBasic", 3.10, 3.07)
    assert not is_split_adjustment("EarningsPerShareBasic", 3.0, 2.0)  # ratio 1.5
    assert not is_split_adjustment("Revenues", 100.0, 10.0)
