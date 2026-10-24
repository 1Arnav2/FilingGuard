"""Live target route: asks the frozen 10-K agent a question, which makes model calls.

Included only when `FILINGGUARD_LIVE_TARGET=1` (see `main.create_app`). Off by default and never set
on the public deploy, whose image holds no index and no key. The spend cap still applies when on.
"""

from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from filingguard.agents.schema import TargetAgent
from filingguard.data.filings import COMPANIES

router = APIRouter(prefix="/api")


class AnswerRequest(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    company: str


@lru_cache(maxsize=1)
def get_target_agent() -> TargetAgent:
    """Build the 10-K RAG agent once per process."""
    from filingguard.agents.targets.tenk_rag import build_tenk_rag_agent

    return build_tenk_rag_agent()


@router.post("/target/answer")
def answer(request: AnswerRequest, agent: TargetAgent = Depends(get_target_agent)) -> dict:
    """Ask the target agent a question about one corpus company."""
    company = request.company.upper()
    if company not in COMPANIES:
        raise HTTPException(status_code=404, detail=f"unknown company {company}")
    return agent.answer(request.question, company).to_dict()
