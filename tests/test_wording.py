"""Wording guards for the README and the site copy."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = [ROOT / "README.md", *sorted((ROOT / "web" / "content").glob("*.json"))]


def test_no_seven_attack_types():
    """Control is a control group, not an attack type: there are six attack types plus controls."""
    wrong = re.compile(r"\b(?:7|seven)\s+attack\s+types\b", re.I)
    for path in FILES:
        assert not wrong.search(path.read_text(encoding="utf-8")), path.name
