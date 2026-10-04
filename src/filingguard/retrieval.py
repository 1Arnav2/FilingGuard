"""Retrievers over the chunk index, shared by the target agent and (later) the verifier.

Parameters are textbook defaults, not tuned on the smoke set (D-023).
"""

import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Protocol

from filingguard.data.index import VectorIndex

BM25_K1 = 1.2
BM25_B = 0.75
RRF_K = 60
FUSION_DEPTH = 50  # candidates taken from each retriever before fusion

# Numbers keep their commas and decimal points ("416,161", "1.64") so figures match exactly.
_TOKEN = re.compile(r"\d[\d,]*(?:\.\d+)?|[a-z][a-z0-9]*")


def tokenize(text: str) -> list[str]:
    """Lowercase words and numbers; trailing commas on numbers are dropped."""
    return [t.rstrip(",") for t in _TOKEN.findall(text.lower())]


@dataclass(frozen=True)
class Retrieved:
    rank: int
    score: float
    chunk: dict
    source: str  # which retriever produced the score


class Retriever(Protocol):
    name: str

    def retrieve(self, query: str, ticker: str, k: int) -> list[Retrieved]:
        """Return the top `k` chunks for `query` within one company's filings."""
        ...


class DenseRetriever:
    """Cosine similarity over local embeddings."""

    name = "dense"

    def __init__(self, index: VectorIndex) -> None:
        self.index = index

    def retrieve(self, query: str, ticker: str, k: int) -> list[Retrieved]:
        hits = self.index.search(query, k=k, ticker=ticker)
        return [Retrieved(i + 1, h.score, h.chunk, self.name) for i, h in enumerate(hits)]


class BM25Retriever:
    """Okapi BM25 keyword search. Statistics are computed per company, since every query is
    scoped to one company."""

    name = "bm25"

    def __init__(self, chunks: list[dict], k1: float = BM25_K1, b: float = BM25_B) -> None:
        self.k1, self.b = k1, b
        self.chunks = chunks
        self.tf = [Counter(tokenize(c["text"])) for c in chunks]
        self.length = [sum(tf.values()) for tf in self.tf]
        self.by_ticker: dict[str, list[int]] = defaultdict(list)
        for i, c in enumerate(chunks):
            self.by_ticker[c["ticker"]].append(i)
        self._stats = {t: self._ticker_stats(ids) for t, ids in self.by_ticker.items()}

    def _ticker_stats(self, ids: list[int]) -> tuple[dict[str, float], float]:
        df: Counter = Counter()
        for i in ids:
            df.update(self.tf[i].keys())
        n = len(ids)
        idf = {term: math.log(1 + (n - d + 0.5) / (d + 0.5)) for term, d in df.items()}
        avg_len = sum(self.length[i] for i in ids) / n
        return idf, avg_len

    def retrieve(self, query: str, ticker: str, k: int) -> list[Retrieved]:
        ids = self.by_ticker.get(ticker, [])
        if not ids:
            return []
        idf, avg_len = self._stats[ticker]
        terms = [t for t in set(tokenize(query)) if t in idf]
        scored = []
        for i in ids:
            tf, norm = self.tf[i], self.k1 * (1 - self.b + self.b * self.length[i] / avg_len)
            score = sum(idf[t] * tf[t] * (self.k1 + 1) / (tf[t] + norm) for t in terms if tf[t])
            if score > 0:
                scored.append((score, i))
        scored.sort(key=lambda s: (-s[0], s[1]))
        return [Retrieved(r + 1, s, self.chunks[i], self.name) for r, (s, i) in enumerate(scored[:k])]


class InterleavedRetriever:
    """Round-robin union of keyword and dense rankings: keyword 1, dense 1, keyword 2, ...

    Duplicates are skipped, so the result holds at least the top k/2 of each ranking. Chosen
    over RRF because equal-weight fusion let dense noise push out exact keyword matches (D-023).
    """

    name = "interleaved"

    def __init__(self, keyword: Retriever, dense: Retriever) -> None:
        self.retrievers = (keyword, dense)

    def retrieve(self, query: str, ticker: str, k: int) -> list[Retrieved]:
        rankings = [r.retrieve(query, ticker, k) for r in self.retrievers]
        merged: list[Retrieved] = []
        seen: set[str] = set()
        for position in range(k):
            for ranking in rankings:
                if position < len(ranking) and ranking[position].chunk["chunk_id"] not in seen:
                    hit = ranking[position]
                    seen.add(hit.chunk["chunk_id"])
                    merged.append(Retrieved(len(merged) + 1, hit.score, hit.chunk, hit.source))
                if len(merged) == k:
                    return merged
        return merged


class HybridRetriever:
    """Reciprocal rank fusion of dense and keyword rankings: score = sum of 1 / (RRF_K + rank)."""

    name = "hybrid"

    def __init__(self, dense: Retriever, keyword: Retriever, depth: int = FUSION_DEPTH, rrf_k: int = RRF_K) -> None:
        self.retrievers = (dense, keyword)
        self.depth, self.rrf_k = depth, rrf_k

    def retrieve(self, query: str, ticker: str, k: int) -> list[Retrieved]:
        fused: dict[str, float] = defaultdict(float)
        chunk_by_id: dict[str, dict] = {}
        for retriever in self.retrievers:
            for r in retriever.retrieve(query, ticker, self.depth):
                fused[r.chunk["chunk_id"]] += 1 / (self.rrf_k + r.rank)
                chunk_by_id[r.chunk["chunk_id"]] = r.chunk
        ranked = sorted(fused.items(), key=lambda kv: (-kv[1], kv[0]))[:k]
        return [Retrieved(i + 1, s, chunk_by_id[cid], self.name) for i, (cid, s) in enumerate(ranked)]
