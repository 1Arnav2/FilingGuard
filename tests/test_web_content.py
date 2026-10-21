"""Every number in the dashboard's content files traces to a results/ file (Phase 6b)."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "web" / "content"
SOURCES = {"summary": ROOT / "results" / "summary.json", "meta": ROOT / "results" / "dashboard" / "meta_v1.json"}
PLACEHOLDER = re.compile(r"\{(summary|meta):([A-Za-z0-9_.]+)\}")
# Identifiers that contain digits but are not results: decision and hurdle ids, EVAL sections, 10-K.
REFERENCE = re.compile(r"\b(?:D|H)-\d{3}\b|§\d+|\b10-K\b")
NUMBER = re.compile(r"\d[\d,.]*%?")


def resolve(source: str, path: str):
    node = json.loads(SOURCES[source].read_text(encoding="utf-8"))
    for key in path.split("."):
        node = node[key]
    return node


def test_headline_numbers_match_summary():
    headline = json.loads((CONTENT / "headline.json").read_text(encoding="utf-8"))
    declared = {n["shown"] for n in headline["numbers"]}
    assert set(NUMBER.findall(REFERENCE.sub("", headline["text"]))) == declared
    for n in headline["numbers"]:
        assert n["file"] == "results/summary.json" and n["shown"] in headline["text"]
        value = resolve("summary", n["path"])
        shown = f"{round(value * 100)}%" if n["as"] == "percent" else str(value)
        assert shown == n["shown"], (n, value)


def test_method_numbers_are_all_placeholders_that_resolve():
    method = json.loads((CONTENT / "method.json").read_text(encoding="utf-8"))
    paragraphs = [p for s in method["sections"] for p in s["paragraphs"]]
    assert paragraphs
    for text in paragraphs:
        for source, path in PLACEHOLDER.findall(text):
            resolve(source, path)
        bare = NUMBER.findall(REFERENCE.sub("", PLACEHOLDER.sub("", text)))
        assert not bare, (bare, text)
