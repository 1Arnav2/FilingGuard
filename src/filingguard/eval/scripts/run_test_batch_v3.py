"""Phase 5 step 3, remaining items (owner's decisions D-068, D-069). Repo code unchanged: the same
`dev_run` checks, `dev_run.submit` and `dev_run.write_rows`.

Before every job its size is recomputed from the actual spend: min(30, floor((7 - spend) / 0.1306),
items left). A refused cap check, a job error or expiry, a missing item, an invalid answer not cut off
at MAX_TOKENS, or more than 2 invalid answers in a sub-batch stops the run. Saved raw files are never
rewritten: each new sub-batch's raw file is written once; finish reasons go to a separate file; new
answer rows are appended to the answers file. Each sub-batch is committed before the next is sent.
"""
import dataclasses
import json
import math
import os
import subprocess
import sys
import tempfile
import traceback
from datetime import date
from pathlib import Path

from filingguard.eval import dev_run
from filingguard.llm.client import client_from_env, gemini_file_batch_backend
from filingguard.llm.spend import price_for

CAP = 7.0
WORST_PER_ITEM = 0.1306   # D-069
MAX_PER_JOB = 30
LIMIT_USD = 3.00          # D-068
MAX_INVALID = 2
RAW_DIR = Path("results/runs/test_target_v1_raw")
REASONS = RAW_DIR / "finish_reasons.jsonl"
SPEC = dev_run.SPECS["test"]


def log(msg: str) -> None:
    print(msg, flush=True)


def finish_reason(raw) -> str | None:
    stack = [raw]
    while stack:
        o = stack.pop()
        if isinstance(o, dict):
            for k, v in o.items():
                if k.lower().replace("_", "") == "finishreason":
                    return v
                stack.append(v)
        elif isinstance(o, list):
            stack.extend(o)
    return None


