"""Committed Phase 5 results, loaded once for the read-only dashboard API.

Reads only files under `results/` (the directory is `FILINGGUARD_RESULTS`, default `results`
relative to the working directory). No model calls, no gold labels, nothing written.
"""

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

SUMMARY = "summary.json"
BASELINE = "test/baseline_scores_v1.jsonl"
TREATMENT = "test/treatment_scores_v1.jsonl"
CORRECTIONS = "test/baseline_corrections_v1.json"
VERDICTS = "test/verifier_v1.jsonl"
ANSWERS = "runs/test_target_v1.jsonl"


@dataclass(frozen=True)
class Results:
    """Everything the routes serve, keyed by item id where per item."""

    summary: dict[str, Any]
    order: list[str]
    answers: dict[str, dict[str, Any]]
    scores: dict[str, dict[str, dict[str, dict[str, Any]]]]  # basis -> condition -> id -> score row
    verdicts: dict[str, dict[str, dict[str, Any]]]  # mode -> id -> natural verdict row
    corrections: dict[str, dict[str, Any]]


def results_dir() -> Path:
    """The results directory the API reads."""
    return Path(os.environ.get("FILINGGUARD_RESULTS", "results"))


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def overlay(rows: dict[str, dict[str, Any]], fixes: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """The D-071 corrected basis, as the Phase 5 summary applies it: a fix replaces outcome and label
    unless the verifier blocked the answer."""
    out = {}
    for item_id, row in rows.items():
        fix = fixes.get(item_id)
        if fix is None or "blocked" in row["notes"]:
            out[item_id] = row
            continue
        outcome, label = fix["corrected"]
        out[item_id] = {**row, "outcome": outcome, "label": label, "abstained": False, "returned": True,
                        "gives_figure": True}
    return out


@lru_cache(maxsize=1)
def load() -> Results:
    """Read the committed results once per process."""
    root = results_dir()
    answers = {r["id"]: r for r in _jsonl(root / ANSWERS)}
    baseline = {r["id"]: r for r in _jsonl(root / BASELINE)}
    treatment = {r["id"]: r for r in _jsonl(root / TREATMENT)}
    fixes = {c["item"]: c for c in _json(root / CORRECTIONS)["corrections"]}
    verdicts: dict[str, dict[str, dict[str, Any]]] = {"full": {}, "quote_off": {}}
    for row in _jsonl(root / VERDICTS):
        if row["kind"] == "natural":
            verdicts[row["mode"]][row["source_id"]] = row
    return Results(
        summary=_json(root / SUMMARY),
        order=list(baseline),
        answers=answers,
        scores={"as_scored": {"baseline": baseline, "treatment": treatment},
                "corrected": {"baseline": overlay(baseline, fixes), "treatment": overlay(treatment, fixes)}},
        verdicts=verdicts,
        corrections=fixes,
    )
