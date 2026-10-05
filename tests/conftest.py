import json
from datetime import date

import pytest

from filingguard.llm.spend import SpendLedger

TEST_PRICES = {"input": 1.0, "output": 2.0}  # USD per 1M tokens, for fake models only


@pytest.fixture
def ledger(tmp_path):
    """A spend ledger in a temp dir, priced for the fake models used in tests."""
    pricing = tmp_path / "pricing.json"
    band = [{"from": "2026-01-01", "until": None, **TEST_PRICES}]
    pricing.write_text(json.dumps({"models": {"m": band, "test-model": band, "other-model": band}}), encoding="utf-8")
    return SpendLedger(tmp_path / "spend", warn_usd=5.0, cap_usd=7.0, pricing_path=pricing, today=date(2026, 10, 4))
