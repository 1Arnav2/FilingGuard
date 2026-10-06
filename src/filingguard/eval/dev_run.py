"""Run the frozen target (`target-v1`) on a split through the Batch API (D-025, D-046, Phase 5 plan).

Pass 1 builds each item's exact request with the target's own code and a recorder in place of
the model. The requests go out in sub-batches through `LLMClient.generate_batch`. Pass 2 runs
the target again with a client that serves only the stored batch answers, so prompt-building
and parsing are the frozen code's own. This module reads no gold labels.

The test split (D-062): `check` builds the requests locally and makes no model call; `submit`
and `write` refuse to run without `--owner-approved-test`.

Usage: python -m filingguard.eval.dev_run {check,submit,write} [--split test [--owner-approved-test]]
"""

import argparse
import hashlib
import json
import statistics
import subprocess
import sys
from dataclasses import dataclass
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
BATCHES = RUNS / "dev_target_v1_rerun_batches.json"  # the first run's record, dev_target_v1_batches.json, is H-028
TAG = "batch-file"
SPLIT = "dev"
DEV_COUNT = 90
SUB_BATCH_SIZES = (5, 30, 30, 25)
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


_JSON_TYPES = {"string": str, "boolean": bool, "array": list, "object": dict, "null": type(None)}


def schema_errors(value: Any, schema: dict[str, Any], path: str = "$") -> list[str]:
    """Errors of `value` against the subset of JSON Schema the target's response schema uses:
    type (one or a list), required, properties, items."""
    types = schema.get("type")
    if types is not None:
        allowed = types if isinstance(types, list) else [types]
        ok = any((isinstance(value, (int, float)) and not isinstance(value, bool)) if t == "number"
                 else isinstance(value, _JSON_TYPES[t]) and not (t != "boolean" and isinstance(value, bool))
                 for t in allowed)
        if not ok:
            return [f"{path}: expected {allowed}, got {type(value).__name__}"]
    errors = []
    if isinstance(value, dict):
        errors += [f"{path}: missing {k}" for k in schema.get("required", []) if k not in value]
        for k, sub in schema.get("properties", {}).items():
            if k in value:
                errors += schema_errors(value[k], sub, f"{path}.{k}")
    if isinstance(value, list) and "items" in schema:
        for i, v in enumerate(value):
            errors += schema_errors(v, schema["items"], f"{path}[{i}]")
    return errors


def reply_errors(text: str, hits: list[Any]) -> list[str]:
    """Why a target reply is not valid: not JSON, off the response schema, or not parsed cleanly
    by the frozen parser (H-028). Empty if valid."""
    from filingguard.agents.targets.tenk_rag import RESPONSE_SCHEMA, parse_response
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return [f"invalid JSON: {exc}"]
    errors = schema_errors(data, RESPONSE_SCHEMA)
    if errors:
        return errors
    try:
        _, parse_error = parse_response(text, hits)
    except Exception as exc:  # the frozen parser must not crash on a valid reply
        return [f"frozen parser raised {type(exc).__name__}: {exc}"]
    return [parse_error] if parse_error else []


@dataclass(frozen=True)
class RunSpec:
    split: str
    count: int
    out: Path
    batches: Path
    sub_batch_sizes: tuple[int, ...]
    limit_usd: float
    reason: str


SPECS = {
    "dev": RunSpec("dev", DEV_COUNT, OUT, BATCHES, SUB_BATCH_SIZES, 1.00,
                   "re-run of the dev batch under D-025 after H-028; file-based jobs"),
    # Phase 5 plan (D-062): a one-item probe first; the $2.60 limit is the owner's.
    "test": RunSpec("test", 210, RUNS / "test_target_v1.jsonl", RUNS / "test_target_v1_batches.json",
                    (1, 30, 30, 50, 50, 49), 2.60, "test batch under D-025 and docs/PHASE5_PLAN.md; file-based jobs"),
}


def load_items(split: str = SPLIT, allow_test: bool = False) -> list[dict[str, Any]]:
    """One split's items, in ID order; the other split is dropped before anything else is done.
    The test split loads only when the caller says so (`allow_test`)."""
    if split not in SPECS or (split == "test" and not allow_test):
        raise ValueError("only the dev split loads by default; the test split needs allow_test")
    spec = SPECS[split]
    rows = [json.loads(line) for line in ITEMS.read_text(encoding="utf-8").splitlines() if line.strip()]
    chosen = sorted((r for r in rows if r["split"] == split), key=lambda r: r["id"])
    if len(chosen) != spec.count:
        raise RuntimeError(f"expected {spec.count} {split} items, found {len(chosen)}")
    return chosen


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
                    "key": batch_cache_key(model, prompt, params, TAG)})
    return out


def _batches_path(spec: RunSpec) -> Path:
    return BATCHES if spec.split == "dev" else spec.batches  # dev's path can be patched in tests


def _load_batches(spec: RunSpec = SPECS["dev"]) -> dict[str, Any]:
    path = _batches_path(spec)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"sub_batches": []}


