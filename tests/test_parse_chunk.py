from filingguard.data.chunk import chunk_filing, chunk_span
from filingguard.data.parse_10k import html_to_text, label_segments, split_items

DOC = b"""<html><head><title>x</title><style>p{}</style></head><body>
<div style="display:none"><ix:header>hidden facts 999</ix:header></div>
<table><tr><td>Item 1.</td><td>Business</td><td>3</td></tr>
<tr><td>Item 7.</td><td>MD&amp;A</td><td>9</td></tr></table>
<p>Item 1. Business</p>
<p>We make <span>widgets</span> and <b>gadgets</b>.&#160;See Item 7 of this report for a long discussion of results and much more text.</p>
<p>Item 7. Management's Discussion</p>
<p>PART II</p><p>Item 7</p><p>Results continued after a running page header.</p>
<table>
<tr><td>Net sales</td><td>$</td><td>391,035</td><td></td><td>$</td><td>383,285</td></tr>
<tr><td>Change</td><td>(2</td><td>)%</td></tr>
</table>
<p>Item 8. Financial Statements</p><p>Statements.</p>
<p>Item 15. Exhibits</p><p>FINANCIAL SECTION</p><p>Consolidated statement of income.</p>
</body></html>"""


def test_text_drops_hidden_and_keeps_inline_flow():
    text = html_to_text(DOC)
    assert "hidden facts" not in text and "p{}" not in text
    assert "We make widgets and gadgets. See Item 7" in text


def test_table_rows_join_currency_and_parentheses():
    text = html_to_text(DOC)
    assert "Net sales | $391,035 | $383,285" in text
    assert "Change | (2)%" in text


def test_split_items_skips_toc_and_prose_mentions():
    text = html_to_text(DOC)
    spans = split_items(text)
    assert set(spans) == {"1", "7", "8", "15"}
    assert text[slice(*spans["1"])].startswith("Item 1. Business")
    assert "widgets" in text[slice(*spans["1"])]


def test_running_page_header_does_not_split_a_section():
    text = html_to_text(DOC)
    item7 = text[slice(*split_items(text)["7"])]
    assert "running page header" in item7 and "391,035" in item7


def test_segments_cover_whole_text_and_label_kept_items():
    text = html_to_text(DOC)
    segments = label_segments(text)
    assert segments[0][1] == 0 and segments[-1][2] == len(text)
    assert all(a[2] == b[1] for a, b in zip(segments, segments[1:])), "no gaps or overlaps"
    labels = [label for label, _, _ in segments]
    assert labels == ["other", "1", "7", "8", "other"]
    assert "FINANCIAL SECTION" in text[segments[-1][1]:segments[-1][2]]


def test_chunks_cover_span_with_overlap_and_offsets():
    text = " ".join(f"w{i}" for i in range(3000))
    windows = chunk_span(text, 0, len(text), size=500, overlap=100)
    assert windows[0][0] == 0 and windows[-1][1] == len(text)
    for (s1, e1), (s2, e2) in zip(windows, windows[1:]):
        assert s2 < e1, "consecutive chunks overlap"
        assert e1 - s1 <= 500
        assert text[s2 - 1] == " ", "chunks start on a word boundary"


def test_chunk_text_matches_offsets():
    text = html_to_text(DOC)
    chunks = chunk_filing("ACME", "0001-26-1", text, label_segments(text))
    assert chunks and all(text[c.start:c.end] == c.text for c in chunks)
    assert {c.item for c in chunks} == {"other", "1", "7", "8"}
    assert [c.chunk_id for c in chunks] == [f"0001-26-1:{i}" for i in range(len(chunks))]