def git_commit(message: str) -> None:
    subprocess.run(["git", "add", "results/runs/test_target_v1.jsonl", "results/runs/test_target_v1_batches.json",
                    str(RAW_DIR), "results/spend/ledger.jsonl", "results/spend/total.json"], check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode != 0:
        subprocess.run(["git", "commit", "-q", "-m", message], check=True)
        log("committed: " + subprocess.run(["git", "log", "-1", "--format=%h %s"], capture_output=True,
                                           text=True).stdout.strip())


def append_lines(path: Path, lines: list[str]) -> None:
    with path.open("ab") as f:
        f.write("".join(l + "\n" for l in lines).encode("utf-8"))


def save_new(h, items, llm, keys, entry) -> int:
    """Write the new sub-batch's raw file once, append its finish reasons and its answer rows."""
    by_id = {it["id"]: it for it in items}
    raw_path = RAW_DIR / f"sub_batch_{entry['n']}.jsonl"
    assert not raw_path.exists(), f"{raw_path} already saved; never rewritten"
    got = [i for i in entry["ids"] if llm.cache.get(keys[i]) is not None]
    invalid = entry.get("invalid_replies") or {}
    raw_lines, reason_lines = [], []
    for i in got:
        hit = llm.cache.get(keys[i])
        raw_lines.append(json.dumps({"id": i, "key": keys[i], "batch_job": hit.get("batch_job"), "text": hit["text"],
                                     "raw": hit["raw"], "valid": i not in invalid}, ensure_ascii=False))
        reason_lines.append(json.dumps({"id": i, "sub_batch": entry["n"], "finish_reason": finish_reason(hit["raw"])}))
    raw_path.write_bytes("".join(l + "\n" for l in raw_lines).encode("utf-8"))
    append_lines(REASONS, reason_lines)
    if got:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "rows.jsonl"
            dev_run.write_rows(h, [by_id[i] for i in sorted(got)], llm, dataclasses.replace(SPEC, out=out))
            append_lines(SPEC.out, out.read_text(encoding="utf-8").splitlines())
    return len(got)


def ensure_reasons_file(llm, keys) -> None:
    """Finish reasons for the 61 answers saved before D-069, in the separate file (raw files untouched)."""
    if REASONS.exists():
        return
    lines = []
    for b in dev_run._load_batches(SPEC)["sub_batches"]:
        for i in b["ids"]:
            hit = llm.cache.get(keys[i])
            if hit is not None:
                lines.append(json.dumps({"id": i, "sub_batch": b["n"], "finish_reason": finish_reason(hit["raw"])}))
    REASONS.write_bytes("".join(l + "\n" for l in lines).encode("utf-8"))


def checks(h, items, llm, keys) -> None:
    std, batch = price_for(llm.model, date.today()), price_for(llm.model, date.today(), batch=True)
    problems = []
    if (batch.input_per_1m, batch.output_per_1m) != (std.input_per_1m / 2, std.output_per_1m / 2):
        problems.append("batch price is not half of standard")
    problems += dev_run.check_frozen_target() + dev_run.check_frozen_verifier()
    problems += dev_run.check_poisoned(items, h.index.chunks) + dev_run.check_prompt_identity(h, llm)
    if len(items) != 210 or any(i["split"] != "test" for i in items):
        problems.append("expected 210 test items only")
    record = dev_run._load_batches(SPEC)
    saved_ids = {i for b in record["sub_batches"] for i in b["ids"]}
    cached = {i for i, k in keys.items() if llm.cache.get(k) is not None}
    if cached != saved_ids or len(cached) != 61:
        problems.append(f"cached test answers ({len(cached)}) are not exactly the 61 saved")
    if not all(b.get("complete") for b in record["sub_batches"]):
        problems.append("a saved sub-batch is not complete")
    rows = SPEC.out.read_text(encoding="utf-8").splitlines()
    if len(rows) != 61:
        problems.append(f"answers file has {len(rows)} rows, expected 61")
    log("checks: " + json.dumps({"problems": problems, "cached_test_answers": len(cached),
                                 "spend_usd": round(llm.ledger.total()["cost_usd"], 6)}))
    if problems:
        raise SystemExit("checks failed; nothing sent")


def main() -> None:
    items = dev_run.load_items("test", allow_test=True)
    llm = client_from_env("TARGET_MODEL")
    h = dev_run.Harness()
    keys = {r["id"]: r["key"] for r in dev_run.build_requests(h, items, llm.model)}
    checks(h, items, llm, keys)
    ensure_reasons_file(llm, keys)
    backend = gemini_file_batch_backend(os.environ["GEMINI_API_KEY"])
    while True:
        record = dev_run._load_batches(SPEC)
        sizes = [len(b["ids"]) for b in record["sub_batches"]]
        left = len(items) - sum(sizes)
        if left <= 0:
            break
        spend = llm.ledger.total()["cost_usd"]
        size = min(MAX_PER_JOB, math.floor((CAP - spend) / WORST_PER_ITEM), left)
        n = len(sizes) + 1
        if size <= 0:
            log(f"STOPPED: no room under the cap check for another job (spend ${spend:.4f}); {left} items not run")
            sys.exit(1)
        log(f"sub-batch {n}: size {size} (floor((7 - {spend:.4f}) / {WORST_PER_ITEM}) capped at {MAX_PER_JOB}, "
            f"{left} left); spend before ${spend:.4f}")
        spec_n = dataclasses.replace(SPEC, sub_batch_sizes=tuple(sizes + [size]))
        stop = None
        try:
            dev_run.submit(h, items, llm, backend, LIMIT_USD, spec_n)
        except Exception as exc:
            msg = "".join(traceback.format_exception_only(type(exc), exc)).strip()
            record = dev_run._load_batches(SPEC)
            entry = next((b for b in record["sub_batches"] if b["n"] == n), None)
            invalid = (entry or {}).get("invalid_replies") or {}
            missing = (entry or {}).get("errors") or {}
            reasons = {i: finish_reason((llm.cache.get(keys[i]) or {}).get("raw")) for i in invalid}
            if entry is None or "invalid_replies" not in entry or missing:
                stop = f"{msg} (cap check, gate, job error, expiry or missing items)"
            elif len(invalid) > MAX_INVALID:
                stop = f"{len(invalid)} invalid answers in sub-batch {n} (limit {MAX_INVALID}): {reasons}"
            elif any(r != "MAX_TOKENS" for r in reasons.values()):
                stop = f"invalid answer not cut off at the output limit: {reasons} {invalid}"
            else:
                entry["complete"] = True
                entry["owner_ruling"] = {"date": "2026-10-19", "decision": "D-068", "unparseable": reasons,
                                         "reason": "cut off at the output limit; recorded as unparseable "
                                                   "(Missed, counted separately, EVAL 3); not resent"}
                dev_run._save_batches(record, SPEC)
                log(f"sub-batch {n}: unparseable under D-068 (MAX_TOKENS): {sorted(reasons)}; continuing")
        record = dev_run._load_batches(SPEC)
        entry = next((b for b in record["sub_batches"] if b["n"] == n), None)
        new = save_new(h, items, llm, keys, entry) if entry and entry.get("answered") else 0
        total_saved = len(SPEC.out.read_text(encoding="utf-8").splitlines())
        after = llm.ledger.total()["cost_usd"]
        e = entry or {}
        log(f"sub-batch {n}: job {e.get('job')} sent {len(e.get('ids') or [])} answered {e.get('answered')} "
            f"invalid {len(e.get('invalid_replies') or {})} missing {len(e.get('errors') or {})} "
            f"cost ${after - spend:.4f}; new answers {new}; saved {total_saved}/210; spend ${after:.4f}")
        if stop:
            log("STOPPED: " + stop)
        git_commit(f"Phase 5 step 3: test batch sub-batch {n} saved ({total_saved} of 210 answers)"
                   + (" - run stopped" if stop else ""))
        if stop:
            sys.exit(1)
    log(f"all items sent; saved {len(SPEC.out.read_text(encoding='utf-8').splitlines())}/210")


if __name__ == "__main__":
    main()
