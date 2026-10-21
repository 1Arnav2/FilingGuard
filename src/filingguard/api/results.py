"""Committed results, loaded once for the read-only dashboard API.

Reads only files under `results/` (the directory is `FILINGGUARD_RESULTS`, default `results`
relative to the working directory): `summary.json` and the per-item dashboard export written by
`eval/scripts/export_dashboard.py` (D-075). No model calls, nothing computed, nothing written.
"""

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

SUMMARY = "summary.json"
ITEMS = "dashboard/items_v1.jsonl"
META = "dashboard/meta_v1.json"


@dataclass(frozen=True)
class Results:
    """Everything the routes serve."""

    summary: dict[str, Any]
    meta: dict[str, Any]
    items: dict[str, dict[str, Any]]  # id -> export row, in id order


def results_dir() -> Path:
    """The results directory the API reads."""
    return Path(os.environ.get("FILINGGUARD_RESULTS", "results"))


def _json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load() -> Results:
    """Read the committed results once per process."""
    root = results_dir()
    rows = [json.loads(line) for line in (root / ITEMS).read_text(encoding="utf-8").splitlines() if line.strip()]
    return Results(summary=_json(root / SUMMARY), meta=_json(root / META), items={r["id"]: r for r in rows})
