"""Spot-check XBRL facts against the 10-K text (ROADMAP Phase 1 done condition).

Picks one current-year fact from each of 10 companies (fixed seed), renders the value the
ways filings print it, and records where it appears in the parsed text. A person reviews
each snippet and records the verdict in `data/processed/spot_check.json`.

Run with `python -m filingguard.data.spot_check`.
"""

import json
import random
from pathlib import Path

import pandas as pd

from filingguard.data.facts import is_annual

PROCESSED = Path("data/processed")
SEED = 20261004
SAMPLE = 10
CONTEXT_CHARS = 160


def renderings(value: float, unit: str) -> list[str]:
    """Strings a 10-K might use for `value`, most specific first."""
    if unit == "USD/shares":
        return [f"{value:.2f}"]
    out = []
    for divisor in (1e6, 1e3, 1):
        scaled = value / divisor
        if abs(scaled - round(scaled)) < 1e-9 or divisor == 1e6:
            n = f"{abs(round(scaled)):,}"
            out.append(f"({n})" if value < 0 else n)
    return out


def find_in_text(text: str, value: float, unit: str) -> dict | None:
    """Return the first rendering found in `text`, with surrounding context."""
    for rendering in renderings(value, unit):
        pos = text.find(rendering)
        if pos != -1:
            lo, hi = max(0, pos - CONTEXT_CHARS), pos + len(rendering) + CONTEXT_CHARS
            return {"rendering": rendering, "offset": pos, "context": text[lo:hi]}
    return None


def sample_facts(facts: pd.DataFrame, filings: list[dict], concept_map: dict) -> list[dict]:
    """One current-year fact per company for SAMPLE companies, chosen with a fixed seed."""
    rng = random.Random(SEED)
    picks = []
    for company in rng.sample(filings, SAMPLE):
        latest = company["latest_10k"]
        concepts = sorted(v for k, v in concept_map[company["ticker"]].items() if k != "revenue_status" and v)
        rows = facts[
            (facts["accession"] == latest["accession"])
            & (facts["period_end"] == latest["report_date"])
            & facts["concept"].isin(concepts)
            & is_annual(facts)
        ].drop_duplicates(subset=["concept", "unit", "period_start", "period_end"])
        row = rows.iloc[rng.randrange(len(rows))]
        picks.append({
            "ticker": company["ticker"],
            "accession": latest["accession"],
            "concept": row["concept"],
            "unit": row["unit"],
            "period_start": row["period_start"],
            "period_end": row["period_end"],
            "value": row["value"],
        })
    return picks


def run(out_dir: Path = PROCESSED) -> list[dict]:
    """Sample facts, search the filing text, and write the results for review."""
    facts = pd.read_parquet(out_dir / "facts.parquet")
    filings = json.loads((out_dir / "filings.json").read_text(encoding="utf-8"))
    concept_map = json.loads((out_dir / "concept_map.json").read_text(encoding="utf-8"))
    results = []
    for pick in sample_facts(facts, filings, concept_map):
        text = (out_dir / "text" / f"{pick['accession']}.txt").read_text(encoding="utf-8")
        match = find_in_text(text, pick["value"], pick["unit"])
        results.append(pick | {"found": match is not None, "match": match, "verdict": None, "note": None})
    path = out_dir / "spot_check.json"
    path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return results


if __name__ == "__main__":
    for r in run():
        ctx = r["match"]["context"].replace("\n", " / ") if r["match"] else "NOT FOUND"
        print(f"\n## {r['ticker']} {r['concept']} {r['period_start']}..{r['period_end']} = {r['value']:,} {r['unit']}\n   {ctx}")
