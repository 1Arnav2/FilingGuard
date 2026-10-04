"""Gemini client that checks the disk cache before every API call."""

import os
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from filingguard.llm.cache import DiskCache, cache_key
from filingguard.retry import RETRYABLE_STATUS, RetryPolicy, with_retry

# A backend takes (model, prompt, params) and returns {"text": str, "raw": dict}.
Backend = Callable[[str, str, dict[str, Any]], dict[str, Any]]


def is_retryable_gemini_error(exc: Exception) -> bool:
    """True for rate limits, server errors and network faults; False for bad requests."""
    import httpx
    from google.genai import errors

    if isinstance(exc, errors.APIError):
        return exc.code in RETRYABLE_STATUS
    return isinstance(exc, httpx.TransportError)


@dataclass(frozen=True)
class LLMResponse:
    text: str
    model: str
    cached: bool
    raw: dict[str, Any]


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


class LLMClient:
    """Generates text for one pinned model. Identical requests are served from the cache."""

    def __init__(self, model: str, cache: DiskCache, backend: Backend) -> None:
        self.model = model
        self.cache = cache
        self.backend = backend

    def generate(self, prompt: str, **params: Any) -> LLMResponse:
        """Return the model's reply, calling the API only on a cache miss."""
        key = cache_key({"model": self.model, "prompt": prompt, "params": params})
        hit = self.cache.get(key)
        if hit is not None:
            return LLMResponse(text=hit["text"], model=self.model, cached=True, raw=hit["raw"])
        result = self.backend(self.model, prompt, params)
        self.cache.put(key, {"model": self.model, "prompt": prompt, "params": params, **result})
        return LLMResponse(text=result["text"], model=self.model, cached=False, raw=result["raw"])


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
    return LLMClient(model=model, cache=DiskCache(cache_dir), backend=gemini_backend(api_key))
