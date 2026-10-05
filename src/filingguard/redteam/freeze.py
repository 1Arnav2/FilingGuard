"""Freeze the reviewed draft as test set v1 (EVAL §2, §10 step 1).

The split is assigned here, once, from the final item set (H-023); the latency sample is drawn
from its test half. The frozen files are written, every pre-review check is re-run on them,
and a manifest records the seeds, the item-set hash and the SHA-256 of each frozen file. No
model calls.
"""

import hashlib
import json
import random
from collections import Counter
from pathlib import Path
from statistics import median

from filingguard.data.facts import is_annual
from filingguard.data.filings import COMPANIES
from filingguard.redteam import assemble as asm
from filingguard.redteam import judge_inputs
from filingguard.redteam.corpus import METRICS, Corpus, _printed, fiscal_label
from filingguard.redteam.counts import ATTACK_TYPES
from filingguard.redteam.generators.period_mismatch import trap_far_enough
from filingguard.redteam.generators.unanswerable import absence_check
from filingguard.redteam.injection import poisoned_text
from filingguard.redteam.phrasing import leaked
from filingguard.redteam.spec import ItemSpec

ITEMS = Path("data/testset/v1.jsonl")
GOLD = Path("data/gold/gold_v1.jsonl")
POISONED = Path("data/testset/poisoned_chunks_v1.jsonl")
LATENCY = Path("data/testset/latency_sample_v1.json")
MANIFEST = Path("data/testset/freeze_v1.json")
FROZEN_FILES = (ITEMS, GOLD, judge_inputs.OUT, POISONED, LATENCY)
EXPECTED_COUNTS = {"control": 60, "unanswerable": 46, "unit_trap": 46, "period_mismatch": 46, "restated": 12,
                   "false_premise": 45, "injection": 45}
ITEM_KEYS = {"id", "company", "attack_type", "subtype", "question", "split", "injection"}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def item_set_hash(id_to_spec: dict[str, str]) -> str:
    """SHA-256 of the sorted "item id <tab> spec id" lines."""
    body = "\n".join(sorted(f"{i}\t{s}" for i, s in id_to_spec.items()))
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _read_jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def counts(items: list[dict]) -> dict:
    """Counts by type, subtype, split and company."""
    by_type = Counter(i["attack_type"] for i in items)
    return {
        "total": len(items),
        "by_type": {t: by_type[t] for t in ATTACK_TYPES},
        "by_subtype": {t: dict(sorted(Counter(i["subtype"] for i in items if i["attack_type"] == t).items()))
                       for t in ATTACK_TYPES},
        "split_by_type": {t: {v: sum(1 for i in items if i["attack_type"] == t and i["split"] == v)
                              for v in ("dev", "test")} for t in ATTACK_TYPES},
        "split": dict(Counter(i["split"] for i in items)),
        "per_company": dict(sorted(Counter(i["company"] for i in items).items())),
        "companies_per_type": {t: len({i["company"] for i in items if i["attack_type"] == t}) for t in ATTACK_TYPES},
    }


def _period_of(corpus: Corpus, ticker: str, concept: str, accession: str, year: int, value: float) -> tuple | None:
    """(period_start, period_end) of the annual fact for fiscal `year` with `value` in a filing."""
    f = corpus.facts
    rows = f[(f["ticker"] == ticker) & (f["concept"] == concept) & (f["accession"] == accession) & is_annual(f)
             & (f["value"] == value)]
    rows = rows[rows["period_end"].map(fiscal_label) == year]
    if rows.empty:
        return None
    r = rows.iloc[0]
    return (r["period_start"] if isinstance(r["period_start"], str) else None), r["period_end"]


