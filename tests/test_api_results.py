"""Read-only results API (Phase 6a): routes serve committed `results/` files only, no model calls."""

import ast
import json
from collections import Counter
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from filingguard.api import results as results_store
from filingguard.api.main import app

ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "src" / "filingguard" / "api"
SUMMARY = json.loads((ROOT / "results" / "summary.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def client(monkeypatch_module):
    return TestClient(app)


@pytest.fixture(scope="module")
def monkeypatch_module():
    """Any LLM client built while the routes run fails the test."""
    mp = pytest.MonkeyPatch()
    from filingguard.llm import client as llm_client

    def refuse(*args, **kwargs):
        raise AssertionError("results routes must not build an LLM client")

    mp.setattr(llm_client.LLMClient, "__init__", refuse)
    results_store.load.cache_clear()
    yield mp
    mp.undo()


def all_items(client, **params) -> list[dict]:
    body = client.get("/api/items", params={"page_size": 500, **params}).json()
    assert body["total"] == len(body["items"])
    return body["items"]


def test_summary_is_the_file_unchanged(client):
    response = client.get("/api/summary")
    assert response.status_code == 200
    body = response.json()
    assert body.pop("generated_from") == "results/summary.json"
    assert body == SUMMARY


@pytest.mark.parametrize("basis", ["corrected", "as_scored"])
@pytest.mark.parametrize("condition", ["baseline", "treatment"])
def test_item_outcomes_add_up_to_summary(client, basis, condition):
    items = all_items(client, basis=basis)
    assert len(items) == 210
    counts = Counter(i[condition]["outcome"] for i in items)
    assert counts == Counter(SUMMARY["conditions"][basis][condition]["outcomes"])


def test_headline_outcome_counts(client):
    def counts(basis, condition):
        c = Counter(i[condition]["outcome"] for i in all_items(client, basis=basis))
        return c["correct"], c["missed"], c["unsupported"]

    assert counts("corrected", "baseline") == (197, 10, 3)
    assert counts("corrected", "treatment") == (188, 22, 0)
    assert counts("as_scored", "baseline") == (186, 11, 13)
    assert counts("as_scored", "treatment") == (186, 23, 1)


def test_verdicts_match_the_frozen_run(client):
    items = all_items(client)
    assert Counter(i["verdict"] for i in items) == {"pass": 194, "block": 13, "flag": 3}
    assert sorted(i["id"] for i in items if i["verdict"] == "block") == sorted(SUMMARY["verifier"]["natural_blocked"])
    assert sorted(i["id"] for i in items if i["verdict"] == "flag") == sorted(SUMMARY["verifier"]["natural_flagged"])
    assert sum(i["corrected"] for i in items) == 11


def test_filters_and_paging(client):
    counts = {t: len(all_items(client, attack_type=t)) for t in
              ("control", "unanswerable", "unit_trap", "period_mismatch", "false_premise", "injection", "restated")}
    assert counts == {"control": 42, "unanswerable": 32, "unit_trap": 32, "period_mismatch": 32,
                      "false_premise": 32, "injection": 32, "restated": 8}
    blocked = all_items(client, verdict="block")
    assert len(blocked) == 13 and all(i["reason_codes"] for i in blocked)
    unsupported = all_items(client, basis="as_scored", condition="baseline", outcome="unsupported")
    assert len(unsupported) == 13
    assert len(all_items(client, basis="as_scored", condition="baseline", label="wrong_number")) == 12

    page = client.get("/api/items", params={"page": 2, "page_size": 50}).json()
    assert (page["total"], page["page"], page["page_size"], len(page["items"])) == (210, 2, 50, 50)
    ids = [i["id"] for i in all_items(client)]
    assert [i["id"] for i in page["items"]] == ids[50:100]


@pytest.mark.parametrize("params", [{"attack_type": "nope"}, {"verdict": "maybe"}, {"basis": "x"},
                                    {"outcome": "wrong"}, {"label": "nope"}, {"page": 0}, {"page_size": 0}])
def test_bad_filters_are_rejected(client, params):
    assert client.get("/api/items", params=params).status_code == 422


def test_item_detail_shows_correction_and_both_bases(client):
    body = client.get("/api/items/FG-0001").json()
    assert body["company"] == "AAPL" and body["attack_type"] == "control"
    assert body["question"].startswith("How much cash")
    assert body["outcomes"]["as_scored"]["baseline"]["outcome"] == "unsupported"
    assert body["outcomes"]["corrected"]["baseline"]["outcome"] == "correct"
    assert body["correction"]["approval"].startswith("approved by owner")
    assert body["answer"]["citations"][0]["chunk_id"] == "0000320193-25-000079:54"
    assert set(body["verdict"]) == {"full", "quote_off"}
    assert body["retrieved"][0]["rank"] == 1


def test_blocked_item_detail_has_reasons(client):
    item_id = SUMMARY["verifier"]["natural_blocked"][0]
    body = client.get(f"/api/items/{item_id}").json()
    assert body["verdict"]["full"]["decision"] == "block"
    assert body["verdict"]["full"]["reasons"] and body["outcomes"]["as_scored"]["treatment"]["outcome"] == "missed"


def test_unknown_item_is_404(client):
    assert client.get("/api/items/FG-9999").status_code == 404


def test_api_reads_no_gold_or_testset_and_no_llm():
    for path in API_DIR.glob("*.py"):
        if path.name == "main.py":
            continue  # the live target route lives there and is gated separately in Phase 6b
        source = path.read_text(encoding="utf-8")
        assert "data/gold" not in source and "data/testset" not in source, path.name
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [a.name for a in node.names] + [getattr(node, "module", None) or ""]
                assert not any(n.startswith(("filingguard.llm", "filingguard.agents", "filingguard.eval"))
                               for n in names), f"{path.name} imports {names}"


def test_meta_is_the_file_unchanged(client):
    body = client.get("/api/meta").json()
    assert body.pop("generated_from") == "results/dashboard/meta_v1.json"
    assert body == json.loads((ROOT / "results" / "dashboard" / "meta_v1.json").read_text(encoding="utf-8"))
    assert body["split"] == {"dev": 90, "test": 210, "total": 300}
    assert body["pass_bars_set"]["decision"] == "D-056" and body["pass_bars_set"]["date"] == "2026-10-05"
    assert set(body["freeze_tags"]) == {"target-v1", "testset-v1", "verifier-v1"}


def test_every_item_detail_validates_and_has_gold(client):
    for row in all_items(client):
        body = client.get(f"/api/items/{row['id']}").json()
        assert body["gold"]["expected_behavior"] and body["gold"]["text"]
        assert body["outcomes"]["corrected"]["treatment"]["outcome"] == row["treatment"]["outcome"]


def test_unparseable_answers_are_not_reproduced(client):
    unparseable = [i for i in all_items(client) if i["unparseable"]]
    assert sorted(i["id"] for i in unparseable) == ["FG-0020", "FG-0308"]
    for item in unparseable:
        answer = client.get(f"/api/items/{item['id']}").json()["answer"]
        assert answer["text"] is None and answer["parse_error"] and answer["unparseable_chars"] > 60_000


def test_judge_correction_and_handcheck_fields(client):
    items = all_items(client)
    details = {i["id"]: client.get(f"/api/items/{i['id']}").json() for i in items}
    judged = [d for d in details.values() if d["judge"] is not None]
    assert len(judged) == 38 and {d["attack_type"] for d in judged} == {"false_premise", "control"}  # 32 false premises, 6 true-premise controls
    statuses = Counter((d["correction"] or {}).get("status") for d in details.values())
    assert statuses == {None: 195, "corrected": 11, "kept as scored": 4}
    checked = [d for d in details.values() if d["handcheck"]]
    assert len(checked) == 53 and sum(i["handchecked"] for i in items) == 53
    assert sum(bool(d["handcheck"]["note"]) for d in checked) == 5
    assert details["FG-0001"]["figures"][0]["metric"] == "CashAndCashEquivalentsAtCarryingValue"


@pytest.mark.parametrize("basis", ["corrected", "as_scored"])
@pytest.mark.parametrize("condition", ["baseline", "treatment"])
def test_items_add_up_to_summary_by_type(client, basis, condition):
    by_type = SUMMARY["conditions"][basis][condition]["by_type"]
    for attack_type, block in by_type.items():
        counts = Counter(i[condition]["outcome"] for i in all_items(client, basis=basis, attack_type=attack_type))
        assert counts == Counter(block["outcomes"]), (basis, condition, attack_type)
