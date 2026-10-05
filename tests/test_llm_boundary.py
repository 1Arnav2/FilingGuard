"""Every model call goes through LLMClient, which checks the cache and the spend ledger.

Fails if any module other than `filingguard/llm/client.py` imports the Gemini SDK, calls the
API directly, or uses the raw backend outside an LLMClient.
"""

import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src" / "filingguard"
CLIENT = SRC / "llm" / "client.py"
DIRECT_USE = re.compile(r"google\.genai|from google import genai|generate_content|gemini_backend|genai\.Client")


def offenders() -> dict[str, list[str]]:
    found = {}
    for path in SRC.rglob("*.py"):
        if path == CLIENT:
            continue
        hits = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if DIRECT_USE.search(line)]
        # Catching the SDK's error type for reporting is allowed; it cannot make a call.
        hits = [h for h in hits if h != "from google.genai import errors"]
        if hits:
            found[str(path.relative_to(SRC))] = hits
    return found


def test_only_the_llm_client_touches_the_model_api():
    assert not offenders(), f"direct model access outside LLMClient: {offenders()}"


def test_backend_is_only_called_from_generate_after_cache_and_ledger():
    source = CLIENT.read_text(encoding="utf-8")
    generate = source[source.index("def generate"):source.index("def client_from_env")]
    order = [generate.index(s) for s in ("self.cache.get", "self.ledger.check", "self.backend(", "self.ledger.record", "self.cache.put")]
    assert order == sorted(order), "generate must check cache, then ledger, then call, then record and cache"
    assert source.count("self.backend(") == 1
