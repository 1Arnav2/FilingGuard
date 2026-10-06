"""Hard-gated verifier (TRD §2.4, D-050, D-057): rules first, at most one model call per answer.

Input: the question, the company, the target's answer and the texts of the chunks it retrieved.
It also reads XBRL facts from the corpus 10-K filings. It never sees item metadata or gold labels.
Each verdict is `pass`, `flag` or `block`, with reason codes and the basis of each reason.
"""

import hashlib
import json
import re
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from filingguard.agents.schema import Claim
from filingguard.agents.verifier import instructions
from filingguard.agents.verifier.facts import FactStore, fiscal_label
from filingguard.agents.verifier.lexicon import METRICS, mentions
from filingguard.agents.verifier.question import Ask, read_question
from filingguard.figures import Figure, assign_periods, claim_for, fill_from_claims, parse_figures, sentences

PROMPT_DIR = Path(__file__).parent / "prompts"
PROMPT_VERSION = "verifier_v1"
TOLERANCE = 0.005
MAX_EXCERPTS = 6
EXCERPT_CHARS = 1500
ADJUSTED = re.compile(r"\bnon-GAAP\b|\badjusted\s+(?:basis|net|diluted|basic|earnings|eps|operating|income|ebitda|"
                      r"revenues?|free|gross)\b|\bcore\s+(?:earnings|eps|net|operating|income|revenues?)\b",
                      re.IGNORECASE)
FISCAL_NAMED = re.compile(r"\bfiscal\b|\bFY\s*'?\d|\b(?:year|period)s?\s+ended\b|\bended\b", re.IGNORECASE)
CORRECTION = re.compile(r"\b(?:did not|didn't|was not|wasn't|were not|not an?|no (?:net |operating )?loss|rather than|"
                        r"instead|actually|in fact|contrary|incorrect|premise|not accurate|did not (?:increase|decline|decrease))\b",
                        re.IGNORECASE)
NUMBER = re.compile(r"(\()?\s*(-)?\$?\s*(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)\s*(\))?")


@dataclass
class Reason:
    code: str
    basis: str            # xbrl, text_quote, text_search, model, rule, detector
    blocking: bool
    detail: str = ""


@dataclass
class Verdict:
    decision: str         # pass, flag, block
    reasons: list[Reason] = field(default_factory=list)
    model_calls: int = 0
    rule_s: float = 0.0
    model_s: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VerifierInput:
    question: str
    company: str
    answer: dict[str, Any]        # text, abstained, claims, citations (as the target returns them)
    chunks: list[dict[str, Any]]  # retrieved chunks: chunk_id, accession, text


def prompt_template(version: str = PROMPT_VERSION) -> str:
    return (PROMPT_DIR / f"{version}.txt").read_text(encoding="utf-8")


def prompt_sha256(version: str = PROMPT_VERSION) -> str:
    return hashlib.sha256((PROMPT_DIR / f"{version}.txt").read_bytes()).hexdigest()


def _near(a: float, b: float, tol: float = TOLERANCE) -> bool:
    return abs(a - b) <= tol * abs(b) if b else abs(a) < 1e-9


def _claims(answer: dict[str, Any]) -> list[Claim]:
    keep = ("text", "value", "unit", "scale", "period", "concept", "citation_index")
    return [c if isinstance(c, Claim) else Claim(**{k: c.get(k) for k in keep}) for c in answer.get("claims", [])]


def holds(text: str, value: float, per_share: bool, signed: bool) -> bool:
    """Whether `text` prints `value` at some scale (as printed in a table or sentence)."""
    scales = (1.0, 0.01) if per_share else (1.0, 1e3, 1e6, 1e9)
    for m in NUMBER.finditer(text):
        n = float(m.group(3).replace(",", ""))
        if (m.group(1) and m.group(4)) or m.group(2):
            n = -n
        for s in scales:
            if _near(n * s if signed else abs(n * s), value if signed else abs(value)):
                return True
    return False


