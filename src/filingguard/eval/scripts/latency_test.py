"""Phase 5 step 8: latency sample (EVAL §4, D-025). The 30 test IDs recorded at the freeze
(`data/testset/latency_sample_v1.json`) run end to end, one at a time: the frozen target on the
standard API, then the frozen verifier (full mode, as in treatment). These answers are for timing
only; they go to `results/test/latency_v1.jsonl` and never replace or rescore the batch answers.

Stops before any call whose worst case would take total spend past $5.50 (owner's limit) and on any
error; the $7 cap and the Phase 5 verifier cap stay in force. As a consistency check, a latency answer
is scored with the frozen scorer only where no judge is needed (premise items are not judged here) and
compared with its batch answer's as-scored outcome.

Usage: python src/filingguard/eval/scripts/latency_test.py
"""

import json
import math
import statistics
import sys
import time
from pathlib import Path

from filingguard.agents.verifier.facts import FactStore
from filingguard.agents.verifier.verifier import Verifier, VerifierInput
from filingguard.eval import verify_dev
from filingguard.eval.dev_report import GOLD, is_premise
from filingguard.eval.dev_run import POISONED, Harness, load_items
from filingguard.eval.score import score_answer
from filingguard.llm.cache import cache_key
from filingguard.llm.client import PromptRecorder, client_from_env

SAMPLE = Path("data/testset/latency_sample_v1.json")
BASE = Path("results/test/baseline_scores_v1.jsonl")
OUT = Path("results/test/latency_v1.jsonl")
SUMMARY = Path("results/test/latency_summary_v1.json")
SPEND_LIMIT_USD = 5.50
PHASE4_VERIFIER_SPEND = 0.062305
PHASE5_VERIFIER_CAP = 0.40


def pct(values: list[float], q: float) -> float:
    """Nearest-rank percentile."""
    s = sorted(values)
    return round(s[max(0, math.ceil(q * len(s)) - 1)], 3)


