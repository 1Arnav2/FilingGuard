import numpy as np

from filingguard.data.index import VectorIndex, cached_embed_fn, index_is_current
from filingguard.llm.cache import DiskCache

VOCAB = ["revenue", "debt", "risk", "cash"]


def bag_of_words(texts):
    """Deterministic stand-in for an embedding model."""
    return np.array([[t.lower().count(w) for w in VOCAB] for t in texts], dtype=np.float32)


def chunks():
    return [
        {"chunk_id": "A:0", "ticker": "AAA", "accession": "A", "item": "7", "text": "revenue revenue grew"},
        {"chunk_id": "A:1", "ticker": "AAA", "accession": "A", "item": "1A", "text": "risk factors and risk"},
        {"chunk_id": "B:0", "ticker": "BBB", "accession": "B", "item": "7", "text": "revenue and debt"},
        {"chunk_id": "B:1", "ticker": "BBB", "accession": "B", "item": "8", "text": "cash cash cash"},
    ]


def test_search_ranks_by_cosine_and_filters_by_company():
    index = VectorIndex.build(chunks(), bag_of_words, "bow")
    assert index.search("revenue", k=1)[0].chunk["chunk_id"] == "A:0"
    hits = index.search("revenue", k=5, ticker="BBB")
    assert [h.chunk["ticker"] for h in hits] == ["BBB", "BBB"]
    assert hits[0].chunk["chunk_id"] == "B:0"
    assert index.search("cash", ticker="ZZZ") == []


def test_save_load_round_trip_and_staleness(tmp_path):
    VectorIndex.build(chunks(), bag_of_words, "bow").save(tmp_path)
    assert index_is_current(tmp_path, chunks(), "bow")
    assert not index_is_current(tmp_path, chunks(), "other-model")
    changed = chunks()
    changed[0]["text"] = "edited"
    assert not index_is_current(tmp_path, changed, "bow")

    loaded = VectorIndex.load(tmp_path, bag_of_words)
    assert loaded.search("risk", k=1)[0].chunk["chunk_id"] == "A:1"


def test_cached_embed_only_computes_misses_and_resumes(tmp_path):
    seen = []

    def counting(texts):
        seen.extend(texts)
        return bag_of_words(texts)

    texts = [c["text"] for c in chunks()]
    first = cached_embed_fn(counting, DiskCache(tmp_path), "bow", group=2)(texts[:3])
    assert len(seen) == 3

    seen.clear()
    again = cached_embed_fn(counting, DiskCache(tmp_path), "bow", group=2)(texts)
    assert seen == [texts[3]], "only the new text is embedded"
    assert np.allclose(again[:3], first)
    assert np.allclose(again, bag_of_words(texts))
