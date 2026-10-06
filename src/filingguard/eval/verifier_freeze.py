"""Freeze record for the verifier (tag `verifier-v1`, D-060): hashes of its code, the detector's
patterns and the final prompt. `tests/test_verifier_frozen.py` fails if any of them changes.

The shared number parser (`figures.py`) and the answer schema are pinned with the verifier code,
because the verifier's behaviour depends on them.

Usage: python -m filingguard.eval.verifier_freeze   (writes the manifest; run once, at the freeze)
"""

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from filingguard.agents.verifier import instructions
from filingguard.agents.verifier.verifier import PROMPT_DIR, PROMPT_VERSION

SRC = Path("src/filingguard")
MANIFEST = Path("results/verifier/freeze_v1.json")
CODE_FILES = (*sorted((SRC / "agents" / "verifier").glob("*.py")), SRC / "figures.py", SRC / "agents" / "schema.py")
DETECTOR_PATTERNS = ("A", "B", "C", "D_CLAIM", "D_REPLACE", "WITHHOLD", "CODE", "NOT_CODE", "QUOTED", "AFTER_DIRECTIVE")


def sha256_text_file(path: Path) -> str:
    """SHA-256 of a text file with line endings normalised to LF."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def detector_sha256() -> str:
    """SHA-256 of the detector's patterns and flags, in a fixed order."""
    pats = {name: [getattr(instructions, name).pattern, int(getattr(instructions, name).flags & ~re.UNICODE)]
            for name in DETECTOR_PATTERNS}
    return hashlib.sha256(json.dumps(pats, sort_keys=True).encode("utf-8")).hexdigest()


def snapshot() -> dict[str, Any]:
    prompt = PROMPT_DIR / f"{PROMPT_VERSION}.txt"
    return {"tag": "verifier-v1", "prompt_version": PROMPT_VERSION,
            "prompt_sha256": hashlib.sha256(prompt.read_bytes()).hexdigest(),
            "detector_patterns_sha256": detector_sha256(),
            "code_sha256": {p.as_posix(): sha256_text_file(p) for p in CODE_FILES}}


def main() -> None:
    MANIFEST.write_text(json.dumps(snapshot(), indent=2) + "\n", encoding="utf-8")
    print(MANIFEST.read_text(encoding="utf-8"))
    print("manifest sha256", sha256_text_file(MANIFEST))


if __name__ == "__main__":
    main()
