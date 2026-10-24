"""Deploy step of Phase 6b: one origin serves the API and the static export; the image holds no secrets."""

import ast
import re
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from filingguard.api.live import get_target_agent
from filingguard.api.main import create_app

ROOT = Path(__file__).resolve().parents[1]
API_DIR = ROOT / "src" / "filingguard" / "api"
SERVE_IMPORTS = ("fastapi", "starlette", "pydantic", "filingguard.api")


@pytest.fixture
def export(tmp_path):
    """A minimal stand-in for `web/out`: the pages the dashboard has, plus 404.html."""
    out = tmp_path / "out"
    for page in ("", "results", "items", "item", "method", "limitations"):
        folder = out / page
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "index.html").write_text(f"<html><body>page {page or 'overview'}</body></html>", encoding="utf-8")
    (out / "404.html").write_text("<html><body>not found page</body></html>", encoding="utf-8")
    return out


@pytest.fixture
def client(export):
    return TestClient(create_app(live_target=False, static_dir=export))


def test_pages_are_served_from_the_export(client):
    for path, text in (("/", "page overview"), ("/results/", "page results"), ("/item/?id=FG-0001", "page item"),
                       ("/limitations/", "page limitations")):
        response = client.get(path)
        assert response.status_code == 200 and text in response.text, path
        assert response.headers["content-type"].startswith("text/html")


def test_page_without_slash_redirects_to_folder(client):
    response = client.get("/method", follow_redirects=False)
    assert response.status_code in (301, 307) and response.headers["location"].endswith("/method/")


def test_unknown_page_gets_the_export_404(client):
    response = client.get("/no-such-page/")
    assert response.status_code == 404 and "not found page" in response.text


def test_api_still_works_with_the_export_mounted(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/api/summary").status_code == 200
    items = client.get("/api/items")
    assert items.status_code == 200 and items.headers["content-type"].startswith("application/json")


def test_unknown_api_path_is_a_json_404_not_a_page(client):
    for method in ("get", "post"):
        response = getattr(client, method)("/api/nope")
        assert response.status_code == 404, method
        assert response.headers["content-type"].startswith("application/json")
        assert "not found page" not in response.text


def test_api_works_without_an_export(tmp_path):
    client = TestClient(create_app(live_target=False, static_dir=tmp_path / "missing"))
    assert client.get("/api/health").status_code == 200
    assert client.get("/").status_code == 404


def test_large_api_responses_are_gzipped(client):
    response = client.get("/api/items", headers={"Accept-Encoding": "gzip"})
    assert response.headers.get("content-encoding") == "gzip"


def test_live_route_is_absent_by_default(export, monkeypatch):
    monkeypatch.delenv("FILINGGUARD_LIVE_TARGET", raising=False)
    client = TestClient(create_app(static_dir=export))
    response = client.post("/api/target/answer", json={"question": "Revenue?", "company": "AAPL"})
    assert response.status_code == 404 and response.json()["detail"] == "no API route /api/target/answer"


@pytest.mark.parametrize("value, on", [("1", True), ("0", False), ("", False), ("true", False), ("yes", False)])
def test_only_exactly_1_switches_the_live_route_on(export, monkeypatch, value, on):
    monkeypatch.setenv("FILINGGUARD_LIVE_TARGET", value)
    app = create_app(static_dir=export)
    app.dependency_overrides[get_target_agent] = lambda: None  # an empty question never reaches the agent
    response = TestClient(app).post("/api/target/answer", json={"question": "", "company": "AAPL"})
    assert response.status_code == (422 if on else 404)


def test_default_app_imports_no_agent_llm_or_data_code():
    """Importing the served app in a clean process loads none of the pipeline."""
    code = ("import os, sys; os.environ.pop('FILINGGUARD_LIVE_TARGET', None); import filingguard.api.main; "
            "print(sorted(m for m in sys.modules if m.startswith(('filingguard.agents', 'filingguard.llm', "
            "'filingguard.data', 'filingguard.eval', 'google', 'fastembed', 'pandas'))))")
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, cwd=ROOT, check=True)
    assert result.stdout.strip() == "[]"


def test_served_api_modules_need_only_the_serve_requirements():
    """Every API module but live.py imports only the standard library and requirements-serve.txt."""
    for path in API_DIR.glob("*.py"):
        if path.name == "live.py":
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ImportFrom) and node.level == 0:
                names = [node.module or ""]
            elif isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            else:
                continue
            for name in names:
                top = name.split(".")[0]
                assert top in sys.stdlib_module_names or name.startswith(SERVE_IMPORTS), f"{path.name}: {name}"


def test_serve_requirements_are_pinned():
    lines = [l for l in (ROOT / "requirements-serve.txt").read_text(encoding="utf-8").splitlines()
             if l.strip() and not l.startswith("#")]
    assert lines and all(re.fullmatch(r"[a-z0-9-]+==[0-9.]+", l) for l in lines), lines
    assert {l.split("==")[0] for l in lines} >= {"fastapi", "uvicorn", "pydantic"}


def test_dockerignore_keeps_secrets_and_data_out():
    rules = [l.strip() for l in (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
             if l.strip() and not l.startswith("#")]
    assert rules[0] == "*"  # allowlist
    allowed = {r[1:] for r in rules if r.startswith("!")}
    # Exactly what the image needs; local files, data/ and secrets can never be let back in.
    assert allowed == {"Dockerfile", "pyproject.toml", "requirements-serve.txt", "src/", "results/summary.json",
                       "results/dashboard/", "web/"}, allowed
    assert {"**/.env", "**/.env.*", "web/node_modules", "web/out"} <= set(rules)


def test_dockerfile_has_no_secrets_and_pinned_bases():
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith(("ENV", "ARG")):
            assert not re.search(r"KEY|TOKEN|SECRET|PASSWORD|GEMINI|LIVE_TARGET", line, re.I), line
        if line.startswith("FROM"):
            assert re.match(r"FROM [a-z]+:\d+\.\d+\.\d+-", line), line
        if line.startswith("COPY") and "--from" not in line:
            assert "data/" not in line and ".env" not in line, line
    assert "USER app" in text


def test_env_example_documents_the_serve_settings():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "FILINGGUARD_LIVE_TARGET=0" in text and "FILINGGUARD_WEB" in text
