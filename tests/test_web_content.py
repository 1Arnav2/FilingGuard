"""Every number in the dashboard's content files traces to a results/ file (Phase 6b, 6c)."""

import json
import re
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "web" / "content"
SOURCES = {"summary": ROOT / "results" / "summary.json", "meta": ROOT / "results" / "dashboard" / "meta_v1.json"}
ITEMS = ROOT / "results" / "dashboard" / "items_v1.jsonl"
PLACEHOLDER = re.compile(r"\{(summary|meta):([A-Za-z0-9_.{}]+?)\}(?!\})")
# Identifiers that contain digits but are not results: decision and hurdle ids, EVAL sections, 10-K.
REFERENCE = re.compile(r"\b(?:D|H)-\d{3}\b|§\d+|\b10-K\b")
# Numbers that are definitions, not results: transform names (T4, T6 in docs/SEEDED_ERRORS.md) and the
# percentile named by a latency label.
DEFINITIONS = ("Scale shifted by 1,000", "Off by 5%", "95th percentile")
NUMBER = re.compile(r"\d[\d,.]*%?")
BASES = ("corrected", "as_scored")


def load(name: str):
    return json.loads((CONTENT / name).read_text(encoding="utf-8"))


def source(name: str):
    return json.loads(SOURCES[name].read_text(encoding="utf-8"))


def resolve(name: str, path: str, basis: str = "corrected"):
    """The value at a dotted path, as web/lib/content.ts resolves it (keys may contain dots)."""
    node, key = source(name), ""
    for part in path.replace("{basis}", basis).split("."):
        key = f"{key}.{part}" if key else part
        if key in node:
            node, key = node[key], ""
    if key:
        raise KeyError(path)
    return node


# Keys that hold file comments, source paths or identifiers rather than display text; source paths are
# checked by test_stat_cards_are_bound_on_both_bases.
NOT_DISPLAY = ("note", "path", "of", "from", "id", "format", "preset", "href")


def strings(node, skip=NOT_DISPLAY):
    """Every display string in a content file."""
    if isinstance(node, str):
        yield node
    elif isinstance(node, list):
        for x in node:
            yield from strings(x, skip)
    elif isinstance(node, dict):
        for k, v in node.items():
            if k not in skip:
                yield from strings(v, skip)


def bare_numbers(text: str) -> list[str]:
    for d in DEFINITIONS:
        text = text.replace(d, "")
    return NUMBER.findall(REFERENCE.sub("", PLACEHOLDER.sub("", text)))


def items() -> list[dict]:
    return [json.loads(line) for line in ITEMS.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_headline_numbers_match_summary():
    headline = load("headline.json")
    declared = {n["shown"] for n in headline["numbers"]}
    assert set(NUMBER.findall(REFERENCE.sub("", headline["text"]))) == declared
    for n in headline["numbers"]:
        assert n["file"] == "results/summary.json" and n["shown"] in headline["text"]
        value = resolve("summary", n["path"])
        shown = f"{round(value * 100)}%" if n["as"] == "percent" else str(value)
        assert shown == n["shown"], (n, value)


@pytest.mark.parametrize("name", ["method.json", "copy.json", "labels.json", "limitations.json", "media.json"])
def test_numbers_are_placeholders_that_resolve(name):
    texts = list(strings(load(name)))
    assert texts
    for text in texts:
        if text.startswith("http") or text.startswith("/"):
            continue  # URLs and in-site links
        for src, path in PLACEHOLDER.findall(text):
            resolve(src, path)
        assert not bare_numbers(text), (name, bare_numbers(text), text)


def test_stat_cards_are_bound_on_both_bases():
    copy = load("copy.json")
    preset_ids = {p["id"] for p in copy["items"]["presets"]}
    for stat in copy["overview"]["stats"]:
        for basis in BASES:
            for key in ("path", "of", "from"):
                if key in stat:
                    assert isinstance(resolve("summary", stat[key], basis), (int, float)), (stat["id"], key, basis)
        assert stat.get("preset") in preset_ids or stat.get("href", "").startswith("/")


def test_presets_use_only_api_filters():
    allowed = {"attack_type", "verdict", "outcome", "label", "condition", "corrected", "unparseable", "handchecked"}
    labels = load("labels.json")
    values = {"attack_type": set(labels["attack_types"]), "verdict": set(labels["verdicts"]),
              "outcome": set(labels["outcomes"]), "condition": set(labels["conditions"]),
              "corrected": {"true", "false"}, "unparseable": {"true", "false"}, "handchecked": {"true", "false"}}
    for preset in load("copy.json")["items"]["presets"]:
        assert set(preset["filters"]) <= allowed, preset["id"]
        for k, v in preset["filters"].items():
            assert v in values.get(k, {v}), (preset["id"], k, v)


def test_every_code_in_the_results_has_a_plain_label():
    labels = load("labels.json")
    rows = items()
    summary = source("summary")
    assert {r["attack_type"] for r in rows} <= set(labels["attack_types"])
    assert {r["subtype"] for r in rows} <= set(labels["subtypes"])
    assert {r["gold"]["expected_behavior"] for r in rows} <= set(labels["expected_behaviors"])
    outcomes = {r["outcomes"][b][c]["outcome"] for r in rows for b in BASES for c in ("baseline", "treatment")}
    assert outcomes <= set(labels["outcomes"])
    failure = {r["outcomes"][b][c]["label"] for r in rows for b in BASES for c in ("baseline", "treatment")} - {None}
    assert failure <= set(labels["failure_labels"])
    reasons = [x for r in rows for m in ("full", "quote_off") for x in r["verdict"][m]["reasons"]]
    assert {r["verdict"]["full"]["decision"] for r in rows} <= set(labels["verdicts"])
    assert {x["code"] for x in reasons} <= set(labels["reason_codes"])
    assert {x["basis"] for x in reasons} <= set(labels["reason_bases"])
    summary_reasons = {k.split(" [")[0] for k in summary["verifier"]["blocks_by_reason_and_basis_full"]}
    assert summary_reasons <= set(labels["reason_codes"])
    assert set(summary["seeded_errors"]["by_transform_quote_off"]) <= set(labels["transforms"])
    hand = [r["handcheck"] for r in rows if r["handcheck"]]
    assert {p.strip() for h in hand for p in h["why_listed"].split(";")} <= set(labels["handcheck_reasons"])
    assert {h["verdict"] or "" for h in hand} <= set(labels["handcheck_verdicts"])
    assert set(labels["statuses"]) >= {b["status"] for basis in BASES for b in summary["pass_bars"][basis].values()}


def test_limitation_groups_cover_every_limitation_once():
    groups = load("limitations.json")["groups"]
    positions = Counter(i for g in groups for i in g["items"])
    assert set(positions) == set(range(len(source("summary")["limitations"])))
    assert all(n == 1 for n in positions.values())


def test_author_and_media_links():
    author = load("author.json")
    assert author["name"] and author["github"].startswith("https://github.com/")
    assert author["repo"].startswith(author["github"] + "/")
    assert author["linkedin"] == "" or author["linkedin"].startswith("https://www.linkedin.com/")
    url = load("media.json")["demo_video_url"]
    assert url == "" or url.startswith("https://")
