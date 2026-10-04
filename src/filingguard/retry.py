"""Retry with exponential backoff and full jitter, shared by the LLM and EDGAR clients."""

import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

T = TypeVar("T")

RETRYABLE_STATUS = frozenset({408, 429, 500, 502, 503, 504})


@dataclass(frozen=True)
class RetryPolicy:
    max_attempts: int = 6
    base_delay_s: float = 2.0
    max_delay_s: float = 60.0

    def delay(self, attempt: int, rng: random.Random) -> float:
        """Full-jitter delay before retry number `attempt` (1-based)."""
        cap = min(self.max_delay_s, self.base_delay_s * 2 ** (attempt - 1))
        return rng.uniform(0, cap)


def with_retry(
    fn: Callable[[], T],
    is_retryable: Callable[[Exception], bool],
    policy: RetryPolicy = RetryPolicy(),
    sleep: Callable[[float], None] = time.sleep,
    rng: random.Random | None = None,
) -> T:
    """Call `fn`, retrying on exceptions that `is_retryable` accepts. Re-raises the last one."""
    rng = rng or random.Random()
    for attempt in range(1, policy.max_attempts + 1):
        try:
            return fn()
        except Exception as exc:
            if attempt == policy.max_attempts or not is_retryable(exc):
                raise
            sleep(policy.delay(attempt, rng))
    raise AssertionError("unreachable")
