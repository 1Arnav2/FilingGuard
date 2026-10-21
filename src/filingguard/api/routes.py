"""Read-only results routes for the dashboard: summary, items list, item detail.

Every response comes from committed `results/` files (see `results.py`); nothing is computed
beyond the D-071 overlay and filtering.
"""

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from filingguard.api.results import SUMMARY, load

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


class ScoreView(BaseModel):
    outcome: Outcome
    label: str | None
    notes: list[str]


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
    text: str
    abstained: bool
    claims: list[Claim]
    citations: list[Citation]
    parse_error: str | None


class Retrieved(BaseModel):
    rank: int
    chunk_id: str
    item: str | None
    source: str
    score: float


class Reason(BaseModel):
    code: str
    basis: str
    blocking: bool
    detail: str


class Verdict(BaseModel):
    decision: Decision
    reasons: list[Reason]


class Correction(BaseModel):
    pattern: str
    evidence: dict[str, Any]
    reason: str
    approval: str


class ItemDetail(BaseModel):
    id: str
    company: str
    attack_type: str
    subtype: str
    question: str
    answer: Answer
    retrieved: list[Retrieved]
    outcomes: dict[Basis, dict[Condition, ScoreView]]
    verdict: dict[Literal["full", "quote_off"], Verdict]
    correction: Correction | None
    scale_not_followed: bool
    unparseable: bool
    injection: str | None


def _score(row: dict[str, Any]) -> ScoreView:
    return ScoreView(outcome=row["outcome"], label=row["label"], notes=row["notes"])


def _row(item_id: str, basis: Basis) -> ItemRow:
    data = load()
    answer, base = data.answers[item_id], data.scores[basis]["baseline"][item_id]
    verdict = data.verdicts["full"][item_id]
    return ItemRow(id=item_id, company=answer["company"], attack_type=base["attack_type"], subtype=base["subtype"],
                   question=answer["question"], baseline=_score(base),
                   treatment=_score(data.scores[basis]["treatment"][item_id]), verdict=verdict["decision"],
                   reason_codes=[r["code"] for r in verdict["reasons"]], corrected=item_id in data.corrections)


@router.get("/summary", response_model=Summary)
def summary() -> dict[str, Any]:
    """`results/summary.json` unchanged, with its source named."""
    return {**load().summary, "generated_from": f"results/{SUMMARY}"}


@router.get("/items", response_model=ItemPage)
def items(attack_type: AttackType | None = None, outcome: Outcome | None = None, label: Label | None = None,
          verdict: Decision | None = None, basis: Basis = "corrected", condition: Condition = "treatment",
          page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=500)) -> ItemPage:
    """The 210 test items, filtered; `outcome` and `label` apply to `condition` on `basis`."""
    rows = [_row(i, basis) for i in load().order]
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
def item(item_id: str) -> ItemDetail:
    """One item: question, answer, retrieval, both bases, both verifier modes, any correction."""
    data = load()
    if item_id not in data.answers:
        raise HTTPException(status_code=404, detail=f"unknown item {item_id}")
    run, base = data.answers[item_id], data.scores["as_scored"]["baseline"][item_id]
    fix = data.corrections.get(item_id)
    return ItemDetail(
        id=item_id, company=run["company"], attack_type=base["attack_type"], subtype=base["subtype"],
        question=run["question"], answer=Answer(**run["answer"]), retrieved=run["retrieved"],
        outcomes={b: {c: _score(data.scores[b][c][item_id]) for c in ("baseline", "treatment")}
                  for b in ("corrected", "as_scored")},
        verdict={m: Verdict(decision=data.verdicts[m][item_id]["decision"], reasons=data.verdicts[m][item_id]["reasons"])
                 for m in ("full", "quote_off")},
        correction=Correction(**{k: fix[k] for k in ("pattern", "evidence", "reason", "approval")}) if fix else None,
        scale_not_followed=base["scale_not_followed"], unparseable=base["unparseable"], injection=base["injection"],
    )
