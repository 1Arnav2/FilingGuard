"""Local embedding index over filing chunks: exact cosine search with numpy (D-016)."""

import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from filingguard.llm.cache import DiskCache, cache_key

EMBED_MODEL = "jinaai/jina-embeddings-v2-small-en"

# Takes texts, returns one vector per text.
EmbedFn = Callable[[Sequence[str]], np.ndarray]


def fastembed_fn(model_name: str = EMBED_MODEL, batch_size: int = 4) -> EmbedFn:
    """Build an embedding function backed by a local fastembed (ONNX) model.

    Small batches keep memory bounded: attention memory grows with the square of sequence
    length, and table-heavy chunks are long (H-005).
    """
    from fastembed import TextEmbedding

    model = TextEmbedding(model_name=model_name)

    def embed(texts: Sequence[str]) -> np.ndarray:
        return np.array(list(model.embed(list(texts), batch_size=batch_size)), dtype=np.float32)

    return embed


def cached_embed_fn(
    embed: EmbedFn,
    cache: DiskCache,
    model_name: str,
    group: int = 64,
    progress: Callable[[int, int], None] | None = None,
) -> EmbedFn:
    """Wrap `embed` so each text's vector is cached on disk; only misses are computed.

    Misses are embedded `group` texts at a time and written immediately, so an interrupted
    build resumes where it stopped.
    """

    def run(texts: Sequence[str]) -> np.ndarray:
        keys = [cache_key({"model": model_name, "text": t}) for t in texts]
        vectors: list[list[float] | None] = [None] * len(texts)
        misses = []
        for i, key in enumerate(keys):
            hit = cache.get(key)
            if hit is None:
                misses.append(i)
            else:
                vectors[i] = hit["vector"]
        for n in range(0, len(misses), group):
            batch = misses[n:n + group]
            for i, vec in zip(batch, embed([texts[i] for i in batch])):
                vectors[i] = vec.tolist()
                cache.put(keys[i], {"vector": vectors[i]})
            if progress:
                progress(min(n + group, len(misses)), len(misses))
        return np.array(vectors, dtype=np.float32)

    return run


def _normalise(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.where(norms == 0, 1, norms)


def content_hash(chunks: list[dict], model_name: str) -> str:
    """Hash of the model name and every chunk id and text, used to skip unchanged rebuilds."""
    h = hashlib.sha256(model_name.encode())
    for c in chunks:
        h.update(c["chunk_id"].encode())
        h.update(c["text"].encode("utf-8"))
    return h.hexdigest()


@dataclass
class Hit:
    score: float
    chunk: dict


class VectorIndex:
    """Chunks plus unit-length embeddings, stored as chunks.jsonl, embeddings.npy, manifest.json."""

    def __init__(self, chunks: list[dict], vectors: np.ndarray, model_name: str, embed: EmbedFn | None = None):
        self.chunks = chunks
        self.vectors = _normalise(vectors)
        self.model_name = model_name
        self._embed = embed

    @classmethod
    def build(cls, chunks: list[dict], embed: EmbedFn, model_name: str = EMBED_MODEL) -> "VectorIndex":
        """Embed every chunk's text."""
        return cls(chunks, embed([c["text"] for c in chunks]), model_name, embed)

    def save(self, out_dir: Path) -> None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        with (out_dir / "chunks.jsonl").open("w", encoding="utf-8") as f:
            for c in self.chunks:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
        np.save(out_dir / "embeddings.npy", self.vectors)
        manifest = {
            "model": self.model_name,
            "chunks": len(self.chunks),
            "dim": int(self.vectors.shape[1]),
            "content_hash": content_hash(self.chunks, self.model_name),
        }
        (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, out_dir: Path, embed: EmbedFn | None = None) -> "VectorIndex":
        out_dir = Path(out_dir)
        manifest = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
        with (out_dir / "chunks.jsonl").open(encoding="utf-8") as f:
            chunks = [json.loads(line) for line in f]
        return cls(chunks, np.load(out_dir / "embeddings.npy"), manifest["model"], embed)

    def search(self, query: str, k: int = 8, ticker: str | None = None, accession: str | None = None) -> list[Hit]:
        """Return the top `k` chunks by cosine similarity, optionally within one company or filing."""
        if self._embed is None:
            raise RuntimeError("index loaded without an embedding function")
        q = _normalise(self._embed([query]))[0]
        mask = np.ones(len(self.chunks), dtype=bool)
        if ticker:
            mask &= np.array([c["ticker"] == ticker for c in self.chunks])
        if accession:
            mask &= np.array([c["accession"] == accession for c in self.chunks])
        idx = np.flatnonzero(mask)
        if idx.size == 0:
            return []
        scores = self.vectors[idx] @ q
        top = idx[np.argsort(-scores)[:k]]
        return [Hit(float(self.vectors[i] @ q), self.chunks[i]) for i in top]


def index_is_current(out_dir: Path, chunks: list[dict], model_name: str = EMBED_MODEL) -> bool:
    """True if a saved index exists for exactly these chunks and this model."""
    path = Path(out_dir) / "manifest.json"
    if not path.exists():
        return False
    return json.loads(path.read_text(encoding="utf-8")).get("content_hash") == content_hash(chunks, model_name)
