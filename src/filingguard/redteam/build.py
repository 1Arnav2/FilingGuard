"""Build red-team candidates and phrase them.

    python -m filingguard.redteam.build candidates      # deterministic specs, no model calls
    python -m filingguard.redteam.build phrase --pilot  # one phrasing call (first batch)
    python -m filingguard.redteam.build phrase          # every batch (cached batches cost nothing)

Outputs go to `data/gold/candidates/`, which only the red-team and `eval/` read.
"""

import argparse
import json
import random
from pathlib import Path

from filingguard.redteam.counts import ATTACK_TYPES, allocate_counts, candidate_counts
from filingguard.redteam.corpus import Corpus
from filingguard.redteam.generators import GENERATORS
from filingguard.redteam.generators.common import GenContext
from filingguard.redteam.phrasing import BATCH_SIZE, check_question, phrase_batch
from filingguard.redteam.restated import select_pairs
from filingguard.redteam.spec import ItemSpec

SEED = 20261004
OUT = Path("data/gold/candidates")
# Types with the scarcest facts claim theirs first; control takes from what is left.
GENERATION_ORDER = ("restated", "false_premise", "injection", "unit_trap", "period_mismatch", "control", "unanswerable")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def generate_candidates(corpus: Corpus, seed: int = SEED) -> tuple[list[ItemSpec], dict]:
    """Every candidate spec, in a seeded order that mixes attack types, plus generation stats."""
    final = allocate_counts(len(select_pairs(corpus.pairs, seed)))
    wanted = candidate_counts(final)
    ctx = GenContext(corpus, random.Random(seed), seed)
    specs: list[ItemSpec] = []
    for t in GENERATION_ORDER:
        made = GENERATORS[t](ctx, wanted[t])
        if len(made) < wanted[t]:
            raise RuntimeError(f"{t}: {len(made)} candidates, {wanted[t]} wanted")
        specs += made
    random.Random(seed).shuffle(specs)
    stats = {"seed": seed, "final_counts": final, "candidate_counts": wanted, **ctx.stats}
    return specs, stats


def phrase(llm, specs: list[ItemSpec], batches: int | None) -> list[dict]:
    """Phrase the first `batches` batches (all if None); one row per spec in those batches."""
    rows = []
    groups = [specs[i:i + BATCH_SIZE] for i in range(0, len(specs), BATCH_SIZE)]
    for n, batch in enumerate(groups[:batches]):
        questions, meta = phrase_batch(llm, batch)
        for spec in batch:
            q = questions.get(spec.spec_id)
            rows.append({"spec_id": spec.spec_id, "batch": n, "question": q, "problems": check_question(spec, q),
                         "call": meta})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=["candidates", "phrase"])
    parser.add_argument("--pilot", action="store_true", help="phrase only the first batch")
    args = parser.parse_args()

    if args.step == "candidates":
        specs, stats = generate_candidates(Corpus())
        _write_jsonl(OUT / "candidates_v1.jsonl", [s.to_dict() for s in specs])
        (OUT / "candidates_v1_stats.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(stats, indent=2))
        return

    from filingguard.llm.client import client_from_env

    specs = [ItemSpec(**row) for row in _read_jsonl(OUT / "candidates_v1.jsonl")]
    rows = phrase(client_from_env("TARGET_MODEL"), specs, 1 if args.pilot else None)
    _write_jsonl(OUT / ("phrased_pilot_v1.jsonl" if args.pilot else "phrased_v1.jsonl"), rows)
    by_type = {t: sum(1 for r, s in zip(rows, specs) if s.attack_type == t) for t in ATTACK_TYPES}
    print(json.dumps({"phrased": len(rows), "failed_checks": sum(bool(r["problems"]) for r in rows),
                      "by_type": by_type}, indent=2))


if __name__ == "__main__":
    main()
