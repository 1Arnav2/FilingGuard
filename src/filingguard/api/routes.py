"""Read-only results routes for the dashboard: summary, method facts, items list, item detail.

Every response comes from committed `results/` files (see `results.py`); nothing is computed
beyond filtering and paging. The corrected basis is in the export, applied by the Phase 5 overlay.
"""

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from filingguard.api.results import META, SUMMARY, load

router = APIRouter(prefix="/api")

Basis = Literal["corrected", "as_scored"]
Condition = Literal["baseline", "treatment"]
Outcome = Literal["correct", "missed", "unsupported"]
Decision = Literal["pass", "flag", "block"]
AttackType = Literal["control", "unanswerable", "unit_trap", "period_mismatch", "false_premise", "injection",
                     "restated"]
Label = Literal["wrong_number", "wrong_unit", "wrong_period", "stale_restated", "fabricated_fact",
                "accepted_false_premise", "rejected_true_premise", "injection_followed", "bad_citation",
                "retrieval_miss", "other"]  # EVAL §7


class Open(BaseModel):
    """A summary section: the typed fields the dashboard uses, every other key passed through."""

    model_config = ConfigDict(extra="allow")


class Rate(Open):
    k: int
    n: int
    rate: float | None
    wilson95: list[float] | None


class StatusRate(Rate):
    status: str


class Bar(Open):
    status: str


class ConditionSummary(Open):
    outcomes: dict[str, int]
    unsupported_claim_rate: Rate
    correct_handling: Rate
    answer_coverage: Rate
    abstain_rate_controls: Rate
    injection_followed: Rate


class FalseBlocks(Open):
    corrected: StatusRate
    as_scored: StatusRate
    threshold: float


class Seeded(Open):
    macro_detection_T1_T3_T4_T5_T6_quote_off: float
    macro_threshold: float
    macro_status: str
    by_transform_quote_off: dict[str, Rate]
    by_transform_full: dict[str, Rate]
    false_block_rate: FalseBlocks


class Timing(Open):
    n: int
    p50: float
    p95: float
    mean: float


class Latency(Open):
    sample: int
    run: int
    end_to_end_s: Timing
    verifier_rule_s: Timing


class Spend(Open):
    total_usd: float
    cap_usd: float


class Summary(Open):
    split: str
    n_items: int
    bases: str
    pass_bars: dict[Basis, dict[str, Bar]]
    seeded_errors: Seeded
    conditions: dict[Basis, dict[Condition, ConditionSummary]]
    latency: Latency
    spend: Spend
    limitations: list[str]
    generated_from: str


class Tag(BaseModel):
    commit: str
    url: str


class Meta(Open):
    split: dict[str, int]
    attack_types_test: dict[str, int]
    companies: int
    freeze_tags: dict[str, Tag]
    repo: str
    pass_bars_set: dict[str, str]
    corrections: dict[str, str | int]
    handcheck: dict[str, str | int]
    inputs_sha256: dict[str, str]
    generated_from: str


class ScoreView(BaseModel):
    outcome: Outcome
    label: str | None
    notes: list[str]
    abstained: bool
    scale_not_followed: bool
    unparseable: bool
    injection: str | None
    answer_followed: bool | None


class ItemRow(BaseModel):
    id: str
    company: str
    attack_type: str
    subtype: str
    question: str
    baseline: ScoreView
    treatment: ScoreView
    verdict: Decision
    reason_codes: list[str]
    corrected: bool
    unparseable: bool
    handchecked: bool


class ItemPage(BaseModel):
    total: int
    page: int
    page_size: int
    basis: Basis
    items: list[ItemRow]


class Claim(BaseModel):
    text: str | None
    value: float | None
    unit: str | None
    scale: str | None
    period: str | None
    concept: str | None
    citation_index: int | None


class Citation(BaseModel):
    doc_id: str
    chunk_id: str
    start: int | None
    end: int | None
    quote: str
    quote_found: bool


class Answer(BaseModel):
    text: str | None  # None when the reply was unparseable; the runaway text is not served
    abstained: bool
    claims: list[Claim]
    citations: list[Citation]
    parse_error: str | None
    unparseable_chars: int | None


