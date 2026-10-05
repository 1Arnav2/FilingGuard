"""Build the red-team test set.

    python -m filingguard.redteam.build candidates      # v1 specs (committed; never overwritten)
    python -m filingguard.redteam.build revise          # v2: v1 revised after the first review, plus replacements
    python -m filingguard.redteam.build phrase --pilot  # one phrasing call (first batch of v1)
    python -m filingguard.redteam.build phrase          # phrase every v2 spec without a question yet
    python -m filingguard.redteam.build assemble        # filter, select, split, latency IDs, review sheet
    python -m filingguard.redteam.build review-apply    # read the owner's decisions back

Candidates and gold go under `data/gold/`, which only the red-team and `eval/` read. The
draft test set goes to `data/testset/draft/`; it is frozen only after review (D-028).
"""

import argparse
import json
import random
from pathlib import Path

from filingguard.data.filings import COMPANIES
from filingguard.redteam import assemble as asm
from filingguard.redteam.counts import ATTACK_TYPES, allocate_counts, candidate_counts
from filingguard.redteam.corpus import Corpus
from filingguard.redteam.generators import GENERATORS
from filingguard.redteam.generators.common import GenContext
from filingguard.redteam.phrasing import BATCH_SIZE, check_question, phrase_batch
from filingguard.redteam.generators.restated import usable_pairs
from filingguard.redteam.restated import select_pairs
from filingguard.redteam.spec import ItemSpec

SEED = 20261004
OUT = Path("data/gold/candidates")
DRAFT_ITEMS = Path("data/testset/draft")
DRAFT_GOLD = Path("data/gold/draft")
CANDIDATES = OUT / "candidates_v2.jsonl"
PHRASED = OUT / "phrased_v2.jsonl"
REVIEW_BOOK = Path("review/review_v2.xlsx")   # v1 was halted at the first pass (H-009)
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


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def generate_candidates(corpus: Corpus, seed: int = SEED) -> tuple[list[ItemSpec], dict]:
    """Every candidate spec, in a seeded order that mixes attack types, plus generation stats."""
    final = allocate_counts(len(select_pairs(usable_pairs(corpus), seed)))
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


def phrase(llm, specs: list[ItemSpec], existing: dict[str, dict], max_batches: int | None = None) -> list[dict]:
    """Phrase every spec that has no question in `existing`, 10 per call, in spec order.

    Specs already phrased keep their row, so changing some briefs re-phrases only those.
    """
    todo = [s for s in specs if s.spec_id not in existing]
    groups = [todo[i:i + BATCH_SIZE] for i in range(0, len(todo), BATCH_SIZE)][:max_batches]
    rows = dict(existing)
    first = 1 + max((r["batch"] for r in existing.values()), default=-1)
    for n, batch in enumerate(groups, start=first):
        questions, meta = phrase_batch(llm, batch)
        for spec in batch:
            q = questions.get(spec.spec_id)
            rows[spec.spec_id] = {"spec_id": spec.spec_id, "batch": n, "question": q,
                                  "problems": check_question(spec, q), "call": meta}
    return [rows[s.spec_id] for s in specs if s.spec_id in rows]


def injection_delivery(specs: list[ItemSpec], questions: dict[str, str]) -> dict[str, int | None]:
    """Rank of the poisoned chunk in the frozen retriever's top 20 for each injection item's
    question, searched over a sandbox copy of the index (None = not delivered)."""
    from filingguard.data.index import VectorIndex, fastembed_fn
    from filingguard.redteam.injection import sandbox_retriever

    embed = fastembed_fn()
    index = VectorIndex.load(Path("data/processed/index"), embed)
    ranks = {}
    for s in specs:
        if s.attack_type != "injection":
            continue
        hits = sandbox_retriever(index, s.injection, embed).retrieve(questions[s.spec_id], s.company, 20)
        ranks[s.spec_id] = next((h.rank for h in hits if h.chunk["chunk_id"] == s.injection["chunk_id"]), None)
    return ranks


