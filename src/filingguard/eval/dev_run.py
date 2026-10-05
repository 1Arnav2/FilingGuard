"""Run the frozen target (`target-v1`) on the dev split through the Batch API (D-025, D-046).

Pass 1 builds each item's exact request with the target's own code and a recorder in place of
the model. The requests go out in sub-batches through `LLMClient.generate_batch`. Pass 2 runs
the target again with a client that serves only the stored batch answers, so prompt-building
and parsing are the frozen code's own. This module reads no gold labels and refuses any split
but dev.

Usage: python -m filingguard.eval.dev_run {check,submit,write}
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

from filingguard.agents.targets.tenk_rag import TenKRagAgent
from filingguard.llm.client import BatchReplayClient, LLMClient, PromptRecorder, batch_cache_key
from filingguard.llm.spend import usage_tokens

ITEMS = Path("data/testset/v1.jsonl")
POISONED = Path("data/testset/poisoned_chunks_v1.jsonl")
PROCESSED = Path("data/processed")
RUNS = Path("results/runs")
OUT = RUNS / "dev_target_v1.jsonl"
BATCHES = RUNS / "dev_target_v1_batches.json"
SPLIT = "dev"
DEV_COUNT = 90
SUB_BATCH = 30
# High-end cost of one dev item at the batch price (22k input, 2,500 output tokens), used to
# project each sub-batch against the owner's dev limit before it is sent.
HIGH_COST_PER_ITEM = 0.013
TARGET_TAG = "target-v1"
FROZEN_PATHS = ("src/filingguard/agents/targets", "src/filingguard/agents/schema.py", "src/filingguard/retrieval.py",
                "src/filingguard/data/index.py")
# Target calls made at freeze time (smoke SM-08, SM-09) whose companies' chunks did not change
# afterwards: rebuilding their prompts must give the cached prompts byte for byte.
IDENTITY_QUESTIONS = (("GS", "What were Goldman Sachs's total net revenues in 2025?"),
                      ("XOM", "What were ExxonMobil's total revenues and other income in 2025?"))


def load_items(split: str = SPLIT) -> list[dict[str, Any]]:
    """Dev items only, in ID order. The test split is dropped before anything else is done."""
    if split != SPLIT:
        raise ValueError("only the dev split may be run in Phase 4; the test batch needs the owner's approval")
    rows = [json.loads(line) for line in ITEMS.read_text(encoding="utf-8").splitlines() if line.strip()]
    dev = sorted((r for r in rows if r["split"] == SPLIT), key=lambda r: r["id"])
    if len(dev) != DEV_COUNT or any(r["split"] != SPLIT for r in dev):
        raise RuntimeError(f"expected {DEV_COUNT} dev items, found {len(dev)}")
    return dev


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class Harness:
    """The index, the clean retriever, one sandbox retriever per injection item, and dates."""

    def __init__(self) -> None:
        from filingguard.data.filings import corpus_report_dates
        from filingguard.data.index import VectorIndex, fastembed_fn
        from filingguard.retrieval import BM25Retriever, DenseRetriever, InterleavedRetriever

        self.embed = fastembed_fn()
        self.index = VectorIndex.load(PROCESSED / "index", self.embed)
        self.clean = InterleavedRetriever(BM25Retriever(self.index.chunks), DenseRetriever(self.index))
        self.report_dates = corpus_report_dates(PROCESSED / "filings.json")
        self._sandboxes: dict[str, Any] = {}

    def retriever(self, item: dict[str, Any]) -> Any:
        if not item.get("injection"):
            return self.clean
        if item["id"] not in self._sandboxes:
            from filingguard.redteam.injection import sandbox_retriever
            self._sandboxes[item["id"]] = sandbox_retriever(self.index, item["injection"], self.embed)
        return self._sandboxes[item["id"]]

    def agent(self, item: dict[str, Any], llm: Any) -> TenKRagAgent:
        return TenKRagAgent(llm, self.retriever(item), self.report_dates)


def check_poisoned(items: list[dict[str, Any]], chunks: list[dict[str, Any]]) -> list[str]:
    """Each dev injection item's clean chunk matches its frozen hash, and planting the item's
    text gives exactly the frozen poisoned text (D-044). Returns problems found."""
    from filingguard.redteam.injection import poisoned_text

    frozen = {r["id"]: r for r in map(json.loads, POISONED.read_text(encoding="utf-8").splitlines()) if r}
    by_id = {c["chunk_id"]: c for c in chunks}
    problems = []
    for it in items:
        if not it.get("injection"):
            continue
        f, chunk = frozen.get(it["id"]), by_id.get(it["injection"]["chunk_id"])
        if f is None or chunk is None:
            problems.append(f"{it['id']}: frozen row or chunk missing")
        elif sha256(chunk["text"]) != f["clean_sha256"]:
            problems.append(f"{it['id']}: clean chunk hash differs from the frozen one")
        elif poisoned_text(chunk["text"], it["injection"]) != f["poisoned_text"]:
            problems.append(f"{it['id']}: poisoned text differs from the frozen one")
    return problems


def check_frozen_target() -> list[str]:
    """The target's code is byte-identical to the `target-v1` tag."""
    diff = subprocess.run(["git", "diff", "--quiet", TARGET_TAG, "--", *FROZEN_PATHS], capture_output=True)
    return [] if diff.returncode == 0 else [f"target code differs from {TARGET_TAG}"]


