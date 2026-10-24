"""Every result number in README.md is bound to results/ (Phase 7a), the same rule as the dashboard."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
SUMMARY = json.loads((ROOT / "results" / "summary.json").read_text(encoding="utf-8"))
META = json.loads((ROOT / "results" / "dashboard" / "meta_v1.json").read_text(encoding="utf-8"))
HEADLINE = json.loads((ROOT / "web" / "content" / "headline.json").read_text(encoding="utf-8"))
# Sections whose numbers are results; setup sections hold versions and ports, not results.
CHECKED = ("FilingGuard", "What it does", "Results", "The main finding", "How it was kept honest", "Limitations")
REFERENCE = re.compile(r"\b(?:D|H)-\d{3}\b|\bFG-\d{4}\b|\b10-Ks?\b|\b\d{4}-\d{2}-\d{2}\b|overview-light-1440")
NUMBER = re.compile(r"\$?\d[\d,.]*%?")
BASES, CONDITIONS = ("corrected", "as_scored"), ("baseline", "treatment")
CONDITION_NAMES = {"baseline": "Without verifier", "treatment": "With verifier"}
BASIS_NAMES = {"corrected": "Corrected", "as_scored": "As scored"}
STATUS = {"met": "Met", "not met": "Not met", "not testable": "Not testable"}


def pct(rate: float) -> str:
    return f"{rate * 100:.1f}%"


def kn(r: dict) -> str:
    return f"{r['k']} of {r['n']}"


def sections() -> dict[str, str]:
    parts = re.split(r"^#{1,2} (.+)$", README, flags=re.M)
    return {parts[i].strip(): parts[i + 1] for i in range(1, len(parts), 2)}


def bound_values() -> set[str]:
    """Every result number the README may show, formatted as it is shown."""
    s, m = SUMMARY, META
    bars, seeded = s["pass_bars"], s["seeded_errors"]
    values = {str(s["n_items"]), str(len(m["attack_types_test"])), str(m["companies"]), str(m["split"]["dev"]),
              str(m["split"]["test"]), str(m["corrections"]["corrected"]), f"${s['spend']['total_usd']:.2f}",
              f"${s['spend']['cap_usd']:.0f}", f"{round(seeded['macro_detection_T1_T3_T4_T5_T6_quote_off'] * 100)}%",
              pct(seeded["macro_detection_T1_T3_T4_T5_T6_quote_off"])}
    for basis in BASES:
        for condition in CONDITIONS:
            values |= {str(v) for v in s["conditions"][basis][condition]["outcomes"].values()} | {"0"}
        b = bars[basis]
        u = b["unsupported_claim_rate_falls_p_lt_0.05"]
        values |= {str(u["baseline_unsupported"]), str(u["exact_two_sided_p"]), str(u["best_possible_p_if_every_one_blocked"])}
        a = b["abstain_rate_controls_le_10pct_treatment"]
        values |= {pct(a["rate"]), pct(a["baseline"]["rate"]), *kn(a).split(" of ")}
        p = b["verifier_precision_ge_0.85"]
        values |= {pct(p["precision"]["rate"]), *kn(p["precision"]).split(" of "), *kn(p["recall"]).split(" of ")}
        f = b["test_set_fault_rate_le_5pct"]
        values |= {pct(f["rate"]), *kn(f).split(" of ")}
        fb = seeded["false_block_rate"][basis]
        values |= {pct(fb["rate"]), *kn(fb).split(" of ")}
    h = s["owner_handcheck_test"]["random_30_agreement_with_as_scored"]
    values |= {str(h["k"]), str(h["n"]), str(s["conditions"]["corrected"]["baseline"]["unparseable"]),
               str(s["latency"]["run"]), str(s["latency"]["sample"])}
    values |= {"2", "10"}  # the owner's offline detector check: "2 of 10" (summary limitation 4)
    # Bar thresholds, from the summary's key names and fields as web/lib/bars.ts reads them.
    for key in bars["corrected"]:
        _, p, value, is_pct = re.match(r"^(.*?)_(p_)?(?:lt|le|ge)_([\d.]+?)(pct)?(?:_[a-z]+)?$", key).groups()
        values.add(value if p else f"{value}%" if is_pct else f"{float(value) * 100:g}%")
    values |= {f"{seeded['macro_threshold'] * 100:g}%", f"{seeded['false_block_rate']['threshold'] * 100:g}%"}
    return values


def test_headline_is_the_sites_sentence():
    assert HEADLINE["text"] in README


def test_every_result_number_is_bound_to_results():
    allowed, found = bound_values(), sections()
    assert set(CHECKED) <= set(found), set(CHECKED) - set(found)
    for name in CHECKED:
        text = REFERENCE.sub("", found[name])
        text = re.sub(r"^\s*\d+\.\s", "", text, flags=re.M)  # numbered-list markers
        for number in NUMBER.findall(text):
            assert number.rstrip(".,") in allowed, (name, number)


def test_outcomes_table_matches_summary():
    for basis in BASES:
        for condition in CONDITIONS:
            o = SUMMARY["conditions"][basis][condition]["outcomes"]
            row = (f"| {BASIS_NAMES[basis]} | {CONDITION_NAMES[condition]} | {o.get('correct', 0)} | "
                   f"{o.get('missed', 0)} | {o.get('unsupported', 0)} |")
            assert row in README, row
            assert sum(o.values()) == SUMMARY["n_items"]


def test_pass_bar_statuses_match_summary():
    rows = {line.split("|")[1].strip(): line for line in README.splitlines() if line.startswith("| ") and "(" in line}
    bars, seeded = SUMMARY["pass_bars"], SUMMARY["seeded_errors"]
    expected = {
        "Unsupported claims fall significantly (p < 0.05)": [bars[b]["unsupported_claim_rate_falls_p_lt_0.05"]["status"] for b in BASES],
        "Control questions left unanswered (≤ 10%, with the verifier)": [bars[b]["abstain_rate_controls_le_10pct_treatment"]["status"] for b in BASES],
        "Verifier precision (≥ 85%)": [bars[b]["verifier_precision_ge_0.85"]["status"] for b in BASES],
        "Test-set fault rate (≤ 5%)": [bars[b]["test_set_fault_rate_le_5pct"]["status"] for b in BASES],
        "Planted errors caught (≥ 80%)": [seeded["macro_status"], None],
        "Correct answers wrongly blocked (≤ 5%)": [seeded["false_block_rate"][b]["status"] for b in BASES],
    }
    for title, statuses in expected.items():
        cells = [c.strip() for c in rows[title].split("|")[2:4]]
        for cell, status in zip(cells, statuses):
            assert cell == "—" if status is None else cell.startswith(f"{STATUS[status]}:"), (title, cell, status)


def test_readme_names_no_key_and_links_the_site_and_screenshot():
    assert not re.search(r"AIza[0-9A-Za-z_-]{20,}|GEMINI_API_KEY\s*=\s*\S", README)
    assert "https://filingguard.vercel.app" in README
    assert (ROOT / "docs" / "images" / "overview-light-1440.png").exists()
    assert "](docs/images/overview-light-1440.png)" in README
