"""The candidate item a generator builds before the model phrases its question."""

import hashlib
import json
from dataclasses import asdict, dataclass, field

from filingguard.redteam.corpus import COMPANY_NAMES, renderings


@dataclass
class ItemSpec:
    """Everything about an item except the question's wording.

    `brief` tells the phrasing model what to ask. `must_include` is a list of groups; the
    question must contain at least one phrase from each group. `forbid` lists strings the
    question must not contain (the answer, in any printed form).
    """

    attack_type: str
    subtype: str
    company: str
    expected_behavior: str
    gold: dict
    source: dict | None
    brief: str
    must_include: list[list[str]]
    forbid: list[str] = field(default_factory=list)
    injection: dict | None = None
    evidence: dict | None = None   # e.g. the evidence-of-absence search for `unanswerable`
    spec_id: str = ""

    def __post_init__(self) -> None:
        names = [*COMPANY_NAMES[self.company], self.company]
        if not self.must_include or self.must_include[0] != names:
            self.must_include = [names] + self.must_include
        if not self.spec_id:
            body = json.dumps([self.attack_type, self.subtype, self.company, self.gold, self.brief], sort_keys=True)
            self.spec_id = f"{self.attack_type}-{self.company}-{hashlib.sha256(body.encode()).hexdigest()[:8]}"

    def to_dict(self) -> dict:
        return asdict(self)


def value_strings(value: float | None, unit: str) -> list[str]:
    """Printed forms of a gold value that must not appear in its question."""
    if value is None:
        return []
    return [r for r, _ in renderings(value, unit)]
