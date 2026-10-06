"""Baseline dev results (EVAL §3, §4), descriptive only, and the owner's 90-row score sheet.

Reads the dev run file, the dev rows of the gold file and the judge inputs (eval/ only), runs
the premise judge on the dev premise items, scores every answer and writes:
- `results/judge/dev_judge_v1.jsonl`: one judge decision per premise answer and condition
- `results/dev/baseline_scores_v2.jsonl`: one scored row per item
- `results/dev/baseline_summary_v2.json`: counts and rates by type
- `review/dev_score_sheet_v2.xlsx`: the sheet the owner spot-checks

Usage: python -m filingguard.eval.dev_report {judge,score}
"""

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from filingguard.eval.dev_run import OUT as RUN_FILE
from filingguard.eval.dev_run import load_items
from filingguard.eval.score import Score, rel_tolerance, score_answer
from filingguard.eval.stats import wilson

GOLD = Path("data/gold/gold_v1.jsonl")
JUDGE_OUT = Path("results/judge/dev_judge_v1.jsonl")
# v2: after the D-053 scorer fixes; the v1 files are kept as the before record.
SCORES = Path("results/dev/baseline_scores_v2.jsonl")
SUMMARY = Path("results/dev/baseline_summary_v2.json")
SHEET = Path("review/dev_score_sheet_v2.xlsx")
CONDITION = "baseline"
JUDGE_LIMIT_USD = 0.15
HIGH_COST_PER_JUDGE_CALL = 0.012  # 6k input and 2k output tokens at the standard price
TYPES = ("control", "unanswerable", "unit_trap", "period_mismatch", "restated", "false_premise", "injection")


def is_premise(item: dict[str, Any]) -> bool:
    return item["attack_type"] == "false_premise" or item["subtype"] == "true_premise_driver"


def load_dev() -> tuple[list[dict], dict[str, dict], dict[str, dict]]:
    """Dev items, their gold rows and their run rows, all keyed by item ID."""
    items = load_items()
    ids = {i["id"] for i in items}
    gold = {}
    for line in GOLD.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            if row["id"] in ids:
                gold[row["id"]] = row
    runs = {r["id"]: r for r in map(json.loads, RUN_FILE.read_text(encoding="utf-8").splitlines()) if r}
    if set(runs) != ids or set(gold) != ids:
        raise RuntimeError("run file or gold does not cover exactly the 90 dev items")
    return items, gold, runs


def run_judge(items: list[dict], gold: dict, runs: dict) -> dict[str, dict]:
    """Judge every dev premise answer once (cached), within the owner's judge limit."""
    from filingguard.eval.judge import judge_answers
    from filingguard.llm.client import client_from_env

    llm = client_from_env("TARGET_MODEL")
    before = llm.ledger.total()["cost_usd"]
    premise = [i for i in items if is_premise(i)]
    if len(premise) * HIGH_COST_PER_JUDGE_CALL > JUDGE_LIMIT_USD + 0.05:
        raise RuntimeError("judge calls could pass the approved limit")
    requests = [{"key": f"{i['id']}:{CONDITION}", "question": i["question"], "spec_id": gold[i["id"]]["spec_id"],
                 "answer_text": runs[i["id"]]["answer"]["text"]} for i in premise]
    decisions = judge_answers(requests, llm)
    spent = llm.ledger.total()["cost_usd"] - before
    JUDGE_OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = [{"key": k, "id": k.split(":")[0], "condition": k.split(":")[1], "model": llm.model, **d}
            for k, d in sorted(decisions.items())]
    JUDGE_OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    print(f"judged {len(rows)} answers; spent ${spent:.4f}")
    return decisions


def load_judge() -> dict[str, dict]:
    if not JUDGE_OUT.exists():
        return {}
    return {r["key"]: r for r in map(json.loads, JUDGE_OUT.read_text(encoding="utf-8").splitlines()) if r}


def score_all(items: list[dict], gold: dict, runs: dict, judge: dict) -> list[Score]:
    return [score_answer(i, gold[i["id"]], runs[i["id"]]["answer"], judge=judge.get(f"{i['id']}:{CONDITION}"))
            for i in items]


def _rate(k: int, n: int) -> dict[str, Any]:
    if n == 0:
        return {"k": 0, "n": 0, "rate": None, "wilson95": None}
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": round(k / n, 4), "wilson95": [round(lo, 4), round(hi, 4)]}


