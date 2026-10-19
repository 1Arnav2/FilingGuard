"""Phase 5 step 4 driver: baseline scoring of the 210 saved test answers (owner's go-ahead).

Frozen code only: `judge.judge_answers` (prompt hash checked), `score.score_answer`, and
`dev_report.summarise` / `is_premise`. Reads the saved answers; never calls the target. The judge
is called only for premise answers that are not unparseable (the scorer scores those Missed before
any judge input is used). Writes results/judge/test_judge_v1.jsonl, results/test/baseline_scores_v1.jsonl
and results/test/baseline_summary_v1.json.

Usage: python score_test.py {judge,score}
"""
import json
import sys
from pathlib import Path

from filingguard.eval import dev_report
from filingguard.eval.dev_run import load_items
from filingguard.eval.score import score_answer

RUNS = Path("results/runs/test_target_v1.jsonl")
JUDGE_OUT = Path("results/judge/test_judge_v1.jsonl")
SCORES = Path("results/test/baseline_scores_v1.jsonl")
SUMMARY = Path("results/test/baseline_summary_v1.json")
CONDITION = "baseline"


def load_test():
    items = load_items("test", allow_test=True)
    ids = {i["id"] for i in items}
    gold = {r["id"]: r for r in map(json.loads, dev_report.GOLD.read_text(encoding="utf-8").splitlines())
            if r and r["id"] in ids}
    runs = {r["id"]: r for r in map(json.loads, RUNS.read_text(encoding="utf-8").splitlines()) if r}
    assert set(gold) == ids == set(runs) and len(ids) == 210
    return items, gold, runs


def judge(items, gold, runs) -> None:
    from filingguard.eval.judge import judge_answers
    from filingguard.llm.client import client_from_env

    assert not JUDGE_OUT.exists(), "test judge decisions already saved; never re-judged"
    llm = client_from_env("TARGET_MODEL")
    before = llm.ledger.total()["cost_usd"]
    need = [i for i in items if dev_report.is_premise(i) and not runs[i["id"]]["answer"].get("parse_error")]
    skipped = [i["id"] for i in items if dev_report.is_premise(i) and runs[i["id"]]["answer"].get("parse_error")]
    print(f"premise answers to judge: {len(need)}; unparseable premise answers not judged: {skipped}", flush=True)
    requests = [{"key": f"{i['id']}:{CONDITION}", "question": i["question"], "spec_id": gold[i["id"]]["spec_id"],
                 "answer_text": runs[i["id"]]["answer"]["text"]} for i in need]
    decisions = judge_answers(requests, llm)
    spent = llm.ledger.total()["cost_usd"] - before
    rows = [{"key": k, "id": k.split(":")[0], "condition": k.split(":")[1], "model": llm.model, **d}
            for k, d in sorted(decisions.items())]
    JUDGE_OUT.parent.mkdir(parents=True, exist_ok=True)
    JUDGE_OUT.write_bytes("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows).encode("utf-8"))
    print(f"judged {len(rows)}; errors {sum('error' in r for r in rows)}; judge cost ${spent:.4f}; "
          f"spend ${llm.ledger.total()['cost_usd']:.4f}", flush=True)


def score(items, gold, runs) -> None:
    jd = {r["key"]: r for r in map(json.loads, JUDGE_OUT.read_text(encoding="utf-8").splitlines()) if r}
    scores = [score_answer(i, gold[i["id"]], runs[i["id"]]["answer"], judge=jd.get(f"{i['id']}:{CONDITION}"))
              for i in items]
    SCORES.parent.mkdir(parents=True, exist_ok=True)
    SCORES.write_bytes("".join(json.dumps(s.to_dict(), ensure_ascii=False) + "\n" for s in scores).encode("utf-8"))
    summary = dev_report.summarise(items, scores, jd)
    summary["split"] = "test"
    summary["scored_by"] = "frozen scorer, as scored (no corrections)"
    summary["definitions"]["abstain_rate_controls"] = ("regular controls abstained (EVAL §3) + driver controls Missed, "
                                                      "over all test controls")
    SUMMARY.write_bytes((json.dumps(summary, indent=2) + "\n").encode("utf-8"))
    print("scored", len(scores), flush=True)


if __name__ == "__main__":
    items, gold, runs = load_test()
    {"judge": judge, "score": score}[sys.argv[1]](items, gold, runs)
