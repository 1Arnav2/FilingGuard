"""Fails if the frozen test seeded-error set changes (Phase 5 step 5, D-072). The manifest's own hash
is pinned here, and the manifest pins the seeded file's hash, so changing the file and updating the
manifest to match still fails."""

import hashlib
import json
from pathlib import Path

MANIFEST = Path("results/test/seeded_freeze_v1.json")
MANIFEST_SHA256 = "171d5e715b201603f6c6d770ddfcdbad78760dd9714bf6d02a0a86f52d1f0c7f"


def test_manifest_is_unchanged():
    assert hashlib.sha256(MANIFEST.read_bytes().replace(b"\r\n", b"\n")).hexdigest() == MANIFEST_SHA256


def test_seeded_file_matches_its_manifest():
    m = json.loads(MANIFEST.read_text(encoding="utf-8"))
    data = Path(m["file"]).read_bytes().replace(b"\r\n", b"\n")
    assert hashlib.sha256(data).hexdigest() == m["sha256"]
    rows = [json.loads(line) for line in data.decode("utf-8").splitlines() if line.strip()]
    assert len(rows) == m["rows"] and sum(r["kept"] for r in rows) == m["kept"]
    assert len({r["key"] for r in rows}) == len(rows)
