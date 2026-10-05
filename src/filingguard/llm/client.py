"""Gemini client that checks the disk cache before every API call."""

import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from dotenv import load_dotenv

from filingguard.llm.cache import DiskCache, cache_key
from filingguard.llm.spend import SpendLedger, ledger_from_env
from filingguard.retry import RETRYABLE_STATUS, RetryPolicy, with_retry

# A backend takes (model, prompt, params) and returns {"text": str, "raw": dict}.
Backend = Callable[[str, str, dict[str, Any]], dict[str, Any]]

BATCH_DONE_STATES = {"JOB_STATE_SUCCEEDED", "JOB_STATE_FAILED", "JOB_STATE_CANCELLED", "JOB_STATE_EXPIRED",
                     "JOB_STATE_PARTIALLY_SUCCEEDED"}


class BatchBackend(Protocol):
    """Submits one Batch API job and reads it back (D-025). Requests are dicts with
    `key`, `prompt` and `params`; results map each key to {"text", "raw"} or {"error"}."""

    def submit(self, model: str, requests: list[dict[str, Any]], display_name: str) -> str: ...

    def state(self, job_name: str) -> str: ...

    def results(self, job_name: str) -> dict[str, dict[str, Any]]: ...


def is_retryable_gemini_error(exc: Exception) -> bool:
    """True for per-minute rate limits, server errors and network faults.

    False for bad requests and for exhausted daily quotas, which no backoff can fix (H-006).
    """
    import httpx
    from google.genai import errors

    if isinstance(exc, errors.APIError):
        if exc.code == 429 and "PerDay" in str(exc):
            return False
        return exc.code in RETRYABLE_STATUS
    return isinstance(exc, httpx.TransportError)


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    cached: bool
    raw: dict[str, Any]
    latency_s: float | None  # wall time of the original API call, also on cache replays


def gemini_backend(api_key: str, policy: RetryPolicy = RetryPolicy()) -> Backend:
    """Build a backend that calls the Gemini API, retrying transient errors with backoff."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    def call(model: str, prompt: str, params: dict[str, Any]) -> dict[str, Any]:
        config = types.GenerateContentConfig(
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            **params,
        )
        response = with_retry(
            lambda: client.models.generate_content(model=model, contents=prompt, config=config),
            is_retryable_gemini_error,
            policy,
        )
        return {"text": response.text or "", "raw": response.model_dump(mode="json", exclude_none=True)}

    return call


def gemini_batch_backend(api_key: str) -> BatchBackend:
    """Batch API backend with inline requests; each request carries its cache key as metadata."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)

    class _Gemini:
        def submit(self, model: str, requests: list[dict[str, Any]], display_name: str) -> str:
            src = [
                types.InlinedRequest(
                    contents=r["prompt"],
                    config=types.GenerateContentConfig(**r["params"]),
                    metadata={"key": r["key"]},
                )
                for r in requests
            ]
            job = client.batches.create(model=model, src=src, config=types.CreateBatchJobConfig(display_name=display_name))
            return job.name

        def state(self, job_name: str) -> str:
            return client.batches.get(name=job_name).state.name

        def results(self, job_name: str) -> dict[str, dict[str, Any]]:
            job = client.batches.get(name=job_name)
            out = {}
            for r in (job.dest.inlined_responses if job.dest else None) or []:
                key = (r.metadata or {}).get("key")
                if key is None:
                    continue
                if r.error is not None or r.response is None:
                    out[key] = {"error": str(r.error)}
                else:
                    out[key] = {"text": r.response.text or "", "raw": r.response.model_dump(mode="json", exclude_none=True)}
            return out

    return _Gemini()


def file_response(response: dict[str, Any]) -> dict[str, Any]:
    """{"text", "raw"} from one REST response in a batch result file. Read directly rather than
    through the SDK's response model, which rejects fields newer than the SDK (`serviceTier`).
    Text joins the first candidate's non-thought text parts, as the SDK's `.text` does; `raw`
    keeps the whole response plus token counts under the names the spend ledger reads."""
    parts = ((response.get("candidates") or [{}])[0].get("content") or {}).get("parts") or []
    text = "".join(p.get("text", "") for p in parts if not p.get("thought"))
    usage = response.get("usageMetadata") or {}
    return {"text": text, "raw": {"response": response, "usage_metadata": {
        "prompt_token_count": usage.get("promptTokenCount"),
        "candidates_token_count": usage.get("candidatesTokenCount"),
        "thoughts_token_count": usage.get("thoughtsTokenCount"),
    }}}


