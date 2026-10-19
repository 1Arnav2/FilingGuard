"""Corrected test baseline summary (EVAL §10 4b, D-071): the owner-approved parsing-fault
corrections in `results/test/baseline_corrections_v1.json`, applied as an overlay on the frozen
scorer's rows in `results/test/baseline_scores_v1.jsonl`. Neither the scorer nor the as-scored files
are changed. Writes `results/test/baseline_summary_corrected_v1.json`. No model calls.

Usage: python src/filingguard/eval/scripts/apply_test_corrections.py
"""

import json
from pathlib import Path

from filingguard.eval import dev_report
from filingguard.eval.dev_run import load_items
from filingguard.eval.score import Score

SCORES = Path("results/test/baseline_scores_v1.jsonl")
CORRECTIONS = Path("results/test/baseline_corrections_v1.json")
JUDGE = Path("results/judge/test_judge_v1.jsonl")
OUT = Path("results/test/baseline_summary_corrected_v1.json")


def corrected_scores() -> list[Score]:
    """The as-scored rows with each approved correction applied: Correct, figure given, returned."""
    scores = [Score(**json.loads(line)) for line in SCORES.read_text(encoding="utf-8").splitlines() if line.strip()]
    fixes = {c["item"]: c for c in json.loads(CORRECTIONS.read_text(encoding="utf-8"))["corrections"]}
    for s in scores:
        c = fixes.get(s.id)
        if c is None:
            continue
        assert [s.outcome, s.label] == c["as_scored"], f"{s.id}: as-scored row differs from the correction record"
        s.outcome, s.label = c["corrected"]
        s.abstained, s.returned, s.gives_figure = False, True, True
        if c.get("scale_not_followed") is not None:
            s.scale_not_followed = c["scale_not_followed"]
        s.notes = s.notes + [f"corrected under D-071: {c['pattern']}"]
    return scores


def main() -> None:
    items = load_items("test", allow_test=True)
    judge = {r["key"]: r for r in map(json.loads, JUDGE.read_text(encoding="utf-8").splitlines()) if r}
    summary = dev_report.summarise(items, corrected_scores(), judge)
    summary["split"] = "test"
    summary["scored_by"] = "frozen scorer with owner-approved parsing-fault corrections (D-071, EVAL 10 4b)"
    summary["corrections_file"] = CORRECTIONS.as_posix()
    summary["definitions"]["abstain_rate_controls"] = ("regular controls abstained (EVAL §3) + driver controls Missed, "
                                                      "over all test controls")
    OUT.write_bytes((json.dumps(summary, indent=2) + "\n").encode("utf-8"))
    print(json.dumps({k: summary[k] for k in ("outcome", "correct_handling", "answer_coverage",
                                              "abstain_rate_controls")}))


if __name__ == "__main__":
    main()
