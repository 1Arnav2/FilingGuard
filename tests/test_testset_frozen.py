"""Fails if any file of the frozen test set v1 changes (EVAL §10 step 1, tag `testset-v1`).

The manifest's own hash is pinned here, and the manifest pins every frozen file, so changing a
file and updating the manifest to match still fails.
"""

import json
from collections import Counter
from pathlib import Path

from filingguard.redteam.freeze import FROZEN_FILES, MANIFEST, item_set_hash, sha256_file

MANIFEST_SHA256 = "cb64b6da012087304de54129b4d858b358b46d88cdcaa492d67966a3a4e758a0"


def _manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def _jsonl(path: str) -> list[dict]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def test_manifest_is_unchanged():
    assert sha256_file(MANIFEST) == MANIFEST_SHA256


def test_every_frozen_file_matches_its_recorded_hash():
    files = _manifest()["files"]
    assert set(files) == {p.as_posix() for p in FROZEN_FILES}
    changed = [path for path, digest in files.items() if sha256_file(Path(path)) != digest]
    assert not changed, f"frozen files changed: {changed}"


def test_item_set_and_split_are_the_recorded_ones():
    m = _manifest()
    items = _jsonl("data/testset/v1.jsonl")
    gold = {g["id"]: g["spec_id"] for g in _jsonl("data/gold/gold_v1.jsonl")}
    assert item_set_hash({i["id"]: gold[i["id"]] for i in items}) == m["item_set_sha256"]
    assert Counter(i["split"] for i in items) == {"dev": 90, "test": 210}
    latency = json.loads(Path("data/testset/latency_sample_v1.json").read_text(encoding="utf-8"))
    split = {i["id"]: i["split"] for i in items}
    assert len(latency["ids"]) == 30 and all(split[i] == "test" for i in latency["ids"])
