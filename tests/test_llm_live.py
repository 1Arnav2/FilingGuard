"""One real Gemini call. Skipped by default; run with `pytest -m live`.

It spends real money (a few hundred tokens), so it goes through the real spend ledger in
`results/spend/` and its cap.
"""

import os

import pytest
from dotenv import load_dotenv

from filingguard.llm.cache import DiskCache
from filingguard.llm.client import LLMClient, gemini_backend
from filingguard.llm.spend import ledger_from_env

load_dotenv()

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(
        not (os.environ.get("GEMINI_API_KEY") and os.environ.get("TARGET_MODEL")),
        reason="GEMINI_API_KEY and TARGET_MODEL must be set in .env",
    ),
]


def test_live_call_is_cached(tmp_path):
    backend_calls = []
    real = gemini_backend(os.environ["GEMINI_API_KEY"])

    def counting(model, prompt, params):
        backend_calls.append(prompt)
        return real(model, prompt, params)

    client = LLMClient(os.environ["TARGET_MODEL"], DiskCache(tmp_path), counting, ledger=ledger_from_env())
    prompt = "Reply with the single word: ok"
    first = client.generate(prompt, purpose="live test", temperature=0)
    second = client.generate(prompt, purpose="live test", temperature=0)

    assert first.text.strip()
    assert not first.cached and second.cached
    assert second.text == first.text
    assert len(backend_calls) == 1