def _save_batches(record: dict[str, Any], spec: RunSpec = SPECS["dev"]) -> None:
    path = _batches_path(spec)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


def submit(h: Harness, items: list[dict[str, Any]], llm: LLMClient, batch_backend: Any, limit_usd: float,
           spec: RunSpec = SPECS["dev"]) -> dict[str, Any]:
    """Send the requests in the split's sub-batches, one after another, recording each job before
    waiting on it so an interrupted run resumes instead of resubmitting. Every reply in a
    sub-batch is checked against the response schema and the frozen parser before the next is
    sent; the run stops on the first invalid reply or missing item (H-028)."""
    requests = build_requests(h, items, llm.model)
    record = _load_batches(spec)
    record.setdefault("tag", TAG)
    record.setdefault("reason", spec.reason)
    record.setdefault("spend_before_usd", llm.ledger.total()["cost_usd"])
    by_id = {it["id"]: it for it in items}
    lo = 0
    for n, size in enumerate(spec.sub_batch_sizes, start=1):
        chunk, lo = requests[lo:lo + size], lo + size
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
            raise RuntimeError(f"sub-batch {n}: projected {spec.split} batch spend ${projected:.4f} is above the approved "
                               f"${limit_usd:.2f}; stopping")

        def on_submit(job: str, entry: dict[str, Any] = entry) -> None:
            entry["job"] = job
            _save_batches(record, spec)

        answers, errors = llm.generate_batch(
            [(r["prompt"], r["params"]) for r in chunk], batch_backend, purpose="target_batch_file",
            display_name=f"filingguard-{spec.split}-target-v1-file-{n}", resume_job=entry["job"],
            on_submit=on_submit, tag=TAG)
        entry["answered"] = sum(1 for r in chunk if r["key"] in answers)
        entry["errors"] = {r["id"]: errors[r["key"]] for r in chunk if r["key"] in errors}
        invalid = {}
        for r in chunk:
            if r["key"] in answers:
                it = by_id[r["id"]]
                problems = reply_errors(answers[r["key"]].text, h.retriever(it).retrieve(it["question"], it["company"], 20))
                if problems:
                    invalid[r["id"]] = problems
        entry["invalid_replies"] = invalid
        entry["complete"] = not entry["errors"] and not invalid
        record["spend_after_usd"] = llm.ledger.total()["cost_usd"]
        _save_batches(record, spec)
        if not entry["complete"]:
            raise RuntimeError(f"sub-batch {n}: {len(invalid)} invalid repl(ies), {len(entry['errors'])} missing; "
                               f"stopping before any further submission: {invalid or entry['errors']}")
    return record


def write_rows(h: Harness, items: list[dict[str, Any]], llm: LLMClient,
               spec: RunSpec = SPECS["dev"]) -> list[dict[str, Any]]:
    """Pass 2: run the frozen agent on stored batch answers and write one row per item. Rows
    carry no attack type, subtype or gold."""
    head = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    target = subprocess.run(["git", "rev-parse", f"{TARGET_TAG}^{{commit}}"], capture_output=True, text=True).stdout.strip()
    jobs = {i: b.get("job") for b in _load_batches(spec)["sub_batches"] for i in b["ids"]}
    subs = {i: b["n"] for b in _load_batches(spec)["sub_batches"] for i in b["ids"]}
    rows = []
    for it in items:
        answer = h.agent(it, BatchReplayClient(llm, TAG)).answer(it["question"], it["company"])
        t = answer.trace
        stored = llm.cache.get(batch_cache_key(llm.model, *_request_of(h, it, llm.model), TAG))
        inp, out = usage_tokens(stored["raw"])
        rows.append({
            "id": it["id"], "split": it["split"], "company": it["company"], "question": it["question"],
            "condition": "baseline", "mode": TAG, "sub_batch": subs.get(it["id"]), "batch_job": jobs.get(it["id"]),
            "answer": {"text": answer.text, "abstained": answer.abstained,
                       "claims": [c.__dict__ for c in answer.claims],
                       "citations": [c.__dict__ for c in answer.citations], "parse_error": t["parse_error"]},
            "retrieved": t["retrieved"],
            "sandbox": ({"chunk_id": it["injection"]["chunk_id"]} if it.get("injection") else None),
            "prompt_sha256": t["prompt_sha256"], "prompt_version": t["prompt_version"], "model": t["model"],
            "raw_response": t["raw_response"], "usage": {"input_tokens": inp, "output_tokens": out},
            "target_commit": target, "run_commit": head,
        })
    spec.out.parent.mkdir(parents=True, exist_ok=True)
    spec.out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return rows


def _request_of(h: Harness, it: dict[str, Any], model: str) -> tuple[str, dict[str, Any]]:
    rec = PromptRecorder(model)
    h.agent(it, rec).answer(it["question"], it["company"])
    return rec.requests[0]


