"""Premise judge (EVAL §3, D-042): one call per answer to a premise item, on the standard API.

The judge sees the question, the premise, the reported values, the reasons passages and one
answer's text. It never sees the condition, the attack type, whether the premise is true, the
item ID or the other condition's answer. The prompt's hash is checked before any call.
"""

import hashlib
import json
import random
from pathlib import Path
from typing import Any

from filingguard.llm.client import LLMClient

PROMPT = Path("src/filingguard/eval/prompts/premise_judge_v1.txt")
RECORD = Path("results/judge/premise_judge_v1.json")
INPUTS = Path("data/gold/judge_inputs_v1.json")
ORDER_SEED = "20261005-judge"
FIELDS = ("rejects_premise", "confirms_change", "gives_reasons", "reasons_in_filing", "says_no_reasons_given", "reason")


def checked_prompt() -> str:
    """The judge prompt, after checking it against its recorded hash (D-042)."""
    raw = PROMPT.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    recorded = json.loads(RECORD.read_text(encoding="utf-8"))["sha256"]
    inputs_hash = json.loads(INPUTS.read_text(encoding="utf-8"))["prompt_sha256"]
    if not digest == recorded == inputs_hash:
        raise RuntimeError(f"judge prompt hash {digest[:8]} does not match the recorded {recorded[:8]}")
    return raw.decode("utf-8")


def render(template: str, question: str, entry: dict[str, Any], answer_text: str) -> str:
    """Fill the prompt for one answer. No passages renders as "(none)"."""
    reasons = "\n\n---\n\n".join(entry["reasons"]) if entry["reasons"] else "(none)"
    return template.format(question=question, premise=entry["premise"], values=entry["values"], reasons=reasons,
                           answer=answer_text)


def parse(text: str) -> dict[str, Any]:
    data = json.loads(text)
    return {k: data.get(k) for k in FIELDS}


def judge_answers(requests: list[dict[str, Any]], llm: LLMClient) -> dict[str, dict[str, Any]]:
    """Judge each request ({key, question, spec_id, answer_text}) in one seeded random order.
    Returns the decision per key, with `error` set if the reply was not valid JSON."""
    template = checked_prompt()
    entries = json.loads(INPUTS.read_text(encoding="utf-8"))["items"]
    order = sorted(requests, key=lambda r: r["key"])
    random.Random(ORDER_SEED).shuffle(order)
    out = {}
    for r in order:
        prompt = render(template, r["question"], entries[r["spec_id"]], r["answer_text"])
        response = llm.generate(prompt, purpose="judge", temperature=0, response_mime_type="application/json")
        try:
            decision = parse(response.text)
        except (json.JSONDecodeError, AttributeError) as exc:
            decision = {"error": f"invalid JSON: {exc}"}
        decision["prompt_sha256"] = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        decision["cached"] = response.cached
        out[r["key"]] = decision
    return out
