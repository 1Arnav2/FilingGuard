from fastapi.testclient import TestClient

from filingguard.agents.schema import AgentAnswer
from filingguard.api.live import get_target_agent
from filingguard.api.main import create_app


class StubAgent:
    name = "stub"

    def __init__(self):
        self.calls = []

    def answer(self, question, company):
        self.calls.append((question, company))
        return AgentAnswer(text="ok", claims=[], citations=[], abstained=False, latency_s=0.1, trace={"agent": "stub"})


def client_with(stub, tmp_path):
    """The app with the live route switched on and the agent replaced by a stub."""
    app = create_app(live_target=True, static_dir=tmp_path / "no-export")
    app.dependency_overrides[get_target_agent] = lambda: stub
    return TestClient(app)


def test_answer_route_returns_agent_answer(tmp_path):
    stub = StubAgent()
    response = client_with(stub, tmp_path).post("/api/target/answer", json={"question": "Revenue?", "company": "aapl"})
    assert response.status_code == 200
    assert response.json()["text"] == "ok" and response.json()["trace"]["agent"] == "stub"
    assert stub.calls == [("Revenue?", "AAPL")]


def test_unknown_company_and_empty_question_are_rejected(tmp_path):
    stub = StubAgent()
    client = client_with(stub, tmp_path)
    assert client.post("/api/target/answer", json={"question": "x", "company": "ZZZZ"}).status_code == 404
    assert client.post("/api/target/answer", json={"question": "", "company": "AAPL"}).status_code == 422
    assert stub.calls == []