class Retrieved(BaseModel):
    rank: int
    chunk_id: str
    item: str | None
    source: str
    score: float


class Figure(BaseModel):
    value: float
    scale: str | None
    negative: bool
    metric: str | None
    adjusted: bool
    asked: bool
    period: str | None
    period_ok: bool | None


class Gold(Open):
    expected_behavior: str
    text: str
    value: float | None
    unit: str | None
    metric: str | None
    fiscal_year: int | None


class Judge(BaseModel):
    rejects_premise: bool | None
    confirms_change: bool | None
    gives_reasons: bool | None
    reasons_in_filing: bool | None
    says_no_reasons_given: bool | None
    reason: str | None


class Reason(BaseModel):
    code: str
    basis: str
    blocking: bool
    detail: str


class Verdict(BaseModel):
    decision: Decision
    reasons: list[Reason]


class Correction(BaseModel):
    status: Literal["corrected", "kept as scored"]
    as_scored: list[str | None]
    corrected: list[str | None] | None
    pattern: str | None
    evidence: dict[str, Any] | None
    reason: str
    approval: str | None


class HandCheck(BaseModel):
    why_listed: str
    verdict: str | None
    note: str | None
    pre_filled: str | None


class ItemDetail(BaseModel):
    id: str
    company: str
    attack_type: str
    subtype: str
    question: str
    gold: Gold
    answer: Answer
    retrieved: list[Retrieved]
    figures: list[Figure]
    judge: Judge | None
    outcomes: dict[Basis, dict[Condition, ScoreView]]
    verdict: dict[Literal["full", "quote_off"], Verdict]
    correction: Correction | None
    handcheck: HandCheck | None


def _row(item: dict[str, Any], basis: Basis) -> ItemRow:
    full = item["verdict"]["full"]
    outcomes = item["outcomes"][basis]
    return ItemRow(id=item["id"], company=item["company"], attack_type=item["attack_type"], subtype=item["subtype"],
                   question=item["question"], baseline=outcomes["baseline"], treatment=outcomes["treatment"],
                   verdict=full["decision"], reason_codes=[r["code"] for r in full["reasons"]],
                   corrected=(item["correction"] or {}).get("status") == "corrected",
                   unparseable=item["answer"]["parse_error"] is not None, handchecked=item["handcheck"] is not None)


@router.get("/summary", response_model=Summary)
def summary() -> dict[str, Any]:
    """`results/summary.json` unchanged, with its source named."""
    return {**load().summary, "generated_from": f"results/{SUMMARY}"}


@router.get("/meta", response_model=Meta)
def meta() -> dict[str, Any]:
    """Method facts from the dashboard export: split, freeze tags, when the bars were set, input hashes."""
    return {**load().meta, "generated_from": f"results/{META}"}


@router.get("/items", response_model=ItemPage)
def items(attack_type: AttackType | None = None, outcome: Outcome | None = None, label: Label | None = None,
          verdict: Decision | None = None, basis: Basis = "corrected", condition: Condition = "treatment",
          page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=500)) -> ItemPage:
    """The test items, filtered; `outcome` and `label` apply to `condition` on `basis`."""
    rows = [_row(item, basis) for item in load().items.values()]
    if attack_type:
        rows = [r for r in rows if r.attack_type == attack_type]
    if verdict:
        rows = [r for r in rows if r.verdict == verdict]
    if outcome:
        rows = [r for r in rows if getattr(r, condition).outcome == outcome]
    if label:
        rows = [r for r in rows if getattr(r, condition).label == label]
    start = (page - 1) * page_size
    return ItemPage(total=len(rows), page=page, page_size=page_size, basis=basis, items=rows[start:start + page_size])


@router.get("/items/{item_id}", response_model=ItemDetail)
def item(item_id: str) -> dict[str, Any]:
    """One item as exported: gold, answer, figures read, judge, both bases, both verifier modes,
    any D-071 correction and the owner's hand-check."""
    row = load().items.get(item_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"unknown item {item_id}")
    return row
