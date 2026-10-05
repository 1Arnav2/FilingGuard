import random

import httpx
import pytest
from google.genai import errors

from filingguard.llm.cache import DiskCache
from filingguard.llm.client import LLMClient, is_retryable_gemini_error
from filingguard.retry import RetryPolicy, with_retry


class Flaky:
    """Raises `exc` for the first `failures` calls, then returns "ok"."""

    def __init__(self, failures, exc):
        self.failures, self.exc, self.calls = failures, exc, 0

    def __call__(self):
        self.calls += 1
        if self.calls <= self.failures:
            raise self.exc
        return "ok"


def run(fn, retryable=lambda e: True, attempts=4):
    sleeps = []
    result = with_retry(fn, retryable, RetryPolicy(max_attempts=attempts), sleeps.append, random.Random(0))
    return result, sleeps


def test_recovers_after_transient_failures():
    fn = Flaky(2, RuntimeError("busy"))
    result, sleeps = run(fn)
    assert result == "ok" and fn.calls == 3 and len(sleeps) == 2


def test_gives_up_after_max_attempts():
    fn = Flaky(10, RuntimeError("busy"))
    with pytest.raises(RuntimeError):
        run(fn, attempts=4)
    assert fn.calls == 4


def test_non_retryable_raises_immediately():
    fn = Flaky(1, ValueError("bad request"))
    with pytest.raises(ValueError):
        run(fn, retryable=lambda e: not isinstance(e, ValueError))
    assert fn.calls == 1


def test_delays_stay_within_exponential_cap():
    policy = RetryPolicy(base_delay_s=2, max_delay_s=10)
    rng = random.Random(0)
    for attempt, cap in [(1, 2), (2, 4), (3, 8), (4, 10), (9, 10)]:
        assert all(0 <= policy.delay(attempt, rng) <= cap for _ in range(50))


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (errors.ServerError(503, {"error": {"message": "high demand"}}), True),
        (errors.ClientError(429, {"error": {"message": "quota"}}), True),
        (errors.ClientError(429, {"error": {"message": "x", "details": [
            {"violations": [{"quotaId": "GenerateRequestsPerDayPerProjectPerModel-FreeTier"}]}]}}), False),
        (errors.ClientError(400, {"error": {"message": "bad"}}), False),
        (errors.ClientError(404, {"error": {"message": "no model"}}), False),
        (httpx.ConnectError("down"), True),
        (ValueError("x"), False),
    ],
)
def test_gemini_retryable_classification(exc, expected):
    assert is_retryable_gemini_error(exc) is expected


def test_failed_call_is_not_cached(tmp_path, ledger):
    calls = []

    def backend(model, prompt, params):
        calls.append(prompt)
        if len(calls) == 1:
            raise RuntimeError("503 after retries")
        return {"text": "ok", "raw": {}}

    client = LLMClient("m", DiskCache(tmp_path / "cache"), backend, ledger=ledger)
    with pytest.raises(RuntimeError):
        client.generate("hi")
    assert not list((tmp_path / "cache").rglob("*.json"))
    assert client.generate("hi").cached is False
    assert len(calls) == 2
