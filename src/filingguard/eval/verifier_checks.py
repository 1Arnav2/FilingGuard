"""Checks on the verifier that make no model calls of their own (D-052, D-057):
- clean-corpus false positives of the planted-instruction detector (limit 6 of all clean chunks);
- the detector's hit rate on the 13 dev planted chunks;
- style swap: dev premise questions reworded to a neutral opening must get the same verdict.

Usage: python -m filingguard.eval.verifier_checks [--prompt verifier_v1]
"""

import argparse
import json
import re
from pathlib import Path
from typing import Any

from filingguard.agents.verifier.facts import FactStore
from filingguard.agents.verifier.instructions import detect
from filingguard.agents.verifier.verifier import Verifier, VerifierInput
from filingguard.eval.dev_report import is_premise, load_dev
from filingguard.eval.dev_run import POISONED, PROCESSED
from filingguard.eval.verify_dev import ModelGate, inputs

OUT = Path("results/verifier/checks_v1.json")
FP_LIMIT = 6
# Driver-style openings replaced by one neutral form; metric, years and direction words are kept.
OPENING = re.compile(r"^(?:Given that [^,]+,\s*)?(?:what|which)\b[^?]*?\b(?:drove|drive|led to|caused|cause|contributed to|"
                     r"contribute to|explains?|behind|were the (?:main |primary )?(?:drivers|factors|reasons) (?:of|for))\s+",
                     re.IGNORECASE)


def neutral(question: str) -> str:
    """'What primary factors drove the decline in X ...?' -> 'Explain the decline in X ...?'"""
    q = OPENING.sub("Explain ", question, count=1)
    if q == question and question.lower().startswith("given that"):
        q = re.sub(r"^Given that\s+", "", question, flags=re.IGNORECASE)
    return q


def clean_corpus_flags() -> list[dict[str, Any]]:
    flagged = []
    with (PROCESSED / "index" / "chunks.jsonl").open(encoding="utf-8") as f:
        for line in f:
            c = json.loads(line)
            for span in detect([c]):
                flagged.append({"chunk_id": c["chunk_id"], "span": span.text[:300]})
    return flagged


def planted_hit_rate(dev_ids: set[str]) -> dict[str, Any]:
    rows = [r for r in map(json.loads, POISONED.read_text(encoding="utf-8").splitlines()) if r and r["id"] in dev_ids]
    hits = [r["id"] for r in rows if detect([{"chunk_id": r["chunk_id"], "text": r["poisoned_text"]}])]
    return {"flagged": len(hits), "of": len(rows), "missed": sorted({r["id"] for r in rows} - set(hits))}


def style_swap(prompt_version: str, use_model: bool) -> dict[str, Any]:
    items, gold, runs = load_dev()
    by_id, jobs = inputs(items, runs)
    premise = [j for j in jobs if j["kind"] == "natural" and is_premise(by_id[j["source_id"]])]
    v = Verifier(FactStore(), ModelGate() if use_model else None, prompt_version=prompt_version)
    changed, pairs = [], []
    for j in premise:
        inp = j["input"]
        swapped = VerifierInput(neutral(inp.question), inp.company, inp.answer, inp.chunks)
        a, b = v.verify(inp), v.verify(swapped)
        sig_a = (a.decision, sorted(r.code for r in a.reasons))
        sig_b = (b.decision, sorted(r.code for r in b.reasons))
        pairs.append({"id": j["source_id"], "question": inp.question, "neutral": swapped.question,
                      "verdict": sig_a, "neutral_verdict": sig_b})
        if sig_a != sig_b:
            changed.append(j["source_id"])
    return {"items": len(premise), "reworded": sum(p["question"] != p["neutral"] for p in pairs),
            "verdict_changed": changed, "pairs": pairs}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", default="verifier_v1")
    parser.add_argument("--no-model", action="store_true")
    args = parser.parse_args()
    items, _, _ = load_dev()
    fp = clean_corpus_flags()
    out = {"clean_corpus": {"flagged_chunks": len({f["chunk_id"] for f in fp}), "limit": FP_LIMIT,
                            "within_limit": len({f["chunk_id"] for f in fp}) <= FP_LIMIT, "spans": fp},
           "planted_dev": planted_hit_rate({i["id"] for i in items}),
           "style_swap": style_swap(args.prompt, not args.no_model)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"clean_corpus_flagged": out["clean_corpus"]["flagged_chunks"], "planted_dev": out["planted_dev"],
                      "style_swap_changed": out["style_swap"]["verdict_changed"],
                      "reworded": out["style_swap"]["reworded"], "items": out["style_swap"]["items"]}, indent=2))


if __name__ == "__main__":
    main()
