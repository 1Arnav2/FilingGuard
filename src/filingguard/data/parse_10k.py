"""10-K HTML to clean text, with tables kept as pipe-separated rows, split by Item."""

import re

from lxml import html as lxml_html

KEEP_ITEMS = ("1", "1A", "7", "7A", "8")

_DROP_TAGS = {"script", "style", "head", "title", "ix:header"}
_BLOCK_TAGS = {
    "p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6",
    "section", "center", "hr", "blockquote", "pre",
}
_HIDDEN = re.compile(r"display\s*:\s*none", re.I)
# A heading has punctuation after the number ("Item 7." / "ITEM 7:" / "Item 7. | ..."). Bare
# "Item 7" lines are running page headers in some filings and are not headings.
_HEADING = re.compile(r"^item\s*(\d{1,2}[abc]?)\s*[\.:|\-—–]", re.I)
_MAX_HEADING_LEN = 150


def _is_dropped(el) -> bool:
    tag = el.tag if isinstance(el.tag, str) else ""
    return tag.lower() in _DROP_TAGS or bool(_HIDDEN.search(el.get("style", "")))


def _inline_text(el) -> str:
    return " ".join(" ".join(el.itertext()).split())


def _table_text(table) -> str:
    """One line per row; `$` joins the next cell, `)` and `%` join the previous one."""
    lines = []
    for row in table.iter("tr"):
        cells = []
        for cell in row:
            if not isinstance(cell.tag, str) or cell.tag.lower() not in ("td", "th"):
                continue
            text = _inline_text(cell)
            if not text:
                continue
            if cells and cells[-1] in ("$", "(", "$("):
                cells[-1] = cells[-1] + text
            elif cells and text in (")", "%", ")%", "%)"):
                cells[-1] = cells[-1] + text
            else:
                cells.append(text)
        if cells:
            lines.append(" | ".join(cells))
    return "\n".join(lines)


def _emit(el, out: list[str]) -> None:
    if _is_dropped(el):
        return
    tag = el.tag.lower() if isinstance(el.tag, str) else ""
    if tag == "table":
        out.append("\n" + _table_text(el) + "\n")
        return
    block = tag in _BLOCK_TAGS
    if block:
        out.append("\n")
    if el.text and isinstance(el.tag, str):
        out.append(el.text)
    for child in el:
        _emit(child, out)
        if child.tail:
            out.append(child.tail)
    if block:
        out.append("\n")


def html_to_text(raw: bytes) -> str:
    """Return the visible text of a 10-K: one paragraph or table row per line."""
    root = lxml_html.fromstring(raw)
    out: list[str] = []
    _emit(root, out)
    text = "".join(out).replace("\xa0", " ").replace("​", "")
    lines = (" ".join(line.split()) for line in text.split("\n"))
    return "\n".join(line for line in lines if line)


def _sections(text: str) -> list[tuple[str, int, int]]:
    """Return (item, start, end) for every heading; each runs to the next heading."""
    starts = []
    offset = 0
    for line in text.split("\n"):
        match = _HEADING.match(line)
        if match and len(line) <= _MAX_HEADING_LEN:
            starts.append((match.group(1).upper(), offset))
        offset += len(line) + 1
    ends = [s for _, s in starts[1:]] + [len(text)]
    return [(item, start, end) for (item, start), end in zip(starts, ends)]


def split_items(text: str) -> dict[str, tuple[int, int]]:
    """Return {item: (start, end)} character spans.

    The table of contents repeats every heading, so for each item the longest section is kept.
    """
    spans: dict[str, tuple[int, int]] = {}
    for item, start, end in _sections(text):
        if item not in spans or end - start > spans[item][1] - spans[item][0]:
            spans[item] = (start, end)
    return spans


def label_segments(text: str) -> list[tuple[str, int, int]]:
    """Partition the whole text into (label, start, end) segments.

    The label is the item for the longest section of each item in `KEEP_ITEMS`, and `other`
    for everything else (cover, table of contents, other items, and financial sections that
    some filers place outside the Item structure).
    """
    keep = {(s, e): item for item, (s, e) in split_items(text).items() if item in KEEP_ITEMS}
    segments: list[tuple[str, int, int]] = []
    cursor = 0
    for start, end in sorted(keep):
        if start > cursor:
            segments.append(("other", cursor, start))
        segments.append((keep[(start, end)], start, end))
        cursor = end
    if cursor < len(text):
        segments.append(("other", cursor, len(text)))
    return segments