def _by_type(specs: list[ItemSpec], extra: dict[str, str] | None = None) -> dict:
    if extra is None:
        return {t: sum(s.attack_type == t for s in specs) for t in ATTACK_TYPES}
    return {t: {v: sum(1 for s in specs if s.attack_type == t and extra[s.spec_id] == v) for v in ("dev", "test")}
            for t in ATTACK_TYPES}


def assemble_draft(seed: int = SEED) -> dict:
    """Filter, select, split, and write the draft set, latency IDs and review workbook."""
    from filingguard.redteam.review import write_workbook

    corpus = Corpus()
    companies = list(corpus.companies)
    specs = [ItemSpec(**row) for row in _read_jsonl(CANDIDATES)]
    phrased = {r["spec_id"]: r for r in _read_jsonl(PHRASED)}
    questions = {k: r["question"] for k, r in phrased.items()}

    failed = {s.spec_id for s in specs if s.spec_id not in phrased or phrased[s.spec_id]["problems"]}
    passing = [s for s in specs if s.spec_id not in failed]
    dupes = asm.near_duplicates(passing, questions)
    passing = [s for s in passing if s.spec_id not in dupes]
    ranks = injection_delivery(passing, questions)
    undelivered = {k for k, r in ranks.items() if r is None}
    passing = [s for s in passing if s.spec_id not in undelivered]

    counts = allocate_counts(sum(s.attack_type == "restated" for s in specs))
    dropped_v1 = _dropped_draft_items(corpus)
    items = asm.select(passing, counts, random.Random(f"{seed}-select"), companies)
    ids = asm.assign_ids(items, companies)
    split = asm.assign_split(items, random.Random(f"{seed}-split"), companies)
    items.sort(key=lambda s: ids[s.spec_id])

    test = [s for s in items if split[s.spec_id] == "test"]
    latency = asm.stratified_sample(test, asm.LATENCY_SAMPLE, random.Random(f"{seed}-latency"), COMPANIES,
                                    lambda s: s.attack_type)
    sample = asm.stratified_sample(items, asm.REVIEW_SAMPLE, random.Random(f"{seed}-review"), COMPANIES,
                                   lambda s: f"{s.attack_type}|{split[s.spec_id]}")
    problems = asm.coverage_problems(sample, COMPANIES)
    if problems:
        raise RuntimeError(f"review sample is not stratified enough: {problems}")
    in_sample = {s.spec_id for s in sample}
    extra = [s for s in items if s.spec_id not in in_sample and (
        s.subtype == "untagged_concept")]

    _write_jsonl(DRAFT_ITEMS / "items_v1.jsonl", [
        {"id": ids[s.spec_id], "company": s.company, "attack_type": s.attack_type, "subtype": s.subtype,
         "question": questions[s.spec_id], "split": split[s.spec_id], "injection": s.injection} for s in items])
    _write_jsonl(DRAFT_GOLD / "gold_v1.jsonl", [
        {"id": ids[s.spec_id], "spec_id": s.spec_id, "expected_behavior": s.expected_behavior, "gold": s.gold,
         "source": s.source, "evidence": s.evidence, "human_checked": False} for s in items])
    latency_ids = sorted(ids[s.spec_id] for s in latency)
    _write_json(DRAFT_ITEMS / "latency_sample_v1.json",
                {"seed": f"{seed}-latency", "split": "test", "ids": latency_ids, "by_type": _by_type(latency)})
    rows = lambda group: [(ids[s.spec_id], s, questions[s.spec_id], split[s.spec_id])
                          for s in sorted(group, key=lambda s: ids[s.spec_id])]
    write_workbook(REVIEW_BOOK, rows(sample), rows(extra), corpus)

    stats = {
        "seed": seed, "candidates": len(specs), "failed_checks": len(failed), "near_duplicates": len(dupes),
        "injection_not_delivered": len(undelivered), "passing_by_type": _by_type(passing),
        "final_counts": _by_type(items), "split": _by_type(items, split),
        "unanswerable_by_subtype": {sub: sum(1 for s in items if s.attack_type == "unanswerable" and s.subtype == sub)
                                    for sub in ("untagged_concept", "single_quarter", "old_period")},
        "companies_per_type": {t: len({s.company for s in items if s.attack_type == t}) for t in ATTACK_TYPES},
        "review_sample_by_type": _by_type(sample, split),
        "review_extra": sorted(ids[s.spec_id] for s in extra),
        "v1_draft_items_dropped": dropped_v1,
        "latency_sample": latency_ids,
        "review_sample": sorted(ids[s.spec_id] for s in sample),
        "injection_delivery_rank": {ids[k]: r for k, r in ranks.items() if k in ids},
    }
    _write_json(DRAFT_GOLD / "assembly_v2.json", stats)
    return stats


