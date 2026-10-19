"""Test seeded-error set (Phase 5 step 5, docs/SEEDED_ERRORS.md, D-057, D-072). No model calls.

Source pool: test answers the frozen scorer scored Correct as scored (no D-071 corrections) that
state a figure for the asked item, in the answer-in-filing types, as on dev. The six transforms,
the copy keys and the sanity gate (Unsupported with the transform's expected label under the frozen
scorer) are the dev code's own (`eval/seeded.py`), unchanged; items are taken in ID order, so the
build is deterministic. Writes `results/test/seeded_v1.jsonl` and its freeze manifest
`results/test/seeded_freeze_v1.json` (SHA-256), pinned by `tests/test_seeded_test_frozen.py`.

Usage: python src/filingguard/eval/scripts/build_test_seeded.py
"""

import hashlib
import json
from collections import Counter
from pathlib import Path

from filingguard.eval.dev_report import ANSWER_IN_FILING, GOLD
from filingguard.eval.dev_run import load_items
from filingguard.eval.score import metric_key, score_answer
from filingguard.eval.seeded import EXPECTED, corrupt, opaque_key, transforms_for

RUNS = Path("results/runs/test_target_v1.jsonl")
SCORES = Path("results/test/baseline_scores_v1.jsonl")
CORRECTIONS = Path("results/test/baseline_corrections_v1.json")
JUDGE = Path("results/judge/test_judge_v1.jsonl")
OUT = Path("results/test/seeded_v1.jsonl")
MANIFEST = Path("results/test/seeded_freeze_v1.json")


def build() -> tuple[list[dict], dict]:
    items = load_items("test", allow_test=True)
    ids = {i["id"] for i in items}
    gold = {r["id"]: r for r in map(json.loads, GOLD.read_text(encoding="utf-8").splitlines()) if r and r["id"] in ids}
    runs = {r["id"]: r for r in map(json.loads, RUNS.read_text(encoding="utf-8").splitlines()) if r}
    scores = {r["id"]: r for r in map(json.loads, SCORES.read_text(encoding="utf-8").splitlines()) if r}
    judge = {r["key"]: r for r in map(json.loads, JUDGE.read_text(encoding="utf-8").splitlines()) if r}
    corrected = {c["item"] for c in json.loads(CORRECTIONS.read_text(encoding="utf-8"))["corrections"]}
    correct = [i for i in items if scores[i["id"]]["outcome"] == "correct"]
    pool = [i for i in correct if i["attack_type"] in ANSWER_IN_FILING and scores[i["id"]]["gives_figure"]
            and i["id"] not in corrected]
    assert not corrected & {i["id"] for i in correct}, "a corrected row was Correct as scored"
    rows = []
    for item in pool:
        g = gold[item["id"]]
        answer = runs[item["id"]]["answer"]
        for t in transforms_for(item, g, metric_key(g["gold"])):
            copy, why = corrupt(item, g, answer, t)
            row = {"key": opaque_key(item["id"], t), "source_id": item["id"], "transform": t,
                   "attack_type": item["attack_type"], "subtype": item["subtype"], "kept": False, "drop_reason": why}
            if copy is not None:
                j = judge.get(f"{item['id']}:baseline") if item["subtype"] == "true_premise_driver" else None
                gate = score_answer(item, g, copy, judge=j)
                row.update(answer=copy, gate_outcome=gate.outcome, gate_label=gate.label)
                if gate.outcome == "unsupported" and gate.label in EXPECTED[t]:
                    row["kept"], row["drop_reason"] = True, ""
                else:
                    row["drop_reason"] = f"gate: scored {gate.outcome}/{gate.label}, expected {sorted(EXPECTED[t])}"
            rows.append(row)
    info = {"correct_as_scored": len(correct), "pool": len(pool),
            "pool_by_type": dict(Counter(i["attack_type"] for i in pool)),
            "excluded_corrected_rows": sorted(corrected)}
    return rows, info


def main() -> None:
    assert not OUT.exists(), f"{OUT} is frozen once written; never rebuilt in place"
    rows, info = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    data = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows).encode("utf-8")
    OUT.write_bytes(data)
    kept = Counter(r["transform"] for r in rows if r["kept"])
    made = Counter(r["transform"] for r in rows)
    manifest = {"file": OUT.as_posix(), "sha256": hashlib.sha256(data).hexdigest(), "rows": len(rows),
                "kept": sum(kept.values()), "kept_by_transform": dict(sorted(kept.items())),
                "made_by_transform": dict(sorted(made.items())),
                "dropped_by_transform": {t: made[t] - kept[t] for t in sorted(made)},
                "drop_reasons": {f"{t}: {why}": n for (t, why), n in sorted(Counter(
                    (r["transform"], r["drop_reason"]) for r in rows if not r["kept"]).items())},
                "macro_set_size_T1_T3_T4_T5_T6": sum(kept[t] for t in ("T1", "T3", "T4", "T5", "T6")),
                **info, "decision": "D-072", "frozen_before_any_verifier_run": True}
    MANIFEST.write_bytes((json.dumps(manifest, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({k: v for k, v in manifest.items() if k != "drop_reasons"}, indent=2))
    print(json.dumps(manifest["drop_reasons"], indent=2))


if __name__ == "__main__":
    main()
