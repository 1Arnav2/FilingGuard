"""The contract between any target agent, the verifier, and the harness (TRD §2.2)."""

from dataclasses import asdict, dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class Citation:
    """A span of a filing's parsed text (`data/processed/text/<doc_id>.txt`)."""

    doc_id: str  # accession number
    chunk_id: str
    start: int
    end: int
    quote: str
    quote_found: bool  # False if the model's quote was not found verbatim in the chunk


@dataclass(frozen=True)
class Claim:
    """One factual statement in an answer, as the agent itself states it."""

    text: str
    value: float | None = None
    unit: str | None = None  # e.g. USD, USD/shares, shares, percent
    scale: str | None = None  # e.g. units, thousands, millions, billions
    period: str | None = None  # as stated, e.g. "fiscal 2025" or "2025-12-31"
    concept: str | None = None
    citation_index: int | None = None  # position in AgentAnswer.citations


@dataclass
class AgentAnswer:
    text: str
    claims: list[Claim]
    citations: list[Citation]
    abstained: bool
    latency_s: float
    trace: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TargetAgent(Protocol):
    name: str

    def answer(self, question: str, company: str) -> AgentAnswer:
        """Answer a question about one company's filings."""
        ...