def _dropped_draft_items(corpus: Corpus) -> list[dict]:
    """The v1 draft items that the v2 rules removed, with the reason (for BUILD_LOG)."""
    from filingguard.redteam.revise import revise_one

    v1 = {r["spec_id"]: ItemSpec(**r) for r in _read_jsonl(OUT / "candidates_v1.jsonl")}
    out = []
    for g in _read_jsonl(DRAFT_GOLD / "first_review" / "gold_v1.jsonl"):
        revised, reason = revise_one(corpus, v1[g["spec_id"]])
        if revised is None and not reason.startswith(("restated pairs", "fiscal_label")):
            out.append({"v1_id": g["id"], "type": v1[g["spec_id"]].attack_type, "company": v1[g["spec_id"]].company,
                        "reason": reason})
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=["candidates", "revise", "phrase", "assemble", "review-apply"])
    parser.add_argument("--pilot", action="store_true", help="phrase only the first batch")
    args = parser.parse_args()

    if args.step == "candidates":
        if (OUT / "candidates_v1.jsonl").exists():
            raise SystemExit("candidates_v1.jsonl is a committed record; v2 comes from `revise`")
        specs, stats = generate_candidates(Corpus())
        _write_jsonl(OUT / "candidates_v1.jsonl", [s.to_dict() for s in specs])
        _write_json(OUT / "candidates_v1_stats.json", stats)
        print(json.dumps(stats, indent=2))
    elif args.step == "revise":
        from filingguard.redteam.revise import revise

        v1 = [ItemSpec(**row) for row in _read_jsonl(OUT / "candidates_v1.jsonl")]
        specs, record = revise(Corpus(), v1, SEED)
        _write_jsonl(CANDIDATES, [s.to_dict() for s in specs])
        _write_json(OUT / "candidates_v2_revision.json", record)
        print(json.dumps(record["stats"], indent=2))
    elif args.step == "phrase":
        from filingguard.llm.client import client_from_env

        if args.pilot:
            specs = [ItemSpec(**row) for row in _read_jsonl(OUT / "candidates_v1.jsonl")]
            rows = phrase(client_from_env("TARGET_MODEL"), specs, {}, 1)
            _write_jsonl(OUT / "phrased_pilot_v1.jsonl", rows)
        else:
            specs = [ItemSpec(**row) for row in _read_jsonl(CANDIDATES)]
            # Questions already phrased for an identical spec (same id) are reused, never re-asked.
            existing = {r["spec_id"]: r for path in (OUT / "phrased_v1.jsonl", PHRASED) if path.exists()
                        for r in _read_jsonl(path)}
            rows = phrase(client_from_env("TARGET_MODEL"), specs, existing)
            _write_jsonl(PHRASED, rows)
        print(json.dumps({"phrased": len(rows), "failed_checks": sum(bool(r["problems"]) for r in rows)}, indent=2))
    elif args.step == "assemble":
        stats = assemble_draft()
        skip = ("latency_sample", "review_sample", "injection_delivery_rank")
        print(json.dumps({k: v for k, v in stats.items() if k not in skip}, indent=2))
    else:
        from filingguard.redteam.review import fault_rate, read_decisions

        decisions = read_decisions(REVIEW_BOOK)
        _write_json(DRAFT_GOLD / "review_v2.json", decisions)
        print(json.dumps({"fault_rate_sample": fault_rate(decisions["Fault-rate sample"]),
                          "extra_checks": fault_rate(decisions["Extra checks"]) | {"counts_toward_fault_rate": False}},
                         indent=2))


if __name__ == "__main__":
    main()
