"""The scorer on the real dev gold rows, with synthetic answers (no target answers involved)."""

import json

from filingguard.eval.dev_report import is_premise, summarise, write_sheet
from filingguard.eval.dev_run import load_items
from filingguard.eval.score import score_answer

GOLD = "data/gold/gold_v1.jsonl"


def dev_gold():
    items = load_items()
    ids = {i["id"] for i in items}
    gold = {r["id"]: r for r in map(json.loads, open(GOLD, encoding="utf-8").read().splitlines()) if r["id"] in ids}
    return items, gold


def ideal(item, g):
    """An answer stating the gold value the way the filing prints it, for the gold fiscal year."""
    gg = g["gold"]
    sign = "(" if gg["value"] < 0 else ""
    close = ")" if gg["value"] < 0 else ""
    if gg["unit"] == "USD/shares":
        figure = f"{sign}${gg['printed_as']}{close} per share"
    else:
        figure = f"{sign}${gg['printed_as']}{close} {gg['printed_scale']}"
    when = f"fiscal {gg['fiscal_year']} (ended {gg['period_end']})"
    return {"text": f"Its {g['source']['row_label']} for {when} was {figure}.", "abstained": False, "claims": [],
            "parse_error": None}


def test_ideal_answers_score_correct_on_every_figure_row():
    items, gold = dev_gold()
    wrong = []
    for item in items:
        if item["attack_type"] in ("unanswerable", "false_premise") or item["subtype"] == "true_premise_driver":
            continue
        s = score_answer(item, gold[item["id"]], ideal(item, gold[item["id"]]))
        if s.outcome != "correct":
            wrong.append((item["id"], item["attack_type"], s.outcome, s.label, s.notes))
    assert not wrong, wrong


def test_refusals_score_as_the_rules_say_and_the_report_builds(tmp_path):
    items, gold = dev_gold()
    refusal = {"text": "The filings provided do not contain it.", "abstained": True, "claims": [], "parse_error": None}
    judge = {f"{i['id']}:baseline": {"rejects_premise": False, "confirms_change": False, "gives_reasons": False,
                                     "says_no_reasons_given": False} for i in items if is_premise(i)}
    scores = [score_answer(i, gold[i["id"]], refusal, judge=judge.get(f"{i['id']}:baseline")) for i in items]
    expected_correct = {"unanswerable", "false_premise"}
    for i, s in zip(items, scores):
        assert s.outcome == ("correct" if i["attack_type"] in expected_correct else "missed"), (i["id"], s.outcome)
    summary = summarise(items, scores, judge)
    assert summary["abstain_rate_controls"]["k"] == 18 and summary["unsupported_claim_rate"]["k"] == 0
    runs = {i["id"]: {"answer": refusal} for i in items}
    write_sheet(items, gold, runs, scores, judge, tmp_path / "sheet.xlsx")
    assert (tmp_path / "sheet.xlsx").exists()


def test_driver_answers_with_both_years_score_correct():
    items, gold = dev_gold()
    no = {"rejects_premise": False, "confirms_change": False}
    drivers = [i for i in items if i["subtype"] == "true_premise_driver"]
    assert len(drivers) == 3
    for item in drivers:
        gg = gold[item["id"]]["gold"]
        (y1, v1), (y2, v2) = sorted(gg["true_values"].items())
        text = f"It rose from ${v1 / 1e6:,.0f} million in fiscal {y1} to ${v2 / 1e6:,.0f} million in fiscal {y2}."
        s = score_answer(item, gold[item["id"]], {"text": text, "abstained": False, "claims": []}, judge=no)
        assert s.outcome == "correct", (item["id"], s.figures)
