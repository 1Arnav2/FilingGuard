import json

from filingguard.agents.targets.tenk_rag import TenKRagAgent, format_excerpts, locate_quote, parse_response
from filingguard.llm.cache import DiskCache
from filingguard.llm.client import LLMClient
from filingguard.retrieval import Retrieved

CHUNK = {
    "chunk_id": "0001-25-1:7", "ticker": "AAPL", "accession": "0001-25-1", "item": "7",
    "start": 1000, "end": 1060, "text": "Total net sales | $416,161 | $391,035 | grew 6% in 2025",
}
OTHER = {
    "chunk_id": "0001-25-1:9", "ticker": "AAPL", "accession": "0001-25-1", "item": "other",
    "start": 2000, "end": 2030, "text": "Unrelated cover page text here",
}
DATES = {"0001-25-1": "2025-09-27"}


class FixedRetriever:
    name = "fixed"

    def retrieve(self, query, ticker, k):
        return [Retrieved(1, 0.9, CHUNK, "bm25"), Retrieved(2, 0.5, OTHER, "dense")][:k]


def reply(payload):
    def backend(model, prompt, params):
        assert "[E1] AAPL 10-K for the fiscal year ended 2025-09-27" in prompt
        assert params["response_mime_type"] == "application/json"
        return {"text": json.dumps(payload) if isinstance(payload, dict) else payload, "raw": {}}
    return backend


def agent(tmp_path, payload, ledger):
    llm = LLMClient("m", DiskCache(tmp_path / "cache"), reply(payload), ledger=ledger)
    return TenKRagAgent(llm, FixedRetriever(), DATES, k=2)


GOOD = {
    "answer": "Apple's total net sales for fiscal 2025 were $416,161 million.",
    "abstain": False,
    "claims": [{"statement": "Total net sales were $416,161 million", "value": 416161, "unit": "USD",
                "scale": "millions", "period": "fiscal 2025", "excerpt": "E1", "quote": "Total net sales | $416,161"}],
}


def test_answer_maps_quote_to_filing_offsets_and_logs_trace(tmp_path, ledger):
    a = agent(tmp_path, GOOD, ledger).answer("What were total net sales?", "AAPL")
    assert not a.abstained and a.claims[0].value == 416161
    cite = a.citations[a.claims[0].citation_index]
    assert (cite.doc_id, cite.chunk_id, cite.quote_found) == ("0001-25-1", "0001-25-1:7", True)
    assert (cite.start, cite.end) == (1000, 1000 + len("Total net sales | $416,161"))
    assert [r["chunk_id"] for r in a.trace["retrieved"]] == ["0001-25-1:7", "0001-25-1:9"]
    assert a.trace["parse_error"] is None and a.trace["llm_cached"] is False
    assert a.latency_s >= 0


def test_second_call_is_cached_and_keeps_original_latency(tmp_path, ledger):
    first = agent(tmp_path, GOOD, ledger).answer("q", "AAPL")
    second = agent(tmp_path, GOOD, ledger).answer("q", "AAPL")
    assert second.trace["llm_cached"] is True
    assert second.trace["llm_latency_s"] == first.trace["llm_latency_s"]


def test_abstention_is_passed_through(tmp_path, ledger):
    a = agent(tmp_path, {"answer": "Not in the filings provided.", "abstain": True, "claims": []}, ledger).answer("q", "AAPL")
    assert a.abstained and a.claims == [] and a.citations == []


def test_unfound_quote_falls_back_to_whole_chunk():
    start, end, found = locate_quote(CHUNK, "a sentence the model invented")
    assert (start, end, found) == (1000, 1060, False)
    assert locate_quote(CHUNK, "TOTAL NET SALES")[2] is True


def test_bad_excerpt_label_gives_claim_without_citation():
    payload = dict(GOOD, claims=[dict(GOOD["claims"][0], excerpt="E9")])
    answer, err = parse_response(json.dumps(payload), [Retrieved(1, 1.0, CHUNK, "bm25")])
    assert err is None and answer.citations == [] and answer.claims[0].citation_index is None


def test_invalid_json_is_recorded_not_raised():
    answer, err = parse_response("not json", [])
    assert err.startswith("invalid JSON") and answer.text == "not json" and answer.claims == []


def test_excerpts_name_section_and_period():
    text = format_excerpts([Retrieved(1, 1.0, CHUNK, "bm25"), Retrieved(2, 1.0, OTHER, "dense")], DATES)
    assert "[E1] AAPL 10-K for the fiscal year ended 2025-09-27 (accession 0001-25-1), Item 7:" in text
    assert "[E2]" in text and "other section" in text
