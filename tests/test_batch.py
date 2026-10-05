"""Batch API path (D-025, D-046): cache, ledger at the batch price, the cap, failures, resume,
and the dev-only run harness."""

import json

import pytest

from filingguard.agents.targets.tenk_rag import TenKRagAgent
from filingguard.llm.cache import DiskCache
from filingguard.llm.client import BatchReplayClient, LLMClient, PromptRecorder, batch_cache_key
from filingguard.llm.spend import BudgetExceeded

USAGE = {"usage_metadata": {"prompt_token_count": 1_000_000, "candidates_token_count": 100_000,
                            "thoughts_token_count": 100_000}}


class FakeBatch:
    """Answers every request unless its prompt is in `fail`; counts submissions."""

    def __init__(self, fail=()):
        self.fail, self.jobs, self.submitted = set(fail), {}, 0

    def submit(self, model, requests, display_name):
        self.submitted += 1
        name = f"batches/{self.submitted}"
        self.jobs[name] = requests
        return name

    def state(self, job_name):
        return "JOB_STATE_SUCCEEDED"

    def results(self, job_name):
        out = {}
        for r in self.jobs[job_name]:
            out[r["key"]] = {"error": "boom"} if r["prompt"] in self.fail else {"text": f"re {r['prompt']}", "raw": USAGE}
        return out


def client(tmp_path, ledger):
    return LLMClient("m", DiskCache(tmp_path / "cache"), lambda *a: pytest.fail("standard API used"), ledger=ledger)


def test_batch_answers_are_priced_at_batch_rate_cached_and_not_resubmitted(tmp_path, ledger):
    llm, fake = client(tmp_path, ledger), FakeBatch()
    answers, errors = llm.generate_batch([("a", {"temperature": 0}), ("b", {"temperature": 0})], fake,
                                         purpose="t", display_name="x", poll_s=0)
    assert len(answers) == 2 and not errors and fake.submitted == 1
    # 1M input at $0.50 + 200k output at $1.00 = $0.70 per answer
    assert ledger.total()["cost_usd"] == pytest.approx(1.40)
    entries = [json.loads(line) for line in (ledger.dir / "ledger.jsonl").read_text().splitlines()]
    assert all(e["mode"] == "batch" and e["purpose"] == "t" for e in entries)
    again, _ = llm.generate_batch([("a", {"temperature": 0})], fake, purpose="t", display_name="x", poll_s=0)
    assert fake.submitted == 1 and again[batch_cache_key("m", "a", {"temperature": 0})].text == "re a"


def test_batch_key_never_collides_with_a_standard_call(tmp_path, ledger):
    from filingguard.llm.cache import cache_key
    assert batch_cache_key("m", "a", {}) != cache_key({"model": "m", "prompt": "a", "params": {}})


def test_whole_batch_worst_case_is_checked_before_submitting(tmp_path, ledger):
    llm, fake = client(tmp_path, ledger), FakeBatch()
    huge = [("x" * 3_000_000 + str(i), {}) for i in range(20)]  # worst case far above $7
    with pytest.raises(BudgetExceeded):
        llm.generate_batch(huge, fake, purpose="t", display_name="x", poll_s=0)
    assert fake.submitted == 0 and ledger.total()["cost_usd"] == 0.0


def test_failed_items_are_reported_not_cached_or_charged(tmp_path, ledger):
    llm, fake = client(tmp_path, ledger), FakeBatch(fail={"b"})
    answers, errors = llm.generate_batch([("a", {}), ("b", {})], fake, purpose="t", display_name="x", poll_s=0)
    assert len(answers) == 1 and list(errors.values()) == ["boom"]
    assert ledger.total()["calls"] == 1
    fake.fail = set()
    answers, _ = llm.generate_batch([("a", {}), ("b", {})], fake, purpose="t", display_name="x", poll_s=0)
    assert len(answers) == 2 and [r["prompt"] for r in fake.jobs["batches/2"]] == ["b"], "only the missing item resent"


def test_resume_collects_a_submitted_job_without_resubmitting(tmp_path, ledger):
    llm, fake = client(tmp_path, ledger), FakeBatch()
    job = fake.submit("m", [{"key": batch_cache_key("m", "a", {}), "prompt": "a", "params": {}}], "x")
    answers, _ = llm.generate_batch([("a", {})], fake, purpose="t", display_name="x", resume_job=job, poll_s=0)
    assert len(answers) == 1 and fake.submitted == 1


def test_replay_serves_only_batch_answers(tmp_path, ledger):
    llm = client(tmp_path, ledger)
    llm.generate_batch([("a", {"temperature": 0})], FakeBatch(), purpose="t", display_name="x", poll_s=0)
    assert BatchReplayClient(llm).generate("a", purpose="target", temperature=0).text == "re a"
    with pytest.raises(KeyError):
        BatchReplayClient(llm).generate("unseen", temperature=0)


def test_recorder_captures_the_agents_exact_request_and_replay_reproduces_its_answer(tmp_path, ledger):
    from tests.test_tenk_rag import DATES, GOOD, FixedRetriever

    rec = PromptRecorder("m")
    TenKRagAgent(rec, FixedRetriever(), DATES, k=2).answer("Net sales?", "AAPL")
    prompt, params = rec.requests[0]
    assert params["temperature"] == 0 and params["response_mime_type"] == "application/json"

    class Answering(FakeBatch):
        def results(self, job_name):
            return {r["key"]: {"text": json.dumps(GOOD), "raw": {}} for r in self.jobs[job_name]}

    llm = client(tmp_path, ledger)
    llm.generate_batch([(prompt, params)], Answering(), purpose="t", display_name="x", poll_s=0)
    answer = TenKRagAgent(BatchReplayClient(llm), FixedRetriever(), DATES, k=2).answer("Net sales?", "AAPL")
    assert answer.text == GOOD["answer"] and answer.trace["prompt_sha256"]


def test_dev_run_loads_only_the_90_dev_items():
    from filingguard.eval.dev_run import load_items

    items = load_items()
    assert len(items) == 90 and {i["split"] for i in items} == {"dev"}
    assert [i["id"] for i in items] == sorted(i["id"] for i in items)
    with pytest.raises(ValueError):
        load_items("test")


def test_dev_run_reads_no_gold():
    from pathlib import Path

    from tests.test_gold_isolation import gold_violations
    source = Path("src/filingguard/eval/dev_run.py").read_text(encoding="utf-8")
    assert not gold_violations(source)


def test_poisoned_chunk_check_detects_a_changed_chunk():
    from filingguard.eval.dev_run import check_poisoned, load_items, sha256

    item = next(i for i in load_items() if i.get("injection"))
    frozen = next(json.loads(line) for line in open("data/testset/poisoned_chunks_v1.jsonl", encoding="utf-8")
                  if json.loads(line)["id"] == item["id"])
    # Rebuild the clean chunk from the frozen poisoned text.
    inj = item["injection"]
    planted = "\n" + inj["text"]
    clean = frozen["poisoned_text"].replace(planted, "", 1)
    assert sha256(clean) == frozen["clean_sha256"]
    good = [{"chunk_id": inj["chunk_id"], "text": clean}]
    assert check_poisoned([item], good) == []
    assert check_poisoned([item], [{"chunk_id": inj["chunk_id"], "text": clean + " changed"}])
