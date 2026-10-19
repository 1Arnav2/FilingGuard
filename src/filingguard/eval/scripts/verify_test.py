"""Phase 5 steps 6 and 7 driver (owner's go-ahead). Frozen code only: the verifier (`verifier-v1`,
prompt `verifier_v2`), `verify_dev.ModelGate`, `score.score_answer`. Never calls the target.

verify: one run of the frozen verifier in the plan's two modes (full; quote rule off) on the 210
saved test answers and the frozen test seeded set (hash checked first), in one seeded random order,
as on dev. The model gate allows $0.40 of Phase 5 verifier spend on top of the $0.0623 spent in
Phase 4. Any exception stops the run (no reruns). Writes results/test/verifier_v1.jsonl.

score: treatment scoring from the saved verdicts (full mode, natural answers): a block is an
abstention; a passed or flagged answer keeps its baseline score and judge decision. No judge calls.
Writes results/test/treatment_scores_v1.jsonl and results/test/verifier_treatment_summary_v1.json.

Usage: python verify_test.py {verify,score}
"""
import hashlib
import json
import random
import statistics
import sys
from collections import Counter
from pathlib import Path

from filingguard.agents.verifier.facts import FactStore
from filingguard.agents.verifier.verifier import PROMPT_VERSION, Verifier, VerifierInput, prompt_sha256
from filingguard.eval import verify_dev
from filingguard.eval.dev_report import GOLD
from filingguard.eval.dev_run import POISONED, load_items
from filingguard.eval.score import Score, score_answer
from filingguard.eval.stats import wilson

RUNS = Path("results/runs/test_target_v1.jsonl")
SEEDED = Path("results/test/seeded_v1.jsonl")
SEEDED_MANIFEST = Path("results/test/seeded_freeze_v1.json")
BASE = Path("results/test/baseline_scores_v1.jsonl")
CORRECTIONS = Path("results/test/baseline_corrections_v1.json")
JUDGE = Path("results/judge/test_judge_v1.jsonl")
VERDICTS = Path("results/test/verifier_v1.jsonl")
TREAT = Path("results/test/treatment_scores_v1.jsonl")
SUMMARY = Path("results/test/verifier_treatment_summary_v1.json")
PHASE4_VERIFIER_SPEND = 0.062305
PHASE5_VERIFIER_CAP = 0.40
MACRO = ("T1", "T3", "T4", "T5", "T6")


def load():
    items = load_items("test", allow_test=True)
    ids = {i["id"] for i in items}
    gold = {r["id"]: r for r in map(json.loads, GOLD.read_text(encoding="utf-8").splitlines()) if r and r["id"] in ids}
    runs = {r["id"]: r for r in map(json.loads, RUNS.read_text(encoding="utf-8").splitlines()) if r}
    assert set(runs) == ids == set(gold) and len(ids) == 210
    return items, gold, runs


def seeded_rows() -> list[dict]:
    m = json.loads(SEEDED_MANIFEST.read_text(encoding="utf-8"))
    data = SEEDED.read_bytes().replace(b"\r\n", b"\n")
    if hashlib.sha256(data).hexdigest() != m["sha256"]:
        raise SystemExit("seeded set hash does not match its freeze manifest; stopping")
    return [r for r in map(json.loads, data.decode("utf-8").splitlines()) if r and r["kept"]]


def jobs(items, runs) -> list[dict]:
    """Verifier inputs for every natural answer and every kept seeded copy, keyed opaquely (as on dev)."""
    poisoned = {r["id"]: r for r in map(json.loads, POISONED.read_text(encoding="utf-8").splitlines()) if r}
    chunks = verify_dev.load_chunks({h["chunk_id"] for r in runs.values() for h in r["retrieved"]})
    by_id = {i["id"]: i for i in items}

    def retrieved(item_id):
        out = []
        for h in runs[item_id]["retrieved"]:
            c = dict(chunks[h["chunk_id"]])
            if item_id in poisoned and c["chunk_id"] == poisoned[item_id]["chunk_id"]:
                c["text"] = poisoned[item_id]["poisoned_text"]
            out.append(c)
        return out

    def answer_of(a):
        return {k: a.get(k) for k in ("text", "abstained", "claims", "citations")}

    out = [{"key": i["id"], "kind": "natural", "source_id": i["id"], "transform": None,
            "input": VerifierInput(i["question"], i["company"], answer_of(runs[i["id"]]["answer"]), retrieved(i["id"]))}
           for i in items]
    for r in seeded_rows():
        it = by_id[r["source_id"]]
        a = {**answer_of(runs[it["id"]]["answer"]), **{k: r["answer"][k] for k in ("text", "claims")}}
        out.append({"key": r["key"], "kind": "seeded", "source_id": it["id"], "transform": r["transform"],
                    "input": VerifierInput(it["question"], it["company"], a, retrieved(it["id"]))})
    random.Random(verify_dev.ORDER_SEED).shuffle(out)
    return out


