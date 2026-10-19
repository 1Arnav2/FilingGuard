"""Phase 5 step 3, sub-batches 3-6 (owner's decision D-068). Repo code unchanged: the same
`dev_run` checks, `dev_run.submit` and `dev_run.write_rows`.

Stop rule (D-068): an invalid answer whose finish reason is MAX_TOKENS is recorded as unparseable
and the run continues; any other invalid answer, a missing item (job error or expiry), any other
failure, or more than 2 invalid answers in one sub-batch stops the run. Gate $3.00 of batch spend.
Each sub-batch is saved and committed before the next is sent. Nothing is ever resent: cached
answers are skipped by `generate_batch`, and completed sub-batches by `submit`.
"""
import dataclasses
import json
import os
import subprocess
import sys
import traceback
from datetime import date
from pathlib import Path

from filingguard.eval import dev_run
from filingguard.llm.client import client_from_env, gemini_file_batch_backend
from filingguard.llm.spend import price_for

LIMIT_USD = 3.00  # D-068
MAX_INVALID = 2
RAW_DIR = Path("results/runs/test_target_v1_raw")
SPEC = dev_run.SPECS["test"]
SAVED_BEFORE = 31


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


def save(h, items, llm, keys) -> int:
    record = dev_run._load_batches(SPEC)
    by_id = {it["id"]: it for it in items}
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    answered = []
    for b in record["sub_batches"]:
        lines = []
        for i in b["ids"]:
            hit = llm.cache.get(keys[i])
            if hit is None:
                continue
            lines.append(json.dumps({"id": i, "key": keys[i], "batch_job": hit.get("batch_job"), "text": hit["text"],
                                     "raw": hit["raw"], "finish_reason": finish_reason(hit["raw"]),
                                     "valid": i not in (b.get("invalid_replies") or {})}, ensure_ascii=False))
            answered.append(by_id[i])
        (RAW_DIR / f"sub_batch_{b['n']}.jsonl").write_bytes("".join(l + "\n" for l in lines).encode("utf-8"))
    if answered:
        dev_run.write_rows(h, sorted(answered, key=lambda it: it["id"]), llm, SPEC)
    return len(answered)


def checks(h, items, llm, keys) -> None:
    std, batch = price_for(llm.model, date.today()), price_for(llm.model, date.today(), batch=True)
    problems = []
    if (batch.input_per_1m, batch.output_per_1m) != (std.input_per_1m / 2, std.output_per_1m / 2):
        problems.append("batch price is not half of standard")
    problems += dev_run.check_frozen_target() + dev_run.check_frozen_verifier()
    problems += dev_run.check_poisoned(items, h.index.chunks) + dev_run.check_prompt_identity(h, llm)
    if len(items) != 210 or any(i["split"] != "test" for i in items):
        problems.append("expected 210 test items only")
    cached = [i for i, k in keys.items() if llm.cache.get(k) is not None]
    record = dev_run._load_batches(SPEC)
    saved_ids = {i for b in record["sub_batches"] for i in b["ids"]}
    if len(cached) != SAVED_BEFORE or set(cached) != saved_ids:
        problems.append(f"cached test answers {len(cached)} do not equal the {SAVED_BEFORE} saved ones")
    if not all(b.get("complete") for b in record["sub_batches"]):
        problems.append("a saved sub-batch is not complete")
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
    backend = gemini_file_batch_backend(os.environ["GEMINI_API_KEY"])
    sizes = SPEC.sub_batch_sizes
    for n in range(3, len(sizes) + 1):
        spec_n = dataclasses.replace(SPEC, sub_batch_sizes=sizes[:n])
        before = llm.ledger.total()["cost_usd"]
        log(f"sub-batch {n}/{len(sizes)}: sending up to {sizes[n - 1]} items; spend before ${before:.4f}")
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
                stop = f"{msg} (job error, expiry, gate or missing items)"
            elif len(invalid) > MAX_INVALID:
                stop = f"{len(invalid)} invalid answers in sub-batch {n} (limit {MAX_INVALID}): {reasons}"
            elif any(r != "MAX_TOKENS" for r in reasons.values()):
                stop = f"invalid answer not cut off at the output limit: {reasons} {invalid}"
            else:
                entry["complete"] = True
                entry["owner_ruling"] = {"date": "2026-10-19", "decision": "D-068",
                                         "unparseable": reasons,
                                         "reason": "cut off at the output limit; recorded as unparseable "
                                                   "(Missed, counted separately, EVAL 3); not resent"}
                dev_run._save_batches(record, SPEC)
                log(f"sub-batch {n}: unparseable under D-068 (MAX_TOKENS): {sorted(reasons)}; continuing")
        saved = save(h, items, llm, keys)
        after = llm.ledger.total()["cost_usd"]
        entry = next((b for b in dev_run._load_batches(SPEC)["sub_batches"] if b["n"] == n), {})
        log(f"sub-batch {n}: job {entry.get('job')} answered {entry.get('answered')} invalid "
            f"{len(entry.get('invalid_replies') or {})} missing {len(entry.get('errors') or {})} "
            f"cost ${after - before:.4f}; answers saved so far {saved}; spend ${after:.4f}")
        if stop:
            log("STOPPED: " + stop)
        git_commit(f"Phase 5 step 3: test batch sub-batch {n} of {len(sizes)} saved ({saved} answers so far)"
                   + (" - run stopped" if stop else ""))
        if stop:
            sys.exit(1)
    log("all sub-batches complete")


if __name__ == "__main__":
    main()
