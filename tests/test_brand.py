"""Phase 7b brand files: logo, favicon, touch icon, link-preview image, README lockup."""

import json
import re
import struct
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
OUT = WEB / "out"
COBALT = ("#2D46C8", "#98B0FF")  # light and dark logo accent
LOGO_FILES = {WEB / "components" / "site" / "Logo.tsx", WEB / "app" / "icon.svg"}
SITE = "https://filingguard.vercel.app"
SVG_TAGS = {"svg", "title", "style", "rect", "path", "g"}  # brand SVGs hold nothing else: no metadata, desc or comments
built = pytest.mark.skipif(not (OUT / "index.html").exists(), reason="web/out not built; run `npm run build` in web/")


def png_info(path: Path) -> tuple[int, int, set[str]]:
    data = path.read_bytes()
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", data[16:24])
    chunks, i = set(), 8
    while i < len(data):
        (n,) = struct.unpack(">I", data[i:i + 4])
        chunks.add(data[i + 4:i + 8].decode())
        i += 12 + n
    return width, height, chunks


def test_cobalt_appears_only_in_the_logo():
    sources = [p for d in ("app", "components", "lib", "content") for p in (WEB / d).rglob("*")
               if p.is_file() and p.suffix in (".ts", ".tsx", ".css", ".json", ".svg")]
    for path in sources:
        text = path.read_text(encoding="utf-8").upper()
        if any(c in text for c in COBALT):
            assert path in LOGO_FILES, path.relative_to(ROOT)


def test_favicon_follows_the_colour_scheme():
    icon = (WEB / "app" / "icon.svg").read_text(encoding="utf-8")
    assert "prefers-color-scheme: dark" in icon
    assert all(c in icon.upper() for c in COBALT + ("#F7F7F5", "#0B0D10"))
    assert 'viewBox="0 0 32 32"' in icon and "filter" not in icon  # no glow on the site


@pytest.mark.parametrize("path, size", [(WEB / "app" / "apple-icon.png", (180, 180)), (WEB / "public" / "og.png", (1200, 630))])
def test_pngs_have_the_right_size_and_no_metadata(path, size):
    width, height, chunks = png_info(path)
    assert (width, height) == size
    assert not chunks & {"tEXt", "iTXt", "zTXt", "eXIf", "tIME"}, chunks


def test_brand_svgs_carry_no_metadata():
    for path in [WEB / "app" / "icon.svg", ROOT / "docs" / "images" / "filingguard-lockup-light.svg",
                 ROOT / "docs" / "images" / "filingguard-lockup-dark.svg"]:
        text = path.read_text(encoding="utf-8")
        assert set(re.findall(r"<([a-zA-Z][\w:-]*)", text)) <= SVG_TAGS, path.relative_to(ROOT)
        assert "<!--" not in text and re.findall(r"<title>([^<]*)</title>", text) == ["FilingGuard"], path.relative_to(ROOT)


def test_header_logo_keeps_its_accessible_name_and_overview_link():
    header = (WEB / "components" / "site" / "SiteHeader.tsx").read_text(encoding="utf-8")
    assert 'href={withBasis("/")} aria-label={copy.site.name}' in header and "<Logo " in header
    assert json.loads((WEB / "content" / "copy.json").read_text(encoding="utf-8"))["site"]["name"] == "FilingGuard"
    assert 'aria-hidden="true"' in (WEB / "components" / "site" / "Logo.tsx").read_text(encoding="utf-8")


def test_readme_lockup_switches_with_the_theme():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert readme.index("<picture>") < readme.index("# FilingGuard")
    for name in ("filingguard-lockup-dark.svg", "filingguard-lockup-light.svg"):
        assert f"docs/images/{name}" in readme and (ROOT / "docs" / "images" / name).exists()
    assert 'media="(prefers-color-scheme: dark)"' in readme and 'alt="FilingGuard"' in readme


@built
def test_built_page_has_absolute_share_tags():
    html = (OUT / "index.html").read_text(encoding="utf-8")
    share = json.loads((WEB / "content" / "copy.json").read_text(encoding="utf-8"))["site"]["share"]
    for prop in ("og:image", "twitter:image"):
        assert re.search(rf'(property|name)="{prop}" content="{re.escape(SITE)}/og\.png"', html), prop
    assert f'property="og:description" content="{share}"' in html
    assert 'property="og:title" content="FilingGuard"' in html
    assert 'name="twitter:card" content="summary_large_image"' in html
    assert re.search(r'rel="apple-touch-icon" href="/apple-icon\.png', html)
    assert (OUT / "og.png").exists()