def main() -> None:
    assert not OUT.exists(), "latency answers already saved; the sample runs once"
    ids = json.loads(SAMPLE.read_text(encoding="utf-8"))["ids"]
    items = {i["id"]: i for i in load_items("test", allow_test=True)}
    sample = [items[i] for i in ids]
    gold = {r["id"]: r for r in map(json.loads, GOLD.read_text(encoding="utf-8").splitlines()) if r and r["id"] in ids}
    base = {r["id"]: r for r in map(json.loads, BASE.read_text(encoding="utf-8").splitlines()) if r}
    poisoned = {r["id"]: r for r in map(json.loads, POISONED.read_text(encoding="utf-8").splitlines()) if r}
    h, llm = Harness(), client_from_env("TARGET_MODEL")
    gate = verify_dev.ModelGate(cap_usd=PHASE4_VERIFIER_SPEND + PHASE5_VERIFIER_CAP)
    verifier = Verifier(FactStore(), gate, quote_rule=True)

    prompts = {}
    for it in sample:
        rec = PromptRecorder(llm.model)
        h.agent(it, rec).answer(it["question"], it["company"])
        prompts[it["id"]] = rec.requests[0]
    cached = [i for i, (p, params) in prompts.items()
              if llm.cache.get(cache_key({"model": llm.model, "prompt": p, "params": params})) is not None]
    print(json.dumps({"sample": len(sample), "standard_answers_already_cached": cached,
                      "spend_before": round(llm.ledger.total()["cost_usd"], 6)}), flush=True)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for n, it in enumerate(sample, start=1):
        spend = llm.ledger.total()["cost_usd"]
        worst = llm.ledger.estimate(llm.model, prompts[it["id"]][0])
        if spend + worst > SPEND_LIMIT_USD:
            print(f"STOPPED before {it['id']}: spend ${spend:.4f} + worst case ${worst:.4f} would pass "
                  f"${SPEND_LIMIT_USD:.2f}; {len(sample) - n + 1} items not run", flush=True)
            break
        t0 = time.perf_counter()
        answer = h.agent(it, llm).answer(it["question"], it["company"])
        target_wall = time.perf_counter() - t0
        hits = answer.trace["retrieved"]
        chunks = verify_dev.load_chunks({x["chunk_id"] for x in hits})
        texts = []
        for x in hits:
            c = dict(chunks[x["chunk_id"]])
            if it["id"] in poisoned and c["chunk_id"] == poisoned[it["id"]]["chunk_id"]:
                c["text"] = poisoned[it["id"]]["poisoned_text"]
            texts.append(c)
        ans = {"text": answer.text, "abstained": answer.abstained, "claims": [c.__dict__ for c in answer.claims],
               "citations": [c.__dict__ for c in answer.citations], "parse_error": answer.trace["parse_error"]}
        t1 = time.perf_counter()
        verdict = verifier.verify(VerifierInput(it["question"], it["company"],
                                                {k: ans[k] for k in ("text", "abstained", "claims", "citations")}, texts))
        verifier_wall = time.perf_counter() - t1
        consistent = None
        if not is_premise(it):
            consistent = score_answer(it, gold[it["id"]], ans).outcome == base[it["id"]]["outcome"]
        row = {"id": it["id"], "type": it["attack_type"], "subtype": it["subtype"], "answer": ans,
               "target_llm_s": answer.trace["llm_latency_s"],
               "target_retrieval_plus_llm_s": answer.latency_s, "target_wall_s": round(target_wall, 3),
               "verifier_rule_s": round(verdict.rule_s, 4), "verifier_model_s": round(verdict.model_s, 3),
               "verifier_model_calls": verdict.model_calls, "verifier_wall_s": round(verifier_wall, 3),
               "end_to_end_s": round(target_wall + verifier_wall, 3), "decision": verdict.decision,
               "reasons": [r.__dict__ for r in verdict.reasons], "same_outcome_as_batch": consistent}
        rows.append(row)
        with OUT.open("ab") as f:
            f.write((json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8"))
        print(f"{n}/{len(sample)} {it['id']}: target {row['target_wall_s']}s (llm {row['target_llm_s']}s), "
              f"verifier {row['verifier_wall_s']}s ({verdict.decision}); spend ${llm.ledger.total()['cost_usd']:.4f}",
              flush=True)

    def stats(key: str) -> dict:
        v = [r[key] for r in rows if r[key] is not None]
        return {"n": len(v), "p50": pct(v, 0.50), "p95": pct(v, 0.95), "mean": round(statistics.mean(v), 3)} if v else {}

    checked = [r for r in rows if r["same_outcome_as_batch"] is not None]
    summary = {"sample": len(sample), "run": len(rows), "measured_on": "a 30-item sample (EVAL §4)",
               "standard_answers_already_cached": cached,
               "target_llm_s": stats("target_llm_s"), "target_wall_s": stats("target_wall_s"),
               "verifier_rule_s": stats("verifier_rule_s"), "verifier_model_s_when_called": {},
               "verifier_model_calls": sum(r["verifier_model_calls"] for r in rows),
               "verifier_wall_s": stats("verifier_wall_s"), "end_to_end_s": stats("end_to_end_s"),
               "consistency_with_batch": {"checked_non_premise": len(checked),
                                          "same_outcome": sum(r["same_outcome_as_batch"] for r in checked),
                                          "premise_items_not_checked": [r["id"] for r in rows if is_premise(items[r["id"]])]},
               "spend_after": round(llm.ledger.total()["cost_usd"], 6)}
    if summary["verifier_model_calls"]:
        called = [r["verifier_model_s"] for r in rows if r["verifier_model_calls"]]
        summary["verifier_model_s_when_called"] = {"n": len(called), "p50": pct(called, 0.5), "p95": pct(called, 0.95)}
    SUMMARY.write_bytes((json.dumps(summary, indent=2) + "\n").encode("utf-8"))
    print(json.dumps(summary, indent=2), flush=True)
    if len(rows) < len(sample):
        sys.exit(1)


if __name__ == "__main__":
    main()