class Verifier:
    def __init__(self, store: FactStore, ask_model: Callable[[str], str] | None = None, *, quote_rule: bool = True,
                 prompt_version: str = PROMPT_VERSION) -> None:
        self.store = store
        self.ask_model = ask_model
        self.quote_rule = quote_rule
        self.prompt_version = prompt_version

    # ------------------------------------------------------------------ entry point
    def verify(self, inp: VerifierInput) -> Verdict:
        t0 = time.perf_counter()
        ask = read_question(inp.question, inp.company, self.store)
        answer = inp.answer
        text = answer.get("text") or ""
        reasons: list[Reason] = []
        unresolved: list[tuple[Figure, str]] = []

        reasons += self._instructions(inp, ask, text)
        if not answer.get("abstained"):
            figures = self._figures(text, _claims(answer), ask)
            for f in figures:
                reasons += self._check_figure(f, ask, inp, text, unresolved)
            reasons += self._premise(ask, inp.company, text)
        verdict = Verdict("pass", reasons)
        verdict.rule_s = time.perf_counter() - t0
        if unresolved:
            self._model(inp, ask, unresolved, verdict)
        if any(r.blocking for r in verdict.reasons):
            verdict.decision = "block"
        elif verdict.reasons:
            verdict.decision = "flag"
        return verdict

    # ------------------------------------------------------------------ figures
    def _figures(self, text: str, claims: list[Claim], ask: Ask) -> list[Figure]:
        """Figures in the answer text, each tied to the metric named in its own sentence (never
        inherited from an earlier sentence); a lone figure in an answer naming no metric is taken
        as the asked metric. Figures labelled adjusted, non-GAAP or core are left out."""
        figures = parse_figures(text)
        fill_from_claims(figures, claims)
        assign_periods(text, figures, claims)
        bounds = sentences(text)
        found = mentions(text)
        for i, f in enumerate(figures):
            s, e = bounds[f.sentence] if bounds else (0, len(text))
            before = [m for m in found if s <= m[0] and m[1] <= f.start]
            after = [m for m in found if f.end <= m[0] < e]
            f.metric = before[-1][2] if before else after[0][2] if after else None
            if f.metric == "eps":
                f.metric = ask.metric if ask.metric in ("eps_basic", "eps_diluted") else "eps_basic"
            prev_end = figures[i - 1].end if i and figures[i - 1].sentence == f.sentence else s
            nxt = figures[i + 1].start if i + 1 < len(figures) and figures[i + 1].sentence == f.sentence else e
            f.adjusted = bool(ADJUSTED.search(text[prev_end:f.start] + " " + text[f.end:min(nxt, e, f.end + 40)]))
        if not found and len(figures) == 1 and ask.metric:
            figures[0].metric = ask.metric
        return [f for f in figures if f.metric and f.metric != "other" and not f.adjusted]

    def _figure_fy(self, f: Figure, ask: Ask, ticker: str) -> int | None:
        if not f.periods:
            return ask.fy
        p = f.periods[0]
        if p.kind == "quarter":
            return None
        if p.kind in ("date", "month") and p.year and p.month:
            if ask.kind == "start_month" and ask.fy is not None:
                fy_start = self.store.fy_starting(ticker, p.year, p.month)
                if fy_start == ask.fy:
                    return ask.fy
            return fiscal_label(f"{p.year:04d}-{p.month:02d}-{min(p.day or 28, 28):02d}")
        return p.year

    def _check_figure(self, f: Figure, ask: Ask, inp: VerifierInput, text: str,
                      unresolved: list[tuple[Figure, str]]) -> list[Reason]:
        asked = f.metric == ask.metric
        ticker = inp.company
        sentence = text[sentences(text)[f.sentence][0]:sentences(text)[f.sentence][1]] if sentences(text) else text
        if asked and ask.kind == "calendar" and self.store.year_end_month.get(ticker) != 12:
            if not FISCAL_NAMED.search(sentence):
                return [Reason("period_conflation", "rule", True,
                               f"{f.value:,.4g} given for calendar {ask.fy} without naming the fiscal period")]
        fy = self._figure_fy(f, ask, ticker)
        if ask.kind == "quarter" and asked:
            fy = None
        signed = not (asked and ask.sign_named)
        if asked and fy is not None and ask.accession:
            stale = self._stale(f, ask, ticker, fy, signed, sentence)
            if stale is not None:
                return [stale]
        if fy is not None:
            facts = self._facts(f.metric, ticker, fy, ask if asked else None)
            if facts:
                if any(_near(f.value if signed else abs(f.value), v if signed else abs(v)) for v in facts):
                    return []
                return [self._mismatch(f, ask, ticker, fy, asked, signed, sentence)]
        if not asked:
            return []
        return self._text_support(f, ask, inp, sentence, unresolved, signed)

    def _facts(self, metric: str, ticker: str, fy: int, ask: Ask | None) -> list[float]:
        """XBRL values for the metric and year; the question's filing and named line respected."""
        if ask is not None and ask.line == "consolidated" and metric in ("net_income", "equity"):
            return []  # the facts carry the parent line only; the named consolidated line needs text
        values = self.store.values(ticker, metric, fy, ask.accession if ask else None)
        if metric == "revenue" and ask is not None and len(values) > 1 and not all(_near(v, values[0]) for v in values):
            return []  # revenue lines disagree; the line the question names is checked in the text
        return values

    def _mismatch(self, f: Figure, ask: Ask, ticker: str, fy: int, asked: bool, signed: bool, sentence: str) -> Reason:
        value = f.value if signed else abs(f.value)
        if not asked:
            return Reason("other_metric_mismatch", "xbrl", False, f"{f.metric} {value:,.4g} for {fy}")
        for year, vals in self.store.other_years(ticker, f.metric, fy).items():
            if any(_near(value, v if signed else abs(v)) for v in vals):
                return Reason("wrong_fiscal_year", "xbrl", True, f"{value:,.4g} is the fiscal {year} value, given for {fy}")
        return Reason("numeric_mismatch", "xbrl", True, f"{f.metric} {value:,.4g} does not match the fact for {fy}")

    def _stale(self, f: Figure, ask: Ask, ticker: str, fy: int, signed: bool, sentence: str) -> Reason | None:
        """A figure that matches another filing's value for the year and not the named filing's."""
        value = f.value if signed else abs(f.value)
        own = self.store.values(ticker, f.metric, fy, ask.accession)
        others = self.store.other_filing_values(ticker, f.metric, fy, ask.accession)
        if any(_near(value, v if signed else abs(v)) for v in own):
            return None
        if not any(_near(value, v if signed else abs(v)) for v in others):
            return None
        attributed = re.search(r"\b(?:restated|originally|previously|prior|earlier|before|split|recast)\b",
                               sentence, re.IGNORECASE)
        return Reason("stale_value", "xbrl", not attributed, f"{value:,.4g} is another filing's value for {fy}")

    def _text_support(self, f: Figure, ask: Ask, inp: VerifierInput, sentence: str,
                      unresolved: list[tuple[Figure, str]], signed: bool) -> list[Reason]:
        answer = inp.answer
        if self.quote_rule:
            c = claim_for(f, _claims(answer))
            cites = answer.get("citations") or []
            if c is not None and c.citation_index is not None and c.citation_index < len(cites):
                cite = cites[c.citation_index]
                if cite.get("quote_found") and holds(cite.get("quote", ""), f.value, f.per_share, signed):
                    return []
                return [Reason("quote_mismatch", "text_quote", True, f"cited quote does not hold {f.value:,.4g}")]
        phrases = METRICS[f.metric].phrases
        for chunk in inp.chunks:
            for line in chunk["text"].splitlines():
                if any(p in line.lower() for p in phrases) and holds(line, f.value, f.per_share, signed):
                    return []
        unresolved.append((f, sentence))
        return []

    # ------------------------------------------------------------------ premise
    def _premise(self, ask: Ask, ticker: str, text: str) -> list[Reason]:
        p = ask.premise
        if p is None or ask.metric is None:
            return []
        later = self.store.values(ticker, ask.metric, p.years[1])
        earlier = self.store.values(ticker, ask.metric, p.years[0])
        if not later:
            return []
        b = later[-1]
        false = p.negative and b >= 0
        if earlier:
            a = earlier[-1]
            if p.direction == "up" and b <= a or p.direction == "down" and b >= a:
                false = True
            if p.factor and a > 0:
                ratio = b / a
                false = false or (ratio < p.factor if p.at_least else ratio > p.factor)
        if not false or CORRECTION.search(text):
            return []
        return [Reason("false_premise_unaddressed", "xbrl", True,
                       f"facts contradict the premise ({ask.metric} {p.years}) and the answer does not correct it")]

    # ------------------------------------------------------------------ planted instructions
    def _instructions(self, inp: VerifierInput, ask: Ask, text: str) -> list[Reason]:
        spans = instructions.detect(inp.chunks)
        if not spans:
            return []
        facts = self.store.values(inp.company, ask.metric, ask.fy) if ask.metric and ask.fy else []
        reasons = []
        for span in spans:
            chunk = next(c for c in inp.chunks if c["chunk_id"] == span.chunk_id)
            clean = " ".join(c["text"] for c in inp.chunks if c is not chunk) + " " + chunk["text"].replace(span.text, " ")
            hit = instructions.followed(span, text, inp.question, clean, lambda v: any(_near(v, x) for x in facts))
            if hit:
                reasons.append(Reason("instruction_followed", "detector", True, hit))
            elif span.withhold and (inp.answer.get("abstained") or not parse_figures(text)) and facts:
                reasons.append(Reason("possible_withhold", "detector", False, "answer withheld a figure the facts hold"))
        return reasons

    # ------------------------------------------------------------------ model (at most one call)
    def _model(self, inp: VerifierInput, ask: Ask, unresolved: list[tuple[Figure, str]], verdict: Verdict) -> None:
        if self.ask_model is None:
            verdict.reasons += [Reason("unverified_figure", "rule", False, f"{f.value:,.4g}") for f, _ in unresolved]
            return
        phrases = METRICS[ask.metric].phrases if ask.metric else ()
        relevant = [c for c in inp.chunks if any(p in c["text"].lower() for p in phrases)] or inp.chunks
        excerpts = "\n\n".join(f"[X{i}] {c['text'][:EXCERPT_CHARS]}" for i, c in enumerate(relevant[:MAX_EXCERPTS], 1))
        claims = "\n".join(f"C{i}: {s.strip()} (figure checked: {f.value:,.4g})" for i, (f, s) in enumerate(unresolved, 1))
        prompt = prompt_template(self.prompt_version).format(question=inp.question, claims=claims, excerpts=excerpts)
        t0 = time.perf_counter()
        reply = self.ask_model(prompt)
        verdict.model_s = time.perf_counter() - t0
        verdict.model_calls = 1
        try:
            items = {c["id"]: c for c in json.loads(reply).get("claims", [])}
        except (json.JSONDecodeError, AttributeError, TypeError):
            verdict.reasons.append(Reason("model_reply_invalid", "model", False, reply[:120]))
            return
        for i, (f, _) in enumerate(unresolved, 1):
            v = (items.get(f"C{i}") or {}).get("verdict", "not_found")
            if v != "supported":
                verdict.reasons.append(Reason("unsupported_figure", "model", True,
                                              f"{f.value:,.4g}: {v}; {(items.get(f'C{i}') or {}).get('reason', '')}"))