def multi_filing_conflicts(corpus: Corpus, items: dict[str, dict], gold_rows: list[dict]) -> dict:
    """Items (not `restated`, not `unanswerable`) whose gold value, or either premise year's
    value, is reported differently at printed precision in another corpus filing."""
    f = corpus.facts
    annual = f[is_annual(f)]
    checked, conflicts = [], []
    for g in gold_rows:
        item, gg = items[g["id"]], g["gold"]
        if item["attack_type"] in ("restated", "unanswerable"):
            continue
        ticker, accession = item["company"], g["source"]["accession"]
        others = [x["accession"] for x in corpus.filings(ticker) if x["accession"] != accession]
        if not others:
            continue
        periods = [(gg["period_start"], gg["period_end"], gg["value"])]
        for year, value in gg.get("true_values", {}).items():
            if int(year) != gg["fiscal_year"]:
                found = _period_of(corpus, ticker, gg["concept"], accession, int(year), value)
                if found is None:
                    conflicts.append({"id": g["id"], "problem": f"fiscal {year} value not found in its filing"})
                    continue
                periods.append((*found, value))
        checked.append(g["id"])
        for start, end, value in periods:
            rows = annual[(annual["ticker"] == ticker) & (annual["concept"] == gg["concept"])
                          & annual["accession"].isin(others) & (annual["period_end"] == end)
                          & (annual["unit"] == gg["unit"])]
            rows = rows[rows["period_start"].isna()] if start is None else rows[rows["period_start"] == start]
            for r in rows.itertuples():
                if _printed(float(r.value), gg["unit"], gg["printed_scale"]) != _printed(value, gg["unit"], gg["printed_scale"]):
                    conflicts.append({"id": g["id"], "period_end": end, "value": value, "other_accession": r.accession,
                                      "other_value": float(r.value)})
    return {"items_checked": len(checked), "conflicts": conflicts}


def absence_failures(corpus: Corpus, items: dict[str, dict], gold_rows: list[dict]) -> dict:
    """Re-runs the D-041 absence rule over every corpus filing for each `unanswerable` item."""
    by_label = {m.label: m for m in METRICS.values()}
    failures, checked = [], 0
    for g in gold_rows:
        item = items[g["id"]]
        if item["attack_type"] != "unanswerable":
            continue
        ev, gg = g["evidence"], g["gold"]
        search = {"terms": ev["searched_terms"], "near": ev["required_nearby"]}
        result = absence_check(corpus, item["company"], item["subtype"], by_label[gg["metric"]], gg["fiscal_year"], search)
        all_filings = [x["accession"] for x in corpus.filings(item["company"])]
        if result is None or result["filings"] != all_filings or ev["filings"] != all_filings:
            failures.append(g["id"])
        checked += 1
    return {"items_checked": checked, "failures": failures}


def trap_failures(items: dict[str, dict], gold_rows: list[dict]) -> dict:
    """`period_mismatch` items whose trap value could score as correct (D-041)."""
    failures, checked = [], 0
    for g in gold_rows:
        if items[g["id"]]["attack_type"] != "period_mismatch":
            continue
        trap = g["gold"].get("trap_value", (g.get("evidence") or {}).get("trap_value"))
        if trap is None or not trap_far_enough(g["gold"]["value"], trap):
            failures.append(g["id"])
        checked += 1
    return {"items_checked": checked, "failures": failures}


def injection_ranks(specs: dict[str, ItemSpec], items: list[dict]) -> dict:
    """Rank of each poisoned chunk for its frozen question in the frozen retriever's top 20."""
    from filingguard.redteam.build import injection_delivery

    inj = [i for i in items if i["attack_type"] == "injection"]
    by_spec = {specs[i["id"]].spec_id: i for i in inj}
    ranks = injection_delivery([specs[i["id"]] for i in inj], {k: i["question"] for k, i in by_spec.items()})
    ranks = {by_spec[k]["id"]: r for k, r in ranks.items()}
    delivered = [r for r in ranks.values() if r is not None]
    return {"items": len(inj), "delivered": len(delivered), "median_rank": median(delivered) if delivered else None,
            "worst_rank": max(delivered) if delivered else None,
            "not_delivered": sorted(k for k, r in ranks.items() if r is None), "ranks": dict(sorted(ranks.items()))}


def gold_separation(items: list[dict], gold_rows: list[dict], specs: dict[str, ItemSpec]) -> dict:
    """Item rows carry no gold field, and no question prints its own answer."""
    extra_keys = sorted({k for i in items for k in i} - ITEM_KEYS)
    leaks = [i["id"] for i in items if leaked(specs[i["id"]].forbid, i["question"])]
    gold_ids = {g["id"] for g in gold_rows}
    return {"item_keys": sorted(ITEM_KEYS), "unexpected_item_keys": extra_keys, "questions_printing_gold": leaks,
            "gold_ids_match_items": gold_ids == {i["id"] for i in items},
            "gold_path": GOLD.as_posix(), "judge_inputs_path": judge_inputs.OUT.as_posix()}


def poisoned_rows(corpus: Corpus, items: list[dict]) -> list[dict]:
    """The exact poisoned text each injection item delivers, with a hash of the clean chunk so a
    run can check that the local index still holds the same text."""
    chunks = {c["chunk_id"]: c for c in corpus.chunks}
    rows = []
    for i in items:
        if i["attack_type"] != "injection":
            continue
        inj, chunk = i["injection"], chunks[i["injection"]["chunk_id"]]
        rows.append({"id": i["id"], "chunk_id": inj["chunk_id"], "accession": inj["accession"],
                     "clean_sha256": hashlib.sha256(chunk["text"].encode("utf-8")).hexdigest(),
                     "poisoned_text": poisoned_text(chunk["text"], inj)})
    return rows


