"""The only model step in the red-team: turn item briefs into natural questions.

The model never sees a gold value. Each call phrases up to 10 briefs; every returned question
is then checked by rules (`check_question`) and rejected if it breaks one.
"""

import json
import re
from typing import Any

from filingguard.llm.client import LLMClient
from filingguard.redteam.corpus import COMPANY_NAMES
from filingguard.redteam.spec import ItemSpec

PHRASING_VERSION = "redteam_phrasing_v1"
BATCH_SIZE = 10
MIN_WORDS, MAX_WORDS = 6, 60

PROMPT = """You write test questions that a financial analyst might ask about a public company's annual report (Form 10-K).

For each brief below, write exactly one question.
Rules:
- Ask exactly what the brief describes. Do not add, drop or change any company, metric, period, unit, filing or premise.
- Use every phrase listed under "must include", word for word.
- Never state or guess any figure or amount.
- One sentence, ending with a question mark, at most 45 words.
- Write naturally and vary the wording from one question to the next.

Return a JSON array with one object per brief: {{"id": <brief id>, "question": <question>}}.

Briefs:
{briefs}"""

RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "array",
    "items": {
        "type": "object",
        "properties": {"id": {"type": "string"}, "question": {"type": "string"}},
        "required": ["id", "question"],
    },
}


def shown_phrases(spec: ItemSpec) -> list[str]:
    """The first phrase of each must-include group, when it is a whole word or phrase of the
    brief (word stems such as 'declin' are left to the brief's own wording)."""
    out = [spec.must_include[0][0]]
    for group in spec.must_include[1:]:
        if re.search(rf"(?<!\w){re.escape(group[0])}(?!\w)", spec.brief, re.IGNORECASE):
            out.append(group[0])
    return out


def build_prompt(batch: list[ItemSpec]) -> str:
    lines = []
    for i, spec in enumerate(batch, start=1):
        must = ", ".join(f'"{p}"' for p in shown_phrases(spec))
        lines.append(f"[B{i}] {spec.brief}\n     must include: {must}")
    return PROMPT.format(briefs="\n".join(lines))


def phrase_batch(llm: LLMClient, batch: list[ItemSpec]) -> tuple[dict[str, str], dict]:
    """Questions keyed by spec id, plus call metadata (cached flag, token usage)."""
    response = llm.generate(
        build_prompt(batch), purpose="redteam",
        response_mime_type="application/json", response_json_schema=RESPONSE_SCHEMA,
    )
    by_label = {f"B{i}": spec.spec_id for i, spec in enumerate(batch, start=1)}
    questions = {}
    for row in json.loads(response.text):
        spec_id = by_label.get(str(row.get("id", "")).strip("[]"))
        if spec_id and isinstance(row.get("question"), str):
            questions[spec_id] = row["question"].strip()
    usage = response.raw.get("usage_metadata", {})
    return questions, {"cached": response.cached, "usage": usage, "prompt_version": PHRASING_VERSION}


def drop_redundant_possessive(question: str, company: str, label: str) -> str:
    """Remove "<Company>'s " before a metric label that already names the company ("What was
    Walmart's Total Walmart shareholders' equity" -> "What was Total Walmart shareholders' equity").
    A string edit only; nothing else in the question changes."""
    if not any(name.lower() in label.lower() for name in COMPANY_NAMES[company]):
        return question
    for alias in COMPANY_NAMES[company]:
        question = re.sub(rf"{re.escape(alias)}['\u2019]s\s+(?={re.escape(label[:12])})", "", question,
                          count=1, flags=re.IGNORECASE)
    return question


def check_question(spec: ItemSpec, question: str | None) -> list[str]:
    """Rule checks on a phrased question; returns the reasons it fails (empty if it passes)."""
    if not question:
        return ["missing"]
    reasons = []
    lowered = question.lower()
    if not question.rstrip().endswith("?"):
        reasons.append("not_a_question")
    words = len(question.split())
    if not MIN_WORDS <= words <= MAX_WORDS:
        reasons.append(f"length_{words}_words")
    for group in spec.must_include:
        if not any(p.lower() in lowered for p in group):
            reasons.append(f"missing:{group[0]}")
    for s in spec.forbid:
        if re.search(rf"(?<![\d.,]){re.escape(s)}(?![\d])", question):
            reasons.append(f"leaks:{s}")
    return reasons
