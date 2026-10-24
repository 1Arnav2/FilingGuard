"""Phase 6d (D-079): the public site is a static export that reads results/ at build time and calls no API."""

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from filingguard.api.main import create_app

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
OUT = WEB / "out"
RESULTS = ROOT / "results"
SOURCE_DIRS = ("app", "components", "lib", "scripts", "content")
NODE = shutil.which("node")
needs_node = pytest.mark.skipif(NODE is None, reason="node is not installed")


def web_sources():
    """Every source file of the site (not dependencies, builds or generated data)."""
    files = [WEB / "next.config.ts", WEB / "package.json"]
    for d in SOURCE_DIRS:
        files += [p for p in (WEB / d).rglob("*") if p.is_file() and p.suffix in (".ts", ".tsx", ".mjs", ".js", ".json")]
    return files


def presets():
    return [p["filters"] for p in json.loads((WEB / "content" / "copy.json").read_text(encoding="utf-8"))["items"]["presets"]]


@pytest.fixture(scope="module")
def synced(tmp_path_factory):
    out = tmp_path_factory.mktemp("generated")
    subprocess.run([NODE, str(WEB / "scripts" / "sync-results.mjs"), str(out)], check=True, capture_output=True)
    return out


@needs_node
def test_build_data_is_the_results_files_unchanged(synced):
    summary = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))
    meta = json.loads((RESULTS / "dashboard" / "meta_v1.json").read_text(encoding="utf-8"))
    items = [json.loads(l) for l in (RESULTS / "dashboard" / "items_v1.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert json.loads((synced / "summary.json").read_text(encoding="utf-8")) == {**summary, "generated_from": "results/summary.json"}
    assert json.loads((synced / "meta.json").read_text(encoding="utf-8")) == {**meta, "generated_from": "results/dashboard/meta_v1.json"}
    assert json.loads((synced / "items.json").read_text(encoding="utf-8")) == items
    rows = json.loads((synced / "rows.json").read_text(encoding="utf-8"))
    assert [r["id"] for r in rows] == [i["id"] for i in items]
    assert all(r["outcomes"] == i["outcomes"] for r, i in zip(rows, items))


@needs_node
def test_page_filtering_matches_the_api(synced):
    """Every preset, search, sort and paging the Items page offers gives the API's exact page, on both bases."""
    queries = []
    for basis in ("corrected", "as_scored"):
        for filters in presets() + [{}, {"q": "aapl"}, {"q": "FG-01"}, {"q": "zzz"}, {"verdict": "block"},
                                    {"outcome": "missed", "condition": "baseline"}, {"label": "wrong_number"},
                                    {"corrected": "false", "attack_type": "control"}, {"page": 2, "page_size": 25}]:
            queries.append({**filters, "basis": basis, "page_size": filters.get("page_size", 500)})
        for sort in ("id", "company", "attack_type", "baseline", "verdict", "treatment"):
            for order in ("asc", "desc"):
                queries.append({"basis": basis, "sort": sort, "order": order, "page_size": 500})
    script = ("import { readFileSync } from 'node:fs'; import { queryItems } from './lib/query.ts';"
              f"const rows = JSON.parse(readFileSync({json.dumps(str(synced / 'rows.json'))}, 'utf-8'));"
              "const qs = JSON.parse(readFileSync(0, 'utf-8'));"
              "process.stdout.write(JSON.stringify(qs.map((q) => queryItems(rows, q))));")
    result = subprocess.run([NODE, "--input-type=module", "-e", script], input=json.dumps(queries), cwd=WEB,
                            capture_output=True, text=True, encoding="utf-8", check=True)
    pages = json.loads(result.stdout)
    client = TestClient(create_app(live_target=False, static_dir=WEB / "no-export"))
    for query, page in zip(queries, pages):
        assert page == client.get("/api/items", params=query).json(), query


def test_site_source_calls_no_api():
    # `/api` as a URL in a string; file paths such as src/filingguard/api/routes.py in comments are fine.
    banned = re.compile(r"\bfetch\(|[\"'`]/api\b|localhost|127\.0\.0\.1|:8000|FILINGGUARD_API|target/answer")
    for path in web_sources():
        hits = banned.findall(path.read_text(encoding="utf-8"))
        assert not hits, (path.relative_to(ROOT), hits)


def test_no_environment_variable_or_public_secret_in_web():
    """The site reads no environment variable at all, so none can hold a key; no NEXT_PUBLIC_ variable exists."""
    for path in web_sources():
        text = path.read_text(encoding="utf-8")
        assert "process.env" not in text and "NEXT_PUBLIC_" not in text, path.relative_to(ROOT)
    assert not [p.name for p in WEB.glob(".env*")]


def test_static_export_only_no_server_features():
    config = (WEB / "next.config.ts").read_text(encoding="utf-8")
    assert 'output: "export"' in config
    assert not re.search(r"\b(rewrites|redirects|headers)\s*\(", config)
    assert not (WEB / "middleware.ts").exists() and not (WEB / "middleware.js").exists()
    assert not (WEB / "app" / "api").exists()
    assert not list((WEB / "app").rglob("route.ts")) and not list((WEB / "app").rglob("route.js"))
    for path in web_sources():
        assert '"use server"' not in path.read_text(encoding="utf-8"), path.relative_to(ROOT)


def test_no_live_target_route_in_the_static_site():
    assert not list((WEB / "app").rglob("*target*"))
    for path in web_sources():
        assert "target/answer" not in path.read_text(encoding="utf-8")


@pytest.mark.skipif(not (OUT / "index.html").exists(), reason="web/out not built; run `npm run build` in web/")
def test_built_output_fetches_no_api_or_local_server():
    """The framework runtime contains the bare words, so the scan looks for addresses and API paths."""
    banned = re.compile(r"/api/[a-z]|https?://localhost|127\.0\.0\.1|:8000\b|FILINGGUARD|target/answer|GEMINI|API_KEY|NEXT_PUBLIC_")
    for path in OUT.rglob("*"):
        if path.suffix in (".html", ".txt", ".js", ".json", ".css"):
            hits = banned.findall(path.read_text(encoding="utf-8", errors="ignore"))
            assert not hits, (path.relative_to(OUT), hits[:3])
    for path in (OUT / "_next" / "static" / "chunks" / "app").rglob("*.js"):
        assert "localhost" not in path.read_text(encoding="utf-8") and "/api" not in path.read_text(encoding="utf-8")


@pytest.mark.skipif(not (OUT / "index.html").exists(), reason="web/out not built; run `npm run build` in web/")
def test_every_item_has_its_own_static_page():
    ids = [json.loads(l)["id"] for l in (RESULTS / "dashboard" / "items_v1.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    assert len(ids) == 210
    for item_id in ids:
        page = OUT / "item" / item_id / "index.html"
        assert page.exists() and item_id in page.read_text(encoding="utf-8"), item_id
    assert not (OUT / "api").exists()
