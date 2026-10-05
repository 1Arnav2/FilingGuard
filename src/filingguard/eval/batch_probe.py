"""Probe the Batch API with one dev control item before any re-run (H-028).

Probe 1: file-based batch job, request identical to a standard call. Probe 2: inline batch
with the same schema sent as `response_schema`. Reference: the same item once on the standard
API through the frozen agent. Each reply is checked against the target's response schema and
the frozen parser. Writes `results/runs/batch_probe_v1.json`.

Usage: python -m filingguard.eval.batch_probe
"""

import json
from pathlib import Path
from typing import Any

from filingguard.eval.dev_run import Harness, load_items, reply_errors
from filingguard.llm.client import (
    LLMClient, PromptRecorder, batch_backend_from_env, client_from_env, gemini_file_batch_backend,
)

OUT = Path("results/runs/batch_probe_v1.json")
LIMIT_USD = 0.05
TAG_FILE, TAG_SCHEMA = "batch-file-probe", "batch-schema-probe"


def shape(text: str) -> dict[str, Any]:
    """Top-level keys and claim fields of a reply, for side-by-side comparison."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return {"json": False}
    claims = data.get("claims") if isinstance(data, dict) else None
    return {"keys": sorted(data) if isinstance(data, dict) else type(data).__name__,
            "claims": len(claims) if isinstance(claims, list) else None,
            "claim_fields": sorted({k for c in claims for k in c}) if isinstance(claims, list)
            and all(isinstance(c, dict) for c in claims) else [type(c).__name__ for c in claims or []]}


def run_probe(name: str, llm: LLMClient, backend: Any, prompt: str, params: dict[str, Any], tag: str,
              hits: list[Any]) -> dict[str, Any]:
    before = llm.ledger.total()["cost_usd"]
    display = f"filingguard-{tag}"
    # A job already submitted under this name is collected, never resubmitted.
    resume = backend.find_job(display) if hasattr(backend, "find_job") else None
    try:
        answers, errors = llm.generate_batch([(prompt, params)], backend, purpose=f"probe:{name}",
                                             display_name=display, tag=tag, poll_s=15, resume_job=resume)
    except Exception as exc:  # a request the SDK or service rejects is a failed probe, not a crash
        return {"probe": name, "passed": False, "error": f"{type(exc).__name__}: {exc}", "cost_usd": 0.0}
    if errors or not answers:
        return {"probe": name, "passed": False, "error": json.dumps(errors),
                "cost_usd": round(llm.ledger.total()["cost_usd"] - before, 6)}
    text = next(iter(answers.values())).text
    problems = reply_errors(text, hits)
    return {"probe": name, "passed": not problems, "problems": problems, "shape": shape(text), "reply": text,
            "job": resume, "collected_existing_job": resume is not None,
            "cost_usd": round(llm.ledger.total()["cost_usd"] - before, 6)}


def main() -> None:
    item = next(i for i in load_items() if i["attack_type"] == "control" and i["subtype"] != "true_premise_driver")
    h, llm = Harness(), client_from_env("TARGET_MODEL")
    start = llm.ledger.total()["cost_usd"]
    rec = PromptRecorder(llm.model)
    h.agent(item, rec).answer(item["question"], item["company"])
    prompt, params = rec.requests[0]
    hits = h.retriever(item).retrieve(item["question"], item["company"], 20)
    import os
    file_backend = gemini_file_batch_backend(os.environ["GEMINI_API_KEY"])
    schema_params = {k: v for k, v in params.items() if k != "response_json_schema"}
    schema_params["response_schema"] = params["response_json_schema"]

    results = []
    for name, backend, p, tag in (("file_job_same_request", file_backend, params, TAG_FILE),
                                  ("inline_response_schema", batch_backend_from_env(), schema_params, TAG_SCHEMA)):
        if llm.ledger.total()["cost_usd"] - start > LIMIT_USD - 0.02:
            results.append({"probe": name, "passed": False, "error": "skipped: probe limit"})
            continue
        results.append(run_probe(name, llm, backend, prompt, p, tag, hits))

    before = llm.ledger.total()["cost_usd"]
    reference: dict[str, Any] = {"probe": "standard_api_reference"}
    if before - start <= LIMIT_USD - 0.025:
        response = llm.generate(prompt, purpose="probe:standard_reference", **params)
        problems = reply_errors(response.text, hits)
        reference.update(passed=not problems, problems=problems, cached=response.cached, shape=shape(response.text),
                         reply=response.text, cost_usd=round(llm.ledger.total()["cost_usd"] - before, 6))
    else:
        reference.update(passed=None, error="skipped: probe limit")
    record = {"item": item["id"], "question": item["question"], "company": item["company"],
              "request_difference": {"file_job_same_request": "none: SDK standard-call body in a JSONL file",
                                     "inline_response_schema": "response_json_schema sent as response_schema"},
              "probes": results, "reference": reference,
              "spend_usd": round(llm.ledger.total()["cost_usd"] - start, 6),
              "total_spend_usd": llm.ledger.total()["cost_usd"]}
    OUT.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({**record, "probes": [{k: v for k, v in r.items() if k != "reply"} for r in results],
                      "reference": {k: v for k, v in reference.items() if k != "reply"}}, indent=2))


if __name__ == "__main__":
    main()