def check_frozen_verifier() -> list[str]:
    """The verifier matches its freeze record (`verifier-v1`, D-060, D-061): its pinned test passes.
    Run as a subprocess, because this module imports nothing else from `eval/` (gold isolation)."""
    test = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests/test_verifier_frozen.py"], capture_output=True)
    return [] if test.returncode == 0 else ["verifier differs from its freeze record"]


def project_cost(h: Harness, requests: list[dict[str, Any]], llm: LLMClient, batch: Any) -> dict[str, Any]:
    """Projected batch cost of `requests`, calibrated on the dev batch: input tokens from prompt
    characters at dev's measured tokens per character; output tokens at dev's mean and 90th
    percentile. No model call."""
    dev_rows = [json.loads(line) for line in OUT.read_text(encoding="utf-8").splitlines() if line.strip()]
    dev_items = {i["id"]: i for i in load_items("dev")}
    dev_chars = sum(len(_request_of(h, dev_items[r["id"]], llm.model)[0]) for r in dev_rows)
    per_char = sum(r["usage"]["input_tokens"] for r in dev_rows) / dev_chars
    outs = sorted(r["usage"]["output_tokens"] for r in dev_rows)
    tokens_in = per_char * sum(len(r["prompt"]) for r in requests)

    def usd(out_per_item: float) -> float:
        return round((tokens_in * batch.input_per_1m + len(requests) * out_per_item * batch.output_per_1m) / 1e6, 4)

    return {"items": len(requests), "input_tokens_per_char_dev": round(per_char, 4),
            "projected_input_tokens": round(tokens_in), "projected_usd_mean_output": usd(statistics.mean(outs)),
            "projected_usd_p90_output": usd(outs[int(0.9 * len(outs))]),
            "worst_case_usd_at_dev_high_cost": round(len(requests) * HIGH_COST_PER_ITEM, 4)}


def pre_submit_checks(h: Harness, items: list[dict[str, Any]], llm: LLMClient,
                      spec: RunSpec = SPECS["dev"]) -> dict[str, Any]:
    """Every check that must pass before a batch is sent. Raises on any failure. Makes no model call."""
    from datetime import date

    from filingguard.llm.spend import price_for
    std, batch = price_for(llm.model, date.today()), price_for(llm.model, date.today(), batch=True)
    problems = []
    if (batch.input_per_1m, batch.output_per_1m) != (std.input_per_1m / 2, std.output_per_1m / 2):
        problems.append("batch price is not half of standard")
    problems += check_frozen_target()
    problems += check_poisoned(items, h.index.chunks)
    problems += check_prompt_identity(h, llm)
    other = sum(1 for i in items if i["split"] != spec.split)
    if other or len(items) != spec.count:
        problems.append(f"expected {spec.count} {spec.split} items and no others; got {len(items)}, {other} others")
    report = {"split": spec.split, "items": len(items), "other_split_items": other,
              "injection_items": sum(1 for i in items if i.get("injection")), "problems": problems,
              "batch_price": [batch.input_per_1m, batch.output_per_1m]}
    if spec.split == "test":
        problems += check_frozen_verifier()
        requests = build_requests(h, items, llm.model)
        cached = sum(1 for r in requests if llm.cache.get(r["key"]) is not None)
        if cached:
            problems.append(f"{cached} test answers are already in the cache")
        report.update(test_answers_already_cached=cached, sub_batches=list(spec.sub_batch_sizes),
                      limit_usd=spec.limit_usd, cost=project_cost(h, requests, llm, batch),
                      spend_so_far_usd=round(llm.ledger.total()["cost_usd"], 4))
    if problems:
        raise RuntimeError(f"pre-submit checks failed: {problems}")
    return report


def main() -> None:
    import os

    from filingguard.llm.client import client_from_env, gemini_file_batch_backend

    parser = argparse.ArgumentParser()
    parser.add_argument("step", choices=("check", "submit", "write"))
    parser.add_argument("--split", choices=tuple(SPECS), default="dev")
    parser.add_argument("--owner-approved-test", action="store_true",
                        help="required for submit and write on the test split (owner's go-ahead)")
    parser.add_argument("--limit-usd", type=float)
    args = parser.parse_args()
    spec = SPECS[args.split]
    if spec.split == "test" and args.step != "check" and not args.owner_approved_test:
        raise SystemExit("the test batch needs the owner's go-ahead: pass --owner-approved-test")
    items = load_items(spec.split, allow_test=spec.split == "test")
    h, llm = Harness(), client_from_env("TARGET_MODEL")
    report = pre_submit_checks(h, items, llm, spec)
    print(json.dumps(report, indent=2))
    if args.step == "submit":
        backend = gemini_file_batch_backend(os.environ["GEMINI_API_KEY"])
        print(json.dumps(submit(h, items, llm, backend, args.limit_usd or spec.limit_usd, spec), indent=2))
    elif args.step == "write":
        rows = write_rows(h, items, llm, spec)
        print(f"wrote {len(rows)} rows to {spec.out}")


if __name__ == "__main__":
    main()
