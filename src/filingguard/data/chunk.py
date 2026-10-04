"""Split filing text into overlapping chunks that keep character offsets into the source."""

from dataclasses import asdict, dataclass

# CORPUS.md §6 asks for about 800 tokens with 100 overlap; at about 4 characters per token
# for English filing text that is 3,200 and 400 characters (D-017).
CHUNK_CHARS = 3200
OVERLAP_CHARS = 400


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    ticker: str
    accession: str
    item: str
    start: int
    end: int
    text: str

    def to_dict(self) -> dict:
        return asdict(self)


def _snap_end(text: str, start: int, end: int) -> int:
    """Move `end` back to the last line break or space, if one is in the second half."""
    if end >= len(text):
        return len(text)
    floor = start + (end - start) // 2
    for sep in ("\n", " "):
        cut = text.rfind(sep, floor, end)
        if cut != -1:
            return cut
    return end


def chunk_span(
    text: str, span_start: int, span_end: int, size: int = CHUNK_CHARS, overlap: int = OVERLAP_CHARS
) -> list[tuple[int, int]]:
    """Return (start, end) windows covering text[span_start:span_end]."""
    windows = []
    start = span_start
    while start < span_end:
        end = _snap_end(text, start, min(start + size, span_end)) if start + size < span_end else span_end
        windows.append((start, end))
        if end >= span_end:
            break
        start = max(end - overlap, start + 1)
        while start < end and not text[start - 1].isspace():
            start += 1
    return windows


def chunk_filing(ticker: str, accession: str, text: str, segments: list[tuple[str, int, int]]) -> list[Chunk]:
    """Chunk each labelled segment; chunk ids are `<accession>:<n>` in document order."""
    chunks = []
    for item, s, e in sorted(segments, key=lambda seg: seg[1]):
        for start, end in chunk_span(text, s, e):
            body = text[start:end].strip()
            if body:
                chunks.append(Chunk(f"{accession}:{len(chunks)}", ticker, accession, item, start, end, text[start:end]))
    return chunks
