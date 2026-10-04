"""FastAPI app. Run with `uvicorn filingguard.api.main:app`."""

from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

from filingguard.agents.schema import TargetAgent
from filingguard.data.filings import COMPANIES

app = FastAPI(title="FilingGuard")


class AnswerRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    company: str


@lru_cache(maxsize=1)
def get_target_agent() -> TargetAgent:
    """Build the 10-K RAG agent once per process."""
    from filingguard.agents.targets.tenk_rag import build_tenk_rag_agent

    return build_tenk_rag_agent()


@app.post("/api/target/answer")
def answer(request: AnswerRequest, agent: TargetAgent = Depends(get_target_agent)) -> dict:
    """Ask the target agent a question about one corpus company."""
    company = request.company.upper()
    if company not in COMPANIES:
        raise HTTPException(status_code=404, detail=f"unknown company {company}")
    return agent.answer(request.question, company).to_dict()