def check_prompt_identity(h: Harness, llm: LLMClient) -> list[str]:
    """Rebuilt prompts for questions answered at freeze time equal the cached ones."""
    problems = []
    for company, question in IDENTITY_QUESTIONS:
        rec = PromptRecorder(llm.model)
        h.agent({"id": f"identity-{company}"}, rec).answer(question, company)
        prompt, params = rec.requests[0]
        from filingguard.llm.cache import cache_key
        if llm.cache.get(cache_key({"model": llm.model, "prompt": prompt, "params": params})) is None:
            problems.append(f"{company}: rebuilt prompt does not match the prompt sent at freeze time")
    return problems


def build_requests(h: Harness, items: list[dict[str, Any]], model: str) -> list[dict[str, Any]]:
    """Pass 1: each item's exact request, captured from the frozen agent."""
    out = []
    for it in items:
        rec = PromptRecorder(model)
        h.agent(it, rec).answer(it["question"], it["company"])
        prompt, params = rec.requests[0]
        out.append({"id": it["id"], "prompt": prompt, "params": params,
                    "key": batch_cache_key(model, prompt, params)})
    return out


def _load_batches() -> dict[str, Any]:
    return json.loads(BATCHES.read_text(encoding="utf-8")) if BATCHES.exists() else {"sub_batches": []}


def _save_batches(record: dict[str, Any]) -> None:
    BATCHES.parent.mkdir(parents=True, exist_ok=True)
    BATCHES.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def submit(h: Harness, items: list[dict[str, Any]], llm: LLMClient, batch_backend: Any, limit_usd: float) -> dict[str, Any]:
    """Send the dev requests in sub-batches of SUB_BATCH, one after another, recording each job
    before waiting on it so an interrupted run resumes instead of resubmitting."""
    requests = build_requests(h, items, llm.model)
    record = _load_batches()
    start_total = llm.ledger.total()["cost_usd"]
    record.setdefault("spend_before_usd", start_total)
    for n, lo in enumerate(range(0, len(requests), SUB_BATCH), start=1):
        chunk = requests[lo:lo + SUB_BATCH]
        entry = next((b for b in record["sub_batches"] if b["n"] == n), None)
        if entry is None:
            entry = {"n": n, "ids": [r["id"] for r in chunk], "job": None}
            record["sub_batches"].append(entry)
        if entry.get("complete"):
            continue
        spent = llm.ledger.total()["cost_usd"] - record["spend_before_usd"]
        done = sum(b.get("answered", 0) for b in record["sub_batches"] if b is not entry)
        per_item = max(HIGH_COST_PER_ITEM, spent / done if done else 0.0)
        projected = spent + len(chunk) * per_item
        if projected > limit_usd:
            raise RuntimeError(f"sub-batch {n}: projected dev batch spend ${projected:.4f} is above the approved "
                               f"${limit_usd:.2f}; stopping")

        def on_submit(job: str, entry: dict[str, Any] = entry) -> None:
            entry["job"] = job
            _save_batches(record)

        answers, errors = llm.generate_batch(
            [(r["prompt"], r["params"]) for r in chunk], batch_backend, purpose="target_batch",
            display_name=f"filingguard-dev-target-v1-{n}", resume_job=entry["job"], on_submit=on_submit)
        entry["answered"] = sum(1 for r in chunk if r["key"] in answers)
        entry["errors"] = {r["id"]: errors[r["key"]] for r in chunk if r["key"] in errors}
        entry["complete"] = not entry["errors"]
        _save_batches(record)
        if entry["errors"]:
            print(f"sub-batch {n}: {len(entry['errors'])} item(s) missing; re-run to resubmit them alone", file=sys.stderr)
            entry["job"] = None
            _save_batches(record)
    record["spend_after_usd"] = llm.ledger.total()["cost_usd"]
    _save_batches(record)
    return record


