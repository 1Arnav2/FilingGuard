"""Build the red-team test set.

    python -m filingguard.redteam.build candidates      # v1 specs (committed; never overwritten)
    python -m filingguard.redteam.build revise          # v2: v1 revised after the first review, plus replacements
    python -m filingguard.redteam.build phrase --pilot  # one phrasing call (first batch of v1)
    python -m filingguard.redteam.build phrase          # phrase every v2 spec without a question yet
    python -m filingguard.redteam.build assemble        # filter, select, split, latency IDs, review sheet
    python -m filingguard.redteam.build review-apply    # read the owner's decisions back
    python -m filingguard.redteam.build judge-inputs    # premise-judge inputs (data/gold/, eval only)

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
from filingguard.redteam.phrasing import BATCH_SIZE, check_question, drop_redundant_possessive, phrase_batch
from filingguard.redteam.generators.restated import usable_pairs
from filingguard.redteam.restated import select_pairs
from filingguard.redteam.spec import ItemSpec

SEED = 20261004
OUT = Path("data/gold/candidates")
DRAFT_ITEMS = Path("data/testset/draft")
DRAFT_GOLD = Path("data/gold/draft")
CANDIDATES = OUT / "candidates_v3.jsonl"
PHRASED = OUT / "phrased_v3.jsonl"
REVIEW_BOOK = Path("review/review_v3.xlsx")   # v2 was withdrawn before review (H-017)   # v1 was halted at the first pass (H-009)
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
    by_spec = {s.spec_id: s for s in specs}
    questions = {k: drop_redundant_possessive(r["question"], by_spec[k].company, by_spec[k].gold.get("metric") or "")
                 if k in by_spec and r["question"] else r["question"] for k, r in phrased.items()}
    possessives_dropped = sum(questions[k] != r["question"] for k, r in phrased.items() if k in by_spec)

    failed = {s.spec_id for s in specs if s.spec_id not in phrased or phrased[s.spec_id]["problems"]}
    passing = [s for s in specs if s.spec_id not in failed]
    dupes = asm.near_duplicates(passing, questions)
    passing = [s for s in passing if s.spec_id not in dupes]
    ranks = injection_delivery(passing, questions)
    undelivered = {k for k, r in ranks.items() if r is None}
    passing = [s for s in passing if s.spec_id not in undelivered]

    counts = allocate_counts(sum(s.attack_type == "restated" for s in specs))
    dropped_v1 = _dropped_draft_items(corpus)
    prev = _previous_draft()
    if prev:
        items, selection = asm.sticky_select(passing, counts, random.Random(f"{seed}-select"), companies,
                                             prev["types"], COMPANIES)
        ids = asm.sticky_ids(items, prev["ids"], companies)
    else:
        items, selection = asm.select(passing, counts, random.Random(f"{seed}-select"), companies), {}
        ids = asm.assign_ids(items, companies)
    split = asm.assign_split(items, random.Random(f"{seed}-split"), companies)
    items.sort(key=lambda s: ids[s.spec_id])

    test = [s for s in items if split[s.spec_id] == "test"]
    latency = asm.stratified_sample(test, asm.LATENCY_SAMPLE, random.Random(f"{seed}-latency"), COMPANIES,
                                    lambda s: s.attack_type)
    swaps: list[dict] = []
    if prev and prev["sample"]:
        sample, swaps = asm.revise_sample(prev["sample"], items, split, random.Random(f"{seed}-review"), COMPANIES,
                                          prev["types"])
        for sw in swaps:
            sw |= {"old_id": prev["ids"][sw["old_spec_id"]], "new_id": ids[sw["new_spec_id"]],
                   "reason": _departure_reason(sw["old_spec_id"], prev["types"][sw["old_spec_id"]], specs, passing)}
    else:
        sample = asm.stratified_sample(items, asm.REVIEW_SAMPLE, random.Random(f"{seed}-review"), COMPANIES,
                                       lambda s: f"{s.attack_type}|{split[s.spec_id]}")
    problems = asm.coverage_problems(sample, COMPANIES)
    if problems:
        raise RuntimeError(f"review sample is not stratified enough: {problems}")
    in_sample = {s.spec_id for s in sample}
    # Extra checks (not in the fault rate): every untagged-concept, start-month and true-premise
    # driver item not already in the sample (D-028, D-034, D-041).
    extra = [s for s in items if s.spec_id not in in_sample
             and s.subtype in ("untagged_concept", "start_month", "true_premise_driver")]

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
        "selection": selection,
        "review_sample_swaps": swaps,
        "possessives_dropped_among_candidates": possessives_dropped,
        "latency_sample": latency_ids,
        "review_sample": sorted(ids[s.spec_id] for s in sample),
        "injection_delivery_rank": {ids[k]: r for k, r in ranks.items() if k in ids},
    }
    _write_json(DRAFT_GOLD / "assembly_v3.json", stats)
    return stats


def _previous_draft() -> dict | None:
    """The current draft's IDs, types and review sample, read before they are overwritten, so a
    rebuild keeps surviving items, IDs and sampled rows (D-041)."""
    gold_path, items_path, assembly_path = DRAFT_GOLD / "gold_v1.jsonl", DRAFT_ITEMS / "items_v1.jsonl", \
        DRAFT_GOLD / "assembly_v3.json"
    if not (gold_path.exists() and items_path.exists()):
        return None
    spec_of = {g["id"]: g["spec_id"] for g in _read_jsonl(gold_path)}
    items = _read_jsonl(items_path)
    assembly = json.loads(assembly_path.read_text(encoding="utf-8")) if assembly_path.exists() else {}
    return {
        "ids": {spec_of[i["id"]]: i["id"] for i in items},
        "types": {spec_of[i["id"]]: (i["attack_type"], i["subtype"]) for i in items},
        "sample": [spec_of[i] for i in assembly.get("review_sample", [])],
    }


def _departure_reason(spec_id: str, kind: tuple[str, str], specs: list[ItemSpec], passing: list[ItemSpec]) -> str:
    """Why an item in the previous draft is not in this one."""
    typ, sub = kind
    if spec_id in {s.spec_id for s in passing}:
        if typ == "control":
            return "not selected: one of the 10 control slots given to a true-premise driver (D-041)"
        return "not selected"
    if spec_id in {s.spec_id for s in specs}:
        return "failed a draft check (phrasing rule, near-duplicate or injection delivery)"
    record = json.loads((OUT / "candidates_v3_revision.json").read_text(encoding="utf-8"))["per_spec"]
    if spec_id in record:
        return record[spec_id]["reason"]
    if typ == "unanswerable":
        return "absence rule fails in another corpus filing (D-041)"
    if typ == "period_mismatch":
        return "trap value within 2% of gold or equal at 3 significant figures (D-041)"
    return "removed in revision"


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
    parser.add_argument("step", choices=["candidates", "revise", "phrase", "assemble", "review-apply", "judge-inputs"])
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
        corpus = Corpus()
        final = allocate_counts(len(select_pairs(usable_pairs(corpus), SEED)))
        specs, record = revise(corpus, v1, SEED, final)
        _write_jsonl(CANDIDATES, [s.to_dict() for s in specs])
        _write_json(OUT / "candidates_v3_revision.json", record)
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
            existing = {r["spec_id"]: r for path in (OUT / "phrased_v1.jsonl", OUT / "phrased_v2.jsonl", PHRASED)
                        if path.exists() for r in _read_jsonl(path)}
            rows = phrase(client_from_env("TARGET_MODEL"), specs, existing)
            _write_jsonl(PHRASED, rows)
        print(json.dumps({"phrased": len(rows), "failed_checks": sum(bool(r["problems"]) for r in rows)}, indent=2))
    elif args.step == "judge-inputs":
        from filingguard.redteam import judge_inputs

        items = {i["id"]: i for i in _read_jsonl(DRAFT_ITEMS / "items_v1.jsonl")}
        data = judge_inputs.build(_read_jsonl(DRAFT_GOLD / "gold_v1.jsonl"), items, Corpus())
        _write_json(judge_inputs.OUT, data)
        with_reasons = sum(bool(v["reasons"]) for v in data["items"].values())
        print(json.dumps({"items": len(data["items"]), "with_reasons": with_reasons,
                          "prompt_sha256": data["prompt_sha256"]}, indent=2))
    elif args.step == "assemble":
        stats = assemble_draft()
        skip = ("latency_sample", "review_sample", "injection_delivery_rank")
        print(json.dumps({k: v for k, v in stats.items() if k not in skip}, indent=2))
    else:
        from filingguard.redteam.review import fault_rate, read_decisions

        decisions = read_decisions(REVIEW_BOOK)
        _write_json(DRAFT_GOLD / "review_v3.json", decisions)
        print(json.dumps({"fault_rate_sample": fault_rate(decisions["Fault-rate sample"]),
                          "extra_checks": fault_rate(decisions["Extra checks"]) | {"counts_toward_fault_rate": False}},
                         indent=2))


if __name__ == "__main__":
    main()