def gemini_file_batch_backend(api_key: str, work_dir: Path = Path(".cache/batch_files")) -> BatchBackend:
    """Batch API backend with a JSONL input file (H-028). Each line's request body is built by
    the SDK's own converter for a standard `generate_content` call, so the request matches a
    standard call field for field; only the URL part is dropped."""
    import json

    from google import genai
    from google.genai import models, types

    client = genai.Client(api_key=api_key)

    def body(model: str, prompt: str, params: dict[str, Any]) -> dict[str, Any]:
        config = types.GenerateContentConfig(
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True), **params)
        request = models._GenerateContentParameters_to_mldev(
            client._api_client, types._GenerateContentParameters(model=model, contents=prompt, config=config))
        request.pop("_url", None)
        return request

    class _GeminiFile:
        def submit(self, model: str, requests: list[dict[str, Any]], display_name: str) -> str:
            work_dir.mkdir(parents=True, exist_ok=True)
            path = work_dir / f"{display_name}.jsonl"
            lines = [json.dumps({"key": r["key"], "request": body(model, r["prompt"], r["params"])}) for r in requests]
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            uploaded = client.files.upload(file=str(path), config=types.UploadFileConfig(
                display_name=display_name, mime_type="jsonl"))
            job = client.batches.create(model=model, src=uploaded.name,
                                        config=types.CreateBatchJobConfig(display_name=display_name))
            return job.name

        def state(self, job_name: str) -> str:
            return client.batches.get(name=job_name).state.name

        def find_job(self, display_name: str) -> str | None:
            """The newest job with this display name (a free listing call), to collect a job whose
            name was not recorded."""
            jobs = [j for j in client.batches.list() if j.display_name == display_name]
            jobs.sort(key=lambda j: j.create_time, reverse=True)
            return jobs[0].name if jobs else None

        def results(self, job_name: str) -> dict[str, dict[str, Any]]:
            job = client.batches.get(name=job_name)
            if not job.dest or not job.dest.file_name:
                return {}
            out = {}
            for line in client.files.download(file=job.dest.file_name).decode("utf-8").splitlines():
                if not line.strip():
                    continue
                row = json.loads(line)
                key = row.get("key")
                if key is None:
                    continue
                if row.get("error") or "response" not in row:
                    out[key] = {"error": json.dumps(row.get("error") or "no response")}
                    continue
                out[key] = file_response(row["response"])
            return out

    return _GeminiFile()


def batch_cache_key(model: str, prompt: str, params: dict[str, Any], tag: str = "batch") -> str:
    """Cache key for a Batch API answer: tagged so it never collides with a standard call (D-025),
    nor with another batch run under a different tag (H-028)."""
    return cache_key({"model": model, "prompt": prompt, "params": params, "mode": tag})


