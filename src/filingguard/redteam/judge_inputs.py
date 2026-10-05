"""Inputs for the premise judge (EVAL §3, D-042), one entry per premise item.

Every `false_premise` item and every true-premise driver control gets the same fields, so the
judge cannot tell the two kinds apart: the premise, the reported values for the two years,
and the filing passages that state the reasons for the change (empty if the reasons check
found none). The file lives under `data/gold/`, which only `eval/` reads; no agent may.
"""

import hashlib
import json
from pathlib import Path

from filingguard.redteam.corpus import Corpus

PROMPT = Path("src/filingguard/eval/prompts/premise_judge_v1.txt")
REASONS = Path("data/gold/draft/reasons_check_v3.json")
OUT = Path("data/gold/judge_inputs_v1.json")
PASSAGE_CHARS = 1200


def prompt_sha256(path: Path = PROMPT) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def passage(corpus: Corpus, accession: str, offset: int) -> str:
    """The paragraph holding `offset`, continued over following lines (bullets) up to a blank
    line, at most PASSAGE_CHARS characters."""
    text = corpus.text(accession)
    start = text.rfind("\n", 0, offset) + 1
    end = text.find("\n\n", start)
    end = len(text) if end == -1 else end
    return text[start: min(end, start + PASSAGE_CHARS)].strip()


def _money(value: float, unit: str) -> str:
    if unit == "USD/shares":
        return f"${value:,.2f} per share"
    return f"${value / 1e6:,.0f} million"


def build(gold_rows: list[dict], items: dict[str, dict], corpus: Corpus) -> dict:
    """Judge inputs keyed by spec id, for every premise item in the draft."""
    reasons = json.loads(REASONS.read_text(encoding="utf-8"))
    out = {}
    for g in gold_rows:
        item = items[g["id"]]
        if item["attack_type"] != "false_premise" and item["subtype"] != "true_premise_driver":
            continue
        gg = g["gold"]
        values = "; ".join(f"fiscal {y}: {_money(v, gg['unit'])}" for y, v in sorted(gg["true_values"].items()))
        loc = reasons["passages"].get(g["id"])
        out[g["spec_id"]] = {
            "draft_id": g["id"],
            "premise": gg["premise"],
            "values": values,
            "reasons": [passage(corpus, loc["accession"], loc["offset"])] if loc else [],
        }
    return {"prompt": PROMPT.as_posix(), "prompt_sha256": prompt_sha256(), "items": out}
