"""Facts check (D-061, owner's request): for every company and metric the verifier can look up, does
the XBRL fact it would use appear on a printed table row for that metric in the filing?

Dev only, no model calls, no gold labels. The filings are the dev items' filings: the 10-K a dev
question names, else the company's latest corpus 10-K. The verifier is not changed; its own lookup
(`FactStore.values`), row-label rule (`names_metric`) and number reading (`holds`) are reused, so
the check sees what the verifier sees.

Usage: python -m filingguard.eval.facts_check
"""

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from filingguard.agents.verifier.facts import FactStore
from filingguard.agents.verifier.lexicon import METRICS
from filingguard.agents.verifier.question import read_question
from filingguard.agents.verifier.verifier import names_metric
from filingguard.eval.dev_report import load_dev
from filingguard.eval.dev_run import PROCESSED

OUT = Path("results/verifier/facts_check_dev_v1.json")
_CELL = re.compile(r"(\()?\s*-?\$?\s*(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)")


def printed_exactly(line: str, value: float, per_share: bool) -> bool:
    """`line` prints `value` exactly at the precision shown: per-share as printed, amounts as a table
    cell in millions or thousands. Stricter than the verifier's 0.5% tolerance, which lets unrelated
    rows match by coincidence."""
    for m in _CELL.finditer(line):
        n = float(m.group(2).replace(",", ""))
        decimals = len(m.group(2).split(".")[1]) if "." in m.group(2) else 0
        if per_share and not decimals:
            continue  # a per-share amount is printed with cents; a bare integer is a page or a count
        for scale in ((1.0,) if per_share else (1e6, 1e3)):
            if abs(n * scale - abs(value)) <= scale * 10 ** -decimals / 2:
                return True
    return False


def label_text(line: str) -> str:
    """Filings print a curly apostrophe ("shareholders’ equity"); the verifier's row-label rule
    matches only a straight one, so the check reads both."""
    return line.replace("’", "'")


def dev_filings(store: FactStore) -> dict[tuple[str, str], int]:
    """(ticker, accession) -> the fiscal year that filing reports, for every dev item's filing."""
    items, _, _ = load_dev()
    out = {}
    for it in items:
        ask = read_question(it["question"], it["company"], store)
        filings = store.filings.get(it["company"], [])
        f = next((x for x in filings if x["accession"] == ask.accession), None) or max(filings, key=lambda x: x["fy"])
        out[(it["company"], f["accession"])] = f["fy"]
    return out


def table_lines(accessions: set[str]) -> dict[str, list[str]]:
    lines: dict[str, list[str]] = {a: [] for a in accessions}
    with (PROCESSED / "index" / "chunks.jsonl").open(encoding="utf-8") as f:
        for row in f:
            c = json.loads(row)
            if c["accession"] in lines:
                lines[c["accession"]] += [ln for ln in c["text"].splitlines() if "|" in ln]
    return lines


def check() -> dict[str, Any]:
    store = FactStore()
    filings = dev_filings(store)
    lines = table_lines({a for _, a in filings})
    rows = []
    for (ticker, accession), fy in sorted(filings.items()):
        for key, m in METRICS.items():
            facts = store.values(ticker, key, fy, accession)
            named = [ln for ln in lines[accession] if names_metric(label_text(ln), m.phrases)]
            per_share = key.startswith("eps")
            if not facts:
                status = "no_fact"
            elif not named:
                status = "no_printed_row"
            elif any(printed_exactly(ln, v, per_share) for ln in named for v in facts):
                status = "match"
            else:
                status = "differs"
            elsewhere = [] if status in ("match", "no_fact") else [
                ln[:160] for ln in lines[accession] if any(printed_exactly(ln, v, per_share) for v in facts)][:4]
            rows.append({"ticker": ticker, "accession": accession, "fy": fy, "metric": key, "facts": facts,
                         "status": status, "rows": [ln[:160] for ln in named[:4]] if status == "differs" else [],
                         "fact_printed_on": elsewhere})
    curly = [r for r in rows if r["status"] != "no_fact" and r["metric"] == "equity"]
    missed = sum(1 for r in curly if not any(names_metric(ln, METRICS["equity"].phrases)
                                             for ln in lines[r["accession"]]) and r["status"] != "no_printed_row")
    return {"filings": len(filings), "pairs": len(rows), "status_counts": dict(Counter(r["status"] for r in rows)),
            "equity_rows_found_only_with_curly_apostrophe": missed, "rows": rows}


def main() -> None:
    out = check()
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(out["filings"], out["pairs"], out["status_counts"])
    for r in out["rows"]:
        if r["status"] in ("differs", "no_printed_row"):
            print(r["status"], r["ticker"], r["fy"], r["metric"], [f"{v:,.0f}" if abs(v) > 100 else v for v in r["facts"]])
            for ln in r["fact_printed_on"]:
                print("   printed on:", ln)


if __name__ == "__main__":
    main()
