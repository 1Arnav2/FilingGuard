"""Fails if any agent module can reach gold labels (D-013).

Flags, in every .py file under src/filingguard/agents/:
- imports from `filingguard.eval` (the only package allowed to read gold) or any module named *gold*;
- string literals with a `gold` path segment (`data/gold`, `data\\gold`, `"gold"` in a Path join),
  which also catches reading an item's `"gold"` key.
"""

import ast
import re
from pathlib import Path

AGENTS_DIR = Path(__file__).resolve().parents[1] / "src" / "filingguard" / "agents"
GOLD_SEGMENT = re.compile(r"(^|[\\/])gold([\\/]|$)", re.IGNORECASE)


def gold_violations(source: str) -> list[str]:
    """Return a description of each gold reference found in `source`."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            names = [node.module or ""] + [f"{node.module}.{a.name}" for a in node.names]
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if GOLD_SEGMENT.search(node.value):
                found.append(f"line {node.lineno}: string {node.value!r}")
            continue
        else:
            continue
        for name in names:
            if name.startswith("filingguard.eval") or "gold" in name.lower().split("."):
                found.append(f"line {node.lineno}: import {name}")
    return found


def test_agents_package_exists():
    assert AGENTS_DIR.is_dir(), "move this test if the agents package is renamed"


def test_no_agent_module_references_gold():
    violations = {
        str(path.relative_to(AGENTS_DIR)): v
        for path in AGENTS_DIR.rglob("*.py")
        if (v := gold_violations(path.read_text(encoding="utf-8")))
    }
    assert not violations, f"agents must not reach gold labels: {violations}"


def test_checker_catches_each_pattern():
    bad = [
        'open("data/gold/labels.jsonl")',
        'p = Path("data") / "gold" / "x.json"',
        'open(r"data\\gold\\x.json")',
        'value = item["gold"]["value"]',
        "from filingguard.eval import score",
        "import filingguard.eval.score",
        "from filingguard.data import gold",
    ]
    for src in bad:
        assert gold_violations(src), f"missed: {src}"


def test_checker_allows_clean_code():
    ok = 'facts = read("data/processed/facts.parquet")\nlabel = "golden_ratio"\n'
    assert gold_violations(ok) == []


TESTSET_SEGMENT = re.compile(r"(^|[\/])testset([\/]|$)", re.IGNORECASE)


def test_no_agent_module_reads_the_test_set():
    """Agents get a question and a company from the harness; they never open the item files,
    which carry attack types and injection payloads (D-028)."""
    violations = {
        str(path.relative_to(AGENTS_DIR)): [
            f"line {n.lineno}: {n.value!r}" for n in ast.walk(ast.parse(path.read_text(encoding="utf-8")))
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and TESTSET_SEGMENT.search(n.value)
        ]
        for path in AGENTS_DIR.rglob("*.py")
    }
    assert not {k: v for k, v in violations.items() if v}, violations
    assert TESTSET_SEGMENT.search("data/testset/v1.jsonl") and not TESTSET_SEGMENT.search("testsets_note")