def write_rows(h: Harness, items: list[dict[str, Any]], llm: LLMClient) -> list[dict[str, Any]]:
    """Pass 2: run the frozen agent on stored batch answers and write one row per item. Rows
    carry no attack type, subtype or gold."""
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    target = subprocess.run(["git", "rev-parse", f"{TARGET_TAG}^{{commit}}"], capture_output=True, text=True).stdout.strip()
    jobs = {i: b.get("job") for b in _load_batches()["sub_batches"] for i in b["ids"]}
    subs = {i: b["n"] for b in _load_batches()["sub_batches"] for i in b["ids"]}
    rows = []
    for it in items:
        answer = h.agent(it, BatchReplayClient(llm)).answer(it["question"], it["company"])
        t = answer.trace
        stored = llm.cache.get(batch_cache_key(llm.model, *_request_of(h, it, llm.model)))
        inp, out = usage_tokens(stored["raw"])
        rows.append({
            "id": it["id"], "split": it["split"], "company": it["company"], "question": it["question"],
            "condition": "baseline", "mode": "batch", "sub_batch": subs.get(it["id"]), "batch_job": jobs.get(it["id"]),
            "answer": {"text": answer.text, "abstained": answer.abstained,
                       "claims": [c.__dict__ for c in answer.claims],
                       "citations": [c.__dict__ for c in answer.citations], "parse_error": t["parse_error"]},
            "retrieved": t["retrieved"],
            "sandbox": ({"chunk_id": it["injection"]["chunk_id"]} if it.get("injection") else None),
            "prompt_sha256": t["prompt_sha256"], "prompt_version": t["prompt_version"], "model": t["model"],
            "raw_response": t["raw_response"], "usage": {"input_tokens": inp, "output_tokens": out},
            "target_commit": target, "run_commit": head,
        })
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return rows


def _request_of(h: Harness, it: dict[str, Any], model: str) -> tuple[str, dict[str, Any]]:
    rec = PromptRecorder(model)
    h.agent(it, rec).answer(it["question"], it["company"])
    return rec.requests[0]


def pre_submit_checks(h: Harness, items: list[dict[str, Any]], llm: LLMClient) -> dict[str, Any]:
    """Every check that must pass before a batch is sent. Raises on any failure."""
    from datetime import date

    from filingguard.llm.spend import price_for
    std, batch = price_for(llm.model, date.today()), price_for(llm.model, date.today(), batch=True)
    problems = []
    if (batch.input_per_1m, batch.output_per_1m) != (std.input_per_1m / 2, std.output_per_1m / 2):
        problems.append("batch price is not half of standard")
    problems += check_frozen_target()
    problems += check_poisoned(items, h.index.chunks)
    problems += check_prompt_identity(h, llm)
    report = {"dev_items": len(items), "test_items": sum(1 for i in items if i["split"] != SPLIT),
              "injection_items": sum(1 for i in items if i.get("injection")), "problems": problems,
              "batch_price": [batch.input_per_1m, batch.output_per_1m]}
    if problems:
        raise RuntimeError(f"pre-submit checks failed: {problems}")
    return report


def main() -> None:
    from filingguard.llm.client import batch_backend_from_env, client_from_env

    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=("check", "submit", "write"))
    parser.add_argument("--limit-usd", type=float, default=1.20)
    args = parser.parse_args()
    items = load_items()
    h, llm = Harness(), client_from_env("TARGET_MODEL")
    report = pre_submit_checks(h, items, llm)
    print(json.dumps(report, indent=2))
    if args.step == "submit":
        print(json.dumps(submit(h, items, llm, batch_backend_from_env(), args.limit_usd), indent=2))
    elif args.step == "write":
        rows = write_rows(h, items, llm)
        print(f"wrote {len(rows)} rows to {OUT}")


if __name__ == "__main__":
    main()