def summarise(items: list[dict], scores: list[Score], judge: dict) -> dict[str, Any]:
    """Counts by type and the EVAL §4 rates for one condition on dev. Descriptive (n = 90)."""
    by_type = {}
    for t in TYPES:
        ss = [s for s in scores if s.attack_type == t]
        by_type[t] = {"n": len(ss), "outcome": dict(Counter(s.outcome for s in ss)),
                      "labels": dict(Counter(s.label for s in ss if s.label)),
                      "returned": sum(s.returned for s in ss),
                      "unsupported_rate": _rate(sum(s.outcome == "unsupported" for s in ss), sum(s.returned for s in ss))}
    returned = [s for s in scores if s.returned]
    controls = [s for s in scores if s.attack_type == "control"]
    drivers = [s for s in controls if s.subtype == "true_premise_driver"]
    regular = [s for s in controls if s.subtype != "true_premise_driver"]
    injections = [s for s in scores if s.attack_type == "injection"]
    premise_ids = {i["id"] for i in items if is_premise(i)}
    decisions = [judge[k] for k in judge if k.split(":")[0] in premise_ids]
    reasons_given = [d for d in decisions if d.get("gives_reasons")]
    return {
        "condition": CONDITION, "split": "dev", "descriptive_only": True, "n_items": len(scores),
        "tolerance": rel_tolerance(),
        "outcome": dict(Counter(s.outcome for s in scores)),
        "unsupported_claim_rate": _rate(sum(s.outcome == "unsupported" for s in returned), len(returned)),
        "verified_answer_rate": _rate(sum(s.outcome == "correct" and s.returned for s in scores), len(scores)),
        "correct_rate_all_items": _rate(sum(s.outcome == "correct" for s in scores), len(scores)),
        "abstain_rate_controls": _rate(sum(s.abstained for s in regular) + sum(s.outcome == "missed" for s in drivers),
                                       len(controls)),
        "abstain_rate_injection": _rate(sum(s.abstained for s in injections), len(injections)),
        "injection_breakdown": dict(Counter(s.injection or "not followed" for s in injections)),
        "rejected_true_premise": _rate(sum(s.label == "rejected_true_premise" for s in drivers), len(drivers)),
        "scale_not_followed": sum(s.scale_not_followed for s in scores),
        "unparseable": sum(s.unparseable for s in scores),
        "restated_case_study": [{"id": s.id, "subtype": s.subtype, "outcome": s.outcome, "label": s.label}
                                for s in scores if s.attack_type == "restated"],
        "reasons_diagnostic": {"premise_answers": len(decisions), "gives_reasons": len(reasons_given),
                               "every_reason_in_passages": sum(bool(d.get("reasons_in_filing")) for d in reasons_given),
                               "says_no_reasons_given": sum(bool(d.get("says_no_reasons_given")) for d in decisions),
                               "judge_errors": sum("error" in d for d in decisions),
                               "note": "lower bound; outside every pass bar (EVAL §4, D-042)"},
        "by_type": by_type,
        "definitions": {
            "answers_returned": "not abstained under EVAL §3, or scored Unsupported",
            "verified_answer_rate": "Correct and returned / all items (definition pending owner confirmation)",
            "abstain_rate_controls": "regular controls abstained (EVAL §3) + driver controls Missed, over all dev controls",
        },
    }


def _gold_text(item: dict, g: dict) -> str:
    gg = g["gold"]
    if gg.get("value") is None:
        q = f", quarter {gg['quarter']}" if gg.get("quarter") else ""
        return f"ABSENT: {gg.get('metric')} for fiscal {gg.get('fiscal_year')}{q}"
    unit = "per share" if gg["unit"] == "USD/shares" else gg.get("printed_scale", "")
    parts = [f"{gg.get('metric')} = {gg.get('printed_as')} ({unit}), fiscal {gg.get('fiscal_year')}, "
             f"period end {gg.get('period_end')}"]
    for k in ("requested_scale", "premise", "trap_value", "other_value", "canary", "calendar_year", "start_month"):
        if gg.get(k) not in (None, ""):
            parts.append(f"{k}: {gg[k]}")
    if gg.get("true_values"):
        parts.append(f"values: {gg['true_values']}")
    return "\n".join(parts)


def _figures_text(s: Score) -> str:
    return "\n".join(
        f"{f['value']:,.4g} [{f['scale'] or '-'}{', neg' if f['negative'] else ''}] metric={f['metric']} "
        f"asked={f['asked']} period={f['period']} ok={f['period_ok']}" for f in s.figures) or "(none)"


def write_sheet(items: list[dict], gold: dict, runs: dict, scores: list[Score], judge: dict, path: Path = SHEET) -> None:
    """One row per dev item for the owner's spot check of the scorer."""
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font

    wb = Workbook()
    ws = wb.active
    ws.title = "dev baseline"
    head = ["ID", "Type", "Subtype", "Company", "Question", "Gold", "Answer", "Abstain flag", "Figures read",
            "Judge", "Outcome", "Label", "Notes", "Scale not followed", "Injection", "Your check (ok / wrong)", "Your note"]
    ws.append(head)
    for item, s in zip(items, scores):
        a = runs[item["id"]]["answer"]
        d = judge.get(f"{item['id']}:{CONDITION}")
        jtext = "" if not d else (f"rejects={d.get('rejects_premise')} confirms={d.get('confirms_change')}\n"
                                  f"{d.get('reason') or d.get('error', '')}")
        ws.append([item["id"], item["attack_type"], item["subtype"], item["company"], item["question"],
                   _gold_text(item, gold[item["id"]]), a["text"], a["abstained"], _figures_text(s), jtext,
                   s.outcome, s.label or "", "; ".join(s.notes), s.scale_not_followed or "", s.injection or "", "", ""])
    widths = [9, 14, 18, 8, 40, 36, 70, 8, 48, 36, 11, 20, 30, 9, 10, 14, 30]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = w
    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = "B2"
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=("judge", "score"))
    args = parser.parse_args()
    items, gold, runs = load_dev()
    if args.step == "judge":
        run_judge(items, gold, runs)
        return
    judge = load_judge()
    scores = score_all(items, gold, runs, judge)
    SCORES.parent.mkdir(parents=True, exist_ok=True)
    SCORES.write_text("".join(json.dumps(s.to_dict(), ensure_ascii=False) + "\n" for s in scores), encoding="utf-8")
    summary = summarise(items, scores, judge)
    SUMMARY.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    write_sheet(items, gold, runs, scores, judge)
    print(json.dumps({k: summary[k] for k in ("outcome", "unsupported_claim_rate", "abstain_rate_controls")}, indent=2))


if __name__ == "__main__":
    main()
