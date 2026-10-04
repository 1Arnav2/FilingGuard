import httpx
import pytest

from filingguard.data.edgar_client import (
    EdgarClient,
    companyfacts_url,
    document_url,
    submissions_url,
)
from filingguard.retry import RetryPolicy

UA = "Test Person test@example.com"


class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps = []

    def time(self):
        return self.now

    def sleep(self, seconds):
        self.sleeps.append(seconds)
        self.now += seconds


def make(tmp_path, handler, clock=None):
    clock = clock or FakeClock()
    client = EdgarClient(
        UA,
        tmp_path,
        transport=httpx.MockTransport(handler),
        policy=RetryPolicy(max_attempts=3, base_delay_s=0.01),
        sleep=clock.sleep,
        clock=clock.time,
    )
    return client, clock


def test_url_builders_pad_and_strip():
    assert submissions_url(320193) == "https://data.sec.gov/submissions/CIK0000320193.json"
    assert companyfacts_url(320193).endswith("/CIK0000320193.json")
    assert document_url(320193, "0000320193-25-000079", "aapl.htm") == (
        "https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl.htm"
    )


def test_sends_user_agent_and_caches(tmp_path):
    seen = []

    def handler(request):
        seen.append(request.headers["User-Agent"])
        return httpx.Response(200, json={"ok": True})

    client, _ = make(tmp_path, handler)
    assert client.get_json("https://data.sec.gov/x.json") == {"ok": True}
    assert client.get_json("https://data.sec.gov/x.json") == {"ok": True}
    assert seen == [UA]
    assert client.network_requests == 1


def test_cache_survives_new_client(tmp_path):
    client, _ = make(tmp_path, lambda r: httpx.Response(200, content=b"body"))
    client.get_bytes("https://www.sec.gov/a")
    rerun, _ = make(tmp_path, lambda r: pytest.fail("network called on re-run"))
    assert rerun.get_bytes("https://www.sec.gov/a") == b"body"


def test_throttles_to_five_per_second(tmp_path):
    client, clock = make(tmp_path, lambda r: httpx.Response(200, content=b"x"))
    for i in range(5):
        client.get_bytes(f"https://www.sec.gov/{i}")
    assert client.network_requests == 5
    assert clock.now >= 4 * 0.2 - 1e-9


def test_retries_503_then_succeeds_and_caches(tmp_path):
    responses = iter([httpx.Response(503), httpx.Response(429), httpx.Response(200, content=b"ok")])
    client, _ = make(tmp_path, lambda r: next(responses))
    assert client.get_bytes("https://www.sec.gov/r") == b"ok"
    assert client.network_requests == 3


def test_404_is_not_retried_or_cached(tmp_path):
    client, _ = make(tmp_path, lambda r: httpx.Response(404))
    with pytest.raises(httpx.HTTPStatusError):
        client.get_bytes("https://www.sec.gov/missing")
    assert client.network_requests == 1
    assert not list(tmp_path.rglob("*.bin"))


def test_exhausted_retries_leave_nothing_cached(tmp_path):
    client, _ = make(tmp_path, lambda r: httpx.Response(503))
    with pytest.raises(httpx.HTTPStatusError):
        client.get_bytes("https://www.sec.gov/down")
    assert client.network_requests == 3
    assert not list(tmp_path.rglob("*.bin"))


def test_rejects_user_agent_without_email(tmp_path):
    with pytest.raises(ValueError):
        EdgarClient("Just A Name", tmp_path)