def freeze(draft_items: Path, draft_gold: Path, candidates: Path, review: Path, seed: int) -> dict:
    """Assign the split, draw the latency sample, write the frozen files, re-run the checks and
    write the manifest. Refuses to overwrite an existing frozen set."""
    if ITEMS.exists() or MANIFEST.exists():
        raise SystemExit(f"{ITEMS} is frozen; it is never rewritten")
    corpus = Corpus()
    companies = list(corpus.companies)
    draft = _read_jsonl(draft_items)
    gold_rows = _read_jsonl(draft_gold)
    spec_of = {g["id"]: g["spec_id"] for g in gold_rows}
    all_specs = {row["spec_id"]: row for row in _read_jsonl(candidates)}
    specs = {i["id"]: ItemSpec(**all_specs[spec_of[i["id"]]]) for i in draft}
    for g in gold_rows:   # the draft gold must be exactly the candidates' gold
        assert specs[g["id"]].gold == g["gold"], g["id"]

    split_seed, latency_seed = f"{seed}-split", f"{seed}-latency"
    ordered = [specs[i["id"]] for i in draft]
    split = asm.assign_split(ordered, random.Random(split_seed), companies)
    test = [s for s in ordered if split[s.spec_id] == "test"]
    latency = asm.stratified_sample(test, asm.LATENCY_SAMPLE, random.Random(latency_seed), COMPANIES,
                                    lambda s: s.attack_type)
    id_of = {s.spec_id: k for k, s in specs.items()}

    decisions = json.loads(review.read_text(encoding="utf-8"))
    reviewed = {d["id"] for rows in decisions.values() for d in rows}
    items = [i | {"split": split[spec_of[i["id"]]]} for i in draft]
    gold = [g | {"human_checked": g["id"] in reviewed} for g in gold_rows]
    latency_ids = sorted(id_of[s.spec_id] for s in latency)

    _write_jsonl(ITEMS, items)
    _write_jsonl(GOLD, gold)
    _write_jsonl(POISONED, poisoned_rows(corpus, items))
    latency_types = Counter(specs[k].attack_type for k in latency_ids)
    _write_json(LATENCY, {"seed": latency_seed, "split": "test", "ids": latency_ids,
                          "by_type": {t: latency_types[t] for t in ATTACK_TYPES}})

    by_id = {i["id"]: i for i in items}
    rebuilt = judge_inputs.build(gold, by_id, corpus)
    on_disk = json.loads(judge_inputs.OUT.read_text(encoding="utf-8"))
    if rebuilt != on_disk:
        raise RuntimeError("judge inputs differ when rebuilt from the frozen gold")

    c = counts(items)
    checks = {
        "counts_as_specified": c["by_type"] == EXPECTED_COUNTS and c["split"] == {"test": 210, "dev": 90},
        "split_equals_draft": all(i["split"] == d["split"] for i, d in zip(items, draft)),
        "latency_equals_draft": latency_ids == json.loads(
            (draft_items.parent / "latency_sample_v1.json").read_text(encoding="utf-8"))["ids"],
        "multi_filing": multi_filing_conflicts(corpus, by_id, gold),
        "absence": absence_failures(corpus, by_id, gold),
        "trap_distance": trap_failures(by_id, gold),
        "injection_delivery": injection_ranks(specs, items),
        "gold_separation": gold_separation(items, gold, specs),
        "judge_inputs_rebuilt_equal": True,
        "human_checked": sum(g["human_checked"] for g in gold),
    }
    manifest = {
        "version": "testset-v1",
        "seed": seed, "split_seed": split_seed, "latency_seed": latency_seed,
        "item_set_sha256": item_set_hash({k: s.spec_id for k, s in specs.items()}),
        "item_set_hash_input": "sorted lines of '<item id>\\t<spec id>', joined by \\n, UTF-8",
        "files": {p.as_posix(): sha256_file(p) for p in FROZEN_FILES},
        "premise_judge_prompt_sha256": judge_inputs.prompt_sha256(),
        "counts": c,
        "latency_sample": {"ids": latency_ids, "by_type": {t: latency_types[t] for t in ATTACK_TYPES}},
        "checks": checks,
    }
    _write_json(MANIFEST, manifest)
    return manifest
