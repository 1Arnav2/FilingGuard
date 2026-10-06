"""Fails if the frozen verifier changes (tag `verifier-v1`, D-060; re-frozen in D-061): its code,
the shared number parser, the detector's patterns or the final prompt.

The manifest's own hash is pinned here, and the manifest pins every frozen part, so changing a
file and updating the manifest to match still fails.
"""

import json

from filingguard.eval.verifier_freeze import MANIFEST, sha256_text_file, snapshot

MANIFEST_SHA256 = "17f2d78a7f547180a51bf8b5d5a3d556756e50b82dc26b55c00dee336b829df2"


def test_manifest_is_unchanged():
    assert sha256_text_file(MANIFEST) == MANIFEST_SHA256


def test_verifier_matches_its_freeze_record():
    recorded = json.loads(MANIFEST.read_text(encoding="utf-8"))
    now = snapshot()
    assert now["prompt_version"] == recorded["prompt_version"] == "verifier_v2"
    assert now["prompt_sha256"] == recorded["prompt_sha256"]
    assert now["detector_patterns_sha256"] == recorded["detector_patterns_sha256"]
    changed = sorted(k for k in set(now["code_sha256"]) | set(recorded["code_sha256"])
                     if now["code_sha256"].get(k) != recorded["code_sha256"].get(k))
    assert not changed, f"frozen verifier files changed: {changed}"
