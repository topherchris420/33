"""The project home page (`_layouts/lab-home.html`, selected by `index.md`) is a static Jekyll
layout. These checks keep it self-contained, keep its links on pages GitHub Pages actually
publishes, and keep its static fallbacks in step with the evidence record's vocabulary."""

import re
from pathlib import Path

from evidence import vocabulary as V

ROOT = Path(__file__).resolve().parents[1]
LAYOUT = ROOT / "_layouts" / "lab-home.html"
HTML = LAYOUT.read_text(encoding="utf-8")
SCRIPTS = [ROOT / "lab/js/home.js", *sorted((ROOT / "lab/js/home").glob("*.js"))]
# GitHub Pages (jekyll-optional-front-matter) does not render Markdown files with these names;
# a folder's README.md is published as that folder's index page instead.
UNRENDERED_NAMES = {"README", "LICENSE", "LICENCE", "COPYING", "CODE_OF_CONDUCT", "CONTRIBUTING",
                    "ISSUE_TEMPLATE", "PULL_REQUEST_TEMPLATE"}


def _published(rel):
    """Whether a site path (relative to the base URL) is produced by the Pages build."""
    path = ROOT / rel
    if rel == "":
        return (ROOT / "index.md").is_file()
    if rel.endswith("/"):
        return any((path / name).is_file() for name in ("index.html", "index.md", "README.md"))
    if path.is_file():
        return True
    if rel.endswith(".html"):
        source = ROOT / (rel[: -len(".html")] + ".md")
        return source.is_file() and source.stem.upper() not in UNRENDERED_NAMES
    return False


def test_home_loads_only_same_origin_scripts_and_styles():
    external = re.compile(r"<(?:script|link)\b[^>]*(?:src|href)=\"(?:https?:)?//", re.I)
    assert not external.search(HTML)


def test_every_site_link_in_the_home_layout_is_published():
    targets = re.findall(r"\{\{\s*'/([^'#]*)(?:#[^']*)?'\s*\|\s*(?:relative|absolute)_url\s*\}\}", HTML)
    assert targets, "expected relative_url links in the layout"
    missing = sorted({t for t in targets if not _published(t)})
    assert not missing, missing


def test_in_page_anchors_and_icons_resolve():
    ids = set(re.findall(r'\bid="([^"]+)"', HTML))
    anchors = set(re.findall(r'href="#([^"]+)"', HTML))
    assert anchors <= ids, sorted(anchors - ids)
    symbols = {i for i in ids if i.startswith("i-")}
    used = {a for a in anchors if a.startswith("i-")}
    for script in SCRIPTS:
        used |= set(re.findall(r"#(i-[a-z-]+)", script.read_text(encoding="utf-8")))
    assert used <= symbols, sorted(used - symbols)


def test_home_keeps_the_engineering_brief_and_the_anchor_other_pages_link_to():
    assert "{{ content" in HTML
    assert 'id="research-record"' in HTML
    assert "/#research-record" in (ROOT / "film.html").read_text(encoding="utf-8")


def test_static_gate_track_matches_the_record_vocabulary():
    # The script rebuilds the track from lab/data/evidence.json; the static list is the
    # no-script fallback and must name the same gates in the same order.
    assert re.findall(r'data-gate="([a-z_]+)"', HTML) == [key for key, _ in V.GATES]


def test_home_states_the_validation_boundary_up_front():
    hero = HTML.split('id="status"', 1)[0]
    assert "Bench-validation prototype · not flight-tested" in hero
    assert "nothing here can command hardware" in hero
