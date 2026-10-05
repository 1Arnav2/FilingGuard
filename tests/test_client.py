import json

import pytest

from filingguard.llm.cache import DiskCache
from filingguard.llm.client import LLMClient
from filingguard.llm.spend import BudgetExceeded, SpendLedger, call_cost, price_for

USAGE = {"usage_metadata": {"prompt_token_count": 1_000_000, "candidates_token_count": 200_000,
                            "thoughts_token_count": 300_000}}


class FakeBackend:
    """Counts calls instead of hitting the network; reports token usage like Gemini."""

    def __init__(self, raw=None):
        self.calls = 0
        self.raw = raw if raw is not None else {}

    def __call__(self, model, prompt, params):
        self.calls += 1
        return {"text": f"reply to {prompt}", "raw": {"n": self.calls, **self.raw}}


def make_client(tmp_path, backend, ledger, model="test-model"):
    return LLMClient(model, DiskCache(tmp_path / "cache"), backend, ledger=ledger)


def test_second_identical_call_is_cached(tmp_path, ledger):
    backend = FakeBackend()
    client = make_client(tmp_path, backend, ledger)
    first = client.generate("hi", temperature=0)
    second = client.generate("hi", temperature=0)
    assert backend.calls == 1
    assert not first.cached and second.cached
    assert second.text == first.text and second.raw == first.raw
    assert first.latency_s is not None and second.latency_s == first.latency_s


def test_rerun_with_fresh_client_makes_zero_calls(tmp_path, ledger):
    make_client(tmp_path, FakeBackend(), ledger).generate("hi")
    rerun_backend = FakeBackend()
    response = make_client(tmp_path, rerun_backend, ledger).generate("hi")
    assert rerun_backend.calls == 0
    assert response.cached


def test_different_params_or_model_miss(tmp_path, ledger):
    backend = FakeBackend()
    make_client(tmp_path, backend, ledger).generate("hi", temperature=0)
    make_client(tmp_path, backend, ledger).generate("hi", temperature=1)
    make_client(tmp_path, backend, ledger, model="other-model").generate("hi", temperature=0)
    assert backend.calls == 3


def test_paid_call_is_costed_and_cached_call_is_free(tmp_path, ledger):
    client = make_client(tmp_path, FakeBackend(USAGE), ledger)
    client.generate("hi", purpose="test")
    client.generate("hi", purpose="test")
    total = ledger.total()
    # 1M input at $1 + (200k + 300k thinking) output at $2 = $2.00
    assert total["calls"] == 1 and total["cost_usd"] == pytest.approx(2.0)
    entries = [json.loads(line) for line in (ledger.dir / "ledger.jsonl").read_text().splitlines()]
    assert len(entries) == 1 and entries[0]["output_tokens"] == 500_000 and entries[0]["purpose"] == "test"


def test_spend_never_passes_the_cap(tmp_path, ledger):
    # Realistic call: a 3M-character prompt is <= 1M tokens; output within the model's limit.
    realistic = {"usage_metadata": {"prompt_token_count": 1_000_000, "candidates_token_count": 40_000,
                                    "thoughts_token_count": 20_000}}  # $1.00 + $0.12 = $1.12
    backend = FakeBackend(realistic)
    client = make_client(tmp_path, backend, ledger)
    calls = 0
    with pytest.raises(BudgetExceeded):
        while True:
            client.generate("x" * 3_000_000 + str(calls))
            calls += 1
            assert ledger.total()["cost_usd"] <= 7.0
    # 6th allowed ($5.60 + worst case $1.13 = $6.73); 7th refused ($6.72 + $1.13 > $7).
    assert backend.calls == calls == 6
    assert ledger.total()["cost_usd"] == pytest.approx(6.72)
    assert client.generate("x" * 3_000_000 + "0").cached, "cached calls still work at the cap"


def test_warning_printed_once_when_crossing_warn_level(tmp_path, ledger, capsys):
    client = make_client(tmp_path, FakeBackend(USAGE), ledger)
    for i in range(3):
        client.generate(f"q{i}")
    assert capsys.readouterr().err.count("WARNING") == 1


def test_failed_call_costs_nothing(tmp_path, ledger):
    def broken(model, prompt, params):
        raise RuntimeError("503")

    with pytest.raises(RuntimeError):
        make_client(tmp_path, broken, ledger).generate("hi")
    assert ledger.total()["cost_usd"] == 0.0


def test_real_pricing_file_prices_both_bands():
    from datetime import date

    before = price_for("gemini-3.8-flash", date(2026, 12, 31))
    after = price_for("gemini-3.8-flash", date(2027, 1, 1))
    assert (before.input_per_1m, before.output_per_1m) == (0.75, 3.75)
    assert (after.input_per_1m, after.output_per_1m) == (1.50, 7.50)
    assert call_cost(before, 17_577, 1_209) == pytest.approx(0.01772, abs=1e-5)


def test_cap_above_approved_is_rejected(monkeypatch):
    from filingguard.llm.spend import ledger_from_env

    monkeypatch.setenv("SPEND_CAP_USD", "9")
    with pytest.raises(ValueError):
        ledger_from_env()


def test_warn_above_cap_is_rejected(tmp_path):
    with pytest.raises(ValueError):
        SpendLedger(tmp_path, warn_usd=8, cap_usd=7)
