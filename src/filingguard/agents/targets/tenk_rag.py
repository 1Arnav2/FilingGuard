"""Agent A: retrieval-augmented answers over a company's 10-K text, with quoted citations.

This is the baseline. It has a standard RAG prompt (answer from excerpts, cite, abstain when
the excerpts lack the answer) and no checks of its own, so the verifier's effect is measured
against an ordinary agent rather than a weakened one.
"""

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from filingguard.agents.schema import AgentAnswer, Citation, Claim
from filingguard.llm.client import LLMClient
from filingguard.retrieval import Retrieved, Retriever

PROMPT_VERSION = "tenk_rag_v1"
DEFAULT_K = 20

INSTRUCTIONS = """You are a financial research assistant. Answer the question about {company} using only the 10-K excerpts below.

Rules:
- Answer directly and concisely.
- Support every figure or factual statement with a claim that names the excerpt label it came from (for example "E3") and quotes the exact supporting text from that excerpt, copied verbatim.
- State the unit, the scale (for example "millions") and the period for every figure.
- If the excerpts do not contain the answer, set "abstain" to true and say that the filings provided do not contain it. Do not use outside knowledge.

Question: {question}

Excerpts:
{excerpts}"""

RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "answer": {"type": "string"},
        "abstain": {"type": "boolean"},
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "statement": {"type": "string"},
                    "value": {"type": ["number", "null"]},
                    "unit": {"type": ["string", "null"]},
                    "scale": {"type": ["string", "null"]},
                    "period": {"type": ["string", "null"]},
                    "excerpt": {"type": "string"},
                    "quote": {"type": "string"},
                },
                "required": ["statement", "excerpt", "quote"],
            },
        },
    },
    "required": ["answer", "abstain", "claims"],
}


def load_report_dates(filings_path: Path = Path("data/processed/filings.json")) -> dict[str, str]:
    """Map every corpus accession to its fiscal period end, for excerpt headers."""
    dates = {}
    for company in json.loads(filings_path.read_text(encoding="utf-8")):
        for key in ("latest_10k", "prior_10k"):
            filing = company[key]
            dates[filing["accession"]] = filing["report_date"]
    return dates


def format_excerpts(hits: list[Retrieved], report_dates: dict[str, str]) -> str:
    """Label each retrieved chunk E1..En with its filing and section."""
    blocks = []
    for i, hit in enumerate(hits, start=1):
        c = hit.chunk
        period = report_dates.get(c["accession"], "unknown")
        section = f"Item {c['item']}" if c["item"] != "other" else "other section"
        blocks.append(
            f"[E{i}] {c['ticker']} 10-K for the fiscal year ended {period} "
            f"(accession {c['accession']}), {section}:\n{c['text'].strip()}"
        )
    return "\n\n".join(blocks)


def locate_quote(chunk: dict, quote: str) -> tuple[int, int, bool]:
    """Character span of `quote` in the filing text; the whole chunk if not found verbatim."""
    text = chunk["text"]
    pos = text.find(quote) if quote else -1
    if pos == -1 and quote:
        pos = text.lower().find(quote.lower())
    if pos == -1:
        return chunk["start"], chunk["end"], False
    return chunk["start"] + pos, chunk["start"] + pos + len(quote), True


def _excerpt_index(label: str, n: int) -> int | None:
    digits = "".join(ch for ch in str(label) if ch.isdigit())
    if not digits:
        return None
    i = int(digits) - 1
    return i if 0 <= i < n else None


def parse_response(raw_text: str, hits: list[Retrieved]) -> tuple[AgentAnswer, str | None]:
    """Turn the model's JSON into an AgentAnswer (latency and trace filled in by the caller)."""
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return AgentAnswer(raw_text, [], [], False, 0.0), f"invalid JSON: {exc}"

    claims, citations = [], []
    for c in data.get("claims", []):
        idx = _excerpt_index(c.get("excerpt", ""), len(hits))
        citation_index = None
        if idx is not None:
            chunk = hits[idx].chunk
            start, end, found = locate_quote(chunk, c.get("quote", ""))
            citations.append(Citation(chunk["accession"], chunk["chunk_id"], start, end, c.get("quote", ""), found))
            citation_index = len(citations) - 1
        claims.append(Claim(
            text=c.get("statement", ""),
            value=c.get("value"),
            unit=c.get("unit"),
            scale=c.get("scale"),
            period=c.get("period"),
            citation_index=citation_index,
        ))
    answer = AgentAnswer(data.get("answer", ""), claims, citations, bool(data.get("abstain", False)), 0.0)
    return answer, None


class TenKRagAgent:
    """Retrieve the top-k chunks for the company, then answer with quoted citations."""

    name = "tenk_rag"

    def __init__(self, llm: LLMClient, retriever: Retriever, report_dates: dict[str, str], k: int = DEFAULT_K) -> None:
        self.llm = llm
        self.retriever = retriever
        self.report_dates = report_dates
        self.k = k

    def answer(self, question: str, company: str) -> AgentAnswer:
        t0 = time.perf_counter()
        hits = self.retriever.retrieve(question, company, self.k)
        retrieval_s = time.perf_counter() - t0

        prompt = INSTRUCTIONS.format(company=company, question=question, excerpts=format_excerpts(hits, self.report_dates))
        response = self.llm.generate(
            prompt,
            purpose="target",
            temperature=0,
            response_mime_type="application/json",
            response_json_schema=RESPONSE_SCHEMA,
        )
        answer, parse_error = parse_response(response.text, hits)
        answer.latency_s = round(retrieval_s + (response.latency_s or 0.0), 3)
        answer.trace = {
            "agent": self.name,
            "prompt_version": PROMPT_VERSION,
            "model": response.model,
            "question": question,
            "company": company,
            "retriever": {"name": self.retriever.name, "k": self.k},
            "retrieved": [
                {"rank": h.rank, "chunk_id": h.chunk["chunk_id"], "item": h.chunk["item"], "source": h.source,
                 "score": round(h.score, 4)}
                for h in hits
            ],
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "llm_cached": response.cached,
            "llm_latency_s": response.latency_s,
            "retrieval_s": round(retrieval_s, 3),
            "raw_response": response.text,
            "parse_error": parse_error,
        }
        return answer


def build_tenk_rag_agent(processed: Path = Path("data/processed")) -> TenKRagAgent:
    """Assemble the agent from the local index and `.env` (TARGET_MODEL)."""
    from filingguard.data.index import VectorIndex, fastembed_fn
    from filingguard.llm.client import client_from_env
    from filingguard.retrieval import BM25Retriever, DenseRetriever, InterleavedRetriever

    index = VectorIndex.load(processed / "index", fastembed_fn())
    retriever = InterleavedRetriever(BM25Retriever(index.chunks), DenseRetriever(index))
    return TenKRagAgent(client_from_env("TARGET_MODEL"), retriever, load_report_dates(processed / "filings.json"))