class LLMClient:
    """Generates text for one pinned model.

    Identical requests are served from the cache at no cost. Every cache miss is checked
    against the spend ledger before it is sent and recorded after it returns. The ledger is a
    required argument so no client can be built that spends without tracking.
    """

    def __init__(self, model: str, cache: DiskCache, backend: Backend, *, ledger: SpendLedger) -> None:
        self.model = model
        self.cache = cache
        self.backend = backend
        self.ledger = ledger

    def generate(self, prompt: str, *, purpose: str | None = None, **params: Any) -> LLMResponse:
        """Return the model's reply, calling the API only on a cache miss.

        `purpose` labels the ledger entry and is not part of the cache key.
        Raises `BudgetExceeded` before a call that could pass the hard cap.
        """
        key = cache_key({"model": self.model, "prompt": prompt, "params": params})
        hit = self.cache.get(key)
        if hit is not None:
            return LLMResponse(hit["text"], self.model, True, hit["raw"], hit.get("latency_s"))
        self.ledger.check(self.model, prompt)
        started = time.perf_counter()
        result = self.backend(self.model, prompt, params)
        latency_s = round(time.perf_counter() - started, 3)
        self.ledger.record(self.model, result["raw"], key, purpose)
        self.cache.put(key, {"model": self.model, "prompt": prompt, "params": params, "latency_s": latency_s, **result})
        return LLMResponse(result["text"], self.model, False, result["raw"], latency_s)


    def generate_batch(
        self,
        requests: list[tuple[str, dict[str, Any]]],
        batch_backend: BatchBackend,
        *,
        purpose: str,
        display_name: str,
        resume_job: str | None = None,
        on_submit: Callable[[str], None] | None = None,
        poll_s: float = 30.0,
        tag: str = "batch",
    ) -> tuple[dict[str, LLMResponse], dict[str, str]]:
        """Answer (prompt, params) pairs through one Batch API job at the batch price.

        Cached answers are not resubmitted. The whole job's worst case is checked against the
        cap before it is sent; each returned answer is recorded and cached. Returns answers and
        errors, both keyed by `batch_cache_key`. `resume_job` collects a job already submitted.
        """
        keyed = {batch_cache_key(self.model, p, params, tag): (p, params) for p, params in requests}
        done = {k: self.cache.get(k) for k in keyed}
        pending = [k for k, hit in done.items() if hit is None]
        if pending:
            if resume_job is None:
                self.ledger.check_many(self.model, [keyed[k][0] for k in pending], batch=True)
                payload = [{"key": k, "prompt": keyed[k][0], "params": keyed[k][1]} for k in pending]
                resume_job = batch_backend.submit(self.model, payload, display_name)
                if on_submit:
                    on_submit(resume_job)
            while batch_backend.state(resume_job) not in BATCH_DONE_STATES:
                time.sleep(poll_s)
            returned = batch_backend.results(resume_job)
            for k in pending:
                result = returned.get(k)
                if result is None or "error" in result:
                    continue
                self.ledger.record(self.model, result["raw"], k, purpose, batch=True)
                p, params = keyed[k]
                entry = {"model": self.model, "prompt": p, "params": params, "mode": tag,
                         "batch_job": resume_job, "latency_s": None, **result}
                self.cache.put(k, entry)
                done[k] = entry
        answers = {k: LLMResponse(v["text"], self.model, False, v["raw"], None) for k, v in done.items() if v}
        errors = {k: (returned.get(k) or {}).get("error", "missing from batch results")
                  for k in keyed if k not in answers} if pending else {}
        return answers, errors

    def batch_answer(self, prompt: str, tag: str = "batch", **params: Any) -> LLMResponse:
        """A stored Batch API answer for this exact request. Never calls the model; raises
        KeyError if the request was not answered in a batch."""
        hit = self.cache.get(batch_cache_key(self.model, prompt, params, tag))
        if hit is None:
            raise KeyError("no batch answer for this request")
        return LLMResponse(hit["text"], self.model, True, hit["raw"], None)


class BatchReplayClient:
    """Stands in for LLMClient inside an agent, serving only stored batch answers, so a batch
    run uses the agent's own prompt-building and parsing code unchanged."""

    def __init__(self, llm: LLMClient, tag: str = "batch") -> None:
        self.llm = llm
        self.tag = tag

    def generate(self, prompt: str, *, purpose: str | None = None, **params: Any) -> LLMResponse:
        return self.llm.batch_answer(prompt, self.tag, **params)


class PromptRecorder:
    """Stands in for LLMClient inside an agent to capture the exact request it would send,
    returning an empty reply. Makes no call."""

    def __init__(self, model: str) -> None:
        self.model = model
        self.requests: list[tuple[str, dict[str, Any]]] = []

    def generate(self, prompt: str, *, purpose: str | None = None, **params: Any) -> LLMResponse:
        self.requests.append((prompt, params))
        return LLMResponse("{}", self.model, False, {}, None)


def batch_backend_from_env() -> BatchBackend:
    """Batch API backend using GEMINI_API_KEY from `.env`."""
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in .env")
    return gemini_batch_backend(api_key)


def client_from_env(model_var: str = "TARGET_MODEL") -> LLMClient:
    """Build a Gemini client from `.env`, using the model ID named by `model_var`."""
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    model = os.environ.get(model_var)
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in .env")
    if not model:
        raise RuntimeError(f"{model_var} is not set in .env")
    cache_dir = Path(os.environ.get("CACHE_DIR", ".cache")) / "llm"
    return LLMClient(model, DiskCache(cache_dir), gemini_backend(api_key), ledger=ledger_from_env())