def verify() -> None:
    assert not VERDICTS.exists(), "verdicts already saved; the verifier runs once"
    items, gold, runs = load()
    js = jobs(items, runs)
    gate = verify_dev.ModelGate(cap_usd=PHASE4_VERIFIER_SPEND + PHASE5_VERIFIER_CAP)
    before = gate.spent()
    store = FactStore()
    rows = []
    for mode, quote_rule in (("full", True), ("quote_off", False)):
        v = Verifier(store, gate, quote_rule=quote_rule, prompt_version=PROMPT_VERSION)
        for j in js:
            verdict = v.verify(j["input"])
            rows.append({k: j[k] for k in ("key", "kind", "source_id", "transform")} | {"mode": mode} | verdict.to_dict())
        print(f"mode {mode}: {len(js)} answers verified; verifier spend so far ${gate.spent() - before:.4f}", flush=True)
    VERDICTS.parent.mkdir(parents=True, exist_ok=True)
    VERDICTS.write_bytes("".join(json.dumps(r) + "\n" for r in rows).encode("utf-8"))
    print(json.dumps({"rows": len(rows), "natural": sum(r["kind"] == "natural" for r in rows) // 2,
                      "seeded": sum(r["kind"] == "seeded" for r in rows) // 2,
                      "model_calls": sum(r["model_calls"] for r in rows),
                      "verifier_spend_usd": round(gate.spent() - before, 6),
                      "prompt": PROMPT_VERSION, "prompt_sha256": prompt_sha256()}), flush=True)


def _rate(k, n):
    if not n:
        return {"k": 0, "n": 0, "rate": None, "wilson95": None}
    lo, hi = wilson(k, n)
    return {"k": k, "n": n, "rate": round(k / n, 4), "wilson95": [round(lo, 4), round(hi, 4)]}


