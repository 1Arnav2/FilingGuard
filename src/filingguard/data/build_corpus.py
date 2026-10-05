"""Build the Phase 1 corpus: filings, facts, concept map, restatement pairs, text, and index.

Run with `python -m filingguard.data.build_corpus`. Every SEC request is cached under
`data/raw/sec/`, so a re-run makes no network requests.
"""

import json
from collections import Counter
from datetime import date
from pathlib import Path

import pandas as pd

from filingguard.data.chunk import chunk_filing
from filingguard.data.edgar_client import EdgarClient, companyfacts_url, document_url, edgar_client_from_env, submissions_url
from filingguard.data.facts import USABLE_KINDS, find_restatements, map_concepts, normalise_company_facts
from filingguard.data.filings import CIK_OVERRIDES, COMPANIES, Filing, resolve_ciks, ten_k_filings
from filingguard.data.index import EMBED_MODEL, VectorIndex, cached_embed_fn, content_hash, fastembed_fn, index_is_current
from filingguard.data.parse_10k import KEEP_ITEMS, html_to_text, label_segments, split_items
from filingguard.llm.cache import DiskCache

PROCESSED = Path("data/processed")
# Three 10-Ks per company are searched for restated pairs (D-021).
FILINGS_PER_COMPANY = 3


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _parse_filing(client: EdgarClient, filing: Filing, out_dir: Path) -> tuple[str, dict]:
    """Download and parse one 10-K; save its text; return the text and item coverage stats."""
    raw = client.get_bytes(document_url(filing.cik, filing.accession, filing.primary_document))
    text = html_to_text(raw)
    (out_dir / "text").mkdir(parents=True, exist_ok=True)
    (out_dir / "text" / f"{filing.accession}.txt").write_text(text, encoding="utf-8")
    spans = split_items(text)
    item_chars = {item: spans[item][1] - spans[item][0] for item in KEEP_ITEMS if item in spans}
    stats = {
        "chars": len(text),
        "item_chars": item_chars,
        "labelled_share": round(sum(item_chars.values()) / len(text), 3) if text else 0.0,
    }
    return text, stats


def build(
    out_dir: Path = PROCESSED,
    client: EdgarClient | None = None,
    embed_cache_dir: Path = Path(".cache/embeddings"),
) -> dict:
    """Run the pipeline and return the corpus card as a dict (also written to disk)."""
    client = client or edgar_client_from_env()
    ciks = resolve_ciks(client, list(COMPANIES))

    companies, fact_frames, concept_map, pairs, chunks = [], [], {}, [], []
    for ticker, cik in ciks.items():
        submissions = client.get_json(submissions_url(cik))
        filings = ten_k_filings(client, ticker, cik, submissions, limit=FILINGS_PER_COMPANY)
        latest, prior, older = (filings + [None, None])[:3]
        facts = normalise_company_facts(ticker, cik, client.get_json(companyfacts_url(cik)))
        fact_frames.append(facts)
        concept_map[ticker] = map_concepts(facts, latest)
        company_pairs = find_restatements(facts, filings, concept_map[ticker])
        pairs.extend(company_pairs)
        restated = [p for p in company_pairs if p["kind"] in USABLE_KINDS]

        # Index an older 10-K only when it supplies a usable restated pair (D-021, D-026).
        in_pairs = {p[side]["accession"] for p in restated for side in ("original", "restated")}
        corpus_filings = [f for f in filings if f is latest or f.accession in in_pairs]
        parsed = {}
        for filing in corpus_filings:
            text, stats = _parse_filing(client, filing, out_dir)
            chunks.extend(c.to_dict() for c in chunk_filing(ticker, filing.accession, text, label_segments(text)))
            parsed[filing.accession] = stats

        def older_entry(filing: Filing | None) -> dict | None:
            if filing is None:
                return None
            return filing.to_dict() | {"in_corpus": filing.accession in parsed}

        companies.append({
            "ticker": ticker,
            "name": submissions["name"],
            "cik": cik,
            "cik_override": ticker in CIK_OVERRIDES,
            "sector": COMPANIES[ticker],
            "fiscal_year_end": submissions["fiscalYearEnd"],
            "latest_10k": latest.to_dict() | {"parsed": parsed[latest.accession]},
            "prior_10k": older_entry(prior),
            "older_10k": older_entry(older),
            "indexed_report_dates": sorted((f.report_date for f in corpus_filings), reverse=True),
            "revenue_concept": concept_map[ticker]["Revenue"],
            "revenue_status": concept_map[ticker]["revenue_status"],
            "unreported_concepts": sorted(k for k, v in concept_map[ticker].items() if v is None),
            "restatement_pairs": len(restated),
            "restatement_pairs_by_kind": dict(Counter(p["kind"] for p in restated)),
            "excluded_pairs": dict(Counter(p["kind"] for p in company_pairs if p["kind"] not in USABLE_KINDS)),
        })

    facts_all = pd.concat(fact_frames, ignore_index=True)
    facts_all.to_parquet(out_dir / "facts.parquet", index=False)
    _write_json(out_dir / "concept_map.json", concept_map)
    _write_json(out_dir / "restatement_pairs.json", pairs)
    _write_json(out_dir / "filings.json", companies)

    index_dir = out_dir / "index"
    if not index_is_current(index_dir, chunks, EMBED_MODEL):
        embed = cached_embed_fn(
            fastembed_fn(EMBED_MODEL),
            DiskCache(embed_cache_dir),
            EMBED_MODEL,
            progress=lambda done, total: print(f"embedded {done}/{total}", flush=True),
        )
        VectorIndex.build(chunks, embed, EMBED_MODEL).save(index_dir)

    usable = [p for p in pairs if p["kind"] in USABLE_KINDS]
    card = {
        "date_pulled": date.today().isoformat(),
        "companies": len(companies),
        "filings": sum(len(c["indexed_report_dates"]) for c in companies),
        "filings_per_company_searched": FILINGS_PER_COMPANY,
        "multi_year_indexed": {c["ticker"]: c["indexed_report_dates"] for c in companies if len(c["indexed_report_dates"]) > 1},
        "chunks": len(chunks),
        "embedding_model": EMBED_MODEL,
        "index_content_hash": content_hash(chunks, EMBED_MODEL),
        "fact_rows": len(facts_all),
        "fact_rows_latest_10k": int(facts_all["accession"].isin([c["latest_10k"]["accession"] for c in companies]).sum()),
        "restatement_pairs": len(usable),
        "restatement_pairs_by_kind": dict(Counter(p["kind"] for p in usable)),
        "restatement_pairs_by_company": dict(Counter(p["ticker"] for p in usable)),
        "restatement_companies": sorted({p["ticker"] for p in usable}),
        "rounding_pairs_excluded": sum(p["kind"] == "rounding" for p in pairs),
        "ambiguous_pairs_excluded": sum(p["kind"] == "ambiguous" for p in pairs),
        "revenue_fallback": [c["ticker"] for c in companies if c["revenue_status"] == "fallback"],
        "revenue_unmapped": [c["ticker"] for c in companies if c["revenue_status"] == "unmapped"],
        "cik_overrides": {t: c for t, c in CIK_OVERRIDES.items() if t in ciks},
        "exclusions": [],
        "sec_network_requests_this_run": client.network_requests,
    }
    _write_json(out_dir / "corpus_card.json", card)
    return card


