"""The website builds from the repo data, matches the model, and keeps the repo's rules."""

import json
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from follow_me import bom
from follow_me.replay import trace
from follow_me.website import MARKER, build, costs_data, markdown_section, replay_data

REPO = Path(__file__).resolve().parents[1]
PAGES = ("index.html", "replay.html", "costs.html")
# Stricter than the group-order check: a package@version string is not an email.
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(\.[\w-]+)*\.[A-Za-z]{2,}\b")
PHONE = re.compile(r"\(?\b\d{3}\)?[-. ]\d{3}[-. ]\d{4}\b")


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("site") / "out"
    build(out)
    return out


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in ("href", "src") and value:
                self.links.append(value)


def test_site_builds_every_page_and_its_data(site):
    for name in (*PAGES, "assets/style.css", "assets/common.js", "data/costs.json",
                 "data/replay-example.json", "data/replay.example.json", "data/build.json", ".nojekyll"):
        assert (site / name).is_file(), name
    index = (site / "index.html").read_text(encoding="utf-8")
    assert "<!-- build:" not in index
    assert "Built and tested" in index  # the README status section was filled in


def test_cost_data_matches_the_cost_model():
    data = costs_data()
    materials = bom.load_materials()
    catalog = bom.load_catalog(bom.DEFAULT_CATALOG, materials)
    _, raw = bom.load_passes()
    passes = {p.id: p for p in bom.resolve(catalog, raw)}
    assert data["drone_counts"] == list(bom.DRONE_COUNTS)
    assert [p["id"] for p in data["passes"]] == list(passes)
    for row in data["passes"]:
        t = bom.totals(catalog, passes[row["id"]].items, materials)
        assert row["core"] == [t.core_low, t.core_high]
        assert row["cash_min_orders"] == list(bom.cash_outlay(catalog, passes[row["id"]].items, materials))
        assert row["per_drone"][0] == row["cash"][0]  # one drone: the cash is the cost per drone
    flying = {p["id"]: p["flying"] for p in data["passes"]}
    assert flying["pass3_bench_first"] is False and flying["pass5_made_tag"] is False
    assert flying["pass0_retail_autopilot"] is True and flying["pass10_factory_and_lab"] is True


def test_replay_data_is_the_trace_of_the_example_log():
    log = json.loads((REPO / "examples" / "replay.example.json").read_text(encoding="utf-8"))
    assert replay_data() == trace(log)


def test_every_local_link_and_import_resolves(site):
    for page in PAGES:
        parser = _Links()
        parser.feed((site / page).read_text(encoding="utf-8"))
        for link in parser.links:
            if re.match(r"[a-z]+:", link) or link.startswith("#"):
                continue
            target = site / link.split("#")[0].split("?")[0]
            assert target.is_file(), f"{page} links to missing {link}"
    for script in (site / "assets").glob("*.js"):
        for name in re.findall(r'from "\./([\w.-]+)"', script.read_text(encoding="utf-8")):
            assert (site / "assets" / name).is_file(), f"{script.name} imports missing {name}"


def test_site_has_no_email_or_phone_like_text(site):
    for path in site.rglob("*"):
        if path.suffix in (".html", ".js", ".json", ".css"):
            text = path.read_text(encoding="utf-8")
            assert not EMAIL.search(text), f"email-like text in {path.name}"
            assert not PHONE.search(text), f"phone-like text in {path.name}"


def _keys(value):
    if isinstance(value, dict):
        for key, inner in value.items():
            yield key
            yield from _keys(inner)
    elif isinstance(value, list):
        for inner in value:
            yield from _keys(inner)


def test_site_ships_no_place_data(site):
    names = {p.name for p in site.rglob("*")}
    assert not any(n.startswith("places") or n.endswith(".local.json") for n in names)
    for path in (site / "data").glob("*.json"):
        keys = set(_keys(json.loads(path.read_text(encoding="utf-8"))))
        assert not keys & {"lat", "lon", "latitude", "longitude"}, f"coordinates in {path.name}"


def test_pages_carry_the_honest_framing(site):
    for page in PAGES:
        text = (site / page).read_text(encoding="utf-8")
        assert "hobby and learning project" in text.lower(), page
        assert "written by AI coding agents" in text, page
        assert "No review of the code by the owner is recorded" in text, page
    assert "Nothing has flown" in (site / "index.html").read_text(encoding="utf-8")


def test_builder_replaces_only_a_directory_it_made(tmp_path):
    other = tmp_path / "other"
    other.mkdir()
    (other / "keep.txt").write_text("not a site", encoding="utf-8")
    with pytest.raises(ValueError, match="not replacing"):
        build(other)
    assert (other / "keep.txt").exists()

    out = tmp_path / "site"
    build(out)
    (out / "stale.txt").write_text("from an old build", encoding="utf-8")
    assert (out / MARKER).exists()
    build(out)
    assert not (out / "stale.txt").exists()


def test_markdown_section_converts_links_bold_code_and_lists():
    md = "# T\n\n## Status\n\n- **Built:** see [the plan](docs/plan.md) & `code`\n- [site](https://example.org)\n\nA paragraph\nover two lines.\n\n## Next\n\nignored\n"
    out = markdown_section(md, "Status")
    assert out.startswith("<ul><li><strong>Built:</strong>")
    assert 'href="https://github.com/dylanstechmann/follow-me-drone-agent/blob/main/docs/plan.md"' in out
    assert "&amp; <code>code</code>" in out
    assert 'href="https://example.org"' in out
    assert "<p>A paragraph over two lines.</p>" in out
    assert "ignored" not in out
    with pytest.raises(ValueError):
        markdown_section(md, "Missing")
