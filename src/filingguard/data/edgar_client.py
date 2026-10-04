"""Throttled, cached, retrying client for SEC EDGAR."""

import hashlib
import json
import os
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
from dotenv import load_dotenv

from filingguard.retry import RETRYABLE_STATUS, RetryPolicy, with_retry

TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_MIN_INTERVAL_S = 0.2  # at most 5 requests per second


def submissions_url(cik: int) -> str:
    return f"https://data.sec.gov/submissions/CIK{cik:010d}.json"


def companyfacts_url(cik: int) -> str:
    return f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"


def document_url(cik: int, accession: str, document: str) -> str:
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}/{document}"


def is_retryable_http_error(exc: Exception) -> bool:
    """True for rate limits, server errors and network faults."""
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRYABLE_STATUS
    return isinstance(exc, httpx.TransportError)


class EdgarClient:
    """GETs SEC URLs with a User-Agent, a request-rate cap, retries, and a disk cache.

    Only successful responses are cached, so a failed request is retried on the next run.
    """

    def __init__(
        self,
        user_agent: str,
        cache_dir: Path,
        transport: httpx.BaseTransport | None = None,
        min_interval_s: float = SEC_MIN_INTERVAL_S,
        policy: RetryPolicy = RetryPolicy(),
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if "@" not in user_agent:
            raise ValueError("SEC_USER_AGENT must contain a name and an email address")
        self.cache_dir = Path(cache_dir)
        self.min_interval_s = min_interval_s
        self.policy = policy
        self._sleep = sleep
        self._clock = clock
        self._lock = threading.Lock()
        self._last_request = float("-inf")
        self.network_requests = 0
        self._http = httpx.Client(
            headers={"User-Agent": user_agent, "Accept-Encoding": "gzip, deflate"},
            timeout=60.0,
            follow_redirects=True,
            transport=transport,
        )

    def _cache_path(self, url: str) -> Path:
        key = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.cache_dir / key[:2] / f"{key}.bin"

    def _throttle(self) -> None:
        with self._lock:
            wait = self._last_request + self.min_interval_s - self._clock()
            if wait > 0:
                self._sleep(wait)
            self._last_request = self._clock()

    def _fetch(self, url: str) -> bytes:
        self._throttle()
        self.network_requests += 1
        response = self._http.get(url)
        response.raise_for_status()
        return response.content

    def get_bytes(self, url: str) -> bytes:
        """Return the body of `url`, from the cache when present."""
        path = self._cache_path(url)
        if path.exists():
            return path.read_bytes()
        body = with_retry(lambda: self._fetch(url), is_retryable_http_error, self.policy, self._sleep)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_bytes(body)
        os.replace(tmp, path)
        return body

    def get_json(self, url: str) -> Any:
        """Return `url` parsed as JSON."""
        return json.loads(self.get_bytes(url))


def edgar_client_from_env(cache_dir: Path = Path("data/raw/sec")) -> EdgarClient:
    """Build a client using SEC_USER_AGENT from `.env`."""
    load_dotenv()
    user_agent = os.environ.get("SEC_USER_AGENT", "").strip().strip('"')
    if not user_agent:
        raise RuntimeError("SEC_USER_AGENT is not set in .env")
    return EdgarClient(user_agent, cache_dir)