def card_markdown(out_dir: Path = PROCESSED) -> str:
    """Render CORPUS.md §7 from the committed corpus files, so no number is typed by hand."""
    card = json.loads((out_dir / "corpus_card.json").read_text(encoding="utf-8"))
    companies = json.loads((out_dir / "filings.json").read_text(encoding="utf-8"))
    overrides = ", ".join(f"{t} → CIK {c} (D-014)" for t, c in card["cik_overrides"].items()) or "none"
    spot_path = out_dir / "spot_check.json"
    spot = json.loads(spot_path.read_text(encoding="utf-8")) if spot_path.exists() else []
    spot_matches = sum(r.get("verdict") == "match" for r in spot)
    multi_year = "; ".join(f"{t}: {', '.join(d)}" for t, d in card["multi_year_indexed"].items()) or "none"
    by_company = ", ".join(f"{t} {n}" for t, n in card["restatement_pairs_by_company"].items()) or "none"
    by_kind = ", ".join(f"{n} {k}" for k, n in card["restatement_pairs_by_kind"].items()) or "none"
    lines = [
        "| Field | Value |",
        "|---|---|",
        f"| Companies | {card['companies']} |",
        f"| Filings | {card['filings']} indexed: the latest 10-K for each company, plus the older "
        f"10-Ks that supply restated pairs ({multi_year}) |",
        f"| Chunks | {card['chunks']:,} ({card['embedding_model']}); index content hash "
        f"`{card['index_content_hash'][:12]}` |",
        f"| Facts | {card['fact_rows']:,} rows from original 10-Ks, all years; "
        f"{card['fact_rows_latest_10k']:,} from the latest 10-Ks |",
        f"| Restatement pairs found | {card['restatement_pairs']} across the last "
        f"{card['filings_per_company_searched']} 10-Ks ({by_company}; {by_kind}); "
        f"{card['rounding_pairs_excluded']} rounding-only and {card['ambiguous_pairs_excluded']} "
        "ambiguous pairs excluded |",
        f"| Revenue not mapped | {', '.join(card['revenue_unmapped']) or 'none'} "
        f"(fallback concept used: {', '.join(card['revenue_fallback']) or 'none'}) |",
        f"| Exclusions and why | {', '.join(card['exclusions']) or 'none'}. CIK overrides: {overrides} |",
        f"| Date pulled | {card['date_pulled']} |",
        f"| Spot check | {spot_matches}/{len(spot)} facts match the filing text for the right period "
        "(`data/processed/spot_check.json`) |",
        "",
        "Per company. Fiscal year-end is `MMDD` from SEC submissions data. Labelled share is the",
        "share of text inside Items 1, 1A, 7, 7A, 8 (the rest is indexed as `other`, D-018). The",
        "last column lists CORPUS §4 concepts with no annual value under that exact tag in the",
        "latest 10-K; the company may report the figure under another tag.",
        "",
        "| Ticker | Fiscal year-end | Latest 10-K period | Filed | Revenue concept | Labelled share | Standard concepts not tagged |",
        "|---|---|---|---|---|---|---|",
    ]
    for c in companies:
        latest = c["latest_10k"]
        revenue = c["revenue_concept"] or "**unmapped**"
        if c["revenue_status"] == "fallback":
            revenue += " **(fallback)**"
        lines.append(
            f"| {c['ticker']} | {c['fiscal_year_end']} | {latest['report_date']} | {latest['filed']} | "
            f"{revenue} | {latest['parsed']['labelled_share']:.0%} | {', '.join(c['unreported_concepts']) or '—'} |"
        )
    return "\n".join(lines)


if __name__ == "__main__":
    print(json.dumps(build(), indent=2))
