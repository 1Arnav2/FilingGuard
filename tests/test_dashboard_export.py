"""The dashboard export (D-075) is reproducible from the frozen inputs and matches the Phase 5 files."""

import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "filingguard" / "eval" / "scripts"))

import export_dashboard  # noqa: E402

ITEMS = ROOT / "results" / "dashboard" / "items_v1.jsonl"
META = ROOT / "results" / "dashboard" / "meta_v1.json"


def committed() -> tuple[list[dict], dict]:
    rows = [json.loads(line) for line in ITEMS.read_text(encoding="utf-8").splitlines() if line.strip()]
    return rows, json.loads(META.read_text(encoding="utf-8"))


def test_export_rebuilds_byte_for_byte(monkeypatch):
    monkeypatch.chdir(ROOT)
    rows, meta = export_dashboard.build()
    assert "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows) == ITEMS.read_text(encoding="utf-8")
    assert json.dumps(meta, indent=2, ensure_ascii=False) + "\n" == META.read_text(encoding="utf-8")


def test_input_hashes_match_the_files():
    _, meta = committed()
    for path, digest in meta["inputs_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, path


def test_corrected_baseline_matches_the_corrected_summary_file():
    rows, _ = committed()
    corrected = json.loads((ROOT / "results/test/baseline_summary_corrected_v1.json").read_text(encoding="utf-8"))
    for attack_type, block in corrected["by_type"].items():
        counts: dict[str, int] = {}
        for r in rows:
            if r["attack_type"] == attack_type:
                o = r["outcomes"]["corrected"]["baseline"]["outcome"]
                counts[o] = counts.get(o, 0) + 1
        assert counts == block["outcome"], attack_type


def test_corrections_come_from_the_corrections_file():
    rows, _ = committed()
    fixes = {c["item"]: c for c in json.loads(
        (ROOT / "results/test/baseline_corrections_v1.json").read_text(encoding="utf-8"))["corrections"]}
    for r in rows:
        if r["id"] in fixes:
            assert r["correction"]["corrected"] == fixes[r["id"]]["corrected"]
            assert [r["outcomes"]["as_scored"]["baseline"][k] for k in ("outcome", "label")] == fixes[r["id"]]["as_scored"]
            if r["verdict"]["full"]["decision"] != "block":
                assert [r["outcomes"]["corrected"]["baseline"][k] for k in ("outcome", "label")] == fixes[r["id"]]["corrected"]
