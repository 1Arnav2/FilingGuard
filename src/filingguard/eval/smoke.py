"""Phase 2 smoke test: retrieval hit rate and target-agent answers on hand-written questions.

The smoke set (`data/smoke/smoke_v1.jsonl`) is separate from the test set and is never used to
build test items. A retrieval hit means a chunk containing one of the expected answer strings
is in the top k for the question's company.

Run with `python -m filingguard.eval.smoke [--retrieval-only] [--retrieval-out NAME]`.
"""

import argparse
import json
from pathlib import Path

from filingguard.retrieval import Retriever

SMOKE_PATH = Path("data/smoke/smoke_v1.jsonl")
# Paraphrased questions, each set written before any retrieval was run on it (D-023).
# holdout_v1 checked interleaved k=10; holdout_v2 checks the final interleaved k=20.
HOLDOUT_PATHS = {"holdout_v1": Path("data/smoke/holdout_v1.jsonl"), "holdout_v2": Path("data/smoke/holdout_v2.jsonl")}
K_VALUES = (3, 5, 10, 20)


def load_smoke(path: Path = SMOKE_PATH) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def contains_answer(chunk: dict, expected: list[str]) -> bool:
    return any(s in chunk["text"] for s in expected)


def answer_chunks(chunks: list[dict], ticker: str, expected: list[str]) -> set[str]:
    """Ids of every chunk for `ticker` that contains an expected answer string."""
    return {c["chunk_id"] for c in chunks if c["ticker"] == ticker and contains_answer(c, expected)}


def first_hit_rank(retriever: Retriever, item: dict, k: int) -> int | None:
    """1-based rank of the first answer-bearing chunk in the top `k`, or None."""
    for r in retriever.retrieve(item["question"], item["company"], k):
        if contains_answer(r.chunk, item["expected"]):
            return r.rank
    return None


def hit_rates(retriever: Retriever, items: list[dict], chunks: list[dict]) -> dict:
    """Per-question first-hit rank and the hit rate at each k in K_VALUES."""
    k_max = max(K_VALUES)
    rows = []
    for item in items:
        rows.append({
            "id": item["id"],
            "company": item["company"],
            "answer_chunks": len(answer_chunks(chunks, item["company"], item["expected"])),
            "first_hit_rank": first_hit_rank(retriever, item, k_max),
        })
    rates = {
        f"hit@{k}": sum(r["first_hit_rank"] is not None and r["first_hit_rank"] <= k for r in rows) / len(rows)
        for k in K_VALUES
    }
    return {"retriever": retriever.name, "questions": rows, **rates}


def mentions_expected(answer, item: dict) -> bool:
    """Loose correctness signal: an expected string appears in the answer text or a quote.
    Each answer is also read by hand; this flag only speeds that up."""
    haystacks = [answer.text] + [c.quote for c in answer.citations]
    return any(s in h for s in item["expected"] for h in haystacks)


def retrieval_table(reports: list[dict]) -> str:
    """Markdown table: first-hit rank per question for each retriever, then hit rates."""
    names = [r["retriever"] for r in reports]
    lines = ["| Question | Company | " + " | ".join(names) + " |", "|---|---|" + "---|" * len(names)]
    for i, q in enumerate(reports[0]["questions"]):
        ranks = [str(r["questions"][i]["first_hit_rank"] or "miss") for r in reports]
        lines.append(f"| {q['id']} | {q['company']} | " + " | ".join(ranks) + " |")
    for k in K_VALUES:
        lines.append(f"| **hit@{k}** | | " + " | ".join(f"{r[f'hit@{k}']:.0%}" for r in reports) + " |")
    return "\n".join(lines)


def main() -> None:
    from filingguard.data.index import VectorIndex, fastembed_fn
    from filingguard.retrieval import BM25Retriever, DenseRetriever, HybridRetriever, InterleavedRetriever

    parser = argparse.ArgumentParser()
    parser.add_argument("--retrieval-only", action="store_true")
    parser.add_argument("--retrieval-out", default="retrieval.json", help="file name under results/smoke/")
    args = parser.parse_args()

    index = VectorIndex.load(Path("data/processed/index"), fastembed_fn())
    dense, bm25 = DenseRetriever(index), BM25Retriever(index.chunks)
    retrievers = (dense, bm25, HybridRetriever(dense, bm25), InterleavedRetriever(bm25, dense))
    retrieval = {}
    for name, path in {"smoke": SMOKE_PATH, **HOLDOUT_PATHS}.items():
        reports = [hit_rates(r, load_smoke(path), index.chunks) for r in retrievers]
        retrieval[name] = reports
        print(f"\n### {name}\n{retrieval_table(reports)}")
    out_dir = Path("results/smoke")
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / args.retrieval_out).write_text(json.dumps(retrieval, indent=2) + "\n", encoding="utf-8")
    if args.retrieval_only:
        return

    from filingguard.agents.targets.tenk_rag import TenKRagAgent, load_report_dates
    from filingguard.llm.client import client_from_env

    agent = TenKRagAgent(client_from_env("TARGET_MODEL"), retrievers[-1], load_report_dates())
    from google.genai import errors

    rows, not_run = [], []
    for item in load_smoke(SMOKE_PATH):
        try:
            answer = agent.answer(item["question"], item["company"])
        except errors.APIError as exc:
            not_run.append({"id": item["id"], "error": f"{exc.code} {exc.status}"})
            print(f"{item['id']} {item['company']:5} NOT RUN: {exc.code} {exc.status}")
            continue
        rows.append({"item": item, "answer": answer.to_dict(), "mentions_expected": mentions_expected(answer, item)})
        print(f"{item['id']} {item['company']:5} abstained={answer.abstained} cites={len(answer.citations)} "
              f"expected_in_answer={rows[-1]['mentions_expected']} | {answer.text[:120]}")
    with (out_dir / "smoke_v1_answers.jsonl").open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    answers = [r["answer"] for r in rows]
    summary = {
        "agent": agent.name,
        "model": agent.llm.model,
        "retriever": {"name": agent.retriever.name, "k": agent.k},
        "questions": len(rows) + len(not_run),
        "run": len(rows),
        "not_run": not_run,
        "answered": sum(not a["abstained"] for a in answers),
        "with_citations": sum(bool(a["citations"]) for a in answers),
        "citations_total": sum(len(a["citations"]) for a in answers),
        "quotes_found_verbatim": sum(c["quote_found"] for a in answers for c in a["citations"]),
        "mentions_expected": sum(r["mentions_expected"] for r in rows),
        "parse_errors": sum(a["trace"]["parse_error"] is not None for a in answers),
        "latency_s": sorted(a["latency_s"] for a in answers),
    }
    (out_dir / "smoke_v1_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "retrieval"}, indent=2))


if __name__ == "__main__":
    main()
