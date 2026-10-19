"""Phase 5 step 3 driver (owner's go-ahead, D-067). Uses the repo's own tested code unchanged:
`dev_run.pre_submit_checks`, `dev_run.submit` (validation and stop rules) and `dev_run.write_rows`.

`submit` is called once per sub-batch with the plan's sizes as a growing prefix, so it sends one new
sub-batch per call; completed sub-batches are skipped and cached answers are never resent. After
each sub-batch: raw outputs, validated answers and the batch record are written under results/runs/
and committed locally before the next sub-batch is sent. Any failure stops the run (no retries).
"""
import dataclasses
import json
import os
import subprocess
import sys
import traceback
from pathlib import Path

from filingguard.eval import dev_run
from filingguard.llm.client import client_from_env, gemini_file_batch_backend

LIMIT_USD = 2.75  # D-067
RAW_DIR = Path("results/runs/test_target_v1_raw")
SPEC = dev_run.SPECS["test"]


def log(msg: str) -> None:
    print(msg, flush=True)


def git_commit(message: str) -> None:
    subprocess.run(["git", "add", "results/runs/test_target_v1.jsonl", "results/runs/test_target_v1_batches.json",
                    str(RAW_DIR), "results/spend/ledger.jsonl", "results/spend/total.json"], check=True)
    if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode != 0:
        subprocess.run(["git", "commit", "-q", "-m", message], check=True)
        log("committed: " + subprocess.run(["git", "log", "-1", "--format=%h %s"], capture_output=True,
                                           text=True).stdout.strip())


def save(h, items, llm, keys: dict[str, str]) -> int:
    """Raw outputs per sub-batch, the validated answers so far, and the record (already on disk)."""
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
                                     "raw": hit["raw"], "valid": i not in (b.get("invalid_replies") or {})},
                                    ensure_ascii=False))
            answered.append(by_id[i])
        (RAW_DIR / f"sub_batch_{b['n']}.jsonl").write_text("".join(l + "\n" for l in lines), encoding="utf-8")
    if answered:
        dev_run.write_rows(h, sorted(answered, key=lambda it: it["id"]), llm, SPEC)
    return len(answered)


def main() -> None:
    items = dev_run.load_items("test", allow_test=True)
    llm = client_from_env("TARGET_MODEL")
    h = dev_run.Harness()
    report = dev_run.pre_submit_checks(h, items, llm, SPEC)
    log("pre-submit: " + json.dumps({k: report[k] for k in ("items", "other_split_items", "problems",
                                                           "test_answers_already_cached", "spend_so_far_usd")}))
    backend = gemini_file_batch_backend(os.environ["GEMINI_API_KEY"])
    keys = {r["id"]: r["key"] for r in dev_run.build_requests(h, items, llm.model)}
    sizes = SPEC.sub_batch_sizes
    for n in range(1, len(sizes) + 1):
        spec_n = dataclasses.replace(SPEC, sub_batch_sizes=sizes[:n])
        before = llm.ledger.total()["cost_usd"]
        log(f"sub-batch {n}/{len(sizes)}: sending up to {sizes[n - 1]} items; spend before ${before:.4f}")
        failure = None
        try:
            dev_run.submit(h, items, llm, backend, LIMIT_USD, spec_n)
        except Exception as exc:  # any failure stops the run: no retries, no resubmits
            failure = exc
            log("STOPPED: " + "".join(traceback.format_exception_only(type(exc), exc)).strip())
        saved = save(h, items, llm, keys)
        after = llm.ledger.total()["cost_usd"]
        entry = next((b for b in dev_run._load_batches(SPEC)["sub_batches"] if b["n"] == n), {})
        log(f"sub-batch {n}: job {entry.get('job')} answered {entry.get('answered')} invalid "
            f"{len(entry.get('invalid_replies') or {})} missing {len(entry.get('errors') or {})} "
            f"cost ${after - before:.4f}; answers saved so far {saved}; spend ${after:.4f}")
        git_commit(f"Phase 5 step 3: test batch sub-batch {n} of {len(sizes)} saved ({saved} answers so far)"
                   + (" - run stopped" if failure else ""))
        if failure is not None:
            sys.exit(1)
    log("all sub-batches complete")


if __name__ == "__main__":
    main()
