from filingguard.retrieval import BM25Retriever, HybridRetriever, InterleavedRetriever, Retrieved, tokenize


def chunk(cid, ticker, text):
    return {"chunk_id": cid, "ticker": ticker, "accession": "A", "item": "7", "text": text}


CHUNKS = [
    chunk("a0", "AAA", "Total net sales | $416,161 | $391,035"),
    chunk("a1", "AAA", "Risk factors about supply chains and net sales risk"),
    chunk("a2", "AAA", "We had approximately 65,900 employees at year end"),
    chunk("b0", "BBB", "Total net sales | 1,000 | 900"),
]


def test_tokenize_keeps_figures_whole():
    assert tokenize("Sales were $416,161, up 1.64 million.") == ["sales", "were", "416,161", "up", "1.64", "million"]


def test_bm25_finds_exact_terms_within_company():
    bm25 = BM25Retriever(CHUNKS)
    hits = bm25.retrieve("how many employees", "AAA", 3)
    assert hits[0].chunk["chunk_id"] == "a2"
    assert all(h.chunk["ticker"] == "AAA" for h in bm25.retrieve("total net sales", "AAA", 5))
    assert bm25.retrieve("anything", "ZZZ", 3) == []


def test_bm25_prefers_rarer_terms():
    hits = BM25Retriever(CHUNKS).retrieve("total net sales", "AAA", 3)
    assert hits[0].chunk["chunk_id"] == "a0", "'total' only appears in a0"


class Fixed:
    def __init__(self, name, ids):
        self.name, self.ids = name, ids

    def retrieve(self, query, ticker, k):
        by_id = {c["chunk_id"]: c for c in CHUNKS}
        return [Retrieved(i + 1, 1.0, by_id[cid], self.name) for i, cid in enumerate(self.ids[:k])]


def test_rrf_rewards_agreement_and_keeps_unique_hits():
    hybrid = HybridRetriever(Fixed("dense", ["a1", "a0", "a2"]), Fixed("bm25", ["a0", "a2"]))
    ranked = [r.chunk["chunk_id"] for r in hybrid.retrieve("q", "AAA", 3)]
    assert ranked[0] == "a0", "ranked high by both"
    assert set(ranked) == {"a0", "a1", "a2"}


def test_interleave_alternates_skips_duplicates_and_records_source():
    merged = InterleavedRetriever(Fixed("bm25", ["a2", "a0"]), Fixed("dense", ["a2", "a1", "a0"])).retrieve("q", "AAA", 3)
    assert [(r.rank, r.chunk["chunk_id"], r.source) for r in merged] == [
        (1, "a2", "bm25"), (2, "a0", "bm25"), (3, "a1", "dense"),
    ]


def test_interleave_keeps_top_half_of_each_ranking():
    merged = InterleavedRetriever(Fixed("bm25", ["a0", "a1"]), Fixed("dense", ["a2", "b0"])).retrieve("q", "AAA", 4)
    ids = [r.chunk["chunk_id"] for r in merged]
    assert ids == ["a0", "a2", "a1", "b0"]
