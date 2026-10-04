from filingguard.data.spot_check import find_in_text, renderings


def test_renderings_cover_millions_thousands_eps_and_negatives():
    assert renderings(416_161_000_000, "USD")[0] == "416,161"
    assert "416,161,000" in renderings(416_161_000_000, "USD")
    assert renderings(7.46, "USD/shares") == ["7.46"]
    assert renderings(-1_234_000_000, "USD")[0] == "(1,234)"
    assert renderings(1_234_567_890, "USD")[0] == "1,235"


def test_find_in_text_returns_context():
    text = "Total net sales | $416,161 | $391,035"
    match = find_in_text(text, 416_161_000_000, "USD")
    assert match["rendering"] == "416,161" and "Total net sales" in match["context"]
    assert find_in_text(text, 1.0, "USD/shares") is None
