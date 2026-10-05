from filingguard.eval.rules import CORRECT, MISSED, UNSUPPORTED, figure_outcome


def test_no_figure_and_no_abstention_is_missed_not_correct():
    # D-043: "every figure matches" must not be satisfied by giving no figure at all.
    assert figure_outcome(abstained=False, figure_matches=[]) == MISSED


def test_figure_rule_outcomes():
    assert figure_outcome(False, [True]) == CORRECT
    assert figure_outcome(False, [True, True]) == CORRECT
    assert figure_outcome(False, [True, False]) == UNSUPPORTED
    assert figure_outcome(False, [False]) == UNSUPPORTED
    assert figure_outcome(True, [True]) == MISSED      # an abstention is Missed even with a right figure
    assert figure_outcome(True, []) == MISSED


def test_wilson_interval():
    from filingguard.eval.stats import wilson
    low, high = wilson(0, 60)
    assert low == 0.0 and round(high, 4) == 0.0602
    low, high = wilson(5, 10)
    assert round(low, 4) == 0.2366 and round(high, 4) == 0.7634
