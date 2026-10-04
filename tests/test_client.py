from filingguard.llm.cache import DiskCache
from filingguard.llm.client import LLMClient


class FakeBackend:
    """Counts calls instead of hitting the network."""

    def __init__(self):
        self.calls = 0

    def __call__(self, model, prompt, params):
        self.calls += 1
        return {"text": f"reply to {prompt}", "raw": {"n": self.calls}}


def make_client(tmp_path, backend, model="test-model"):
    return LLMClient(model=model, cache=DiskCache(tmp_path), backend=backend)


def test_second_identical_call_is_cached(tmp_path):
    backend = FakeBackend()
    client = make_client(tmp_path, backend)
    first = client.generate("hi", temperature=0)
    second = client.generate("hi", temperature=0)
    assert backend.calls == 1
    assert not first.cached and second.cached
    assert second.text == first.text and second.raw == first.raw


def test_rerun_with_fresh_client_makes_zero_calls(tmp_path):
    make_client(tmp_path, FakeBackend()).generate("hi")
    rerun_backend = FakeBackend()
    response = make_client(tmp_path, rerun_backend).generate("hi")
    assert rerun_backend.calls == 0
    assert response.cached


def test_different_params_or_model_miss(tmp_path):
    backend = FakeBackend()
    make_client(tmp_path, backend).generate("hi", temperature=0)
    make_client(tmp_path, backend).generate("hi", temperature=1)
    make_client(tmp_path, backend, model="other-model").generate("hi", temperature=0)
    assert backend.calls == 3
