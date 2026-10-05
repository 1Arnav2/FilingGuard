"""One generator per attack type. Each builds item specs from located XBRL facts; the model
only phrases the question afterwards (`redteam.phrasing`)."""

from filingguard.redteam.generators import (
    control, false_premise, injection, period_mismatch, restated, unanswerable, unit_trap,
)

GENERATORS = {
    "control": control.generate,
    "unanswerable": unanswerable.generate,
    "unit_trap": unit_trap.generate,
    "period_mismatch": period_mismatch.generate,
    "restated": restated.generate,
    "false_premise": false_premise.generate,
    "injection": injection.generate,
}