def score() -> None:
    items, gold, runs = load()
    by_id = {i["id"]: i for i in items}
    rows = [json.loads(l) for l in VERDICTS.read_text(encoding="utf-8").splitlines() if l.strip()]
    judge = {r["key"]: r for r in map(json.loads, JUDGE.read_text(encoding="utf-8").splitlines()) if r}
    base = {d["id"]: Score(**d) for d in map(json.loads, BASE.read_text(encoding="utf-8").splitlines()) if d}
    fixes = {c["item"]: c for c in json.loads(CORRECTIONS.read_text(encoding="utf-8"))["corrections"]}

    def corrected(s: Score) -> Score:
        c = fixes.get(s.id)
        if c is None or "blocked" in s.notes:
            return s
        s = Score(**s.to_dict())
        s.outcome, s.label = c["corrected"]
        s.abstained, s.returned, s.gives_figure = False, True, True
        if c.get("scale_not_followed") is not None:
            s.scale_not_followed = c["scale_not_followed"]
        s.notes = s.notes + [f"corrected under D-071: {c['pattern']}"]
        return s

    natural_full = {r["source_id"]: r for r in rows if r["kind"] == "natural" and r["mode"] == "full"}
    treat = {}
    for i in items:
        r = natural_full[i["id"]]
        blocked = r["decision"] == "block"
        treat[i["id"]] = score_answer(i, gold[i["id"]], runs[i["id"]]["answer"], blocked=blocked,
                                      judge=judge.get(f"{i['id']}:baseline"))
        if not blocked:
            assert treat[i["id"]].outcome == base[i["id"]].outcome, f"{i['id']}: unblocked treatment differs"
    TREAT.write_bytes("".join(json.dumps(treat[i["id"]].to_dict(), ensure_ascii=False) + "\n"
                              for i in items).encode("utf-8"))
    base_c = {k: corrected(v) for k, v in base.items()}
    treat_c = {k: corrected(v) for k, v in treat.items()}

    out = {"prompt": PROMPT_VERSION, "prompt_sha256": prompt_sha256(), "modes": {}}
    for mode in ("full", "quote_off"):
        mr = [r for r in rows if r["mode"] == mode]
        seeded = [r for r in mr if r["kind"] == "seeded"]
        natural = [r for r in mr if r["kind"] == "natural"]
        per = {t: _rate(sum(r["decision"] == "block" for r in seeded if r["transform"] == t),
                        sum(r["transform"] == t for r in seeded)) for t in sorted({r["transform"] for r in seeded})}
        macro = [per[t]["rate"] for t in MACRO if per.get(t, {}).get("n")]
        called = [r for r in mr if r["model_calls"]]
        out["modes"][mode] = {
            "detection_by_transform": per,
            "detection_macro_T1_T3_T4_T5_T6": round(statistics.mean(macro), 4),
            "detection_pooled_macro_set": _rate(sum(r["decision"] == "block" for r in seeded if r["transform"] in MACRO),
                                                sum(r["transform"] in MACRO for r in seeded)),
            "seeded_flagged_not_blocked": sum(r["decision"] == "flag" for r in seeded),
            "false_block_correct_as_scored": _rate(sum(r["decision"] == "block" for r in natural
                                                       if base[r["source_id"]].outcome == "correct"),
                                                   sum(base[r["source_id"]].outcome == "correct" for r in natural)),
            "false_block_correct_corrected": _rate(sum(r["decision"] == "block" for r in natural
                                                       if base_c[r["source_id"]].outcome == "correct"),
                                                   sum(base_c[r["source_id"]].outcome == "correct" for r in natural)),
            "natural_blocked": sorted(r["source_id"] for r in natural if r["decision"] == "block"),
            "natural_flagged": sorted(r["source_id"] for r in natural if r["decision"] == "flag"),
            "blocks_by_reason_and_basis": dict(Counter(f"{x['code']} [{x['basis']}]" for r in mr for x in r["reasons"]
                                                       if x["blocking"])),
            "model_calls": sum(r["model_calls"] for r in mr),
            "rule_s_mean": round(statistics.mean(r["rule_s"] for r in mr), 4),
            "rule_s_p95": round(sorted(r["rule_s"] for r in mr)[int(0.95 * len(mr))], 4),
            "model_s_mean_when_called": round(statistics.mean(r["model_s"] for r in called), 3) if called else None,
        }
    natural = {r["source_id"]: r for r in rows if r["kind"] == "natural" and r["mode"] == "full"}
    out["natural_blocked_or_flagged"] = [
        {"item": k, "type": by_id[k]["attack_type"], "subtype": by_id[k]["subtype"], "decision": r["decision"],
         "reasons": [f"{x['code']} [{x['basis']}]{' (blocking)' if x['blocking'] else ''}: {x['detail']}"
                     for x in r["reasons"]],
         "baseline_as_scored": [base[k].outcome, base[k].label], "baseline_corrected": [base_c[k].outcome, base_c[k].label]}
        for k, r in sorted(natural.items()) if r["decision"] != "pass"]
    controls = [i["id"] for i in items if i["attack_type"] == "control"]
    out["control_abstentions_added"] = sum(1 for k in controls if natural[k]["decision"] == "block"
                                           and not base[k].abstained and base[k].outcome != "missed")

    def table(scores):
        return {t: dict(Counter(scores[i["id"]].outcome for i in items if i["attack_type"] == t))
                for t in sorted({i["attack_type"] for i in items})} | {"total": dict(Counter(s.outcome for s in scores.values()))}

    out["outcomes"] = {"baseline_as_scored": table(base), "treatment_as_scored": table(treat),
                       "baseline_corrected": table(base_c), "treatment_corrected": table(treat_c)}
    for name, b, t in (("as_scored", base, treat), ("corrected", base_c, treat_c)):
        should = [k for k in b if b[k].outcome == "unsupported"]
        blocked = [k for k in b if natural[k]["decision"] == "block"]
        out[f"precision_recall_{name}"] = {"blocked": len(blocked), "correctly_blocked": sum(b[k].outcome == "unsupported" for k in blocked),
                                          "should_block": len(should), "recall_k": sum(natural[k]["decision"] == "block" for k in should)}
    SUMMARY.write_bytes((json.dumps(out, indent=2) + "\n").encode("utf-8"))
    print(json.dumps(out, indent=1)[:6000])


if __name__ == "__main__":
    {"verify": verify, "score": score}[sys.argv[1]]()
